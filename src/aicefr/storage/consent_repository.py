"""Persistence for research participation consent. Implements FR-01 and FR-35.

Why this is a separate collection and not a field on `account`:

Consent is not a property of a person, it is an *event* that happened at a
point in time, under a specific wording. A student who signs version `dt-v1`,
withdraws, then signs `dt-v2` has three facts worth keeping, and a boolean
field can only remember the last one. The rule the university ethics guidance
cares about -- "you must be able to show what the participant agreed to, at the
time they agreed to it" -- is unanswerable with a boolean.

So every signature and every withdrawal is a document, and the version of the
text is copied INTO it. Editing the consent page later never rewrites what
somebody already agreed to.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from pathlib import Path

from pymongo import ASCENDING, DESCENDING

from aicefr.storage.db import MongoStore, ensure_indexes
from aicefr.storage.db import now_iso as _now

# The wording currently shown on the consent screen. Bump this when the text
# changes in a way that alters what the participant is agreeing to -- not for
# typos. `docs/plan/KE_HOACH_KHAO_SAT.md` phụ lục A holds the text itself.
CURRENT_CONSENT_VERSION = "dt-v1"

INDEXES = {"consent": [(("consent_id",), True), (("account_id", "signed_at"), False)]}


@dataclass(frozen=True)
class Consent:
    """One signature, exactly as it was given."""

    consent_id: str
    account_id: str
    consent_version: str
    audio_storage_allowed: bool
    research_use_allowed: bool
    signed_at: str
    withdrawn_at: str | None

    @property
    def active(self) -> bool:
        return self.withdrawn_at is None

    @property
    def may_submit(self) -> bool:
        """Recording may only be stored while an unwithdrawn signature allows it."""
        return self.active and self.audio_storage_allowed


class ConsentRepository(MongoStore):
    """The consent collection: one document per signature."""

    def __init__(self, db_path: str | Path = "aicefr.db") -> None:
        self.db_path = str(db_path)
        ensure_indexes(self.db, INDEXES, "consent")

    # ---------- write ----------

    def sign(
        self,
        account_id: str,
        *,
        audio_storage_allowed: bool,
        research_use_allowed: bool,
        consent_version: str = CURRENT_CONSENT_VERSION,
    ) -> Consent:
        """Record a new signature, withdrawing any signature still standing.

        Signing again is how a participant changes their mind in the permissive
        direction (for example: they first refused research use, then allowed
        it). Keeping the old document withdrawn rather than updating it
        preserves the history.
        """
        now = _now()
        cid = uuid.uuid4().hex[:12]
        consents = self.col("consent")
        consents.update_many(
            {"account_id": account_id, "withdrawn_at": None}, {"$set": {"withdrawn_at": now}}
        )
        consents.insert_one(
            {
                "consent_id": cid,
                "account_id": account_id,
                "consent_version": consent_version,
                "audio_storage_allowed": int(audio_storage_allowed),
                "research_use_allowed": int(research_use_allowed),
                "signed_at": now,
                "withdrawn_at": None,
            }
        )
        return Consent(
            consent_id=cid,
            account_id=account_id,
            consent_version=consent_version,
            audio_storage_allowed=audio_storage_allowed,
            research_use_allowed=research_use_allowed,
            signed_at=now,
            withdrawn_at=None,
        )

    def withdraw(self, account_id: str) -> bool:
        """Withdraw the standing signature. True when something was withdrawn.

        Deliberately does NOT delete recordings here. Deletion is a separate,
        auditable step (`retention.py` and the admin erase flow): a student who
        withdraws at 23:00 should not have the system silently destroying data
        that a teacher is halfway through reviewing. What withdrawal does
        immediately is stop any further use.
        """
        done = self.col("consent").update_many(
            {"account_id": account_id, "withdrawn_at": None}, {"$set": {"withdrawn_at": _now()}}
        )
        return done.modified_count > 0

    # ---------- read ----------

    def current(self, account_id: str) -> Consent | None:
        """The signature standing right now, or None."""
        row = self.col("consent").find_one(
            {"account_id": account_id, "withdrawn_at": None},
            sort=[("signed_at", DESCENDING), ("_id", DESCENDING)],
        )
        return self._to_consent(row) if row else None

    def history(self, account_id: str) -> list[Consent]:
        """Every signature and withdrawal, oldest first. Used by the data export."""
        rows = (
            self.col("consent")
            .find({"account_id": account_id})
            .sort([("signed_at", ASCENDING), ("_id", ASCENDING)])
        )
        return [self._to_consent(r) for r in rows]

    def accounts_allowing_research(self) -> set[str]:
        """Account ids whose standing signature allows research use.

        The research export asks this question, not the other way round: it is
        easier to prove "we only exported what this set allows" than to prove a
        filter spread across several queries never leaked a row.
        """
        rows = self.col("consent").find(
            {"withdrawn_at": None, "research_use_allowed": 1}, {"account_id": 1}
        )
        return {r["account_id"] for r in rows}

    @staticmethod
    def _to_consent(row: dict) -> Consent:
        return Consent(
            consent_id=row["consent_id"],
            account_id=row["account_id"],
            consent_version=row["consent_version"],
            audio_storage_allowed=bool(row["audio_storage_allowed"]),
            research_use_allowed=bool(row["research_use_allowed"]),
            signed_at=row["signed_at"],
            withdrawn_at=row.get("withdrawn_at"),
        )
