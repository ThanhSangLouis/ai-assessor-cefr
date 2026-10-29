"""The identity service: accounts, sessions, Google sign-in, terms of use (D043, D058).

The only service that reads the session cookie. The gateway asks it who a
request comes from (`/internal/identity/session`) and forwards the answer to
the other services.
"""

from __future__ import annotations

from aicefr.config import Settings
from aicefr.platform.bus import MessageBus
from aicefr.platform.callers import SessionCallers
from aicefr.platform.rpc import internal_router
from aicefr.services import Parts, Peers
from aicefr.services.core.identity import accounts_api, auth_api, google_api
from aicefr.services.core.identity.facade import IdentityFacade
from aicefr.storage.audit_repository import AuditLog
from aicefr.storage.auth_repository import AuthRepository


def build(settings: Settings, peers: Peers, bus: MessageBus) -> Parts:
    store = settings.store("core")
    auth = AuthRepository(store)
    audit_log = AuditLog(store, "identity")
    facade = IdentityFacade(auth, audit_log)

    auth_api.configure(
        auth_api.Services(
            auth=auth,
            audit_log=audit_log,
            gateway_token=settings.gateway_token,
            peers=peers,
        )
    )
    accounts_api.configure(accounts_api.Services(audit_log=audit_log, peers=peers))
    return Parts(
        name="identity",
        routers=[
            auth_api.router,
            accounts_api.router,
            google_api.router,
            internal_router("identity", facade, settings.internal_token),
        ],
        facade=facade,
        state={
            "auth_repo": auth,
            "callers": SessionCallers(auth),
        },
    )
