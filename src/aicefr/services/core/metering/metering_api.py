"""The metered channel's pages for people (D049): my runs, and a top-up by an administrator."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from aicefr.api.deps import ADMIN_ONLY, require_login
from aicefr.metering.pricing import (
    MAX_SECONDS,
    UNITS_PER_RUN,
    PriceList,
    as_idpoint,
    as_runs,
    hold_for,
)
from aicefr.services.core.metering.price_book import PriceBook
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
    book: PriceBook

    @property
    def prices(self) -> PriceList:
        return self.book.current()


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
        # D094: one of the day's free lesson recordings.
        "free_slot": bool(e.get("free_slot")),
    }


@router.get("/api/v1/me/credits", tags=["student"])
def my_credits(account: Account = Depends(require_login)) -> dict:
    """Runs left this cycle, the price list, and the latest charges (D049)."""
    s = svc()
    if not s.enabled:
        return {"metering": False}
    locked = s.peers.metering.free_runs_locked(account_id=account.account_id)
    balance = s.store.balance(account.account_id, free=not locked)
    return {
        "metering": True,
        # D101: the free runs wait for a verified email.
        "free_locked": locked,
        "free_runs_per_cycle": as_runs(s.store.free_units),
        "price_version": s.prices.version,
        "prices": s.prices.as_dict(),
        "cycle": cycle(),
        "free_runs_left": as_runs(balance["free_left"]),
        "wallet_runs": as_runs(balance["wallet"]),
        "wallet_idpoint": as_idpoint(s.prices, balance["wallet"]),
        # What a one-minute recording costs, for people to read (D057).
        "one_minute": {"assessment": as_runs(hold_for(s.prices, 60.0))},
        "lesson": s.peers.metering.lesson_quote(account_id=account.account_id),
        "history": [_entry(e, s.prices) for e in s.store.history(account.account_id, limit=20)],
    }


@router.get("/api/v1/me/credits/quote", tags=["student"])
def quote(
    seconds: float = Query(gt=0, le=MAX_SECONDS),
    account: Account = Depends(require_login),
) -> dict:
    """The most a recording of up to `seconds` costs: what the submission screen shows (D057)."""
    s = svc()
    if not s.enabled:
        return {"metering": False}
    units = hold_for(s.prices, seconds)
    locked = s.peers.metering.free_runs_locked(account_id=account.account_id)
    return {
        "metering": True,
        "runs": as_runs(units),
        "idpoint": as_idpoint(s.prices, units),
        "free_locked": locked,
        "free_runs_left": as_runs(s.store.free_left(account.account_id, free=not locked)),
        "wallet_runs": as_runs(s.store.wallet(account.account_id)),
    }


@router.get("/api/v1/me/credits/lesson", tags=["student"])
def lesson_quote(account: Account = Depends(require_login)) -> dict:
    """What a lesson recording costs me now (D094): the free ones left today, the cap, the price."""
    quote = svc().peers.metering.lesson_quote(account_id=account.account_id)
    return {"metering": False} if quote is None else {"metering": True, **quote}


class GrantIn(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    runs: int = Field(ge=1, le=10_000)
    # What the top-up answers to: a NetID statement line, a receipt number.
    reference: str = Field(min_length=1, max_length=80)


@router.post("/api/v1/admin/credits/grant", tags=["admin"])
def grant_credits(body: GrantIn, account: Account = ADMIN_ONLY) -> dict:
    """Credit runs to an account once per reference (D049); until NetID's API exists."""
    s = svc()
    if not s.enabled:
        raise HTTPException(409, "bản triển khai này không tính lượt (AICEFR_METERING=off)")
    who = s.peers.identity.by_email(email=body.email)
    if who is None:
        raise HTTPException(404, "không có tài khoản này")
    credited = s.store.grant(
        who["account_id"], body.runs * UNITS_PER_RUN, "admin", body.reference, account.account_id
    )
    if credited:
        s.audit.write(account.account_id, "metering.grant", who["account_id"], f"runs={body.runs}")
    return {"credited": credited, "wallet_runs": as_runs(s.store.wallet(who["account_id"]))}


# ================================================================= prices (D078)


class PackIn(BaseModel):
    runs: int = Field(ge=1, le=10_000)
    price_vnd: int = Field(ge=1, le=100_000_000)


class PricesIn(BaseModel):
    first_minute_runs: float = Field(ge=0, le=100)
    extra_minute_runs: float = Field(ge=0, le=100)
    upgrade_runs: float = Field(ge=0, le=100)
    passage_runs: float = Field(default=0.1, ge=0, le=100)
    # D094: defaults, so a dashboard of before keeps working.
    lesson_minute_runs: float = Field(default=0.1, ge=0, le=100)
    lesson_free_per_day: int = Field(default=5, ge=0, le=1000)
    lesson_daily_cap: int = Field(default=30, ge=1, le=1000)
    idpoint_per_run: int = Field(ge=0, le=10_000_000)
    free_runs: float = Field(ge=0, le=1000)
    packs: list[PackIn] = Field(min_length=1, max_length=10)


@router.get("/api/v1/admin/prices", tags=["admin"])
def prices(account: Account = ADMIN_ONLY) -> dict:
    """The prices in force, where they come from, and the earlier versions."""
    s = svc()
    return {"metering": s.enabled, **s.book.view()}


@router.put("/api/v1/admin/prices", tags=["admin"])
def set_prices(body: PricesIn, account: Account = ADMIN_ONLY) -> dict:
    """A new version of the prices; charges already made keep theirs."""
    s = svc()
    try:
        saved = s.book.set(body.model_dump())
    except ValueError as e:
        raise HTTPException(422, str(e)) from e
    s.audit.write(account.account_id, "metering.prices", None, saved["version"])
    return {"metering": s.enabled, **s.book.view()}
