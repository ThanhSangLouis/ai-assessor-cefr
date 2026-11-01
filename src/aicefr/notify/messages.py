"""What the emails say (D079): a one-time code, and the daily study reminder.

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

BRAND = "AI Assessor CEFR"
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
