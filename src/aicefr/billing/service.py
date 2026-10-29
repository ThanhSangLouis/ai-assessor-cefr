"""Where plans meet the database: the institution's plan, its limits, its orders (D033, D034).

Everything here is off while `AICEFR_BILLING` is off -- every check passes and
nothing is stored -- so a deployment that runs the thesis' data collection, or
any deployment from before D033, behaves exactly as it did.

Switched on, a deployment starts its one trial the first time anything asks
for its plan; when the trial ends it is on Miễn phí. Limits are applied in a
few places only (proposal, mục 4.4): creating, re-enabling or re-roling a
student account (students covered by the plan); writing lesson paths, reading
class statistics and starting a blind rating batch (staff tools of the plan);
and the administrator's warning about the month's assessments, never a refusal.
"""

from __future__ import annotations

import secrets
import uuid
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import UTC, date, datetime, time, timedelta

from aicefr.billing import keys, plans
from aicefr.billing.payments import (
    ORDER_STATUS_NAMES,
    PENDING_MINUTES,
    SETTLEABLE,
    GatewayError,
    OrderStatus,
    PaymentResult,
)
from aicefr.billing.plans import (
    ANNUAL_DISCOUNT,
    FEATURE_NAMES,
    FREE_SEATS,
    MAX_SEATS,
    MIN_SEATS,
    PLAN_FEATURES,
    PLAN_NAMES,
    PURCHASABLE,
    QUOTA_PER_SEAT,
    TERMS,
    License,
    Plan,
    PlanFeature,
    Quote,
    QuoteError,
    Standing,
)
from aicefr.practice.streak import LOCAL_TZ

WARN_AT = (80, 100)  # percent of the month's expected assessments
# What a gateway sees as the order's description: plain ASCII, as VNPay asks.
PLAN_ASCII = {Plan.STANDARD: "Chuan", Plan.ADVANCED: "Nang cao"}
# The plans compared on the administrator's tab, in the order of the ladder.
LADDER = (Plan.FREE, Plan.STANDARD, Plan.ADVANCED)
# An order's gateway by name, for orders whose gateway is no longer offered.
GATEWAY_TITLES = {
    "none": "Không cần thanh toán",
    "sandbox": "Cổng thử",
    "vnpay": "VNPay",
    "stripe": "Stripe",
    "momo": "MoMo",
}


class BillingOff(Exception):
    """The deployment does not sell plans (AICEFR_BILLING is off)."""


class SeatLimit(Exception):
    """No room for a new student account on the plan; the message says what to do."""


class FeatureLocked(Exception):
    """The plan in force does not include what was asked for."""


class PaymentUnavailable(Exception):
    """The gateway would not open the payment; the order is marked failed. Says why."""


def _dmy(day: date) -> str:
    return day.strftime("%d/%m/%Y")


def plans_with(feature: PlanFeature) -> str:
    """'gói Chuẩn và Nâng cao': the plans for sale that include a feature."""
    return "gói " + " và ".join(PLAN_NAMES[p] for p in PURCHASABLE if feature in PLAN_FEATURES[p])


@dataclass(frozen=True)
class Usage:
    students: int  # enabled student accounts
    assessments: int  # this month, research participants left out (BR-30)
    research_assessments: int  # this month, by research participants
    quota: int  # what the plan expects a month
    month: str  # "10/2026"

    @property
    def percent(self) -> int:
        return round(100 * self.assessments / self.quota) if self.quota else 0

    @property
    def warning(self) -> int | None:
        reached = [w for w in WARN_AT if self.percent >= w]
        return reached[-1] if reached else None


class BillingService:
    def __init__(
        self,
        store,  # aicefr.storage.billing_repository.BillingRepository
        # D043: what the plan counts lives in other services, asked through
        # these three: enabled student accounts (identity), assessments per
        # account in [since, until) (assessment), research participants (identity).
        students: Callable[[], int],
        assessments: Callable[[str, str], dict[str, int]],
        research: Callable[[], set[str]],
        settings,  # aicefr.config.Settings
        gateways,  # {name: aicefr.ports.PaymentGateway}, in the order offered; may be empty
        audit: Callable[[str, str, str | None, str | None], None],
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
        gateway_problems: list[str] | None = None,
    ) -> None:
        self.store = store
        self._students = students
        self._assessments = assessments
        self._research = research
        self.settings = settings
        self.gateways = dict(gateways)
        # Why a gateway the settings ask for is off, for the administrator's tab.
        self.gateway_problems = list(gateway_problems or [])
        self._audit = audit
        self._clock = clock

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

    def prices(self) -> dict[Plan, int]:
        return {
            Plan.STANDARD: int(self.settings.price_standard),
            Plan.ADVANCED: int(self.settings.price_advanced),
        }

    def organization(self) -> str:
        return self.store.setting("organization") or ""

    def set_organization(self, name: str, by: str) -> str:
        name = " ".join(name.split())
        if not 2 <= len(name) <= 160:
            raise ValueError("tên tổ chức từ 2 đến 160 ký tự")
        self.store.set_setting("organization", name, by)
        self._audit(by, "billing.organization", None, f"name={name}")
        return name

    # ------------------------------------------------------------ the plan in force

    def _trial(self, today: date) -> License:
        days = max(1, int(self.settings.trial_days))
        return License(
            license_id="trial-" + uuid.uuid4().hex[:8],
            organization=self.organization() or "Dùng thử",
            plan=Plan.TRIAL,
            seats=max(1, int(self.settings.trial_seats)),
            valid_from=today,
            valid_to=today + timedelta(days=days - 1),
            source="trial",
            installed_at=self._stamp(),
        )

    def standing(self) -> Standing | None:
        """The plan in force; None while billing is off. The first call starts the trial."""
        if not self.enabled:
            return None
        today = self.today()
        licences = self.store.licenses()
        if not licences:
            self.store.start_trial(self._trial(today))
            licences = self.store.licenses()
        return plans.standing(licences, today)

    def _month(self) -> tuple[str, str, str]:
        """This Vietnam calendar month as UTC timestamps, and how to write it."""
        first = self.today().replace(day=1)
        after = plans.add_months(first, 1)

        def utc(day: date) -> str:
            moment = datetime.combine(day, time(0), tzinfo=LOCAL_TZ)
            return moment.astimezone(UTC).isoformat(timespec="seconds")

        return utc(first), utc(after), first.strftime("%m/%Y")

    def usage(self, current: Standing) -> Usage:
        since, until, label = self._month()
        per_account = self._assessments(since, until)
        research = self._research()
        return Usage(
            students=self._students(),
            assessments=sum(n for acc, n in per_account.items() if acc not in research),
            research_assessments=sum(n for acc, n in per_account.items() if acc in research),
            quota=current.quota,
            month=label,
        )

    # ------------------------------------------------------------ the limits

    def check_new_students(self, n: int) -> None:
        """Raise SeatLimit when `n` more enabled student accounts would not fit the plan."""
        if not self.enabled or n <= 0:
            return
        current = self.standing()
        active = self._students()
        cap = current.seat_cap
        if active + n <= cap:
            return
        free = max(0, cap - active)
        if current.plan is Plan.FREE:
            raise SeatLimit(
                f"Gói Miễn phí dùng cho tối đa {FREE_SEATS} sinh viên; trường đang có {active}, "
                f"còn {free}: không đủ cho {n} tài khoản mới. Tài khoản đang có vẫn học bình "
                "thường. Nâng cấp ở tab Gói dịch vụ để thêm sinh viên."
            )
        raise SeatLimit(
            f"Gói {PLAN_NAMES[current.plan]} dùng cho {cap} sinh viên; trường đang có {active}, "
            f"còn {free}: không đủ cho {n} tài khoản mới. Tắt tài khoản không còn học, hoặc mua "
            "thêm sinh viên ở tab Gói dịch vụ."
        )

    def require(self, feature: PlanFeature) -> None:
        """Raise FeatureLocked when the plan in force does not include `feature`."""
        if not self.enabled:
            return
        current = self.standing()
        if feature in current.features:
            return
        raise FeatureLocked(
            f"{FEATURE_NAMES[feature]} có ở {plans_with(feature)}; trường đang dùng gói "
            f"{PLAN_NAMES[current.plan]}. Quản trị viên nâng cấp ở tab Gói dịch vụ. Những gì "
            "đã có vẫn dùng được như cũ."
        )

    def features(self) -> dict:
        """What a member of staff needs to know about the plan, to show it where they work."""
        if not self.enabled:
            return {"enabled": False, "plan": None, "plan_name": None, "features": []}
        current = self.standing()
        return {
            "enabled": True,
            "plan": current.plan.value,
            "plan_name": PLAN_NAMES[current.plan],
            "features": sorted(f.value for f in current.features),
        }

    # ------------------------------------------------------------ buying

    def quote(self, plan: Plan, seats: int, months: int) -> Quote:
        if not self.enabled:
            raise BillingOff()
        price = self.prices().get(plan)
        if price is None:
            raise QuoteError("chỉ mua được gói Chuẩn hoặc Nâng cao")
        return plans.quote(self.standing(), plan, seats, months, price, self.today())

    def place_order(
        self,
        plan: Plan,
        seats: int,
        months: int,
        by_account: str,
        by_pseudonym: str,
        site: str,
        client_ip: str,
        gateway_name: str | None = None,
    ) -> tuple[dict, str | None]:
        """Create an order and the address to pay it at; None when nothing is due.

        `site` is this system's address as the gateway reaches it
        (https://cefr.example.edu.vn); the return and notification addresses
        are built on it. `gateway_name` picks one of the gateways offered; the
        first is used when it is not given.

        One order waits at a time: a new one retires the one still pending,
        which stays payable -- a late payment is honoured (payments.SETTLEABLE).
        Raises PaymentUnavailable, with the order marked failed, when the
        gateway will not open the payment.
        """
        if not self.enabled:
            raise BillingOff()
        now = self.now()
        self.store.expire_pending(self._stamp())
        q = self.quote(plan, seats, months)
        gateway = None
        if q.amount:
            if not self.gateways:
                raise QuoteError("cổng thanh toán chưa được cấu hình trên bản triển khai này")
            gateway = self.gateways.get(gateway_name or next(iter(self.gateways)))
            if gateway is None:
                raise QuoteError("bản triển khai này không có cổng thanh toán đó")
        for waiting in self.store.orders(limit=20):
            if waiting["status"] == OrderStatus.PENDING.value:
                self.store.retire(waiting["order_id"])
        order_id = "DH" + now.astimezone(LOCAL_TZ).strftime("%y%m%d") + secrets.token_hex(3).upper()
        self.store.create_order(
            {
                "order_id": order_id,
                "plan": plan.value,
                "seats": seats,
                "months": months,
                "unit_price": q.unit_price,
                "list_vnd": q.list_price,
                "discount_vnd": q.discount,
                "gross_vnd": q.gross,
                "credit_vnd": q.credit,
                "amount_vnd": q.amount,
                "kind": q.kind,
                "starts_on": q.starts_on.isoformat(),
                "ends_on": q.ends_on.isoformat(),
                "status": OrderStatus.PENDING.value,
                "gateway": gateway.name if gateway else "none",
                "live": int(bool(gateway and gateway.live)),
                "created_by": by_account,
                "created_at": self._stamp(),
                "expires_at": (now + timedelta(minutes=PENDING_MINUTES))
                .astimezone(UTC)
                .isoformat(timespec="seconds"),
            }
        )
        self.store.add_event(order_id, "created", {"amount": q.amount, "kind": q.kind})
        self._audit(
            by_pseudonym,
            "billing.order",
            order_id,
            f"plan={plan.value} students={seats} months={months} amount={q.amount}",
        )
        if gateway is None:
            free = PaymentResult(order_id, OrderStatus.PAID, 0, "KHONG-CAN-TT", "free", "")
            self.settle(free, "free", "none")
            return self.store.order(order_id), None
        description = (
            f"Thanh toan don {order_id} goi {PLAN_ASCII[plan]} {seats} sinh vien {months} thang"
        )
        site = site.rstrip("/")
        try:
            checkout = gateway.checkout(
                order_id,
                q.amount,
                description,
                f"{site}/billing/return/{gateway.name}",
                f"{site}/api/v1/billing/notify/{gateway.name}",
                client_ip,
                now,
            )
        except GatewayError as e:
            # Nothing was opened, so nothing can be paid: the order ends here.
            refused = PaymentResult(order_id, OrderStatus.FAILED, q.amount, "", e.code, str(e))
            self.settle(refused, "checkout", gateway.name)
            raise PaymentUnavailable(f"{gateway.title}: {e}") from e
        if checkout.reference:
            self.store.set_checkout_ref(order_id, checkout.reference)
        return self.store.order(order_id), checkout.url

    def _license_for(self, order: dict) -> License:
        return License(
            license_id="L-" + order["order_id"],
            organization=self.organization() or "(chưa đặt tên tổ chức)",
            plan=Plan(order["plan"]),
            seats=order["seats"],
            valid_from=date.fromisoformat(order["starts_on"]),
            valid_to=date.fromisoformat(order["ends_on"]),
            source="order",
            order_id=order["order_id"],
            value_vnd=order["gross_vnd"],
        )

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
            lic = self._license_for(order) if result.outcome is OrderStatus.PAID else None
            changed = self.store.settle(
                order["order_id"],
                result.outcome,
                result.reference,
                result.code,
                license=lic,
                by=f"gateway:{order['gateway']}",
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
        return "ok"

    # ------------------------------------------------------------ keys

    def install_key(self, key: str, by_account: str, by_pseudonym: str) -> License:
        if not self.enabled:
            raise BillingOff()
        if not self.settings.license_secret:
            raise keys.LicenseKeyError(
                "bản triển khai này chưa đặt AICEFR_LICENSE_SECRET nên chưa cài được mã giấy phép"
            )
        lic = keys.read(key, self.settings.license_secret.encode("utf-8"))
        if lic.valid_to < self.today():
            raise keys.LicenseKeyError(f"giấy phép này đã hết hạn ngày {_dmy(lic.valid_to)}")
        if self.store.has_license(lic.license_id):
            raise keys.LicenseKeyError("mã giấy phép này đã được cài")
        lic = replace(lic, installed_at=self._stamp())
        self.store.add_license(lic, key=key.strip(), by=by_account)
        if not self.organization():
            self.store.set_setting("organization", lic.organization, by_account)
        self._audit(
            by_pseudonym,
            "billing.license_install",
            lic.license_id,
            f"plan={lic.plan.value} students={lic.seats} to={lic.valid_to.isoformat()}",
        )
        return lic

    # ------------------------------------------------------------ what the screens read

    def order_view(self, order: dict) -> dict:
        plan = Plan(order["plan"])
        status = OrderStatus(order["status"])
        return {
            "order_id": order["order_id"],
            "plan": plan.value,
            "plan_name": PLAN_NAMES[plan],
            "seats": order["seats"],
            "months": order["months"],
            "unit_price": order["unit_price"],
            "list_vnd": order["list_vnd"],
            "discount_vnd": order["discount_vnd"],
            "gross_vnd": order["gross_vnd"],
            "credit_vnd": order["credit_vnd"],
            "amount_vnd": order["amount_vnd"],
            "kind": order["kind"],
            "starts_on": order["starts_on"],
            "ends_on": order["ends_on"],
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
        """What the administrator reads for an order's gateway, offered now or not."""
        gateway = self.gateways.get(name)
        if gateway is not None:
            return gateway.title
        return GATEWAY_TITLES.get(name, name)

    @staticmethod
    def _license_view(lic: License) -> dict:
        return {
            "license_id": lic.license_id,
            "organization": lic.organization,
            "plan": lic.plan.value,
            "plan_name": PLAN_NAMES[lic.plan],
            "seats": lic.seats,
            "valid_from": lic.valid_from.isoformat(),
            "valid_to": lic.valid_to.isoformat(),
            "source": lic.source,
        }

    def ladder(self) -> list[dict]:
        """The plans side by side, for the comparison on the administrator's tab."""
        prices = self.prices()
        return [
            {
                "plan": p.value,
                "name": PLAN_NAMES[p],
                "price_per_student_month": prices.get(p, 0),
                "students": FREE_SEATS if p is Plan.FREE else None,  # None: as many as bought
                "quota_per_student": QUOTA_PER_SEAT[p],
                "features": sorted(f.value for f in PLAN_FEATURES[p]),
                "for_sale": p in PURCHASABLE,
            }
            for p in LADDER
        ]

    def overview(self) -> dict:
        out: dict = {
            "enabled": self.enabled,
            "organization": self.organization(),
            "ladder": self.ladder(),
            "feature_names": {f.value: FEATURE_NAMES[f] for f in PlanFeature},
            "terms": list(TERMS),
            "annual_discount": ANNUAL_DISCOUNT,
            "limits": {"min_students": MIN_SEATS, "max_students": MAX_SEATS},
            "trial": {
                "days": int(self.settings.trial_days),
                "students": int(self.settings.trial_seats),
            },
            "gateways": [
                {
                    "name": g.name,
                    "title": g.title,
                    "methods": g.methods,
                    "live": g.live,
                    "note": g.note,
                }
                for g in self.gateways.values()
            ],
            "gateway_problems": self.gateway_problems,
            "key_install": bool(self.settings.license_secret),
        }
        if not self.enabled:
            return out
        self.store.expire_pending(self._stamp())
        current = self.standing()
        usage = self.usage(current)
        out.update(
            {
                "plan": current.plan.value,
                "plan_name": PLAN_NAMES[current.plan],
                "state": current.state.value,
                "license": self._license_view(current.license) if current.license else None,
                "lapsed": self._license_view(current.lapsed) if current.lapsed else None,
                "days_left": current.days_left,
                "grace_until": current.grace_until.isoformat() if current.grace_until else None,
                "students_allowed": current.seat_cap,
                "features": sorted(f.value for f in current.features),
                "scheduled": [self._license_view(x) for x in current.scheduled],
                "usage": {
                    "students": usage.students,
                    "assessments": usage.assessments,
                    "research_assessments": usage.research_assessments,
                    "quota": usage.quota,
                    "percent": usage.percent,
                    "warning": usage.warning,
                    "month": usage.month,
                },
                "orders": [self.order_view(o) for o in self.store.orders(limit=20)],
            }
        )
        return out
