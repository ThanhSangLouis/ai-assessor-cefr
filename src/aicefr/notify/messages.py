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
    return Email(to=to, subject=subject, text=text, html=_payment_html(name, order, site, link))


# The receipt as a branded card (owner, 07/11/2026: "the email is too ugly").
# Mail clients ignore <style> blocks and most layout CSS, so it is tables with
# inline styles, a hidden preheader for the inbox line, and one bulletproof
# button; the logo is the site's own PNG, so nothing is attached. Line breaks
# inside the markup are whitespace to a mail client, never layout.
INK, MUTED, LINE, SOFT, CORAL = "#1f2d28", "#56655e", "#e1e9df", "#f5f8f3", "#d9580b"

RECEIPT_HTML = """\
<div style="display:none;max-height:0;overflow:hidden;opacity:0">{preheader}</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0"
 style="background:{soft};font-family:Helvetica,Arial,sans-serif">
<tr><td align="center" style="padding:28px 12px">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0"
 style="max-width:520px;background:#ffffff;border:1px solid {line};
 border-radius:18px;overflow:hidden">
<tr><td style="height:6px;background:{coral};line-height:6px;font-size:0">&nbsp;</td></tr>
<tr><td style="padding:20px 28px 0">{logo}<span style="vertical-align:middle;font-size:18px;
 font-weight:800;color:{ink};margin-left:8px">Speak<span style="color:{coral}">Up</span></span>
</td></tr>
<tr><td align="center" style="padding:26px 28px 6px">
<div style="width:56px;height:56px;line-height:56px;border-radius:28px;background:{mark_bg};
 color:#ffffff;font-size:28px;font-weight:800;text-align:center;margin:0 auto">{mark}</div>
<div style="font-size:22px;font-weight:800;color:{ink};margin-top:14px">{title}</div>
<div style="font-size:14px;color:{muted};margin:6px 0 16px">Chào {name},</div>
{hero}{test}
</td></tr>
<tr><td style="padding:18px 28px 0">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0">{rows}</table>
</td></tr>
<tr><td align="center" style="padding:4px 28px 28px">{actions}</td></tr>
<tr><td style="padding:16px 28px;background:{soft};color:{muted};font-size:12px;
 line-height:1.5;text-align:center">Nếu bạn không thực hiện giao dịch này, hãy báo ngay cho
 quản trị viên.<br>{footer}</td></tr>
</table>
</td></tr>
</table>"""

ROW_HTML = """\
<tr><td style="padding:9px 0;color:{muted};font-size:13px;border-top:1px solid {line};
 width:38%">{label}</td><td style="padding:9px 0;color:{ink};font-size:14px;
 border-top:1px solid {line};text-align:right">{value}</td></tr>"""

BUTTON_HTML = """\
<table role="presentation" cellpadding="0" cellspacing="0" style="margin:24px auto 0">
<tr><td style="border-radius:12px;background:{coral}"><a href="{href}"
 style="display:inline-block;padding:13px 28px;color:#ffffff;font-weight:700;font-size:15px;
 text-decoration:none;border-radius:12px">{label}</a></td></tr></table>"""

MONO = "font-family:Menlo,Consolas,monospace"


def _when(stamp: str | None) -> str:
    """An ISO time as Vietnam reads it: 07/11/2026 17:40."""
    from datetime import datetime

    from aicefr.practice.streak import LOCAL_TZ

    try:
        return datetime.fromisoformat(str(stamp)).astimezone(LOCAL_TZ).strftime("%d/%m/%Y %H:%M")
    except ValueError:
        return ""


def _payment_html(name: str, order: dict, site: str, link: tuple[str, str] | None) -> str:
    paid = order["status"] == "paid"
    runs, amount = int(order["runs"]), _dong(int(order["amount_vnd"]))
    colours = {"ink": INK, "muted": MUTED, "line": LINE, "soft": SOFT, "coral": CORAL}
    if paid:
        hero = (
            f'<div style="font-size:44px;line-height:1.1;font-weight:800;color:{CORAL}">+{runs}'
            '<span style="font-size:20px;font-weight:700"> lượt</span></div>'
            f'<div style="font-size:15px;color:{MUTED};margin-top:4px">đã vào ví của bạn</div>'
        )
    else:
        hero = (
            f'<div style="font-size:15px;color:{MUTED}">Không có lượt nào bị trừ hay được cộng.'
            "<br>Bạn có thể đặt lại gói bất cứ lúc nào.</div>"
        )
    rows = [
        ("Số tiền", f"<b>{escape(amount)}</b>"),
        ("Gói", escape(f"{runs} lượt")),
        ("Cổng", escape(str(order["gateway_title"]))),
    ]
    if when := _when(order.get("settled_at")):
        rows.append(("Thời gian", escape(when)))
    rows.append(("Mã đơn", f'<span style="{MONO}">{escape(order["order_id"])}</span>'))
    if order.get("reference"):
        reference = escape(str(order["reference"]))
        style = f"{MONO};font-size:12px;word-break:break-all"
        rows.append(("Mã giao dịch", f'<span style="{style}">{reference}</span>'))
    actions = ""
    if link:
        actions = BUTTON_HTML.format(href=escape(link[1]), label=escape(link[0]), coral=CORAL)
        if paid and site:
            actions += (
                f'<div style="margin-top:14px"><a href="{escape(site)}/practice" '
                f'style="color:{CORAL};font-size:14px;font-weight:600;text-decoration:none">'
                "Luyện nói ngay &rarr;</a></div>"
            )
    test = ""
    if not order.get("live"):
        test = (
            '<div style="margin-top:16px;padding:8px 12px;border-radius:999px;'
            'background:#fff1d6;color:#b26a00;font-size:12px;font-weight:600;display:inline-block">'
            "Môi trường thử: không có tiền thật nào được chuyển</div>"
        )
    logo = ""
    if site:
        logo = (
            f'<img src="{escape(site)}/static/favicon.png" width="36" height="36" alt="SpeakUp" '
            'style="vertical-align:middle;border:0;border-radius:8px">'
        )
    preheader = (
        f"Đã nhận {amount} · +{runs} lượt vào ví" if paid else f"Đơn {amount} chưa thanh toán"
    )
    return RECEIPT_HTML.format(
        preheader=escape(preheader),
        logo=logo,
        mark="&#10003;" if paid else "!",
        mark_bg="#1f8a4c" if paid else "#c2362c",
        title="Thanh toán thành công" if paid else "Thanh toán chưa thành công",
        name=escape(name),
        hero=hero,
        test=test,
        rows="".join(ROW_HTML.format(label=label, value=value, **colours) for label, value in rows),
        actions=actions,
        footer=BRAND + (f" · {escape(site.split('//')[-1])}" if site else ""),
        **colours,
    )
