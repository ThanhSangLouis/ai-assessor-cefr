"""The three services (D044, after D043's six).

| service | owns                                                           | store       |
|---------|----------------------------------------------------------------|-------------|
| core    | accounts, terms, responses, review, blind rating, the          | schema core |
|         | feedback study, lessons, achievements, plans and payment       |             |
| speech  | QC, recognition, features, scoring, lesson-step measuring      | none        |
| web     | the pages, their static files, the sidebar's counts            | none        |

The core service is built from four parts under `aicefr.services.core`
(identity, assessment, learning, billing). Each part keeps a `facade.py` -- what
the others may ask of it -- so the parts call each other as plain objects inside
core, and the web service reaches the same facades over HTTP
(`aicefr.platform.rpc`). `aicefr.api.main` builds all three into one process.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from fastapi import APIRouter

from aicefr.config import Settings
from aicefr.platform.rpc import remote

PARTS = ("identity", "assessment", "learning", "billing", "metering")


@dataclass
class Peers:
    """The core's parts, as their facades: local objects inside core or in one
    process, `RemoteFacade` from the web service."""

    identity: Any = None
    assessment: Any = None
    learning: Any = None
    billing: Any = None
    metering: Any = None

    @classmethod
    def from_settings(cls, settings: Settings) -> Peers:
        """Every part reached at the core service's address, when one is set."""
        url = settings.service_urls.get("core")
        if not url:
            return cls()
        return cls(**{part: remote(part, url, settings.internal_token) for part in PARTS})


@dataclass
class Parts:
    """What one service contributes to an application."""

    name: str
    routers: list[APIRouter]
    facade: Any = None
    state: dict[str, Any] = field(default_factory=dict)
