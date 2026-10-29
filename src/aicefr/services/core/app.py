"""The core service (D044): accounts, assessment, lessons and plans, in one process.

Its four parts keep their facades and call each other through them as plain
objects; the internal routes let the web service ask the same facades over
HTTP. One store holds every table, so a review decision and its audit row,
or an erasure across responses, lesson attempts and the feedback study, need
no message between services.
"""

from __future__ import annotations

import logging

from aicefr.config import Settings, get_settings
from aicefr.platform.bus import MessageBus
from aicefr.services import Parts, Peers
from aicefr.services.core.assessment import app as assessment
from aicefr.services.core.billing import app as billing
from aicefr.services.core.identity import app as identity
from aicefr.services.core.learning import app as learning

logger = logging.getLogger(__name__)


def build(settings: Settings, peers: Peers, bus: MessageBus) -> Parts:
    """The four parts on one shared `peers`, filled in with their own facades."""
    built = {
        "identity": identity.build(settings, peers, bus),
        "billing": billing.build(settings, peers, bus),
        "assessment": assessment.build(settings, peers, bus),
        "learning": learning.build(settings, peers, bus),
    }
    for name, parts in built.items():
        setattr(peers, name, parts.facade)
    state: dict = {}
    for parts in built.values():
        state.update(parts.state)
    sessions_purge = built["identity"].state["auth_repo"].purge_expired_sessions
    assessment_startup = state.pop("startup", None)

    def startup() -> None:
        # Expired session rows are dead weight: the table grows for every login.
        purged = sessions_purge()
        if purged:
            logger.info("purged %d expired sessions", purged, extra={"event": "startup"})
        if assessment_startup:
            assessment_startup()

    state["startup"] = startup
    state["ready"] = built["assessment"].state["ready"]
    return Parts(
        name="core",
        routers=[r for parts in built.values() for r in parts.routers],
        facade=peers,
        state=state,
    )


def create_app():
    """The core service on its own, as its container runs it."""
    from aicefr.services.runtime import standalone

    return standalone("core", build, get_settings(), login_rate_limit=True)
