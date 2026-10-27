"""Which payment gateways a deployment offers, built from its settings (D035).

`AICEFR_PAYMENT_GATEWAYS` lists them in the order the administrator sees them,
e.g. `stripe,vnpay,momo`. Each one is built from its own settings; one that
cannot be built is left out, and why goes into a list of problems the
administrator's tab shows, so a missing key reads as a sentence rather than as
a payment button that does nothing.

Two rules keep test money and real money apart:

* a gateway that moves real money (a live Stripe key, VNPay's or MoMo's real
  address) runs only when `AICEFR_PAYMENTS_LIVE` is on. This system is built
  to be shown and tested; selling for real is a decision, not a default;
* no test environment runs next to a gateway that moves real money -- not the
  sandbox, and not Stripe on a test key or VNPay's sandbox either: whoever can
  place an order could otherwise buy a real plan with a test card.
"""

from __future__ import annotations

from collections.abc import Callable

from aicefr.billing.gateways import VNPAY_SANDBOX_URL, SandboxGateway, VnpayGateway
from aicefr.billing.momo_gateway import TEST_ENDPOINT as MOMO_TEST_ENDPOINT
from aicefr.billing.momo_gateway import MomoGateway
from aicefr.billing.stripe_gateway import StripeGateway
from aicefr.ports import PaymentGateway

KNOWN = ("sandbox", "vnpay", "stripe", "momo")


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


_TITLES = {"sandbox": "Cổng thử", "vnpay": "VNPay", "stripe": "Stripe", "momo": "MoMo"}


def _build(name: str, settings, sandbox_secret: Callable[[], bytes]) -> PaymentGateway:
    if name == "sandbox":
        return SandboxGateway(sandbox_secret())
    if name == "vnpay":
        if not settings.vnpay_tmn_code or not settings.vnpay_hash_secret:
            raise ValueError("thiếu AICEFR_VNPAY_TMN_CODE hoặc AICEFR_VNPAY_HASH_SECRET")
        return VnpayGateway(
            settings.vnpay_tmn_code,
            settings.vnpay_hash_secret,
            settings.vnpay_url or VNPAY_SANDBOX_URL,
        )
    if name == "stripe":
        if not settings.stripe_secret_key:
            raise ValueError("thiếu AICEFR_STRIPE_SECRET_KEY")
        return StripeGateway(settings.stripe_secret_key, settings.stripe_webhook_secret)
    if not (settings.momo_partner_code and settings.momo_access_key and settings.momo_secret_key):
        raise ValueError(
            "thiếu AICEFR_MOMO_PARTNER_CODE, AICEFR_MOMO_ACCESS_KEY hoặc AICEFR_MOMO_SECRET_KEY"
        )
    return MomoGateway(
        settings.momo_partner_code,
        settings.momo_access_key,
        settings.momo_secret_key,
        settings.momo_endpoint or MOMO_TEST_ENDPOINT,
    )
