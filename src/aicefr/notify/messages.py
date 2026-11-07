"""What the emails say (D079, D096): a one-time code, the daily study reminder,
and the result of a run-pack payment.

Short, in Vietnamese, plain text with a matching simple HTML part. A code
email says what the code is for, how long it lasts and what to do if the
reader did not ask for it. A reminder says why it came and carries a one-click
link to stop the reminders, also as a List-Unsubscribe header.
"""

from __future__ import annotations

import hashlib
import hmac
from html import escape

from aicefr.notify.email import Email

BRAND = "SpeakUp"
PURPOSE = {
    "reset": ("Mã đặt lại mật khẩu", "đặt lại mật khẩu"),
    "verify": ("Mã xác minh email", "xác minh email của tài khoản"),
}


def _html(lines: list[str], code: str | None = None, link: tuple[str, str] | None = None) -> str:
    body = "".join(f"<p>{escape(x)}</p>" for x in lines)
    if code:
        body = (
            f'<p style="font-size:28px;font-weight:700;letter-spacing:6px;margin:16px 0">'
            f"{escape(code)}</p>" + body
        )
    if link:
        body += f'<p><a href="{escape(link[1])}">{escape(link[0])}</a></p>'
    return (
        '<div style="font-family:Helvetica,Arial,sans-serif;font-size:15px;line-height:1.5;'
        f'color:#111;max-width:520px">{body}<p style="color:#666;font-size:13px">{BRAND}</p></div>'
    )


def code_email(to: str, purpose: str, code: str, minutes: int) -> Email:
    subject, what = PURPOSE[purpose]
    lines = [
        f"Mã để {what} của bạn là {code}.",
        f"Mã dùng được một lần, trong {minutes} phút.",
        "Nếu bạn không yêu cầu, hãy bỏ qua email này: tài khoản của bạn không thay đổi gì.",
    ]
    text = "\n\n".join(lines) + f"\n\n{BRAND}"
    return Email(to=to, subject=f"{subject}: {code}", text=text, html=_html(lines[1:], code))


def unsubscribe_token(secret: bytes, account_id: str) -> str:
    """Who to stop reminding, signed so no one can stop someone else's reminders."""
    mac = hmac.new(secret, account_id.encode(), hashlib.sha256).hexdigest()[:32]
    return f"{account_id}.{mac}"


def read_unsubscribe_token(secret: bytes, token: str) -> str | None:
    account_id, _, mac = (token or "").rpartition(".")
    if not account_id or not hmac.compare_digest(unsubscribe_token(secret, account_id), token):
        return None
    return account_id


def reminder_email(to: str, name: str, reasons: list[str], site: str, stop_url: str) -> Email:
    lines = [f"Chào {name},", *reasons, "Một bài ngắn hôm nay là đủ."]
    stop = "Không muốn nhận nhắc học qua email nữa? Tắt tại đây"
    text = "\n\n".join(lines) + f"\n\nVào học: {site}/practice\n\n{stop}: {stop_url}\n\n{BRAND}"
    html = _html(lines, link=("Vào học", f"{site}/practice")).replace(
        f'<p style="color:#666;font-size:13px">{BRAND}</p>',
        f'<p style="color:#666;font-size:13px"><a href="{escape(stop_url)}">{escape(stop)}</a>'
        f" · {BRAND}</p>",
    )
    return Email(
        to=to,
        subject="Hôm nay bạn chưa luyện nói",
        text=text,
        html=html,
        headers={
            "List-Unsubscribe": f"<{stop_url}>",
            "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
        },
    )


def _dong(amount: int) -> str:
    return f"{amount:,}".replace(",", ".") + " đ"


def payment_email(to: str, name: str, order: dict, site: str) -> Email:
    """A paid order's receipt, or word that a payment did not go through (D096).

    Says what was bought, for how much, through which gateway and under which
    transaction number: what the buyer needs to recognise it, or to dispute it.
    Never a card, an account number or a password (BR-32).
    """
    order_id, runs = order["order_id"], int(order["runs"])
    amount, gateway = _dong(int(order["amount_vnd"])), order["gateway_title"]
    paid = order["status"] == "paid"
    if paid:
        subject = f"Đã thanh toán gói {runs} lượt · {order_id}"
        lines = [
            f"Chào {name},",
            f"SpeakUp đã nhận {amount} cho gói {runs} lượt qua {gateway}.",
            f"{runs} lượt đã được cộng vào ví của bạn, dùng ngay được.",
            f"Mã đơn: {order_id}"
            + (f" · Mã giao dịch: {order['reference']}" if order.get("reference") else ""),
        ]
        link = ("Xem biên nhận", f"{site}/billing/orders/{order_id}/receipt") if site else None
    else:
        subject = f"Thanh toán chưa thành công · {order_id}"
        lines = [
            f"Chào {name},",
            f"Thanh toán {amount} cho gói {runs} lượt qua {gateway} chưa thành công.",
            "Không có lượt nào bị trừ hay được cộng. Bạn có thể đặt lại gói ở trang Lượt của tôi.",
            f"Mã đơn: {order_id}",
        ]
        link = ("Mở trang Lượt của tôi", f"{site}/credits") if site else None
    if not order.get("live"):
        lines.append("Đây là môi trường thử: không có tiền thật nào được chuyển.")
    lines.append("Nếu bạn không thực hiện giao dịch này, hãy báo ngay cho quản trị viên.")
    text = "\n\n".join(lines) + (f"\n\n{link[0]}: {link[1]}" if link else "") + f"\n\n{BRAND}"
    return Email(to=to, subject=subject, text=text, html=_html(lines, link=link))
