"""Web Push of the assessment service (D088): register a browser, and what it is told.

`PUT /api/v1/me/push` keeps the browser's subscription for the signed-in
account, `DELETE` forgets it (the browser turned notifications off, or the
person signed out on it). `tell_device` sends the learner's two events of the
live stream (D086) as a notification when no SpeakUp tab of theirs is open.

The server sends an HTTPS request to the endpoint the browser gives, so only
the push services of the browsers are accepted: an endpoint pointing anywhere
else (the server's own network) is refused.
"""

from __future__ import annotations

import base64
import binascii
import logging
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from aicefr.api.deps import require_login
from aicefr.contracts import ResponseStatus
from aicefr.services.core.assessment.context import svc
from aicefr.storage.auth_repository import Account
from aicefr.storage.push_repository import MAX_ENDPOINT

logger = logging.getLogger(__name__)
router = APIRouter()

# Chrome, Edge on Android, Samsung Internet, Opera: Google's; Firefox:
# Mozilla's; Edge on Windows: Microsoft's; Safari (macOS, and iOS once added
# to the home screen): Apple's.
PUSH_HOSTS = (
    "fcm.googleapis.com",
    "push.services.mozilla.com",
    "notify.windows.com",
    "push.apple.com",
)


class PushKeys(BaseModel):
    p256dh: str = Field(min_length=80, max_length=100)
    auth: str = Field(min_length=16, max_length=32)


class PushIn(BaseModel):
    endpoint: str = Field(min_length=20, max_length=MAX_ENDPOINT)
    keys: PushKeys


class PushOut(BaseModel):
    endpoint: str = Field(min_length=20, max_length=MAX_ENDPOINT)


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def push_service(endpoint: str) -> bool:
    """Whether the endpoint is on a browser's push service, over HTTPS, port 443."""
    try:
        u = urlsplit(endpoint)
        host, port = (u.hostname or "").lower(), u.port
    except ValueError:
        return False
    if u.scheme != "https" or u.username or u.password or port not in (None, 443):
        return False
    return any(host == h or host.endswith("." + h) for h in PUSH_HOSTS)


def _valid_keys(keys: PushKeys) -> bool:
    try:
        point, secret = _unb64(keys.p256dh), _unb64(keys.auth)
    except (binascii.Error, ValueError):
        return False
    # An uncompressed P-256 point, and a 16-byte authentication secret (RFC 8291).
    return len(point) == 65 and point[0] == 4 and len(secret) == 16


def _sender():
    push = svc().push
    if push is None or not push.enabled:
        raise HTTPException(503, "máy chủ chưa bật thông báo đẩy")
    return push


@router.get("/api/v1/me/push", tags=["me"])
def push_config(account: Account = Depends(require_login)) -> dict:
    """Whether notifications are on for this server, and the key a browser subscribes with."""
    push = svc().push
    on = bool(push and push.enabled)
    return {"enabled": on, "public_key": push.public_key if on else None}


@router.put("/api/v1/me/push", tags=["me"])
def subscribe(body: PushIn, account: Account = Depends(require_login)) -> dict:
    push = _sender()
    if not push_service(body.endpoint):
        raise HTTPException(422, "địa chỉ nhận thông báo không thuộc dịch vụ của trình duyệt")
    if not _valid_keys(body.keys):
        raise HTTPException(422, "khoá của trình duyệt không hợp lệ")
    push.store.subscribe(account.account_id, body.endpoint, body.keys.p256dh, body.keys.auth)
    return {"subscribed": True}


@router.delete("/api/v1/me/push", tags=["me"])
def unsubscribe(body: PushOut, account: Account = Depends(require_login)) -> dict:
    push = svc().push
    removed = bool(push and push.store.unsubscribe(account.account_id, body.endpoint))
    return {"removed": removed}


# ================================================================= what is sent

_FINISHED = {
    ResponseStatus.COMPLETED.value: ("Bài nói đã chấm xong", "Mở để xem kết quả và nhận xét."),
    ResponseStatus.REVIEW_REQUIRED.value: (
        "Bài nói đã có điểm tạm",
        "Giảng viên sẽ xác nhận kết quả. Mở để xem nhận xét.",
    ),
    ResponseStatus.FAILED.value: ("Bài nói chưa xử lý được", "Mở để xem lý do và nộp lại."),
    ResponseStatus.REJECTED.value: ("Bài nói chưa xử lý được", "Mở để xem lý do và nộp lại."),
}
_REVIEWED = ("Giảng viên đã duyệt bài nói", "Mở để xem kết quả đã xác nhận.")


def tell_device(
    owner_id: str | None, response_id: str, status: str | None, *, reviewed: bool
) -> None:
    """A notification on the learner's devices, unless a SpeakUp tab of theirs is open.

    An open tab hears the live stream (D086) and shows it there; telling the
    device too would say the same thing twice.
    """
    s = svc()
    if s.push is None or not s.push.enabled or not owner_id:
        return
    if s.live is not None and s.live.hub.count(owner_id):
        return
    title, body = _REVIEWED if reviewed else _FINISHED.get(status or "", (None, None))
    if title is None:
        return
    s.push.notify(owner_id, title, body, f"/report/{response_id}", f"response-{response_id}")
