"""Payments for run packs: a learner or a teacher buys runs, a gateway takes the money (D053, D075).

One centre runs this deployment and nobody sells it plans any more (D075):
the institution's service plans, licences, trial and licence keys of D033 and
D034 are gone, and every staff tool is open. What is left is the one thing
that takes money: a pack of runs for the metered channel (D049), ordered by
the person who will use it, paid through a gateway (D035), credited to their
wallet once.

Off while `AICEFR_BILLING` is off: nothing is sold and no gateway is opened.
"""

from __future__ import annotations

import logging
import secrets
from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta

from aicefr.billing.payments import (
    ORDER_STATUS_NAMES,
    PENDING_MINUTES,
    SETTLEABLE,
    GatewayError,
    OrderStatus,
    PaymentResult,
)
from aicefr.practice.streak import LOCAL_TZ

logger = logging.getLogger(__name__)

# An order's gateway by name, for orders whose gateway is no longer offered
# (VNPay and MoMo orders made before D075 among them).
GATEWAY_TITLES = {
    "none": "Không cần thanh toán",
    "sandbox": "Cổng thử",
    "vnpay": "VNPay",
    "stripe": "Stripe",
    "momo": "MoMo",
}


class BillingOff(Exception):
    """The deployment sells nothing (AICEFR_BILLING is off, or nothing is metered)."""


class OrderError(ValueError):
    """An order that cannot be placed; the message says why, for the person."""


class PaymentUnavailable(Exception):
    """The gateway would not open the payment; the order is marked failed. Says why."""


class BillingService:
    def __init__(
        self,
        store,  # aicefr.storage.billing_repository.BillingRepository
        settings,  # aicefr.config.Settings
        gateways,  # {name: aicefr.ports.PaymentGateway}, in the order offered; may be empty
        audit: Callable[[str, str, str | None, str | None], None],
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
        gateway_problems: list[str] | None = None,
        # D053: put runs in a buyer's wallet once per order -- the metering
        # service's `credit`; None where nothing is metered.
        credit: Callable[[str, int, str], bool] | None = None,
        # D078: the run packs on sale, as an administrator set them; the
        # settings' packs where nothing is metered.
        packs: Callable[[], tuple[tuple[int, int], ...]] | None = None,
    ) -> None:
        self.store = store
        self.settings = settings
        self.gateways = dict(gateways)
        # Why a gateway the settings ask for is off, for whoever reads the logs.
        self.gateway_problems = list(gateway_problems or [])
        self._audit = audit
        self._clock = clock
        self._credit = credit
        self._packs = packs or (lambda: tuple(self.settings.credit_packs))

    # ------------------------------------------------------------ basics

    @property
    def enabled(self) -> bool:
        return bool(self.settings.billing_enabled)

    def gateway(self, name: str):
        """The gateway of that name if this deployment offers it, else None."""
        return self.gateways.get(name)

    def now(self) -> datetime:
        return self._clock()

    def today(self) -> date:
        return self.now().astimezone(LOCAL_TZ).date()

    def _stamp(self) -> str:
        return self.now().astimezone(UTC).isoformat(timespec="seconds")

    def _chosen_gateway(self, name: str | None):
        """The gateway asked for, or the first offered; OrderError when there is none."""
        if not self.gateways:
            raise OrderError("cổng thanh toán chưa được cấu hình trên bản triển khai này")
        gateway = self.gateways.get(name or next(iter(self.gateways)))
        if gateway is None:
            raise OrderError("bản triển khai này không có cổng thanh toán đó")
        return gateway

    @staticmethod
    def _new_order_id(prefix: str, now: datetime) -> str:
        """DL (a run pack), the local date, six random hex digits."""
        return prefix + now.astimezone(LOCAL_TZ).strftime("%y%m%d") + secrets.token_hex(3).upper()

    @staticmethod
    def _expiry(now: datetime) -> str:
        """When a pending order nobody paid expires (payments.PENDING_MINUTES)."""
        return (
            (now + timedelta(minutes=PENDING_MINUTES)).astimezone(UTC).isoformat(timespec="seconds")
        )

    def _open_checkout(
        self,
        gateway,
        order_id: str,
        amount: int,
        description: str,
        site: str,
        client_ip: str,
        now: datetime,
    ) -> str:
        """Open the gateway's payment for an order just created; the address to send the payer."""
        site = site.rstrip("/")
        try:
            checkout = gateway.checkout(
                order_id,
                amount,
                description,
                f"{site}/billing/return/{gateway.name}",
                f"{site}/api/v1/billing/notify/{gateway.name}",
                client_ip,
                now,
            )
        except GatewayError as e:
            # Nothing was opened, so nothing can be paid: the order ends here.
            refused = PaymentResult(order_id, OrderStatus.FAILED, amount, "", e.code, str(e))
            self.settle(refused, "checkout", gateway.name)
            raise PaymentUnavailable(f"{gateway.title}: {e}") from e
        if checkout.reference:
            self.store.set_checkout_ref(order_id, checkout.reference)
        return checkout.url

    # ------------------------------------------------------------ run packs (D053)

    @property
    def sells_credits(self) -> bool:
        return self.enabled and self._credit is not None and bool(self._packs())

    def credit_packs(self) -> list[dict]:
        return [
            {"runs": runs, "price_vnd": price, "per_run_vnd": round(price / runs)}
            for runs, price in self._packs()
        ]

    def place_credit_order(
        self,
        runs: int,
        by_account: str,
        by_pseudonym: str,
        site: str,
        client_ip: str,
        gateway_name: str | None = None,
    ) -> tuple[dict, str]:
        """A learner's order for one run pack, and the address to pay it at.

        The runs go to the account that ordered, never to another: the order
        names its buyer, and only the payment's settlement credits them.
        """
        if not self.sells_credits:
            raise BillingOff
        price = dict(self._packs()).get(runs)
        if price is None:
            raise OrderError("không có gói lượt này")
        gateway = self._chosen_gateway(gateway_name)
        now = self.now()
        self.store.expire_pending(self._stamp())
        order_id = self._new_order_id("DL", now)
        self.store.create_order(
            {
                "order_id": order_id,
                "runs": runs,
                "amount_vnd": price,
                "status": OrderStatus.PENDING.value,
                "gateway": gateway.name,
                "live": bool(gateway.live),
                "created_by": by_account,
                "created_at": self._stamp(),
                "expires_at": self._expiry(now),
            }
        )
        self.store.add_event(order_id, "created", {"amount": price, "runs": runs})
        self._audit(by_pseudonym, "billing.credit_order", order_id, f"runs={runs} amount={price}")
        url = self._open_checkout(
            gateway,
            order_id,
            price,
            f"Thanh toan don {order_id} goi {runs} luot",
            site,
            client_ip,
            now,
        )
        return self.store.order(order_id), url  # type: ignore[return-value]

    def credit_order(self, order: dict) -> bool:
        """Put a paid run pack in its buyer's wallet; True once it is there.

        Safe to call any number of times: the metering service credits once
        per order id, and a failure (the service unreachable) leaves the order
        uncredited for the next call -- the return page, the learner's page,
        or `credit_pending`.
        """
        if order["status"] != OrderStatus.PAID.value:
            return False
        if order.get("credited_at"):
            return True
        if self._credit is None:
            return False
        try:
            self._credit(order["created_by"], int(order["runs"]), order["order_id"])
        except Exception:  # noqa: BLE001 - retried later; the payment itself is kept
            logger.exception("crediting order %s failed; will retry", order["order_id"])
            return False
        if self.store.mark_credited(order["order_id"]):
            self.store.add_event(order["order_id"], "credited", {"runs": order["runs"]})
        return True

    def credit_pending(self) -> list[str]:
        """Credit every paid run pack that has not reached its wallet yet."""
        return [o["order_id"] for o in self.store.uncredited() if self.credit_order(o)]

    def settle(self, result: PaymentResult, via: str, gateway: str) -> str:
        """Apply a verified result from `gateway` once. Returns what happened, in VNPay's terms.

        "ok" the order moved; "already" it had been settled; "pending" the
        gateway has no final word yet and nothing changes; "amount" the amount
        is not the order's and nothing changes (BR-33); "not_found", also for a
        result that is not this order's to settle (BR-35): from another
        gateway, from the same gateway in the other money mode -- a test card
        never pays for a real order, nor the other way round -- or about
        another checkout than the one the order opened. Every message about a
        known order is kept as an event; an identical repeat is counted, not
        stored again.
        """
        order = self.store.order(result.order_id) if result.order_id else None
        if order is None:
            return "not_found"
        said = {"outcome": result.outcome.value, "code": result.code, "reference": result.reference}
        current = self.gateways.get(gateway)
        if order["gateway"] != gateway or (
            gateway != "none"
            and (
                current is None
                or bool(current.live) != bool(order["live"])
                or (order["checkout_ref"] and result.checkout != order["checkout_ref"])
            )
        ):
            said |= {"via": via, "from": gateway, "checkout": result.checkout}
            self.store.add_event(order["order_id"], "rejected", said)
            return "not_found"
        if result.outcome is OrderStatus.PENDING:
            self.store.add_event(
                order["order_id"], via, said | dict(result.details) | {"applied": False}
            )
            return "pending"
        if result.amount_vnd != order["amount_vnd"]:
            self.store.add_event(
                order["order_id"], "rejected", said | {"via": via, "amount": result.amount_vnd}
            )
            return "amount"
        changed = False
        if OrderStatus(order["status"]) in SETTLEABLE:
            changed = self.store.settle(
                order["order_id"], result.outcome, result.reference, result.code
            )
        self.store.add_event(
            order["order_id"], via, said | dict(result.details) | {"applied": changed}
        )
        if not changed:
            return "already"
        self._audit(
            f"gateway:{order['gateway']}",
            f"billing.{result.outcome.value}",
            order["order_id"],
            f"amount={result.amount_vnd} ref={result.reference} code={result.code}",
        )
        if result.outcome is OrderStatus.PAID:
            self.credit_order(self.store.order(order["order_id"]))
        return "ok"

    # ------------------------------------------------------------ what the screens read

    def order_view(self, order: dict) -> dict:
        status = OrderStatus(order["status"])
        return {
            "order_id": order["order_id"],
            "plan_name": f"Gói {order['runs']} lượt",
            "runs": order["runs"],
            "credited": bool(order.get("credited_at")),
            "amount_vnd": order["amount_vnd"],
            "status": status.value,
            "status_name": ORDER_STATUS_NAMES[status],
            "gateway": order["gateway"],
            "gateway_title": self._gateway_title(order["gateway"]),
            "live": bool(order["live"]),
            "reference": order["reference"],
            "result_code": order["result_code"],
            "created_at": order["created_at"],
            "settled_at": order["settled_at"],
        }

    def _gateway_title(self, name: str) -> str:
        """The name a buyer reads for an order's gateway, offered now or not."""
        gateway = self.gateways.get(name)
        if gateway is not None:
            return gateway.title
        return GATEWAY_TITLES.get(name, name)
