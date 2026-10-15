"""Immutable, public-safe records for billing operations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class Plan:
    code: str
    title: str
    monthly_minor: int
    student_limit: int
    warning_quota: int
    features: frozenset[str]
    currency: str = "VND"
    active: bool = True


@dataclass(frozen=True, slots=True)
class Entitlement:
    plan_code: str
    features: frozenset[str]
    student_limit: int
    warning_quota: int
    effective_at: datetime | None
    expires_at: datetime | None = None
    grace_until: datetime | None = None
    entitlement_id: str | None = None
    source_order: str | None = None


@dataclass(frozen=True, slots=True)
class Quote:
    quote_id: str
    account_id: str
    plan_code: str
    months: int
    subtotal_minor: int
    discount_minor: int
    credit_minor: int
    total_minor: int
    currency: str
    created_at: datetime
    expires_at: datetime
    context_json: str = "{}"
    effective_at: datetime | None = None
    ends_at: datetime | None = None
    change_kind: str = "initial"


@dataclass(frozen=True, slots=True)
class Order:
    order_id: str
    quote_id: str
    account_id: str
    state: str
    gateway: str
    mode: str
    checkout_ref: str | None
    amount_minor: int
    currency: str
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class Receipt:
    receipt_id: str
    order_id: str
    account_id: str
    plan_code: str
    amount_minor: int
    currency: str
    issued_at: datetime
