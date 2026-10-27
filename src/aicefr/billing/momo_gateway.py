"""MoMo e-wallet as a payment gateway, API v2 "captureWallet" (D035).

Like Stripe, MoMo is asked first: this system posts the order to MoMo's create
endpoint, signed with HMAC-SHA256 over the fields MoMo names, and sends the
browser to the `payUrl` it answers with (a page with a QR code, or the MoMo
app on a phone). Like VNPay, the result comes back twice, signed the same way:
the browser returns to `redirectUrl` with the result in the address, and
MoMo's server posts it as JSON to `ipnUrl`, which this system answers with
204 No Content. A result is believed only with the right signature, this
system's partner code and the order's amount (BR-33).

MoMo's test environment (test-payment.momo.vn) is the default; there, payment
is made with MoMo's test app and test accounts, and no money moves.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from collections.abc import Mapping
from datetime import datetime
from urllib.parse import urlparse

from aicefr.billing.payments import (
    Ack,
    Checkout,
    GatewayError,
    Incoming,
    OrderStatus,
    PaymentResult,
    digits,
    notify_status,
    same_text,
)
from aicefr.billing.transport import Transport, Unreachable, https

TEST_ENDPOINT = "https://test-payment.momo.vn/v2/gateway/api/create"
TEST_HOST = "test-payment.momo.vn"
# What MoMo takes in one wallet payment, in dong.
MIN_AMOUNT, MAX_AMOUNT = 1_000, 50_000_000
# The fields each signature covers, in the order MoMo signs them: the raw
# values, joined as key=value&..., not URL-encoded.
CREATE_FIELDS = (
    "accessKey",
    "amount",
    "extraData",
    "ipnUrl",
    "orderId",
    "orderInfo",
    "partnerCode",
    "redirectUrl",
    "requestId",
    "requestType",
)
RESULT_FIELDS = (
    "accessKey",
    "amount",
    "extraData",
    "message",
    "orderId",
    "orderInfo",
    "orderType",
    "partnerCode",
    "payType",
    "requestId",
    "responseTime",
    "resultCode",
    "transId",
)
# resultCode, as MoMo's table marks it final or not: 0 paid; these cancelled
# (by the payer, the merchant, or the clock); these failed for good. Any other
# code -- 1000, 7000, 7002, 9000, or one MoMo adds later -- is not final, and a
# later result for the same order can still settle it.
CANCELLED = frozenset({"1003", "1005", "1006", "1017"})
FAILED = frozenset(
    {"98", "99", "1001", "1002", "1004", "1007", "1026", "1080", "1081", "1088", "2019"}
    | {"4001", "4002", "4100"}
)
MESSAGES = {
    "0": "Giao dịch thành công.",
    "10": "Hệ thống MoMo đang bảo trì.",
    "11": "MoMo từ chối truy cập.",
    "13": "MoMo không xác thực được doanh nghiệp (kiểm tra mã đối tác và khoá).",
    "20": "Yêu cầu gửi MoMo sai định dạng.",
    "21": "Số tiền không hợp lệ.",
    "22": (
        "Số tiền nằm ngoài mức MoMo nhận cho một giao dịch (1.000 đ đến 50.000.000 đ); "
        "hãy chọn cổng khác."
    ),
    "41": "Mã đơn này đã được gửi MoMo trước đó.",
    "1000": "Đang chờ người trả xác nhận trong ứng dụng MoMo.",
    "1001": "Tài khoản MoMo không đủ tiền.",
    "1002": "Giao dịch bị nơi phát hành từ chối.",
    "1003": "Giao dịch đã bị huỷ sau khi được xác nhận.",
    "1004": "Số tiền vượt hạn mức thanh toán của tài khoản MoMo.",
    "1005": "Mã QR hoặc đường dẫn thanh toán đã hết hạn.",
    "1006": "Người trả đã từ chối xác nhận thanh toán.",
    "1007": "Tài khoản MoMo đang bị tạm khoá.",
    "1017": "Giao dịch đã bị bên bán huỷ.",
    "7000": "Giao dịch đang được xử lý.",
    "7002": "Giao dịch đang được xử lý.",
    "9000": "Giao dịch đã được xác nhận, đang chờ hoàn tất.",
    "99": "MoMo báo lỗi không xác định.",
}


UNREACHABLE = "Không kết nối được MoMo; thử lại sau ít phút."


class MomoGateway:
    """MoMo's payment page; the default endpoint is MoMo's test environment."""

    name = "momo"
    title = "MoMo"
    methods = "Ví MoMo, quét mã QR"

    def __init__(
        self,
        partner_code: str,
        access_key: str,
        secret_key: str,
        endpoint: str = TEST_ENDPOINT,
        transport: Transport = https,
    ) -> None:
        if not partner_code or not access_key or not secret_key:
            raise ValueError("MoMo cần mã đối tác (partner code), access key và secret key")
        if not endpoint.startswith("https://"):
            raise ValueError("địa chỉ tạo giao dịch MoMo phải là https")
        self.partner_code = partner_code
        self._access_key = access_key
        self._secret = secret_key.encode("utf-8")
        self.endpoint = endpoint
        self._send = transport
        self.live = urlparse(endpoint).hostname != TEST_HOST
        self.note = (
            ""
            if self.live
            else "Môi trường thử của MoMo: trả bằng ứng dụng MoMo bản thử và tài khoản thử trong "
            "tài liệu của MoMo."
        )

    def _sign(self, values: Mapping[str, object], fields: tuple[str, ...]) -> str:
        raw = "&".join(f"{k}={values[k]}" for k in fields)
        return hmac.new(self._secret, raw.encode("utf-8"), hashlib.sha256).hexdigest()

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
        if not MIN_AMOUNT <= amount_vnd <= MAX_AMOUNT:
            # MoMo would refuse it with code 22; say so without asking.
            raise GatewayError(MESSAGES["22"], "22")
        request: dict[str, object] = {
            "partnerCode": self.partner_code,
            "requestId": order_id,
            "amount": amount_vnd,
            "orderId": order_id,
            "orderInfo": description,
            "redirectUrl": return_url,
            "ipnUrl": notify_url,
            "requestType": "captureWallet",
            "extraData": "",
            "lang": "vi",
        }
        request["signature"] = self._sign({**request, "accessKey": self._access_key}, CREATE_FIELDS)
        headers = {"Content-Type": "application/json; charset=UTF-8"}
        try:
            reply = self._send("POST", self.endpoint, headers, json.dumps(request).encode("utf-8"))
        except Unreachable as e:
            raise GatewayError(UNREACHABLE, "unreachable") from e
        try:
            data = json.loads(reply.body or b"{}")
        except ValueError:
            data = None
        data = data if isinstance(data, dict) else {}
        code = str(data.get("resultCode", reply.status))
        url = data.get("payUrl")
        if code != "0" or not isinstance(url, str) or not url.startswith("https://"):
            raise GatewayError(
                MESSAGES.get(code, f"MoMo không tạo được giao dịch (mã {code})."), code
            )
        return Checkout(url, str(data.get("requestId") or order_id))

    def _result(self, values: Mapping[str, object]) -> PaymentResult | None:
        received = str(values.get("signature", ""))
        if not received or any(k not in values for k in RESULT_FIELDS[1:]):
            return None
        signed = {k: values[k] for k in RESULT_FIELDS[1:]} | {"accessKey": self._access_key}
        if not same_text(self._sign(signed, RESULT_FIELDS), received.lower()):
            return None
        amount = str(values["amount"])
        if str(values["partnerCode"]) != self.partner_code or not digits(amount):
            return None
        code = str(values["resultCode"])
        if code == "0":
            outcome = OrderStatus.PAID
        elif code in CANCELLED:
            outcome = OrderStatus.CANCELLED
        elif code in FAILED:
            outcome = OrderStatus.FAILED
        else:
            outcome = OrderStatus.PENDING
        return PaymentResult(
            order_id=str(values["orderId"]),
            outcome=outcome,
            amount_vnd=int(amount),
            reference=str(values["transId"]),
            code=code,
            message=MESSAGES.get(code, f"MoMo báo mã {code}; chưa có kết quả cuối."),
            details={
                "pay_type": str(values["payType"]),
                "response_time": str(values["responseTime"]),
            },
            checkout=str(values["requestId"]),
        )

    def return_reference(self, query: Mapping[str, str]) -> str | None:
        return None  # the return address carries the signed result

    def verify_return(self, query: Mapping[str, str]) -> PaymentResult | None:
        return self._result(query)

    def verify_notification(self, message: Incoming, now: datetime) -> PaymentResult | None:
        try:
            values = json.loads(message.body)
        except (ValueError, RecursionError):  # nested deep enough to exhaust the parser
            return None
        return self._result(values) if isinstance(values, dict) else None

    def acknowledge(self, what: str) -> Ack:
        """MoMo wants 204 No Content for a notification it may stop sending."""
        return Ack(notify_status(what, received=204))
