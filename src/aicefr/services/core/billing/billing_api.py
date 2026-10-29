"""HTTP side of service plans and payment (D033, D035).

Four audiences, four kinds of route:

* the administrator: the "Gói dịch vụ" tab's API -- the licence in force, its
  use, a quote, an order (with the gateway picked), a licence key, the
  organisation's name;
* the administrator's browser coming back from the gateway: the return page,
  which applies the result it stands for -- signed into the address (VNPay,
  MoMo, the sandbox) or read back from the gateway (Stripe) -- and says what
  happened;
* the gateway's own server: the notification address, GET for VNPay's IPN,
  POST for Stripe's webhook and MoMo's IPN. No session there: the signature is
  the only credential, and the answer is in the shape each gateway expects;
* the sandbox gateway's page, which stands in for a real gateway's page when no
  money should move.

Wired once at start-up through `configure`, like the other routers.
"""

from __future__ import annotations

import hmac
import logging
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from aicefr.api.deps import (
    ADMIN_ONLY,
    STAFF_ONLY,
    optional_account,
    require_login,
)
from aicefr.api.web import templates
from aicefr.billing.gateways import SandboxGateway
from aicefr.billing.keys import LicenseKeyError
from aicefr.billing.payments import SETTLEABLE, Ack, GatewayError, Incoming, OrderStatus
from aicefr.billing.plans import MAX_SEATS, MIN_SEATS, PLAN_NAMES, Quote, QuoteError, ServicePlan
from aicefr.billing.service import CREDITS, BillingOff, BillingService, PaymentUnavailable
from aicefr.config import get_settings
from aicefr.practice.streak import LOCAL_TZ
from aicefr.storage.auth_repository import Account, Role

router = APIRouter()
logger = logging.getLogger(__name__)


def _vnd(amount: int) -> str:
    """12000000 -> "12.000.000 đ", the way Vietnamese prices are written."""
    return f"{int(amount):,}".replace(",", ".") + " đ"


def _dmy(iso: str | None) -> str:
    """2026-10-07 -> 07/10/2026."""
    return "-".join(reversed((iso or "")[:10].split("-"))).replace("-", "/") if iso else "—"


def _when(iso: str | None) -> str:
    """A stored UTC moment as Vietnam time: 2026-10-06T20:05:00+00:00 -> 07/10/2026 03:05."""
    if not iso:
        return "—"
    return datetime.fromisoformat(iso).astimezone(LOCAL_TZ).strftime("%d/%m/%Y %H:%M")


templates.env.filters["vnd"] = _vnd
templates.env.filters["dmy"] = _dmy
templates.env.filters["vn_time"] = _when

OFF = (
    "bản triển khai này chưa bật thu phí (AICEFR_BILLING): mọi tính năng mở, không giới hạn, "
    "không bán gói"
)


@dataclass
class Services:
    billing: BillingService


_services: Services | None = None


def configure(services: Services) -> None:
    global _services
    _services = services


def svc() -> Services:
    if _services is None:  # pragma: no cover - configured at import of main
        raise RuntimeError("billing API used before configure()")
    return _services


def _billing() -> BillingService:
    return svc().billing


# ================================================================= administrator


class PurchaseIn(BaseModel):
    plan: ServicePlan
    seats: int = Field(ge=MIN_SEATS, le=MAX_SEATS)
    months: int
    # One of the gateways offered; the first offered when not given (D035).
    gateway: str | None = Field(default=None, max_length=20)


class KeyIn(BaseModel):
    key: str = Field(min_length=10, max_length=4000)


class OrganizationIn(BaseModel):
    name: str = Field(min_length=2, max_length=160)


def _quote_view(q: Quote) -> dict:
    return {
        "plan": q.plan.value,
        "plan_name": PLAN_NAMES[q.plan],
        "seats": q.seats,
        "months": q.months,
        "unit_price": q.unit_price,
        "kind": q.kind,
        "starts_on": q.starts_on.isoformat(),
        "ends_on": q.ends_on.isoformat(),
        "list_vnd": q.list_price,
        "discount_vnd": q.discount,
        "gross_vnd": q.gross,
        "credit_vnd": q.credit,
        "amount_vnd": q.amount,
    }


def _site(request: Request) -> str:
    """This system's address as a gateway reaches it: return and notification addresses are full."""
    return (get_settings().public_url or str(request.base_url)).rstrip("/")


@router.get("/api/v1/plan", tags=["teacher"])
def plan_features(account: Account = STAFF_ONLY) -> dict:
    """The plan in force and the staff tools it opens, for the pages where staff work."""
    return _billing().features()


@router.get("/api/v1/admin/billing", tags=["admin"])
def billing_overview(account: Account = ADMIN_ONLY) -> dict:
    """The licence in force, what it allows, what is used, the plans for sale, recent orders."""
    return _billing().overview()


@router.post("/api/v1/admin/billing/quote", tags=["admin"])
def billing_quote(body: PurchaseIn, account: Account = ADMIN_ONLY) -> dict:
    """What a purchase costs today and when it runs, credits included; nothing is stored."""
    try:
        return _quote_view(_billing().quote(body.plan, body.seats, body.months))
    except BillingOff:
        raise HTTPException(409, OFF) from None
    except QuoteError as e:
        raise HTTPException(422, str(e)) from e


@router.post("/api/v1/admin/billing/orders", tags=["admin"])
def billing_order(body: PurchaseIn, request: Request, account: Account = ADMIN_ONLY) -> dict:
    """Place an order; the answer carries the address of the gateway's payment page."""
    billing = _billing()
    try:
        order, url = billing.place_order(
            body.plan,
            body.seats,
            body.months,
            account.account_id,
            account.pseudonym,
            _site(request),
            request.client.host if request.client else "127.0.0.1",
            body.gateway,
        )
    except BillingOff:
        raise HTTPException(409, OFF) from None
    except QuoteError as e:
        raise HTTPException(422, str(e)) from e
    except PaymentUnavailable as e:
        # The gateway refused or was unreachable; the order is already marked failed.
        raise HTTPException(502, str(e)) from e
    return {"order": billing.order_view(order), "checkout_url": url}


# ================================================================= run packs (D053)


class CreditOrderIn(BaseModel):
    runs: int = Field(ge=1, le=10_000)
    gateway: str | None = Field(default=None, max_length=20)


@router.get("/api/v1/me/credit-packs", tags=["student"])
def my_credit_packs(account: Account = Depends(require_login)) -> dict:
    """The run packs on sale, the gateways, and this account's own pack orders."""
    billing = _billing()
    if not billing.sells_credits:
        return {"on_sale": False}
    billing.store.expire_pending(billing._stamp())
    mine = billing.store.orders_by(account.account_id, CREDITS)
    for order in mine:
        billing.credit_order(order)  # a pack paid while the metering service was away
    return {
        "on_sale": True,
        "packs": billing.credit_packs(),
        "gateways": [
            {"name": g.name, "title": g.title, "live": g.live} for g in billing.gateways.values()
        ],
        "orders": [
            billing.order_view(o) for o in billing.store.orders_by(account.account_id, CREDITS)
        ],
    }


@router.post("/api/v1/me/credit-orders", tags=["student"])
def my_credit_order(
    body: CreditOrderIn, request: Request, account: Account = Depends(require_login)
) -> dict:
    """Order one run pack; the answer carries the address of the gateway's payment page."""
    billing = _billing()
    try:
        order, url = billing.place_credit_order(
            body.runs,
            account.account_id,
            account.pseudonym,
            _site(request),
            request.client.host if request.client else "127.0.0.1",
            body.gateway,
        )
    except BillingOff:
        raise HTTPException(409, "bản triển khai này không bán gói lượt") from None
    except QuoteError as e:
        raise HTTPException(422, str(e)) from e
    except PaymentUnavailable as e:
        raise HTTPException(502, str(e)) from e
    return {"order": billing.order_view(order), "checkout_url": url}


@router.post("/api/v1/admin/billing/license", tags=["admin"])
def billing_install_key(body: KeyIn, account: Account = ADMIN_ONLY) -> dict:
    """Install a licence key issued for a contract paid outside the system."""
    try:
        lic = _billing().install_key(body.key, account.account_id, account.pseudonym)
    except BillingOff:
        raise HTTPException(409, OFF) from None
    except LicenseKeyError as e:
        raise HTTPException(409 if "đã được cài" in str(e) else 422, str(e)) from e
    return {
        "license_id": lic.license_id,
        "plan": lic.plan.value,
        "plan_name": PLAN_NAMES[lic.plan],
        "seats": lic.seats,
        "valid_from": lic.valid_from.isoformat(),
        "valid_to": lic.valid_to.isoformat(),
    }


@router.patch("/api/v1/admin/billing/organization", tags=["admin"])
def billing_organization(body: OrganizationIn, account: Account = ADMIN_ONLY) -> dict:
    """The organisation's name, printed on licences and receipts. An organisation, not a person."""
    try:
        return {"organization": _billing().set_organization(body.name, account.pseudonym)}
    except ValueError as e:
        raise HTTPException(422, str(e)) from e


# ================================================================= the gateway's side


def _gateway_or_404(name: str):
    billing = _billing()
    gateway = billing.gateway(name) if billing.enabled else None
    if gateway is None:
        raise HTTPException(404, "không có cổng thanh toán này")
    return gateway


# A gateway's notification is a few kilobytes; anything far larger is not one.
NOTIFY_MAX_BYTES = 256 * 1024


def _answer(ack: Ack) -> Response:
    if ack.body is None:
        return Response(status_code=ack.status)
    return JSONResponse(ack.body, status_code=ack.status)


def _notified(gw, message: Incoming) -> Response:
    billing = _billing()
    try:
        result = gw.verify_notification(message, billing.now())
    except Exception:  # noqa: BLE001 - input from outside; whatever breaks, it is not signed
        logger.warning("billing: unreadable notification from %s", gw.name, exc_info=True)
        result = None
    if result is None:
        logger.warning("billing: notification with a bad signature from %s", gw.name)
        return _answer(gw.acknowledge("signature"))
    try:
        what = billing.settle(result, "notify", gw.name)
    except Exception:  # noqa: BLE001 - the gateway sends it again on an error answer
        logger.exception("billing: could not settle %s", result.order_id)
        return _answer(gw.acknowledge("error"))
    return _answer(gw.acknowledge(what))


@router.api_route("/api/v1/billing/notify/{gateway}", methods=["GET", "POST"], tags=["billing"])
async def billing_notify(gateway: str, request: Request) -> Response:
    """The gateway's server reports a result. The signature is the only credential.

    GET for VNPay's IPN, POST for Stripe's webhook and MoMo's IPN; each
    adapter reads the part its gateway signs, and answers the way it expects.
    """
    gw = _gateway_or_404(gateway)
    body = b""
    if request.method == "POST":
        # Refused before it is held in memory: by what the sender declares,
        # then by what actually arrives.
        declared = request.headers.get("content-length", "")
        if declared.isdigit() and int(declared) > NOTIFY_MAX_BYTES:
            return Response(status_code=413)
        received = bytearray()
        async for chunk in request.stream():
            received += chunk
            if len(received) > NOTIFY_MAX_BYTES:
                return Response(status_code=413)
        body = bytes(received)
    message = Incoming(
        query=dict(request.query_params),
        headers={k.lower(): v for k, v in request.headers.items()},
        body=body,
    )
    return await run_in_threadpool(_notified, gw, message)


@router.get("/billing/return/{gateway}", response_class=HTMLResponse, tags=["web"])
def billing_return(
    gateway: str, request: Request, account: Account | None = Depends(optional_account)
):
    """Where the gateway sends the browser back. Applies the result the address stands for.

    Works without a session on purpose: a session that expired while the
    person was paying must not lose the payment. The page shows only what the
    gateway vouched for, and the plan it bought. `left=1` is this system's own
    mark on the address of a payer who left the gateway's page without paying
    (Stripe's cancel address): nothing is settled, the payment simply expires.
    """
    gw = _gateway_or_404(gateway)
    billing = _billing()
    query = dict(request.query_params)
    context: dict = {
        "account": account,
        "nav_here": "credits" if account and account.role is Role.STUDENT else "admin",
        "test": not gw.live,
        "gateway": gw.title,
        "order": None,
        "message": "",
    }
    if query.get("left") == "1":
        context["state"] = "left"
        return templates.TemplateResponse(request, "billing_result.html", context)
    reference = gw.return_reference(query)
    if reference is not None:
        known = billing.store.order_by_checkout(gw.name, reference)
        if known is None:
            # Not a checkout of ours: the gateway is not asked about it, so a
            # stranger cannot spend this system's allowance of calls to Stripe.
            context["state"] = "invalid"
            return templates.TemplateResponse(request, "billing_result.html", context)
        if OrderStatus(known["status"]) not in SETTLEABLE:
            # Settled already: the page says so from the database, and nobody
            # replaying this address makes the system call the gateway again.
            context.update(
                state=known["status"], order=billing.order_view(known), test=not known["live"]
            )
            return templates.TemplateResponse(request, "billing_result.html", context)
    try:
        result = gw.verify_return(query)
    except GatewayError:
        logger.warning("billing: could not confirm a return with %s", gw.name)
        context["state"] = "unconfirmed"
        return templates.TemplateResponse(request, "billing_result.html", context)
    except Exception:  # noqa: BLE001 - an address from outside; whatever breaks, it is not signed
        logger.warning("billing: unreadable return to %s", gw.name, exc_info=True)
        result = None
    if result is None:
        context["state"] = "invalid"
        return templates.TemplateResponse(request, "billing_result.html", context)
    what = billing.settle(result, "return", gw.name)
    order = billing.store.order(result.order_id) if what not in ("not_found", "amount") else None
    if order is None:
        context["state"] = "amount" if what == "amount" else "not_found"
    else:
        context.update(
            state=order["status"],
            order=billing.order_view(order),
            message=result.message,
            test=not order["live"],
        )
    return templates.TemplateResponse(request, "billing_result.html", context)


# ================================================================= sandbox gateway


def _sandbox_order(order_id: str, token: str) -> tuple[SandboxGateway, dict]:
    billing = _billing()
    gw = billing.gateway("sandbox")
    order = billing.store.order(order_id) if billing.enabled else None
    if not isinstance(gw, SandboxGateway) or order is None or order["gateway"] != gw.name:
        raise HTTPException(404, "không có đơn này")
    if not hmac.compare_digest(gw.token(order_id, order["amount_vnd"]), token):
        raise HTTPException(404, "không có đơn này")
    return gw, order


@router.get("/billing/sandbox/{order_id}", response_class=HTMLResponse, tags=["web"])
def sandbox_page(order_id: str, request: Request, t: str = ""):
    """The sandbox gateway's payment page: the order, and the outcome to simulate."""
    _gw, order = _sandbox_order(order_id, t)
    billing = _billing()
    return templates.TemplateResponse(
        request,
        "billing_sandbox.html",
        {
            "account": None,
            "order": billing.order_view(order),
            "organization": billing.organization(),
            "token": t,
            "payable": OrderStatus(order["status"]) in SETTLEABLE,
        },
    )


@router.post("/billing/sandbox/{order_id}/pay", tags=["web"])
def sandbox_pay(order_id: str, t: str = Form(""), outcome: str = Form("")):
    """Simulate the payer's choice, the way a gateway reports it.

    First the notification, as a real gateway's server sends it, then the
    browser goes back to the return page with the same signed result: both
    paths are exercised, and the second changes nothing.
    """
    gw, order = _sandbox_order(order_id, t)
    if outcome not in ("paid", "failed", "cancelled"):
        raise HTTPException(422, "kết quả thử không hợp lệ")
    billing = _billing()
    params = gw.result(order_id, order["amount_vnd"], outcome, billing.now())
    result = gw.verify(params)
    if result is not None:
        billing.settle(result, "notify", gw.name)
    return RedirectResponse("/billing/return/sandbox?" + urlencode(params), status_code=303)


# ================================================================= receipt


@router.get("/billing/orders/{order_id}/receipt", response_class=HTMLResponse, tags=["web"])
def billing_receipt(
    order_id: str, request: Request, account: Account | None = Depends(optional_account)
):
    """A printable receipt for a paid order. Not a VAT invoice, and it says so."""
    if account is None:
        return RedirectResponse(f"/login?next=/billing/orders/{order_id}/receipt", status_code=303)
    billing = _billing()
    order = billing.store.order(order_id)
    if order is None or order["status"] != OrderStatus.PAID.value:
        raise HTTPException(404, "không có biên nhận cho đơn này")
    # A run pack's receipt is its buyer's too (D053); a plan's is the administrator's.
    buyer = order["kind"] == CREDITS and order["created_by"] == account.account_id
    if account.role is not Role.ADMIN and not buyer:
        raise HTTPException(403, "chỉ quản trị viên xem được biên nhận")
    return templates.TemplateResponse(
        request,
        "billing_receipt.html",
        {
            "account": account,
            "nav_here": "credits" if order["kind"] == CREDITS else "admin",
            "order": billing.order_view(order),
            "organization": billing.organization() or "(chưa đặt tên tổ chức)",
            "test": not order["live"] and order["gateway"] != "none",
        },
    )
