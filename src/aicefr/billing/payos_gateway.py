"""payOS as a payment gateway (D095): a bank transfer by VietQR, Napas 24/7.

payOS does not sign its result into the address as the sandbox does. This
system asks payOS's API for
a payment link (the amount in dong, an integer order code, a short transfer
note) signed with the channel's checksum key, and sends the browser to the page
payOS answers with; the payer scans its QR code in any Vietnamese banking app.
Afterwards two things can say how it went, and both are checked:

* the browser comes back with the link's id and a status in the address. Those
  are a claim, not a proof (anyone can type them), so the link is read back
  from payOS's API with the client id and API key, and its own status and
  amount decide;
* payOS's server posts a webhook. It is believed only when its `signature` is
  the HMAC-SHA256, under the checksum key, of its `data` fields sorted by name
  and joined as `key=value&...` (payOS: "Kiểm tra dữ liệu với signature").

payOS has no test environment: every link moves real money into the bank
account linked to the channel. So the adapter is always `live`, runs only with
`AICEFR_PAYMENTS_LIVE` on (see `registry`), and never next to the sandbox.

payOS's order code is an integer, this system's order id is `DL` + the local
date + six hex digits. The one is turned into the other and back without a
table: date * 16**6 + the hex number, at most about 4.4 * 10**12, well inside
the integers payOS and JavaScript take. Nothing about the payer -- name,
account, bank -- is kept (BR-32); the transfer note carries the order only.
The standard library is enough, so there is no payOS SDK.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import re
from collections.abc import Mapping
from datetime import datetime, timedelta

from aicefr.billing.payments import (
    PENDING_MINUTES,
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
from aicefr.billing.transport import LOOPBACK, Transport, Unreachable, https

API = "https://api-merchant.payos.vn"
# A link outlives the order's wait by a minute: a payment that still arrives is
# honoured (payments.PENDING_MINUTES), one after the link expired cannot happen.
LINK_MINUTES = PENDING_MINUTES + 1
ORDER_ID = re.compile(r"DL(\d{6})([0-9A-F]{6})")
LINK_ID = re.compile(r"[0-9a-f]{32}")
HEX6 = 16**6
# What a link's status means for the order. Anything else (PENDING,
# PROCESSING, UNDERPAID) is no final word yet.
STATUSES = {
    "PAID": OrderStatus.PAID,
    "CANCELLED": OrderStatus.CANCELLED,
    "EXPIRED": OrderStatus.CANCELLED,
    "FAILED": OrderStatus.FAILED,
}
MESSAGES = {
    OrderStatus.PAID: "payOS xác nhận đã nhận chuyển khoản.",
    OrderStatus.FAILED: "payOS báo giao dịch không thành công.",
    OrderStatus.CANCELLED: "Link thanh toán payOS đã huỷ hoặc hết hạn mà chưa được trả.",
    OrderStatus.PENDING: "payOS chưa nhận được chuyển khoản cho đơn này.",
}
UNREACHABLE = "Không kết nối được payOS; thử lại sau ít phút."
STATUS_ERRORS = {
    401: "Client ID hoặc API Key của payOS không đúng.",
    403: "payOS (Cloudflare) từ chối yêu cầu từ máy chủ này; thử lại sau hoặc báo quản trị viên.",
    429: "payOS đang giới hạn số yêu cầu; thử lại sau ít phút.",
}


def order_code(order_id: str) -> int:
    """payOS's integer for an order id `DLyymmddXXXXXX`; ValueError for any other id."""
    found = ORDER_ID.fullmatch(order_id)
    if found is None:
        raise ValueError(f"mã đơn {order_id!r} không đổi được sang mã số của payOS")
    return int(found[1]) * HEX6 + int(found[2], 16)


def order_id_of(code: object) -> str:
    """The order id an integer from payOS stands for; "" for one no order can have."""
    text = str(code)
    if not digits(text) or len(text) > 15:
        return ""
    day, number = divmod(int(text), HEX6)
    if day >= 10**6:
        return ""
    return f"DL{day:06d}{number:06X}"


def sign(fields: Mapping[str, object], key: bytes) -> str:
    """payOS's signature: `k=v` sorted by name, joined by `&`, HMAC-SHA256 in lower-case hex.

    A missing value is empty; a list is JSON with the keys of its items
    sorted, as payOS's own samples do. The values are not URL-encoded.
    """

    def text(value: object) -> str:
        if value is None or value in ("null", "undefined"):
            return ""
        if isinstance(value, list):
            items = [dict(sorted(v.items())) if isinstance(v, dict) else v for v in value]
            return json.dumps(items, ensure_ascii=False, separators=(",", ":"))
        if isinstance(value, bool):
            return "true" if value else "false"
        return str(value)

    query = "&".join(f"{k}={text(fields[k])}" for k in sorted(fields))
    return hmac.new(key, query.encode("utf-8"), hashlib.sha256).hexdigest()


class PayosGateway:
    """payOS payment links through its HTTP API; webhooks signed with the checksum key."""

    name = "payos"
    title = "payOS"
    methods = "Chuyển khoản ngân hàng bằng mã VietQR (Napas 24/7)"
    live = True  # payOS has no test environment
    note = ""

    def __init__(
        self,
        client_id: str,
        api_key: str,
        checksum_key: str,
        transport: Transport = https,
        api: str = API,
    ):
        for value, what in (
            (client_id, "AICEFR_PAYOS_CLIENT_ID"),
            (api_key, "AICEFR_PAYOS_API_KEY"),
            (checksum_key, "AICEFR_PAYOS_CHECKSUM_KEY"),
        ):
            if not value:
                raise ValueError(f"thiếu {what}")
        self._headers = {"x-client-id": client_id, "x-api-key": api_key}
        self._key = checksum_key.encode("utf-8")
        self._send = transport
        self._api = api

    # ------------------------------------------------------------ the API

    def _call(self, method: str, path: str, fields: dict | None = None) -> dict:
        headers = dict(self._headers)
        body = None
        if fields is not None:
            body = json.dumps(fields, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json"
        try:
            reply = self._send(method, self._api + path, headers, body)
        except Unreachable as e:
            raise GatewayError(UNREACHABLE, "unreachable") from e
        try:
            answer = json.loads(reply.body or b"{}")
        except ValueError:
            answer = None
        if not 200 <= reply.status < 300 or not isinstance(answer, dict):
            raise GatewayError(_refusal(reply.status, answer), str(reply.status))
        # payOS answers 200 with its own code; "00" is the only success.
        if answer.get("code") != "00" or not isinstance(answer.get("data"), dict):
            code = str(answer.get("code") or "data")
            raise GatewayError(_refusal(reply.status, answer), code)
        return answer["data"]

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
        """Open a payment link for the order and return its page.

        The transfer note is `SU` and the order's six hex digits: payOS allows
        nine characters on a bank account it does not link itself, and the
        payer sees it in their banking app. The webhook address is not sent:
        payOS takes it from the channel's settings. Leaving payOS's page
        without paying comes back with `left=1`: nothing is settled, the order
        simply expires.
        """
        fields: dict = {
            "orderCode": order_code(order_id),
            "amount": amount_vnd,
            "description": "SU" + order_id[-6:],
            "returnUrl": return_url,
            "cancelUrl": return_url + "?left=1",
        }
        fields["signature"] = sign(fields, self._key)
        fields["expiredAt"] = int((now + timedelta(minutes=LINK_MINUTES)).timestamp())
        link = self._call("POST", "/v2/payment-requests", fields)
        url, link_id = link.get("checkoutUrl"), link.get("paymentLinkId")
        # A page over plain HTTP only from a fake payOS on this machine (D099's tests).
        pages = ("https://", LOOPBACK) if self._api.startswith(LOOPBACK) else ("https://",)
        if not (isinstance(url, str) and url.startswith(pages) and isinstance(link_id, str)):
            raise GatewayError("payOS trả về một link thanh toán không dùng được.", "link")
        return Checkout(url, link_id)

    # ------------------------------------------------------------ results

    def return_reference(self, query: Mapping[str, str]) -> str | None:
        """The payment link the address names: what payOS is asked about, and only if it is ours."""
        return str(query.get("id", ""))

    def verify_return(self, query: Mapping[str, str]) -> PaymentResult | None:
        """Read the link the address names back from payOS; None for an id that is not one.

        The status in the address is ignored: payOS's own record decides.
        Raises GatewayError when payOS cannot be asked; the webhook will say.
        """
        link_id = str(query.get("id", ""))
        if not LINK_ID.fullmatch(link_id):
            return None
        link = self._call("GET", f"/v2/payment-requests/{link_id}")
        outcome = STATUSES.get(str(link.get("status", "")), OrderStatus.PENDING)
        amount = link.get("amount")
        if outcome is OrderStatus.PAID and link.get("amountPaid") != amount:
            outcome = OrderStatus.PENDING  # part of it arrived: not paid yet
        return PaymentResult(
            order_id=order_id_of(link.get("orderCode")),
            outcome=outcome,
            amount_vnd=amount if isinstance(amount, int) else -1,
            reference=str(link.get("id", "")),
            code=str(link.get("status", "")),
            message=MESSAGES[outcome],
            checkout=str(link.get("id", "")),
        )

    def look_up(self, reference: str) -> PaymentResult | None:
        """What payOS's own record says about a payment link this system opened.

        For reconciliation (D099): an order whose webhook never came, and
        whose payer never came back, is asked about by its link id.
        """
        return self.verify_return({"id": reference})

    def verify_notification(self, message: Incoming, now: datetime) -> PaymentResult | None:
        """A webhook, if payOS signed it; None otherwise.

        payOS posts a webhook for a transfer that arrived; its `data.code` "00"
        is a payment. Anything else authentic is acknowledged and changes
        nothing. Saving the address in payOS's dashboard posts a signed sample
        for an order that does not exist: answered 2xx, which is what payOS
        waits for.
        """
        try:
            hook = json.loads(message.body)
        except ValueError:
            return None
        if not isinstance(hook, dict):
            return None
        data, signature = hook.get("data"), hook.get("signature")
        if not isinstance(data, dict) or not isinstance(signature, str):
            return None
        if not same_text(sign(data, self._key), signature):
            return None
        if data.get("code") != "00" or hook.get("code") != "00":
            return PaymentResult("", OrderStatus.PENDING, 0, str(data.get("reference", "")), "", "")
        amount = data.get("amount")
        return PaymentResult(
            order_id=order_id_of(data.get("orderCode")),
            outcome=OrderStatus.PAID,
            amount_vnd=amount if isinstance(amount, int) else -1,
            reference=str(data.get("reference", "")),
            code=str(data.get("code", "")),
            message=MESSAGES[OrderStatus.PAID],
            details={"paid_at": str(data.get("transactionDateTime", ""))},
            checkout=str(data.get("paymentLinkId", "")),
        )

    def acknowledge(self, what: str) -> Ack:
        """payOS reads only the status: 2xx is received, anything else is sent again."""
        return Ack(notify_status(what), {"success": what not in ("signature", "error")})


def _refusal(status: int, answer: object) -> str:
    """Why payOS would not open or show a link, in the administrator's words."""
    if status in STATUS_ERRORS:
        return STATUS_ERRORS[status]
    if status >= 500:
        return "payOS đang gặp sự cố; thử lại sau ít phút."
    desc = answer.get("desc") if isinstance(answer, dict) else None
    if isinstance(desc, str) and desc:
        return f"payOS không mở được link thanh toán: {desc[:200]}"
    return f"payOS không mở được link thanh toán (mã {status})."
