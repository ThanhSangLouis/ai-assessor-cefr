"""The identity service: accounts, sessions, Google sign-in, terms of use (D043, D058).

The only service that reads the session cookie. The gateway asks it who a
request comes from (`/internal/identity/session`) and forwards the answer to
the other services.
"""

from __future__ import annotations

import logging
import secrets
import threading
from datetime import UTC, datetime

from aicefr.config import Settings
from aicefr.notify import reminders
from aicefr.notify.email import sender_from
from aicefr.platform.bus import MessageBus
from aicefr.platform.callers import SessionCallers
from aicefr.platform.rpc import internal_router
from aicefr.services import Parts, Peers
from aicefr.services.core.identity import accounts_api, auth_api, email_api, google_api
from aicefr.services.core.identity.facade import IdentityFacade
from aicefr.storage.audit_repository import AuditLog
from aicefr.storage.auth_repository import SETTING, AuthRepository
from aicefr.storage.db import setting_once

logger = logging.getLogger(__name__)
# How often the reminder loop looks at the clock; a reminder is sent once a day.
REMINDER_TICK_S = 300.0


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
    # D079: the email sender, and the secret that signs the "stop reminders" links.
    sender = sender_from(settings)
    secret, _ = setting_once(auth.db, SETTING + "unsubscribe_secret", secrets.token_hex(32))
    email_api.configure(
        email_api.Services(
            auth=auth, audit_log=audit_log, sender=sender, secret=bytes.fromhex(secret)
        )
    )
    stop = threading.Event()

    def send_reminders() -> int:
        site = (settings.public_url or "").rstrip("/")
        if sender is None or not site:
            return 0
        return reminders.send_due(
            datetime.now(UTC),
            settings.reminder_hour,
            auth,
            peers.learning,
            sender,
            site,
            bytes.fromhex(secret),
        )

    def reminder_loop() -> None:
        while not stop.wait(REMINDER_TICK_S):
            try:
                sent = send_reminders()
                if sent:
                    logger.info("sent %d study reminders", sent)
            except Exception:  # noqa: BLE001 - the loop must not die of one error
                logger.exception("study reminders failed")

    def startup() -> None:
        if sender is not None and settings.reminder_hour >= 0 and settings.job_mode != "inline":
            if not settings.public_url:
                logger.warning("study reminders off: AICEFR_PUBLIC_URL is not set")
                return
            threading.Thread(target=reminder_loop, name="study-reminders", daemon=True).start()

    return Parts(
        name="identity",
        routers=[
            auth_api.router,
            accounts_api.router,
            email_api.router,
            google_api.router,
            internal_router("identity", facade, settings.internal_token),
        ],
        facade=facade,
        state={
            "auth_repo": auth,
            "callers": SessionCallers(auth),
            "startup": startup,
            "send_reminders": send_reminders,
        },
    )
