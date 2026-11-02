"""Where to send a browser's notifications (D088).

One collection, `push_subscription`: a document per browser that allowed
SpeakUp's notifications. The browser's push service (Google's for Chrome,
Mozilla's, Apple's) gives it an `endpoint` and two keys; a notification is
encrypted with those keys, so the push service carries it without reading it.

A subscription is a technical means, like a session: it is not in the class
diagram (domain model), it is in the identity ERD (05c).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from aicefr.storage.db import MongoStore
from aicefr.storage.db import now_iso as _now
from aicefr.storage.migrations import ensure_current

# A push service's endpoint is an HTTPS URL of a few hundred characters.
MAX_ENDPOINT = 1024
# Browsers one account may register; past that the oldest goes.
MAX_PER_ACCOUNT = 10


@dataclass(frozen=True)
class PushSubscription:
    endpoint: str
    account_id: str
    p256dh: str  # the browser's public key, base64url
    auth: str  # the shared authentication secret, base64url

    def info(self) -> dict:
        """The subscription as the browser's PushSubscription.toJSON() gives it."""
        return {"endpoint": self.endpoint, "keys": {"p256dh": self.p256dh, "auth": self.auth}}


class PushRepository(MongoStore):
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = str(db_path)
        ensure_current(self.db_path)

    def subscribe(self, account_id: str, endpoint: str, p256dh: str, auth: str) -> None:
        """Remember this browser for this account; a browser re-subscribing moves to it."""
        col = self.col("push_subscription")
        col.update_one(
            {"endpoint": endpoint},
            {
                "$set": {"account_id": account_id, "p256dh": p256dh, "auth": auth},
                "$setOnInsert": {"created_at": _now()},
            },
            upsert=True,
        )
        held = list(col.find({"account_id": account_id}, {"endpoint": 1}).sort("created_at", -1))
        stale = [d["endpoint"] for d in held[MAX_PER_ACCOUNT:]]
        if stale:
            col.delete_many({"endpoint": {"$in": stale}})

    def unsubscribe(self, account_id: str, endpoint: str) -> bool:
        done = self.col("push_subscription").delete_one(
            {"endpoint": endpoint, "account_id": account_id}
        )
        return bool(done.deleted_count)

    def drop(self, endpoint: str) -> None:
        """The push service said this browser is gone (404, 410)."""
        self.col("push_subscription").delete_one({"endpoint": endpoint})

    def of(self, account_id: str) -> list[PushSubscription]:
        rows = self.col("push_subscription").find({"account_id": account_id})
        return [
            PushSubscription(r["endpoint"], r["account_id"], r["p256dh"], r["auth"]) for r in rows
        ]

    def has(self, account_id: str, endpoint: str) -> bool:
        found = self.col("push_subscription").find_one(
            {"endpoint": endpoint, "account_id": account_id}, {"_id": 1}
        )
        return found is not None

    def forget_account(self, account_id: str) -> int:
        return self.col("push_subscription").delete_many({"account_id": account_id}).deleted_count
