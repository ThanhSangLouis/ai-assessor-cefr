"""MongoDB persistence for metering: usage ledger, credit wallet, free quota (D049, D051)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from aicefr.storage.db import Database, connect


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class MeteringRepository:
    def __init__(self, target: str | Database) -> None:
        self.db: Database = connect(target) if isinstance(target, str) else target
        self.wallets = self.db.collection("credit_wallet")
        self.ledger = self.db.collection("usage_ledger")
        self.grants = self.db.collection("credit_grant")
        self.quotas = self.db.collection("free_quota")

    def get_balance(self, user_ref: str) -> int:
        doc = self.wallets.find_one({"user_ref": user_ref})
        return int(doc.get("balance", 0)) if doc else 0

    def add_grant(self, *, user_ref: str, amount: int, source: str, ref: str) -> bool:
        grant_id = f"grnt_{uuid.uuid4().hex[:12]}"
        now = _utc_now()
        # Ensure unique (source, ref)
        if self.grants.find_one({"source": source, "ref": ref}):
            return False
        self.grants.insert_one(
            {
                "grant_id": grant_id,
                "user_ref": user_ref,
                "amount": amount,
                "source": source,
                "ref": ref,
                "created_at": now,
            }
        )
        self.wallets.update_one(
            {"user_ref": user_ref},
            {"$inc": {"balance": amount}, "$set": {"updated_at": now}},
            upsert=True,
        )
        return True

    def reserve_units(self, *, user_ref: str, units: int, key: str, action: str) -> str:
        entry_id = f"usg_{uuid.uuid4().hex[:12]}"
        now = _utc_now()
        existing = self.ledger.find_one({"key": key, "action": action})
        if existing:
            return str(existing["entry_id"])

        self.ledger.insert_one(
            {
                "entry_id": entry_id,
                "key": key,
                "action": action,
                "user_ref": user_ref,
                "units": units,
                "state": "reserved",
                "created_at": now,
            }
        )
        return entry_id

    def settle_entry(self, entry_id: str, *, state: str) -> bool:
        doc = self.ledger.find_one({"entry_id": entry_id})
        if not doc or doc.get("state") != "reserved":
            return False
        now = _utc_now()
        self.ledger.update_one(
            {"entry_id": entry_id},
            {"$set": {"state": state, "settled_at": now}},
        )
        if state == "charged":
            units = int(doc.get("units", 1))
            self.wallets.update_one(
                {"user_ref": doc["user_ref"]},
                {"$inc": {"balance": -units}, "$set": {"updated_at": now}},
                upsert=True,
            )
        return True

    def list_history(self, user_ref: str, limit: int = 50) -> list[dict[str, Any]]:
        cursor = self.ledger.find({"user_ref": user_ref}).sort("created_at", -1).limit(limit)
        return list(cursor)
