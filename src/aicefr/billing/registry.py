"""Which payment gateways a deployment offers, built from its settings (D035, D075).

`AICEFR_PAYMENT_GATEWAYS` lists them in the order the buyer sees them: Stripe,
and the sandbox for a deployment where no money should move (D075: VNPay and
MoMo were removed). Each one is built from its own settings; one that cannot
be built is left out, and why goes into a list of problems written to the log,
so a missing key reads as a sentence rather than as a payment button that does
nothing.

Two rules keep test money and real money apart:

* a gateway that moves real money (a live Stripe key) runs only when
  `AICEFR_PAYMENTS_LIVE` is on. This system is built to be shown and tested;
  selling for real is a decision, not a default;
* no test environment runs next to a gateway that moves real money: whoever
  can place an order could otherwise buy real runs with a test card.
"""

from __future__ import annotations

from collections.abc import Callable

from aicefr.billing.gateways import SandboxGateway
from aicefr.billing.stripe_gateway import StripeGateway
from aicefr.ports import PaymentGateway

KNOWN = ("sandbox", "stripe")


def build_gateways(
    settings, sandbox_secret: Callable[[], bytes]
) -> tuple[dict[str, PaymentGateway], list[str]]:
    """The gateways to offer, in order, and a sentence for each one left out or limited.

    `settings` is an `aicefr.config.Settings`; `sandbox_secret` is called only
    when the sandbox is wanted.
    """
    gateways: dict[str, PaymentGateway] = {}
    problems: list[str] = []
    seen: set[str] = set()
    for name in settings.payment_gateways:
        if name in seen:
            continue
        seen.add(name)
        if name not in KNOWN:
            problems.append(f"Không có cổng thanh toán tên “{name}” (có: {', '.join(KNOWN)}).")
            continue
        try:
            gateway = _build(name, settings, sandbox_secret)
        except ValueError as e:
            problems.append(f"{_TITLES[name]} chưa bật: {e}.")
            continue
        if gateway.live and not settings.payments_live:
            problems.append(
                f"{gateway.title} chưa bật: cấu hình này thu tiền thật, cần đặt "
                "AICEFR_PAYMENTS_LIVE=on nếu thật sự muốn bán."
            )
            continue
        gateways[name] = gateway
    if any(g.live for g in gateways.values()):
        for name in [n for n, g in gateways.items() if not g.live]:
            title = gateways.pop(name).title
            problems.append(
                f"{title} đã tắt: cổng này ở môi trường thử, không chạy cạnh cổng thu tiền thật."
            )
    stripe = gateways.get("stripe")
    if isinstance(stripe, StripeGateway) and not settings.stripe_webhook_secret:
        problems.append(
            "Stripe chưa có AICEFR_STRIPE_WEBHOOK_SECRET: đơn chỉ được ghi nhận khi trình duyệt "
            "quay về sau khi trả; người trả đóng trang sớm thì phải đối soát tay."
        )
    return gateways, problems


_TITLES = {"sandbox": "Cổng thử", "stripe": "Stripe"}


def _build(name: str, settings, sandbox_secret: Callable[[], bytes]) -> PaymentGateway:
    if name == "sandbox":
        return SandboxGateway(sandbox_secret())
    if name == "stripe":
        if not settings.stripe_secret_key:
            raise ValueError("thiếu AICEFR_STRIPE_SECRET_KEY")
        return StripeGateway(settings.stripe_secret_key, settings.stripe_webhook_secret)
    raise ValueError(f"không có cổng thanh toán tên {name}")  # pragma: no cover - KNOWN
