"""The metered channel's pages for people (D049): my runs, and a top-up by an administrator."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from aicefr.api.deps import ADMIN_ONLY, require_login
from aicefr.contracts import TaskPurpose
from aicefr.metering.pricing import (
    MAX_SECONDS,
    UNITS_PER_RUN,
    PriceList,
    as_idpoint,
    as_runs,
    hold_for,
)
from aicefr.storage.audit_repository import AuditLog
from aicefr.storage.auth_repository import Account
from aicefr.storage.metering_repository import MeteringRepository, cycle

router = APIRouter()


@dataclass
class Services:
    store: MeteringRepository
    audit: AuditLog
    peers: Any
    enabled: bool
    prices: PriceList


_services: Services | None = None


def configure(services: Services) -> None:
    global _services
    _services = services


def svc() -> Services:
    if _services is None:
        raise RuntimeError("metering is not configured")
    return _services


def _entry(e: dict, prices: PriceList) -> dict:
    """A ledger entry as its owner reads it: no internal ids, runs rather than units."""
    return {
        "action": e["action"],
        "state": e["state"],
        "held_runs": as_runs(e["held"]),
        "charged_runs": as_runs(e["charged"]),
        "charged_idpoint": as_idpoint(prices, e["charged"]),
        "created_at": e["created_at"],
        "settled_at": e["settled_at"],
        "input_tokens": e.get("input_tokens"),
        "output_tokens": e.get("output_tokens"),
        "usage_estimated": e.get("usage_estimated"),
    }


@router.get("/api/v1/me/credits", tags=["student"])
def my_credits(account: Account = Depends(require_login)) -> dict:
    """Runs left this cycle, the price list, and the latest charges (D049)."""
    s = svc()
    if not s.enabled:
        return {"metering": False}
    balance = s.store.balance(account.account_id)
    return {
        "metering": True,
        "price_version": s.prices.version,
        "prices": s.prices.as_dict(),
        "cycle": cycle(),
        "free_runs_left": as_runs(balance["free_left"]),
        "wallet_runs": as_runs(balance["wallet"]),
        "wallet_idpoint": as_idpoint(s.prices, balance["wallet"]),
        # What a one-minute recording costs, for people to read (D057).
        "one_minute": {a.value: as_runs(hold_for(s.prices, a, 60.0)) for a in TaskPurpose},
        "history": [_entry(e, s.prices) for e in s.store.history(account.account_id, limit=20)],
    }


@router.get("/api/v1/me/credits/quote", tags=["student"])
def quote(
    seconds: float = Query(gt=0, le=MAX_SECONDS),
    action: TaskPurpose = TaskPurpose.ASSESSMENT,
    account: Account = Depends(require_login),
) -> dict:
    """The most a recording of up to `seconds` costs: what the submission screen shows (D057)."""
    s = svc()
    if not s.enabled:
        return {"metering": False}
    units = hold_for(s.prices, action, seconds)
    return {
        "metering": True,
        "runs": as_runs(units),
        "idpoint": as_idpoint(s.prices, units),
        "free_runs_left": as_runs(s.store.free_left(account.account_id)),
        "wallet_runs": as_runs(s.store.wallet(account.account_id)),
    }


class GrantIn(BaseModel):
    pseudonym: str = Field(min_length=1, max_length=40)
    runs: int = Field(ge=1, le=10_000)
    # What the top-up answers to: a NetID statement line, a receipt number.
    reference: str = Field(min_length=1, max_length=80)


@router.post("/api/v1/admin/credits/grant", tags=["admin"])
def grant_credits(body: GrantIn, account: Account = ADMIN_ONLY) -> dict:
    """Credit runs to an account once per reference (D049); until NetID's API exists."""
    s = svc()
    if not s.enabled:
        raise HTTPException(409, "bản triển khai này không tính lượt (AICEFR_METERING=off)")
    who = s.peers.identity.by_pseudonym(pseudonym=body.pseudonym)
    if who is None:
        raise HTTPException(404, "không có tài khoản này")
    credited = s.store.grant(
        who["account_id"], body.runs * UNITS_PER_RUN, "admin", body.reference, account.account_id
    )
    if credited:
        s.audit.write(account.account_id, "metering.grant", who["account_id"], f"runs={body.runs}")
    return {"credited": credited, "wallet_runs": as_runs(s.store.wallet(who["account_id"]))}
