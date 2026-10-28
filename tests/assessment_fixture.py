from __future__ import annotations

import os
import uuid

from fastapi import FastAPI

from aicefr.config import get_settings
from aicefr.infra.queues import InlineJobQueue
from aicefr.platform.bus import InlineBus
from aicefr.platform.callers import (
    ACCOUNT_HEADER,
    GATEWAY_HEADER,
    GatewayCallers,
    encode_account,
)
from aicefr.services import Peers
from aicefr.services.core.assessment import app as assessment_app
from aicefr.storage.auth_repository import Account, Role
from aicefr.storage.consent_repository import CURRENT_CONSENT_VERSION

GATEWAY_TOKEN = "test-gateway-token"
INTERNAL_TOKEN = "test-internal-token"


class IdentityStub:
    def by_pseudonym(self, *, pseudonym: str) -> dict | None:
        if pseudonym.upper() == "SV-001":
            return {"account_id": "student-1", "role": Role.STUDENT.value}
        return None

    def pseudonyms(self, *, account_ids: list[str]) -> dict[str, str]:
        return {account_id: "SV-001" for account_id in account_ids if account_id == "student-1"}

    def consent(self, *, account_id: str) -> dict:
        return {
            "consent_id": "consent-1",
            "account_id": account_id,
            "consent_version": CURRENT_CONSENT_VERSION,
            "audio_storage_allowed": True,
            "research_use_allowed": True,
            "signed_at": "2026-10-28T00:00:00+00:00",
            "withdrawn_at": None,
        }


def build_assessment_service(tmp_path, monkeypatch, request=None):
    monkeypatch.setenv("AICEFR_INTERNAL_TOKEN", INTERNAL_TOKEN)
    monkeypatch.setenv("AICEFR_GATEWAY_TOKEN", GATEWAY_TOKEN)
    get_settings.cache_clear()
    settings = get_settings()
    server = os.getenv("AICEFR_TEST_MONGO")
    database = f"t_{uuid.uuid4().hex[:12]}" if server else None
    settings.stores["core"] = (
        f"{server.rstrip('/')}/{database}" if server and database else str(tmp_path / "core.db")
    )
    parts = assessment_app.build(
        settings,
        Peers(identity=IdentityStub()),
        InlineBus(InlineJobQueue()),
    )

    if server and database and request is not None:

        def drop_test_database():
            from pymongo import MongoClient

            from aicefr.storage import db as storage_db
            from aicefr.storage import migrations

            with MongoClient(server) as client:
                client.drop_database(database)
            storage_db.forget_indexes()
            migrations.forget_current()

        request.addfinalizer(drop_test_database)

    return parts, settings


def headers(account: Account) -> dict[str, str]:
    return {
        GATEWAY_HEADER: GATEWAY_TOKEN,
        ACCOUNT_HEADER: encode_account(account),
    }


def asgi(parts, settings) -> FastAPI:
    app = FastAPI()
    app.state.callers = GatewayCallers(settings.gateway_token)
    for router in parts.routers:
        app.include_router(router)
    return app
