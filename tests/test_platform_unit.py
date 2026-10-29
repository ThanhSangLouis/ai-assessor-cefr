"""Layer 1 for the service platform (D043): pure functions, no network, no database server.

The SQL translation that lets one repository run on SQLite and PostgreSQL, the
in-process bus, the internal call's refusals, the gateway's account header and
routing table, and the merge of several services' audit logs.
"""

from __future__ import annotations

import pytest

from aicefr.infra.queues import InlineJobQueue
from aicefr.platform.bus import BusTimeout, InlineBus
from aicefr.platform.callers import decode_account, encode_account
from aicefr.platform.gateway import service_for
from aicefr.platform.rpc import RemoteError, RemoteFacade
from aicefr.storage.audit_repository import merge
from aicefr.storage.auth_repository import Account, Role
from aicefr.storage.db import database, fields, next_id

pytestmark = pytest.mark.unit


# ================================================================= SQL dialects


def test_one_path_is_one_in_memory_store_and_two_paths_are_two(tmp_path):
    a, b = tmp_path / "a.db", tmp_path / "b.db"
    database(a)["x"].insert_one({"k": 1})
    assert database(a)["x"].count_documents({}) == 1
    assert database(b)["x"].count_documents({}) == 0


def test_production_refuses_an_in_memory_store(tmp_path, monkeypatch):
    monkeypatch.setenv("AICEFR_ENV", "production")
    with pytest.raises(RuntimeError, match="mongodb://"):
        database(tmp_path / "a.db")


def test_numbers_count_up_from_one_per_series(tmp_path):
    db = database(tmp_path / "n.db")
    assert [next_id(db, "a"), next_id(db, "a"), next_id(db, "b"), next_id(db, "a")] == [1, 2, 1, 3]


def test_a_missing_field_reads_none_and_the_id_stays_inside():
    assert fields({"_id": 1, "a": 2}, ("a", "b")) == {"a": 2, "b": None}
    assert fields(None, ("a",)) is None


def test_inline_events_reach_every_subscriber_and_one_failure_stops_none():
    bus = InlineBus(InlineJobQueue())
    got = []
    bus.subscribe("response.scored", "a", lambda m: (_ for _ in ()).throw(RuntimeError("x")))
    bus.subscribe("response.scored", "b", got.append)
    bus.publish("response.scored", {"account_id": "u"})
    assert got == [{"account_id": "u"}]


def test_only_background_queues_go_through_the_job_queue():
    ran = []

    class Recording(InlineJobQueue):
        def enqueue(self, func, /, *args, **kwargs):
            ran.append("pool")
            super().enqueue(func, *args, **kwargs)

    bus = InlineBus(Recording())
    bus.consume("speech.score", lambda m: ran.append("score"))
    bus.consume("assessment.scoring", lambda m: ran.append("result"))
    bus.send("speech.score", {})
    bus.send("assessment.scoring", {})
    assert ran == ["pool", "score", "result"]


def test_a_call_nobody_serves_is_a_timeout():
    bus = InlineBus(InlineJobQueue())
    with pytest.raises(BusTimeout):
        bus.call("speech.step", {})
    bus.serve("speech.step", lambda req: {"echo": req["x"]})
    assert bus.call("speech.step", {"x": 1}) == {"echo": 1}


# ================================================================= internal calls


def test_a_refused_internal_call_raises_with_its_status():
    def refusing(method, path, body):
        return 403, {"detail": "internal endpoint"}

    remote = RemoteFacade("identity", refusing)
    with pytest.raises(RemoteError) as e:
        remote.count_role(role="student")
    assert e.value.status == 403
    with pytest.raises(AttributeError):
        remote._private  # noqa: B018 - private names are never forwarded


def test_an_unreachable_service_is_a_503():
    def down(method, path, body):
        raise ConnectionRefusedError("no route")

    with pytest.raises(RemoteError) as e:
        RemoteFacade("learning", down).attempts(account_id="a")
    assert e.value.status == 503


# ================================================================= the gateway


def test_the_account_header_round_trips_and_rejects_garbage():
    account = Account("a1", "SV-001", Role.STUDENT, must_change_password=True, daily_goal_s=300)
    back = decode_account(encode_account(account))
    assert back == account
    assert decode_account("") is None and decode_account("bm90IGpzb24") is None
    assert encode_account(None) == ""


@pytest.mark.parametrize(
    ("path", "service"),
    [
        ("/api/v1/me", "core"),
        ("/api/v1/me/profile", "core"),
        ("/api/v1/me/profile.json", "core"),
        ("/api/v1/me/progress", "core"),
        ("/api/v1/me/badges/results/seen", "web"),
        ("/api/v1/me/pronunciation", "core"),
        ("/api/v1/learn", "core"),
        ("/api/v1/learn/review", "core"),
        ("/api/v1/plan", "core"),
        ("/billing/return/stripe", "core"),
        ("/auth/google/callback", "core"),
        ("/api/v1/admin/accounts/x/role", "core"),
        ("/api/v1/admin/erase", "core"),
        ("/review/stats", "web"),
        ("/static/app.js", "web"),
        ("/internal/identity/session", None),
    ],
)
def test_each_path_goes_to_its_service(path, service):
    assert service_for(path) == service


# ================================================================= the audit log


def test_merged_logs_keep_the_order_the_actions_happened_in():
    identity = [{"id": 9, "actor_id": "a", "action": "terms.accept", "target_id": None,
                 "detail": None, "created_at": "2026-10-12T10:00:00.000200+00:00"}]  # fmt: skip
    assessment = [
        {"id": 2, "actor_id": "a", "action": "rating.batch_create", "target_id": None,
         "detail": None, "created_at": "2026-10-12T10:00:00.000900+00:00"},
        {"id": 1, "actor_id": "a", "action": "AUDIO_ACCESS", "target_id": None,
         "detail": None, "created_at": "2026-10-12T09:59:59+00:00"},
    ]  # fmt: skip
    merged = merge([identity, assessment], limit=2)
    assert [e.action for e in merged] == ["rating.batch_create", "terms.accept"]


def test_one_client_per_server_and_the_database_from_the_path():
    from aicefr.storage.db import _split

    assert _split("mongodb://h:27017/t_1") == ("mongodb://h:27017/", "t_1")
    assert _split("mongodb://h:27017") == ("mongodb://h:27017/", "aicefr")
    # A user signs in where the path said, even with the path taken off.
    assert _split("mongodb://core:pw@mongo:27017/aicefr") == (
        "mongodb://core:pw@mongo:27017/?authSource=aicefr",
        "aicefr",
    )
