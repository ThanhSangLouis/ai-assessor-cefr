"""Metering service implementation for NetID credit calculations (D049, D053, D057)."""

from __future__ import annotations

import logging
from typing import Any

from aicefr.storage.metering_repository import MeteringRepository

logger = logging.getLogger(__name__)


class MeteringService:
    def __init__(self, store: MeteringRepository, *, enabled: bool = False) -> None:
        self.store = store
        self._enabled = enabled

    def is_enabled(self) -> bool:
        """Returns True if metering channel is active on this deployment."""
        return self._enabled

    def balance(self, user_ref: str) -> int:
        if not self._enabled:
            return 0
        return self.store.get_balance(user_ref)

    def credit(self, user_ref: str, amount: int, source: str, ref: str) -> bool:
        """Adds credits once per source and ref (unique index D049)."""
        if not self._enabled:
            return True
        return self.store.add_grant(user_ref=user_ref, amount=amount, source=source, ref=ref)

    def reserve(self, user_ref: str, units: int, key: str, action: str) -> str:
        """Reserve usage units before starting evaluation/practice."""
        if not self._enabled:
            return "noop"
        return self.store.reserve_units(user_ref=user_ref, units=units, key=key, action=action)

    def charge(self, entry_id: str) -> bool:
        """Confirm charge after evaluation completes successfully."""
        if not self._enabled or entry_id == "noop":
            return True
        return self.store.settle_entry(entry_id, state="charged")

    def refund(self, entry_id: str) -> bool:
        """Release reservation when evaluation fails or errors."""
        if not self._enabled or entry_id == "noop":
            return True
        return self.store.settle_entry(entry_id, state="refunded")

    def history(self, user_ref: str, limit: int = 50) -> list[dict[str, Any]]:
        if not self._enabled:
            return []
        return self.store.list_history(user_ref, limit=limit)
