"""Email in the identity service (D079): codes for a forgotten password and for
verifying an address, and the switch for study reminders.

* A forgotten password: the learner types their email, gets a six-digit code
  valid ten minutes, and sets a new password with it. The answer to "send me a
  code" is the same whether the email has an account or not, so nobody learns
  who is registered. The recovery code of D065 stays as the way in without
  email.
* Verifying an address: signing up sends a code; the account page sends another
  on request. Only a verified address gets study reminders.
* Reminders: on by default for a verified address, off from the account page
  or from the link in every reminder, which needs no sign-in and is signed so
  nobody can turn off someone else's.
"""

from __future__ import annotations

from dataclasses import dataclass
from html import escape

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi import Response as HttpResponse
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from aicefr.api.deps import ROLE_HOME, require_login, set_session_cookie
from aicefr.api.schemas import SIGN_IN_NAME
from aicefr.auth.sessions import device_label
from aicefr.notify.email import EmailError, EmailSender
from aicefr.notify.messages import code_email, read_unsubscribe_token
from aicefr.storage.audit_repository import AuditLog
from aicefr.storage.auth_repository import (
    EMAIL_CODE_MINUTES,
    Account,
    AccountLocked,
    AuthRepository,
    Role,
)

router = APIRouter()

NO_STORE = {"Cache-Control": "no-store"}
OFF = "hệ thống chưa bật gửi email; hãy dùng mã khôi phục"


@dataclass
class Services:
    auth: AuthRepository
    audit_log: AuditLog
    sender: EmailSender | None
    secret: bytes


_services: Services | None = None


def configure(services: Services) -> None:
    global _services
    _services = services


def svc() -> Services:
    if _services is None:  # pragma: no cover - configured when the service is built
        raise RuntimeError("email API used before configure()")
    return _services


def send_code(row: dict, purpose: str) -> str:
    """Send a fresh code to the account's email: `sent`, `wait` (a minute not passed) or `off`."""
    s = svc()
    if s.sender is None:
        return "off"
    code = s.auth.issue_email_code(row["account_id"], purpose)
    if code is None:
        return "wait"
    try:
        s.sender.send(code_email(row["email"], purpose, code, EMAIL_CODE_MINUTES))
    except EmailError as e:
        raise HTTPException(502, f"chưa gửi được email: {e}") from e
    s.audit_log.write(row["pseudonym"], f"email.code_{purpose}", row["account_id"], None)
    return "sent"


# ================================================================= forgotten password


class ForgotEmailIn(BaseModel):
    email: str = Field(min_length=3, max_length=254)


class ForgotResetIn(BaseModel):
    email: str = Field(min_length=3, max_length=254, validation_alias=SIGN_IN_NAME)
    code: str = Field(min_length=4, max_length=12)
    new_password: str = Field(min_length=1, max_length=256)


@router.post("/api/v1/auth/forgot/email", tags=["auth"])
def forgot_by_email(body: ForgotEmailIn) -> dict:
    """Email a code to set a new password; the same answer for any address."""
    s = svc()
    if s.sender is None:
        raise HTTPException(503, OFF)
    row = s.auth.by_sign_in_name(body.email.strip())
    if row is not None and row.get("email") and not row["disabled"]:
        send_code(row, "reset")
    return {
        "status": "sent_if_known",
        "minutes": EMAIL_CODE_MINUTES,
        "message": "Nếu email này có tài khoản, mã đã được gửi tới. Mã dùng được 10 phút.",
    }


@router.post("/api/v1/auth/forgot/email/reset", tags=["auth"])
def reset_by_email(body: ForgotResetIn, request: Request, response: HttpResponse) -> dict:
    """Set a new password with the code from the email; sign in."""
    s = svc()
    try:
        done = s.auth.reset_with_email_code(
            body.email.strip(),
            body.code,
            body.new_password,
            device_label(request.headers.get("user-agent")),
        )
    except AccountLocked as e:
        raise HTTPException(429, f"tài khoản tạm khóa đến {e.args[0]}, thử lại sau") from e
    except ValueError as e:
        raise HTTPException(422, str(e)) from e
    if done is None:
        raise HTTPException(401, "email hoặc mã không đúng, hoặc mã đã hết hạn")
    token, row = done
    s.audit_log.write(row["pseudonym"], "account.reset_by_email", row["account_id"], None)
    set_session_cookie(response, token)
    response.headers.update(NO_STORE)
    return {"pseudonym": row["pseudonym"], "home": ROLE_HOME.get(Role(row["role"]), "/")}


# ================================================================= the account's own email


class CodeIn(BaseModel):
    code: str = Field(min_length=4, max_length=12)


class RemindersIn(BaseModel):
    on: bool


def _own(account: Account) -> dict:
    row = svc().auth.get(account.account_id)
    if row is None:  # pragma: no cover - the session names a live account
        raise HTTPException(404, "không có tài khoản này")
    return row


@router.get("/api/v1/me/email", tags=["auth"])
def my_email(account: Account = Depends(require_login)) -> dict:
    row = _own(account)
    return {
        "email": row["email"],
        "verified": bool(row["email_verified"]),
        "reminders": row.get("email_reminders") != 0,
        "sending": svc().sender is not None,
    }


@router.post("/api/v1/me/email/verify/send", tags=["auth"])
def send_verification(account: Account = Depends(require_login)) -> dict:
    row = _own(account)
    if not row["email"]:
        raise HTTPException(409, "tài khoản chưa có email")
    if row["email_verified"]:
        return {"status": "verified"}
    return {"status": send_code(row, "verify")}


@router.post("/api/v1/me/email/verify", tags=["auth"])
def verify(body: CodeIn, account: Account = Depends(require_login)) -> dict:
    if not svc().auth.verify_email(account.account_id, body.code):
        raise HTTPException(422, "mã không đúng hoặc đã hết hạn; bấm gửi lại để nhận mã mới")
    svc().audit_log.write(account.pseudonym, "email.verified", account.account_id, None)
    return {"verified": True}


@router.put("/api/v1/me/email/reminders", tags=["auth"])
def set_reminders(body: RemindersIn, account: Account = Depends(require_login)) -> dict:
    svc().auth.set_email_reminders(account.account_id, body.on)
    return {"reminders": body.on}


@router.get("/api/v1/email/unsubscribe", response_class=HTMLResponse, include_in_schema=False)
@router.post("/api/v1/email/unsubscribe", response_class=HTMLResponse, include_in_schema=False)
def unsubscribe(t: str = Query(default="", max_length=200)) -> HTMLResponse:
    """Stop the study reminders from the link in one, with no sign-in."""
    s = svc()
    who = read_unsubscribe_token(s.secret, t)
    if who is None or s.auth.get(who) is None:
        text = "Liên kết không hợp lệ. Bạn có thể tắt nhắc học ở trang Tài khoản."
    else:
        s.auth.set_email_reminders(who, False)
        text = "Đã tắt nhắc học qua email. Bật lại bất cứ lúc nào ở trang Tài khoản."
    return HTMLResponse(
        '<!doctype html><html lang="vi"><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        "<title>Nhắc học qua email · SpeakUp</title>"
        '<body style="font-family:Helvetica,Arial,sans-serif;max-width:520px;margin:48px auto;'
        f'padding:0 16px;line-height:1.5"><p>{escape(text)}</p>'
        '<p><a href="/account">Mở trang Tài khoản</a></p></body></html>'
    )
