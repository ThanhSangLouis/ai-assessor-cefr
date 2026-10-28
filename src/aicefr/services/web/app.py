"""The web service: the pages and their static files (D043).

It keeps no store. A page quotes the limits in force from the assessment
service and who is signed in from the gateway; everything else on it is
fetched by its script from the service that owns the data.
"""

from __future__ import annotations

from aicefr.config import Settings, get_settings
from aicefr.platform.bus import MessageBus
from aicefr.services import Parts, Peers
from aicefr.services.web import bff, pages


def build(settings: Settings, peers: Peers, bus: MessageBus) -> Parts:
    pages.configure(pages.Services(settings=settings, peers=peers))
    return Parts(name="web", routers=[pages.router, bff.router])


def create_app():
    from aicefr.api.web import templates
    from aicefr.services.runtime import standalone

    settings = get_settings()
    app = standalone("web", build, settings, static=True)
    # The administrator's account menu links to /docs only where docs are served.
    templates.env.globals["api_docs"] = not settings.is_production
    return app
