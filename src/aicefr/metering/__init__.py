"""Metering domain: NetID credit balances, usage ledger and quotas (D049, D053, D057)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CreditGrant:
    grant_id: str
    user_ref: str
    amount: int
    source: str
    ref: str
    created_at: str


@dataclass(frozen=True)
class UsageEntry:
    entry_id: str
    key: str
    action: str
    user_ref: str
    units: int
    state: str
    created_at: str
