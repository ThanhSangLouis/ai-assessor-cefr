"""Facade for the metering service exposed to peers and internal RPC."""

from __future__ import annotations

from typing import Any

from aicefr.metering.service import MeteringService


class MeteringFacade:
    def __init__(self, service: MeteringService) -> None:
        self.service = service

    def is_enabled(self) -> bool:
        return self.service.is_enabled()

    def balance(self, user_ref: str) -> int:
        return self.service.balance(user_ref)

    def credit(self, *, user_ref: str, amount: int, source: str, ref: str) -> bool:
        return self.service.credit(user_ref, amount, source, ref)

    def reserve(self, *, user_ref: str, units: int, key: str, action: str) -> str:
        return self.service.reserve(user_ref, units, key, action)

    def charge(self, *, entry_id: str) -> bool:
        return self.service.charge(entry_id)

    def refund(self, *, entry_id: str) -> bool:
        return self.service.refund(entry_id)

    def history(self, *, user_ref: str, limit: int = 50) -> list[dict[str, Any]]:
        return self.service.history(user_ref, limit=limit)
