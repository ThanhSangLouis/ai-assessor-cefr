"""Integration coverage for the transferred W5-S04 research services."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

from aicefr.contracts import ActorRole
from conftest import http, submit_completed


def _research_consent(runtime, token):
    actor = runtime.auth.resolve(token)
    runtime.consents.activate(actor, "demo-v1", research_allowed=True)
    return actor.actor_id


def test_blind_rating_keeps_machine_fields_and_identity_out_of_the_rater_flow(
    portal_runtime,
):
    runtime, tokens = portal_runtime
    owner_id = _research_consent(runtime, tokens["a"])
    response = submit_completed(runtime, tokens["a"])
    made = http(
        runtime,
        "/api/v1/admin/ratings/batches",
        tokens["admin"],
        method="POST",
        payload={
            "name": "Fixture ratings",
            "rater_ids": ["fixture-teacher", "fixture-other-teacher"],
            "seed": 19,
        },
    )
    assert made["code"] == 201, made["body"]
    batch_id = made["json"]["batch_id"]
    sheet_tokens = []
    for key in ("teacher", "other-teacher"):
        assignments = http(runtime, "/api/v1/rating/assignments", tokens[key])["json"][
            "assignments"
        ]
        blind_token = assignments[0]["token"]
        sheet_tokens.append((key, blind_token))
        sheet = http(
            runtime,
            f"/api/v1/rating/assignments/{blind_token}",
            tokens[key],
        )
        assert sheet["code"] == 200
        assert "response_id" not in sheet["json"]
        assert owner_id not in json.dumps(sheet["json"])
        assert str(response.response_id) not in json.dumps(sheet["json"])
        assert http(runtime, sheet["json"]["audio_url"], tokens[key])["code"] == 200

    active_report = http(
        runtime,
        f"/teacher/responses/{response.response_id}/report",
        tokens["teacher"],
    )
    assert active_report["code"] == 403
    for path in (
        f"/teacher/responses/{response.response_id}/audio",
        f"/teacher/reviews/{response.response_id}",
        f"/teacher/reviews/{response.response_id}/audio",
    ):
        assert http(runtime, path, tokens["teacher"])["code"] == 403
    assert (
        http(
            runtime,
            f"/teacher/responses/{response.response_id}/review",
            tokens["teacher"],
            method="POST",
            payload={"expected_revision": 0},
        )["code"]
        == 403
    )
    assert (
        http(
            runtime,
            f"/teacher/reviews/{response.response_id}/reopen",
            tokens["teacher"],
            method="POST",
            payload={"expected_revision": 0, "reason": "Fixture review"},
        )["code"]
        == 403
    )

    for key, blind_token in sheet_tokens:
        score, band = (2.5, "A2") if key == "teacher" else (3.5, "B1")
        rating = {
            "overall": score,
            "band": band,
            "criteria": {
                "range": score,
                "accuracy": score,
                "fluency": score,
                "coherence": score,
                "phonology": score,
            },
            "rationale": "Fixture rating is clear.",
        }
        submitted = http(
            runtime,
            f"/api/v1/rating/assignments/{blind_token}/submit",
            tokens[key],
            method="POST",
            payload=rating,
        )
        assert submitted["code"] == 200, submitted["body"]

    adjudication = http(
        runtime,
        f"/api/v1/admin/ratings/batches/{batch_id}/adjudicate",
        tokens["admin"],
        method="POST",
        payload={"adjudicator_id": "fixture-admin"},
    )
    assert adjudication["code"] == 200
    admin_sheet = http(runtime, "/api/v1/rating/assignments", tokens["admin"])["json"][
        "assignments"
    ][0]
    assert admin_sheet["batch_id"] == batch_id
    adjudication_token = admin_sheet["token"]
    assert (
        http(
            runtime,
            f"/api/v1/admin/ratings/batches/{batch_id}/report",
            tokens["admin"],
        )["code"]
        == 409
    )
    final_rating = {
        "overall": 3.0,
        "band": "B1",
        "criteria": {
            "range": 3.0,
            "accuracy": 3.0,
            "fluency": 3.0,
            "coherence": 3.0,
            "phonology": 3.0,
        },
        "rationale": "Independent fixture adjudication.",
    }
    adjudicated = http(
        runtime,
        f"/api/v1/rating/assignments/{adjudication_token}/adjudicate",
        tokens["admin"],
        method="POST",
        payload=final_rating,
    )
    assert adjudicated["code"] == 200

    report = http(
        runtime,
        f"/api/v1/admin/ratings/batches/{batch_id}/report",
        tokens["admin"],
    )
    assert report["code"] == 200, report["body"]
    assert report["json"]["sample_count"] == 1
    assert report["json"]["report"]["counts"]["rated_twice"] == 1
    assert report["json"]["report"]["counts"]["adjudicated"] == 1
    assert owner_id not in json.dumps(report["json"])

    exported = http(
        runtime,
        f"/api/v1/admin/ratings/batches/{batch_id}/export.csv",
        tokens["admin"],
    )
    csv_text = exported["body"].decode("utf-8-sig")
    assert owner_id not in csv_text
    assert response.response_id not in csv_text
    assert "P001" in csv_text and "R001" in csv_text


def test_feedback_study_balances_consented_members_and_hides_full_feedback(
    portal_runtime,
):
    runtime, tokens = portal_runtime
    student_tokens = {tokens["a"]: "fixture-a", tokens["b"]: "fixture-b"}
    for key in ("a", "b"):
        _research_consent(runtime, tokens[key])
    for name in ("c", "d"):
        actor = runtime.auth.bootstrap_fixture_account(
            f"fixture-{name}",
            ActorRole.STUDENT,
            "fixture-password",
        )
        token = runtime.auth.login(actor.actor_id, "fixture-password")
        runtime.consents.activate(actor, "demo-v1", research_allowed=True)
        student_tokens[token] = actor.actor_id

    created = http(
        runtime,
        "/api/v1/admin/studies",
        tokens["admin"],
        method="POST",
        payload={"title": "Fixture feedback study", "seed": 4, "min_days": 7},
    )
    assert created["code"] == 201
    study_id = created["json"]["study_id"]
    started = http(
        runtime,
        f"/api/v1/admin/studies/{study_id}/start",
        tokens["admin"],
        method="POST",
        payload={},
    )
    assert started["code"] == 200
    assert started["json"]["participants"] == 4

    score_only = runtime.store.connection.execute(
        "SELECT participant_id FROM study_enrollments "
        "WHERE study_id=? AND arm='score_only' LIMIT 1",
        (study_id,),
    ).fetchone()[0]
    token = next(key for key, actor_id in student_tokens.items() if actor_id == score_only)
    report_record = submit_completed(runtime, token)
    report = http(
        runtime,
        f"/api/student/responses/{report_record.response_id}/report",
        token,
    )
    assert report["code"] == 200
    assert set(report["json"]) == {"overall_score", "overall_band"}
    page = http(
        runtime,
        f"/student/responses/{report_record.response_id}/report",
        token,
    )
    assert page["code"] == 200
    assert "đang được ẩn theo nhóm tham gia" in page["body"].decode("utf-8")
    assert "coverage" not in page["body"].decode("utf-8").lower()

    answers = {
        "knew_what_to_practise": 4,
        "understood": 4,
        "trusted": 3,
        "practised_more": 5,
        "would_continue": 4,
    }
    survey = http(
        runtime,
        "/api/v1/me/study/survey",
        token,
        method="POST",
        payload={"phase": "post", "answers": answers},
    )
    assert survey["code"] == 201
    repeated = http(
        runtime,
        "/api/v1/me/study/survey",
        token,
        method="POST",
        payload={"phase": "post", "answers": answers},
    )
    assert repeated["code"] == 409

    csv_response = http(
        runtime,
        f"/api/v1/admin/studies/{study_id}/export.csv",
        tokens["admin"],
    )
    csv_text = csv_response["body"].decode("utf-8-sig")
    assert all(actor_id not in csv_text for actor_id in student_tokens.values())
    assert "P001" in csv_text and "fixture-a" not in csv_text


def test_manual_sem_requires_provenance_and_returns_insufficient_change_state(
    portal_runtime,
):
    runtime, tokens = portal_runtime
    rejected = http(
        runtime,
        "/api/v1/admin/sem",
        tokens["admin"],
        method="POST",
        payload={"value": 0.4, "source": "model RMSE", "sample_count": 12},
    )
    assert rejected["code"] == 422
    saved = http(
        runtime,
        "/api/v1/admin/sem",
        tokens["admin"],
        method="POST",
        payload={"value": 0.4, "source": "same-task retest fixture", "sample_count": 12},
    )
    assert saved["code"] == 201
    change = http(runtime, "/api/v1/me/reliable-change", tokens["a"])
    assert change["code"] == 200
    assert change["json"]["verdict"] == "chua_du_du_lieu"
    assert change["json"]["sem_method"] == "manual"


def test_stale_review_session_keeps_its_recorded_type_after_blind_rating(portal_runtime):
    runtime, tokens = portal_runtime
    _research_consent(runtime, tokens["a"])
    response = submit_completed(runtime, tokens["a"])
    created = http(
        runtime,
        "/api/v1/admin/ratings/batches",
        tokens["admin"],
        method="POST",
        payload={
            "name": "Fixture timing",
            "rater_ids": ["fixture-teacher", "fixture-other-teacher"],
            "seed": 23,
        },
    )
    assert created["code"] == 201
    blind_token = http(runtime, "/api/v1/rating/assignments", tokens["teacher"])["json"][
        "assignments"
    ][0]["token"]
    assert (
        http(runtime, f"/api/v1/rating/assignments/{blind_token}", tokens["teacher"])["code"] == 200
    )
    rating = {
        "overall": 3.0,
        "band": "B1",
        "criteria": dict.fromkeys(("range", "accuracy", "fluency", "coherence", "phonology"), 3.0),
        "rationale": "Fixture review rating.",
    }
    assert (
        http(
            runtime,
            f"/api/v1/rating/assignments/{blind_token}/submit",
            tokens["teacher"],
            method="POST",
            payload=rating,
        )["code"]
        == 200
    )
    research = runtime.app._research_api.service
    actor = runtime.auth.resolve(tokens["teacher"])
    research.mark_review_started(actor.actor_id, response.response_id, action="decision")
    old = (datetime.now(UTC) - timedelta(minutes=31)).isoformat()
    runtime.store.connection.execute(
        "UPDATE review_sessions SET started_at=? WHERE response_id=? AND reviewer_id=? "
        "AND state='OPEN'",
        (old, response.response_id, actor.actor_id),
    )

    research.teacher_time_report()
    session = runtime.store.connection.execute(
        "SELECT action,state FROM review_sessions WHERE response_id=? AND reviewer_id=? "
        "AND started_at=?",
        (response.response_id, actor.actor_id, old),
    ).fetchone()
    assert session == ("decision", "CLOSED")
