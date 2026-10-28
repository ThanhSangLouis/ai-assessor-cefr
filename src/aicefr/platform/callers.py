"""Who is calling: from the session cookie, or from the gateway's header (D043).

Only the identity service holds sessions. Every request reaches the other
services through the gateway, which first asks identity who the cookie belongs
to (`GET /internal/identity/session`) and forwards the answer in
`X-Aicefr-Account`, together with its own key in `X-Aicefr-Gateway`. A service
trusts the account header only when that key is there too, so a header typed by
a browser, or a request that slipped past the gateway, is just anonymous. The
gateway key is not the internal key of service-to-service calls: the gateway
cannot call a facade, and the speech service, which parses audio from the
internet, holds neither.

`SessionCallers` reads the cookie itself: the identity service, and everything
when all services run in one process.
"""

from __future__ import annotations

import base64
import json
from typing import Protocol

from fastapi import Request

from aicefr.auth.sessions import COOKIE_NAME
from aicefr.platform.rpc import same_key
from aicefr.storage.auth_repository import DEFAULT_DAILY_GOAL, Account, Role

ACCOUNT_HEADER = "X-Aicefr-Account"
GATEWAY_HEADER = "X-Aicefr-Gateway"


def encode_account(account: Account | None) -> str:
    """The account as the gateway forwards it: base64url of a small JSON object."""
    if account is None:
        return ""
    data = {
        "account_id": account.account_id,
        "pseudonym": account.pseudonym,
        "role": account.role.value,
        "must_change_password": account.must_change_password,
        "avatar_icon": account.avatar_icon,
        "avatar_color": account.avatar_color,
        "daily_goal_s": account.daily_goal_s,
        "terms_accepted_at": account.terms_accepted_at,
    }
    return base64.urlsafe_b64encode(json.dumps(data).encode()).decode()


def decode_account(value: str | None) -> Account | None:
    if not value:
        return None
    try:
        data = json.loads(base64.urlsafe_b64decode(value.encode()))
        return Account(
            data["account_id"],
            data["pseudonym"],
            Role(data["role"]),
            must_change_password=bool(data.get("must_change_password")),
            avatar_icon=data.get("avatar_icon"),
            avatar_color=data.get("avatar_color"),
            daily_goal_s=int(data.get("daily_goal_s") or DEFAULT_DAILY_GOAL),
            terms_accepted_at=data.get("terms_accepted_at"),
        )
    except (ValueError, KeyError, TypeError):
        return None


class Callers(Protocol):
    def for_request(self, request: Request) -> Account | None: ...


class SessionCallers:
    """Reads the session cookie against the identity store."""

    def __init__(self, auth_repo) -> None:
        self.auth_repo = auth_repo

    def for_request(self, request: Request) -> Account | None:
        return self.auth_repo.account_for_token(request.cookies.get(COOKIE_NAME))


class GatewayCallers:
    """Trusts the gateway's account header, and only next to the gateway's key."""

    def __init__(self, token: str) -> None:
        self.token = token

    def for_request(self, request: Request) -> Account | None:
        if not same_key(self.token, request.headers.get(GATEWAY_HEADER)):
            return None
        return decode_account(request.headers.get(ACCOUNT_HEADER))
