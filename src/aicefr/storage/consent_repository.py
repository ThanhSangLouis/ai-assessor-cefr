"""Persistence for research participation consent. Implements FR-01 and FR-35.

Why this is a separate table and not a column on `account`:

Consent is not a property of a person, it is an *event* that happened at a
point in time, under a specific wording. A student who signs version `dt-v1`,
withdraws, then signs `dt-v2` has three facts worth keeping, and a boolean
column can only remember the last one. The rule the university ethics guidance
cares about -- "you must be able to show what the participant agreed to, at the
time they agreed to it" -- is unanswerable with a boolean.

So every signature and every withdrawal is a row, and the version of the text
is copied INTO the row. Editing the consent page later never rewrites what
somebody already agreed to.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from pathlib import Path

from aicefr.storage.db import DbRow, SqlStore
from aicefr.storage.db import now_iso as _now

# The wording currently shown on the consent screen. Bump this when the text
# changes in a way that alters what the participant is agreeing to -- not for
# typos. `docs/plan/KE_HOACH_KHAO_SAT.md` phụ lục A holds the text itself.
CURRENT_CONSENT_VERSION = "dt-v1"

SCHEMA_CONSENT = """
CREATE TABLE IF NOT EXISTS consent (
    consent_id            TEXT PRIMARY KEY,
    account_id            TEXT NOT NULL,
    consent_version       TEXT NOT NULL,
    audio_storage_allowed INTEGER NOT NULL,
    research_use_allowed  INTEGER NOT NULL,
    signed_at             TEXT NOT NULL,
    withdrawn_at          TEXT
);
CREATE INDEX IF NOT EXISTS idx_consent_account ON consent(account_id);
"""


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


class ConsentRepository(SqlStore):
    """SQLite adapter for the consent table."""

    def __init__(self, db_path: str | Path = "aicefr.db") -> None:
        self.db_path = str(db_path)
        self._prepare_location()
        with self._conn() as c:
            c.executescript(SCHEMA_CONSENT)

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
        it). Keeping the old row withdrawn rather than updating it preserves
        the history.
        """
        now = _now()
        cid = uuid.uuid4().hex[:12]
        with self._conn() as c:
            c.execute(
                "UPDATE consent SET withdrawn_at=? WHERE account_id=? AND withdrawn_at IS NULL",
                (now, account_id),
            )
            c.execute(
                "INSERT INTO consent(consent_id, account_id, consent_version,"
                " audio_storage_allowed, research_use_allowed, signed_at, withdrawn_at)"
                " VALUES(?,?,?,?,?,?,NULL)",
                (
                    cid,
                    account_id,
                    consent_version,
                    int(audio_storage_allowed),
                    int(research_use_allowed),
                    now,
                ),
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
        with self._conn() as c:
            cur = c.execute(
                "UPDATE consent SET withdrawn_at=? WHERE account_id=? AND withdrawn_at IS NULL",
                (_now(), account_id),
            )
            return cur.rowcount > 0

    # ---------- read ----------

    def current(self, account_id: str) -> Consent | None:
        """The signature standing right now, or None."""
        with self._conn() as c:
            row = c.execute(
                "SELECT * FROM consent WHERE account_id=? AND withdrawn_at IS NULL"
                " ORDER BY signed_at DESC LIMIT 1",
                (account_id,),
            ).fetchone()
        return self._to_consent(row) if row else None

    def history(self, account_id: str) -> list[Consent]:
        """Every signature and withdrawal, oldest first. Used by the data export."""
        with self._conn() as c:
            rows = c.execute(
                "SELECT * FROM consent WHERE account_id=? ORDER BY signed_at", (account_id,)
            ).fetchall()
        return [self._to_consent(r) for r in rows]

    def accounts_allowing_research(self) -> set[str]:
        """Account ids whose standing signature allows research use.

        The research export asks this question, not the other way round: it is
        easier to prove "we only exported what this set allows" than to prove a
        filter spread across several queries never leaked a row.
        """
        with self._conn() as c:
            rows = c.execute(
                "SELECT account_id FROM consent"
                " WHERE withdrawn_at IS NULL AND research_use_allowed=1"
            ).fetchall()
        return {r["account_id"] for r in rows}

    @staticmethod
    def _to_consent(row: DbRow) -> Consent:
        return Consent(
            consent_id=row["consent_id"],
            account_id=row["account_id"],
            consent_version=row["consent_version"],
            audio_storage_allowed=bool(row["audio_storage_allowed"]),
            research_use_allowed=bool(row["research_use_allowed"]),
            signed_at=row["signed_at"],
            withdrawn_at=row["withdrawn_at"],
        )
