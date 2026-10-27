"""Payment gateways (D033, D035): a sandbox inside the app, and VNPay.

Both follow the shape most Vietnamese gateways share. The browser is sent to
the gateway's page with the order signed into the address; afterwards the
gateway sends the browser back to a return address and, separately, calls a
notification address from its own server. Both messages carry the result
signed with a secret only the gateway and this system hold. A result is
believed only when its signature checks out and its amount is the order's
(BR-33); the payer types card or bank details on the gateway's page, never
here (BR-32).

Stripe and MoMo, which open a payment by calling their server first, are in
`stripe_gateway` and `momo_gateway`; which gateways a deployment offers is
decided in `registry`.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from collections.abc import Mapping
from datetime import datetime, timedelta
from urllib.parse import quote_plus, urlencode

from aicefr.billing.payments import (
    PENDING_MINUTES,
    Ack,
    Checkout,
    Incoming,
    OrderStatus,
    PaymentResult,
    digits,
    same_text,
)
from aicefr.practice.streak import LOCAL_TZ

# ---------------------------------------------------------------- sandbox

SANDBOX_OUTCOMES = {
    "paid": (OrderStatus.PAID, "Thanh toán thử thành công. Không có tiền thật nào được chuyển."),
    "failed": (OrderStatus.FAILED, "Thanh toán thử không thành công."),
    "cancelled": (OrderStatus.CANCELLED, "Bạn đã huỷ giao dịch thử."),
}
SANDBOX_FIELDS = ("order_id", "amount", "outcome", "ref", "at")


class SignedRedirect:
    """A gateway whose result comes back signed in a query string, VNPay-style:
    the return address and the IPN (a GET) carry the same signed fields, and
    the notification is answered with VNPay's RspCode. The sandbox imitates
    VNPay in this as in everything else. Subclasses provide `verify`."""

    def verify(self, params: Mapping[str, str]) -> PaymentResult | None:
        raise NotImplementedError

    def return_reference(self, query: Mapping[str, str]) -> str | None:
        return None  # the return address carries the signed result

    def verify_return(self, query: Mapping[str, str]) -> PaymentResult | None:
        return self.verify(query)

    def verify_notification(self, message: Incoming, now: datetime) -> PaymentResult | None:
        return self.verify(message.query)

    def acknowledge(self, what: str) -> Ack:
        return vnpay_ack(what)


class SandboxGateway(SignedRedirect):
    """A gateway inside the app, for tests and demonstrations: no money moves.

    Its page lets the person pick the outcome. What it sends back is signed the
    way a real gateway signs, so the return page and the notification run the
    same checks against it that they run against VNPay. It must never be the
    gateway of a deployment that sells for real: anyone holding a checkout
    address can mark that order paid.
    """

    name = "sandbox"
    title = "Cổng thử"
    methods = "Trang thanh toán thử ngay trong ứng dụng"
    live = False
    note = "Chọn kết quả muốn thử trên trang của cổng; không có tiền thật nào được chuyển."

    def __init__(self, secret: bytes) -> None:
        self._secret = secret

    def _mac(self, text: str) -> str:
        return hmac.new(self._secret, text.encode("utf-8"), hashlib.sha256).hexdigest()

    def token(self, order_id: str, amount_vnd: int) -> str:
        """What the checkout address carries, so its page opens for that order only."""
        return self._mac(f"checkout|{order_id}|{amount_vnd}")[:32]

    def checkout(
        self,
        order_id: str,
        amount_vnd: int,
        description: str,
        return_url: str,
        notify_url: str,
        client_ip: str,
        now: datetime,
    ) -> Checkout:
        query = urlencode({"t": self.token(order_id, amount_vnd)})
        return Checkout(f"/billing/sandbox/{order_id}?{query}")

    def result(self, order_id: str, amount_vnd: int, outcome: str, now: datetime) -> dict[str, str]:
        """The signed parameters the sandbox sends back, to the browser and to the notification."""
        if outcome not in SANDBOX_OUTCOMES:
            raise ValueError(outcome)
        params = {
            "order_id": order_id,
            "amount": str(amount_vnd),
            "outcome": outcome,
            "ref": "SB" + secrets.token_hex(5).upper(),
            "at": now.astimezone(LOCAL_TZ).strftime("%Y%m%d%H%M%S"),
        }
        params["sig"] = self._mac("|".join(params[k] for k in SANDBOX_FIELDS))
        return params

    def verify(self, params: Mapping[str, str]) -> PaymentResult | None:
        if any(k not in params for k in (*SANDBOX_FIELDS, "sig")):
            return None
        expected = self._mac("|".join(str(params[k]) for k in SANDBOX_FIELDS))
        if not same_text(expected, str(params["sig"])):
            return None
        if params["outcome"] not in SANDBOX_OUTCOMES or not digits(str(params["amount"])):
            return None
        status, message = SANDBOX_OUTCOMES[params["outcome"]]
        return PaymentResult(
            order_id=str(params["order_id"]),
            outcome=status,
            amount_vnd=int(params["amount"]),
            reference=str(params["ref"]),
            code=str(params["outcome"]),
            message=message,
            details={"pay_date": str(params["at"])},
        )


# ---------------------------------------------------------------- VNPay

VNPAY_SANDBOX_URL = "https://sandbox.vnpayment.vn/paymentv2/vpcpay.html"
# vnp_ResponseCode, as VNPay documents it for version 2.1.0.
VNPAY_MESSAGES = {
    "00": "Giao dịch thành công.",
    "07": "Ngân hàng đã trừ tiền nhưng giao dịch bị nghi ngờ; cần đối soát với VNPay.",
    "09": "Thẻ hoặc tài khoản chưa đăng ký Internet Banking.",
    "10": "Xác thực thông tin thẻ hoặc tài khoản sai quá 3 lần.",
    "11": "Hết thời gian chờ thanh toán.",
    "12": "Thẻ hoặc tài khoản bị khoá.",
    "13": "Nhập sai mã xác thực (OTP).",
    "24": "Bạn đã huỷ giao dịch.",
    "51": "Tài khoản không đủ số dư.",
    "65": "Vượt hạn mức giao dịch trong ngày.",
    "75": "Ngân hàng thanh toán đang bảo trì.",
    "79": "Nhập sai mật khẩu thanh toán quá số lần quy định.",
    "99": "Cổng thanh toán báo lỗi khác.",
}
# What the notification endpoint answers VNPay, by what happened to the order.
VNPAY_ACK = {
    "ok": ("00", "Confirm Success"),
    "not_found": ("01", "Order not found"),
    "already": ("02", "Order already confirmed"),
    "amount": ("04", "Invalid amount"),
    "signature": ("97", "Invalid signature"),
    "error": ("99", "Unknown error"),
}
# Kept for reconciliation; none of them names or identifies the payer.
VNPAY_DETAILS = ("vnp_BankCode", "vnp_BankTranNo", "vnp_CardType", "vnp_PayDate")


class VnpayGateway(SignedRedirect):
    """VNPay, payment page version 2.1.0.

    Off unless `vnpay` is in `AICEFR_PAYMENT_GATEWAYS` with the merchant code
    and hash secret VNPay issues to a registered business; the default address
    is VNPay's sandbox, where no money moves. Building the payment address
    calls nothing: the browser is redirected. VNPay calls the notification
    address (`/api/v1/billing/notify/vnpay`, registered in VNPay's merchant
    portal) and that is the only incoming call.
    """

    name = "vnpay"
    title = "VNPay"
    methods = "Thẻ ATM nội địa, thẻ quốc tế, QR ngân hàng"
    VERSION = "2.1.0"

    def __init__(self, tmn_code: str, hash_secret: str, pay_url: str = VNPAY_SANDBOX_URL) -> None:
        if not tmn_code or not hash_secret:
            raise ValueError("VNPay cần mã website (TMN code) và chuỗi bí mật")
        if not pay_url.startswith("https://"):
            raise ValueError("địa chỉ trang thanh toán VNPay phải là https")
        self.tmn_code = tmn_code
        self._secret = hash_secret.encode("utf-8")
        self.pay_url = pay_url
        # Any address but the sandbox's is VNPay's real payment page.
        self.live = pay_url != VNPAY_SANDBOX_URL
        self.note = (
            ""
            if self.live
            else "Môi trường thử của VNPay: trả bằng thẻ thử trong tài liệu sandbox của VNPay."
        )

    @staticmethod
    def canonical(params: Mapping[str, str]) -> str:
        """VNPay's signed form: keys sorted, values form-encoded, pairs joined by '&'."""
        return "&".join(f"{k}={quote_plus(str(v))}" for k, v in sorted(params.items()))

    def _hash(self, text: str) -> str:
        return hmac.new(self._secret, text.encode("utf-8"), hashlib.sha512).hexdigest()

    def checkout(
        self,
        order_id: str,
        amount_vnd: int,
        description: str,
        return_url: str,
        notify_url: str,
        client_ip: str,
        now: datetime,
    ) -> Checkout:
        local = now.astimezone(LOCAL_TZ)
        params = {
            "vnp_Version": self.VERSION,
            "vnp_Command": "pay",
            "vnp_TmnCode": self.tmn_code,
            "vnp_Amount": str(amount_vnd * 100),  # VNPay counts in hundredths of a dong
            "vnp_CurrCode": "VND",
            "vnp_TxnRef": order_id,
            "vnp_OrderInfo": description,
            "vnp_OrderType": "other",
            "vnp_Locale": "vn",
            "vnp_ReturnUrl": return_url,
            "vnp_IpAddr": client_ip,
            "vnp_CreateDate": local.strftime("%Y%m%d%H%M%S"),
            "vnp_ExpireDate": (local + timedelta(minutes=PENDING_MINUTES)).strftime("%Y%m%d%H%M%S"),
        }
        query = self.canonical(params)
        return Checkout(f"{self.pay_url}?{query}&vnp_SecureHash={self._hash(query)}")

    def verify(self, params: Mapping[str, str]) -> PaymentResult | None:
        received = str(params.get("vnp_SecureHash", "")).lower()
        signed = {
            k: str(v)
            for k, v in params.items()
            if k.startswith("vnp_") and k not in ("vnp_SecureHash", "vnp_SecureHashType")
        }
        if not received or not same_text(self._hash(self.canonical(signed)), received):
            return None
        if "vnp_TxnRef" not in signed or not digits(signed.get("vnp_Amount", "")):
            return None
        code = signed.get("vnp_ResponseCode", "99")
        if code == "00" and signed.get("vnp_TransactionStatus", "00") == "00":
            outcome = OrderStatus.PAID
        elif code == "24":
            outcome = OrderStatus.CANCELLED
        else:
            outcome = OrderStatus.FAILED
        return PaymentResult(
            order_id=signed["vnp_TxnRef"],
            outcome=outcome,
            amount_vnd=int(signed["vnp_Amount"]) // 100,
            reference=signed.get("vnp_TransactionNo", ""),
            code=code,
            message=VNPAY_MESSAGES.get(code, VNPAY_MESSAGES["99"]),
            details={k: signed[k] for k in VNPAY_DETAILS if k in signed},
        )


def vnpay_ack(what: str) -> Ack:
    """Always HTTP 200: VNPay reads what happened from RspCode, not from the status."""
    code, message = VNPAY_ACK.get(what, VNPAY_ACK["error"])
    return Ack(200, {"RspCode": code, "Message": message})
