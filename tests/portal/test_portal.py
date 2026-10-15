from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime, timedelta

import pytest

from aicefr.auth.errors import ConflictError
from aicefr.auth.service import AuthorizationError
from aicefr.contracts import Band, ReviewAction
from aicefr.local.app import create_runtime
from aicefr.portal.contracts import AccountChange, DeleteRequest, PageQuery, QCChange, TaskRecord
from aicefr.report.contracts import DiagnosticReport
from aicefr.review.service import ReviewActionRequest
from aicefr.storage.sqlite import ConcurrentResponseUpdate
from conftest import http, submit_completed


def test_lists_are_owner_scoped_and_staff_stats_separate_teacher_results(portal_runtime):
    runtime, tokens = portal_runtime
    first = submit_completed(runtime, tokens["a"])
    submit_completed(runtime, tokens["b"], score=3.0, band=Band.B1)
    assert runtime.portal.responses(tokens["a"], PageQuery())["total"] == 1
    candidate = runtime.portal.request_review(
        tokens["teacher"], first.response_id, first.revision, runtime.app._reviews
    )
    runtime.app._review_api.decide(
        tokens["teacher"],
        first.response_id,
        ReviewActionRequest(
            action=ReviewAction.OVERRIDE,
            final_band=Band.B1,
            reason="Fixture review",
            expected_revision=candidate.revision,
        ),
    )
    stats = runtime.portal.statistics(tokens["teacher"], PageQuery())
    assert stats["ai_bands"] == {"B1": 1, "B2": 1}
    assert stats["teacher_final_bands"] == {"B1": 1}
    assert stats["mean_overall_by_model"] == {"fixture-model": 3.65}
    assert (
        http(runtime, "/api/student/responses/" + first.response_id + "/report", tokens["b"])[
            "code"
        ]
        == 404
    )
    assert (
        http(runtime, "/api/student/responses", tokens["a"], query="limit=1")["json"]["total"] == 1
    )
    assert (
        http(runtime, "/api/student/progress", tokens["a"])["json"]["teacher_verified_count"] == 1
    )
    assert http(runtime, "/api/teacher/responses", tokens["teacher"])["json"]["total"] == 2
    assert http(runtime, "/api/teacher/responses", tokens["a"])["code"] == 403
    assert (
        http(runtime, "/api/teacher/stats", tokens["teacher"], query="status=WRONG")["code"] == 400
    )
    assert http(runtime, "/api/student/responses", tokens["a"], query="limit=201")["code"] == 400
    assert http(runtime, "/api/student/responses")["code"] == 401


def test_staff_report_not_ready_returns_controlled_conflict(portal_runtime):
    runtime, tokens = portal_runtime
    response = submit_completed(runtime, tokens["a"])
    with runtime.store.transaction() as connection:
        connection.execute(
            "DELETE FROM diagnostic_reports WHERE response_id=?", (response.response_id,)
        )
        connection.execute(
            "UPDATE responses SET status='QUEUED' WHERE response_id=?", (response.response_id,)
        )
    for role in ("teacher", "admin"):
        for prefix in ("", "/api"):
            view = http(
                runtime,
                f"{prefix}/teacher/responses/{response.response_id}/report",
                tokens[role],
            )
            assert view["code"] == 409
            if prefix:
                assert view["json"]["error"] == "REPORT_NOT_READY"
            else:
                assert "Báo cáo chưa sẵn sàng" in view["body"].decode()
    assert (
        http(runtime, f"/api/student/responses/{response.response_id}/report", tokens["b"])["code"]
        == 404
    )


@pytest.mark.parametrize(
    "path",
    [
        "/admin",
        "/admin/accounts",
        "/admin/tasks",
        "/admin/models",
        "/admin/config",
        "/admin/audit",
        "/admin/erase",
        "/admin/maintenance",
        "/teacher/stats",
        "/teacher/responses",
    ],
)
def test_admin_pages_render_and_student_denied(portal_runtime, path):
    runtime, tokens = portal_runtime
    allowed = http(runtime, path, tokens["admin"])
    assert allowed["code"] == 200
    assert allowed["body"].count(b"<html") == 1
    assert http(runtime, path, tokens["a"])["code"] == 403


def test_task_versions_and_closing_survive_restart(portal_runtime):
    runtime, tokens = portal_runtime
    record = submit_completed(runtime, tokens["a"])
    original = runtime.portal.tasks.get(record.task_id, record.task_version)
    changed = original.model_copy(update={"title": "Changed wording"})
    with pytest.raises(ConcurrentResponseUpdate):
        runtime.portal.save_task(tokens["admin"], changed, original.revision)
    runtime.portal.save_task(tokens["admin"], original.model_copy(update={"active": False}), 1)
    assert runtime.portal.task_list(tokens["a"]) == []
    created = runtime.portal.save_task(
        tokens["admin"],
        TaskRecord(
            task_id="new",
            task_version="v2",
            title="<script>unsafe</script>",
            prompt_text="Speak about learning",
        ),
        0,
    )
    assert created["revision"] == 1
    reopened = create_runtime(runtime.store.data_dir, config=runtime.control.config)
    try:
        assert reopened.portal.tasks.get("demo-speaking", "1").active is False
        assert reopened.portal.tasks.get("new", "v2").title == "<script>unsafe</script>"
    finally:
        reopened.close()
    assert b"<script>unsafe</script>" not in http(runtime, "/student/tasks", tokens["a"])["body"]


def test_lockout_unlock_disable_and_session_revocation(portal_runtime):
    runtime, tokens = portal_runtime
    for _ in range(5):
        with pytest.raises(AuthorizationError):
            runtime.auth.login("fixture-a", "wrong")
    with pytest.raises(AuthorizationError):
        runtime.auth.login("fixture-a", "fixture-password")
    assert runtime.store.get_account("fixture-a").failed_attempts == 5
    runtime.portal.change_account(tokens["admin"], "fixture-a", AccountChange(unlock=True))
    new_token = runtime.auth.login("fixture-a", "fixture-password")
    runtime.portal.change_account(tokens["admin"], "fixture-a", AccountChange(disabled=True))
    for token in (tokens["a"], new_token):
        with pytest.raises(AuthorizationError):
            runtime.auth.resolve(token)
        with pytest.raises(ConflictError, match="self_action_prohibited"):
            runtime.portal.change_account(
                tokens["admin"], "fixture-admin", AccountChange(disabled=True)
            )
    accounts = runtime.portal.accounts(tokens["admin"])
    assert "password" not in json.dumps(accounts)
    assert http(runtime, "/api/admin/accounts", tokens["teacher"])["code"] == 403
    assert (
        http(
            runtime,
            "/api/admin/accounts",
            tokens["admin"],
            method="POST",
            payload={"actor_id": "fixture-new", "role": "teacher", "password": "short"},
        )["code"]
        == 400
    )


def test_cookie_mutations_require_origin_and_bearer_cannot_spoof_role(portal_runtime):
    runtime, tokens = portal_runtime
    payload = {"actor_id": "fixture-new", "role": "teacher", "password": "new-password"}
    assert (
        http(
            runtime,
            "/api/admin/accounts",
            tokens["admin"],
            method="POST",
            payload=payload,
            cookie=True,
            origin=False,
        )["code"]
        == 403
    )
    assert (
        http(runtime, "/api/admin/accounts", tokens["a"], method="POST", payload=payload)["code"]
        == 403
    )
    assert (
        http(
            runtime,
            "/api/admin/accounts",
            tokens["admin"],
            method="POST",
            payload=payload,
            origin=False,
        )["code"]
        == 200
    )
    assert (
        http(runtime, "/api/admin/accounts", tokens["admin"], method="POST", payload=payload)[
            "code"
        ]
        == 409
    )


def test_research_export_requires_separate_active_opt_in(portal_runtime):
    runtime, tokens = portal_runtime
    first = submit_completed(runtime, tokens["a"])
    submit_completed(runtime, tokens["b"])
    assert runtime.portal.research_export(tokens["admin"], "demo-v1")["row_count"] == 0
    actor = runtime.auth.resolve(tokens["a"])
    runtime.consents.activate(actor, "demo-v1", research_allowed=True)
    research = runtime.portal.research_export(tokens["admin"], "demo-v1")
    assert research["row_count"] == 1
    assert first.response_id not in json.dumps(research)
    assert "fixture-a" not in json.dumps(research)
    assert runtime.portal.research_export(tokens["admin"], "new-consent")["row_count"] == 0
    runtime.consents.withdraw(actor)
    assert runtime.portal.research_export(tokens["admin"], "demo-v1")["row_count"] == 0
    exported = runtime.portal.export_own(tokens["a"])
    assert exported["row_count"] == 1
    assert "password_hash" not in json.dumps(exported)
    assert exported["responses"][0]["report"]["criteria"][0]["coverage"] == 0.5
    assert all(
        "score" not in criterion for criterion in runtime.portal.profile(tokens["a"])["coverage"]
    )


def test_delete_commits_metadata_and_retryable_blob_intent(portal_runtime, monkeypatch):
    runtime, tokens = portal_runtime
    response = submit_completed(runtime, tokens["a"])
    assert (
        http(
            runtime,
            f"/api/student/responses/{response.response_id}/delete",
            tokens["b"],
            method="POST",
            payload={"confirm_id": response.response_id, "expected_revision": response.revision},
        )["code"]
        == 404
    )
    with pytest.raises(ConcurrentResponseUpdate):
        runtime.data.delete_response(
            tokens["a"],
            response.response_id,
            DeleteRequest(confirm_id=response.response_id, expected_revision=1),
        )
    assert runtime.responses.blobs.read(response.blob)
    original = runtime.data.cleanup_pending
    monkeypatch.setattr(runtime.data, "cleanup_pending", lambda: {"pending": 1})
    runtime.data.delete_response(
        tokens["a"],
        response.response_id,
        DeleteRequest(confirm_id=response.response_id, expected_revision=response.revision),
    )
    assert runtime.store.get_response(response.response_id) is None
    assert (
        runtime.store.connection.execute("SELECT COUNT(*) FROM blob_deletions").fetchone()[0] == 1
    )
    monkeypatch.setattr(runtime.data, "cleanup_pending", original)
    assert original() == {"removed": 1, "pending": 0}
    assert not runtime.responses.blobs._path(response.blob.blob_id).exists()
    assert any(event.action == "response_deleted" for event in runtime.store.list_audit())


def test_delete_rolls_back_without_removing_blob_if_audit_fails(portal_runtime, monkeypatch):
    runtime, tokens = portal_runtime
    response = submit_completed(runtime, tokens["a"])

    def fail(*args, **kwargs):
        raise sqlite3.OperationalError("fixture failure")

    monkeypatch.setattr(runtime.portal, "audit", fail)
    with pytest.raises(sqlite3.OperationalError):
        runtime.data.delete_response(
            tokens["a"],
            response.response_id,
            DeleteRequest(confirm_id=response.response_id, expected_revision=response.revision),
        )
    assert runtime.store.get_response(response.response_id) == response
    assert runtime.responses.blobs.read(response.blob)
    assert (
        runtime.store.connection.execute("SELECT COUNT(*) FROM blob_deletions").fetchone()[0] == 0
    )


def test_erasure_preview_fingerprint_and_retention_keep_scores(portal_runtime):
    runtime, tokens = portal_runtime
    response = submit_completed(runtime, tokens["a"])
    preview = runtime.data.erasure_preview(tokens["admin"], "fixture-a")
    second = submit_completed(runtime, tokens["a"])
    with pytest.raises(ConcurrentResponseUpdate):
        runtime.data.erase(tokens["admin"], "fixture-a", "fixture-a", preview["fingerprint"])
    old_date = (datetime.now(UTC) - timedelta(days=190)).isoformat()
    runtime.store.connection.execute(
        "UPDATE responses SET created_at=? WHERE response_id=?", (old_date, response.response_id)
    )
    assert runtime.data.retention(tokens["admin"])["row_count"] == 1
    assert runtime.store.get_response(response.response_id).audio_available
    runtime.data.retention(tokens["admin"], apply=True)
    assert not runtime.store.get_response(response.response_id).audio_available
    report = runtime.app._reports.get(response.response_id)
    assert isinstance(report, DiagnosticReport)
    assert report.overall_score == 4.3
    assert report.comments == ()
    assert runtime.store.get_response(second.response_id).audio_available
    now = datetime.now(UTC).isoformat()
    runtime.store.connection.execute(
        "INSERT OR IGNORE INTO account_profiles(account_id,updated_at) VALUES (?,?)",
        ("fixture-a", now),
    )
    runtime.store.connection.execute(
        "INSERT INTO temporary_passwords(account_id,password_hash,expires_at,"
        "created_at,created_by) "
        "VALUES (?,?,?,?,?)",
        ("fixture-a", "fixture-hash", now, now, "fixture-admin"),
    )
    runtime.store.connection.execute(
        "INSERT INTO account_identities(identity_id,account_id,provider,subject_hash,created_at) "
        "VALUES (?,?,?,?,?)",
        ("fixture-identity", "fixture-a", "google", "fixture-subject-hash", now),
    )
    runtime.store.connection.execute(
        "INSERT INTO activity_events(event_id,account_id,kind,object_id,recorded_at,detail_code) "
        "VALUES (?,?,?,?,?,?)",
        ("fixture-activity", "fixture-a", "fixture", None, now, None),
    )
    preview = runtime.data.erasure_preview(tokens["admin"], "fixture-a")
    runtime.data.erase(tokens["admin"], "fixture-a", "fixture-a", preview["fingerprint"])
    retained = runtime.store.get_account("fixture-a")
    assert retained is not None and retained.disabled and retained.password_hash == ""
    for table, owner_column in (
        ("account_profiles", "account_id"),
        ("temporary_passwords", "account_id"),
        ("account_identities", "account_id"),
        ("activity_events", "account_id"),
    ):
        assert (
            runtime.store.connection.execute(
                f"SELECT 1 FROM {table} WHERE {owner_column}='fixture-a'"
            ).fetchone()
            is None
        )
    assert runtime.portal.statistics(tokens["admin"], PageQuery())["total"] == 0
    assert runtime.store.list_audit()
    with pytest.raises(AuthorizationError):
        runtime.auth.resolve(tokens["a"])


def test_backup_includes_verified_blobs_and_safe_orphan_preview(portal_runtime, tmp_path):
    runtime, tokens = portal_runtime
    response = submit_completed(runtime, tokens["a"])
    orphan = runtime.responses.blobs.store(b"fixture orphan")
    import os
    import time

    os.utime(
        runtime.responses.blobs._path(orphan.blob_id), (time.time() - 7200, time.time() - 7200)
    )
    preview = runtime.data.orphans(tokens["admin"])
    assert preview["blob_ids"] == [orphan.blob_id]
    assert runtime.responses.blobs._path(orphan.blob_id).exists()
    destination = tmp_path / "backup"
    assert runtime.data.backup(tokens["admin"], destination)["response_count"] == 1
    snapshot = sqlite3.connect(destination / "metadata.sqlite3")
    assert snapshot.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    assert snapshot.execute("SELECT COUNT(*) FROM responses").fetchone()[0] == 1
    snapshot.close()
    assert (
        destination / "blobs" / response.blob.blob_id
    ).read_bytes() == runtime.responses.blobs.read(response.blob)
    with pytest.raises(FileExistsError):
        runtime.data.backup(tokens["admin"], destination)
    runtime.data.orphans(tokens["admin"], apply=True)
    assert runtime.responses.blobs.read(response.blob)
    assert not runtime.responses.blobs._path(orphan.blob_id).exists()


def test_erasure_scrubs_identity_but_retains_immutable_consent_history(portal_runtime):
    runtime, tokens = portal_runtime
    original = runtime.store.get_account("fixture-a").password_hash
    runtime.accounts.set_consent(tokens["a"], "consent-v1", True)
    now = datetime.now(UTC).isoformat()
    runtime.store.connection.execute(
        "INSERT INTO feedback_studies(study_id,title,state,seed,config_json,created_by,created_at) "
        "VALUES (?,?,?,?,?,?,?)",
        ("fixture-study", "Fixture", "RUNNING", 1, "{}", "fixture-admin", now),
    )
    runtime.store.connection.execute(
        "INSERT INTO study_enrollments(enrollment_id,study_id,participant_id,"
        "pseudonym,arm,enrolled_at) "
        "VALUES (?,?,?,?,?,?)",
        ("fixture-enrollment", "fixture-study", "fixture-a", "pseudonym-a", "control", now),
    )
    preview = runtime.data.erasure_preview(tokens["admin"], "fixture-a")
    consent_count = runtime.store.connection.execute(
        "SELECT COUNT(*) FROM consent_events WHERE account_id='fixture-a'"
    ).fetchone()[0]

    runtime.data.erase(tokens["admin"], "fixture-a", "fixture-a", preview["fingerprint"])

    retained = runtime.store.get_account("fixture-a")
    assert retained is not None and retained.disabled
    assert retained.password_hash != original
    assert retained.password_hash == ""
    assert (
        runtime.store.connection.execute(
            "SELECT COUNT(*) FROM consent_events WHERE account_id='fixture-a'"
        ).fetchone()[0]
        == consent_count
    )
    assert runtime.store.connection.execute(
        "SELECT withdrawn_at FROM study_enrollments WHERE participant_id='fixture-a'"
    ).fetchone()[0]
    for table, owner_column in (
        ("sessions", "actor_id"),
        ("account_profiles", "account_id"),
        ("temporary_passwords", "account_id"),
        ("account_identities", "account_id"),
        ("activity_events", "account_id"),
    ):
        assert (
            runtime.store.connection.execute(
                f"SELECT 1 FROM {table} WHERE {owner_column}='fixture-a'"
            ).fetchone()
            is None
        )
    with pytest.raises(AuthorizationError):
        runtime.auth.login("fixture-a", "fixture-password")


def test_qc_cas_validation_restart_and_old_report_provenance(portal_runtime):
    runtime, tokens = portal_runtime
    response = submit_completed(runtime, tokens["a"])
    previous = runtime.app._reports.get(response.response_id)
    updated = runtime.control.change_qc(
        tokens["admin"], QCChange(expected_revision=0, changes={"max_duration_s": 250})
    )
    assert updated["revision"] == 1
    with pytest.raises(ConcurrentResponseUpdate):
        runtime.control.change_qc(
            tokens["admin"], QCChange(expected_revision=0, changes={"max_duration_s": 200})
        )
    with pytest.raises(ValueError):
        runtime.control.change_qc(
            tokens["admin"], QCChange(expected_revision=1, changes={"max_duration_s": 301})
        )
    with pytest.raises(ValueError):
        runtime.control.change_qc(
            tokens["admin"], QCChange(expected_revision=1, changes={"review_silence_ratio": 0.99})
        )
    assert runtime.app._reports.get(response.response_id) == previous
    reopened = create_runtime(runtime.store.data_dir, config=runtime.control.config)
    try:
        assert reopened.control.pipeline._qc_config.version == updated["qc"]["version"]
        assert reopened.control.pipeline._qc_config.max_duration_s == 250
    finally:
        reopened.close()


def test_claim_owner_cas_release_and_admin_override(portal_runtime):
    runtime, tokens = portal_runtime
    response = submit_completed(runtime, tokens["a"])
    candidate = runtime.portal.request_review(
        tokens["teacher"], response.response_id, response.revision, runtime.app._reviews
    )
    claimed = runtime.app._review_api.claim(
        tokens["teacher"], response.response_id, candidate.revision
    )
    assert claimed.claimed_by == "fixture-teacher"
    request = {"expected_revision": claimed.revision, "action": "APPROVE"}
    assert (
        http(
            runtime,
            f"/api/teacher/reviews/{response.response_id}/decision",
            tokens["other-teacher"],
            method="POST",
            payload=request,
        )["code"]
        == 409
    )
    assert (
        http(
            runtime,
            f"/api/teacher/reviews/{response.response_id}/release",
            tokens["other-teacher"],
            method="POST",
            payload={"expected_revision": claimed.revision},
        )["code"]
        == 409
    )
    released = runtime.app._review_api.release(
        tokens["admin"], response.response_id, claimed.revision
    )
    assert released.claimed_by is None
    runtime.app._review_api.decide(
        tokens["other-teacher"],
        response.response_id,
        ReviewActionRequest(action=ReviewAction.APPROVE, expected_revision=released.revision),
    )
    assert runtime.app._reports.get(response.response_id).teacher_verified
    assert any(event.action == "review_released" for event in runtime.app._reviews.list_audit())


def test_liveness_metrics_and_failed_readiness_are_bounded(portal_runtime):
    runtime, tokens = portal_runtime
    assert http(runtime, "/healthz")["json"] == {"alive": True}
    assert http(runtime, "/readyz")["code"] == 503
    assert http(runtime, "/metrics", tokens["teacher"])["code"] == 403
    result = http(runtime, "/metrics", tokens["admin"])
    assert result["code"] == 200
    assert b"aicefr_http_requests_total" in result["body"]
    assert b"fixture-" not in result["body"]


def test_model_activation_keeps_pin_cas_and_reports(portal_runtime, tmp_path):
    import shutil

    from aicefr.scoring.artifact import ModelArtifactError, default_artifact_path

    runtime, tokens = portal_runtime
    directory = tmp_path / "models"
    directory.mkdir()
    try:
        source = default_artifact_path()
    except ModelArtifactError:
        pytest.skip("pinned external model artifact unavailable")
    if not source.is_file():
        pytest.skip("pinned external model artifact unavailable")
    shutil.copyfile(source, directory / "ridge_resp_v2.json")
    runtime.control.config["model_artifact"] = str(directory / "ridge_resp_v2.json")
    (directory / "incompatible.json").write_text("{}")
    items = runtime.control.models(tokens["admin"])["items"]
    assert any(item["name"] == "incompatible" and not item["compatible"] for item in items)
    response = submit_completed(runtime, tokens["a"])
    before = runtime.app._reports.get(response.response_id)
    activated = runtime.control.activate_model(tokens["admin"], "ridge_resp_v2", 0)
    assert activated["revision"] == 1
    with pytest.raises(ModelArtifactError):
        runtime.control.activate_model(tokens["admin"], "incompatible", 1)
    with pytest.raises(ValueError):
        runtime.control.activate_model(tokens["admin"], "../ridge_resp_v2", 1)
    with pytest.raises(ConcurrentResponseUpdate):
        runtime.control.activate_model(tokens["admin"], "ridge_resp_v2", 0)
    assert runtime.app._reports.get(response.response_id) == before


def test_local_server_lock_and_interrupted_job_recovery(portal_runtime):
    from aicefr.local.lock import acquire_server_lock

    runtime, tokens = portal_runtime
    lease = acquire_server_lock(runtime.store.data_dir)
    try:
        with pytest.raises(OSError):
            acquire_server_lock(runtime.store.data_dir)
    finally:
        lease.close()
    acquire_server_lock(runtime.store.data_dir).close()
    response = submit_completed(runtime, tokens["a"])
    runtime.store.connection.execute(
        "UPDATE responses SET status=? WHERE response_id=?", ("RUNNING", response.response_id)
    )
    restarted = create_runtime(
        runtime.store.data_dir, config={**runtime.control.config, "recover_interrupted": True}
    )
    try:
        recovered = restarted.store.get_response(response.response_id)
        assert recovered.status.value == "FAILED"
        assert recovered.status_reason.value == "PIPELINE_INTERRUPTED"
        assert recovered.revision == response.revision + 1
        assert restarted.responses.blobs.read(recovered.blob)
    finally:
        restarted.close()


def test_rate_limiter_expiry_and_bounded_cardinality():
    from aicefr.limits import RateLimiter

    now = [0]
    limiter = RateLimiter(clock=lambda: now[0], capacity=2)
    assert limiter.allow("upload", "fixture-a", limit=2)
    assert limiter.allow("upload", "fixture-a", limit=2)
    assert not limiter.allow("upload", "fixture-a", limit=2)
    now[0] = 61
    assert limiter.allow("upload", "fixture-a", limit=2)
    for key in ("b", "c", "d"):
        limiter.allow("login", key, limit=30)
    assert len(limiter._entries) == 2


def test_expired_claim_can_be_taken_over_but_new_claim_still_excludes_other_teachers(
    portal_runtime,
):
    runtime, tokens = portal_runtime
    response = submit_completed(runtime, tokens["a"])
    candidate = runtime.portal.request_review(
        tokens["teacher"], response.response_id, response.revision, runtime.app._reviews
    )
    claimed = runtime.app._review_api.claim(
        tokens["teacher"], response.response_id, candidate.revision
    )
    old = (datetime.now(UTC) - timedelta(minutes=16)).isoformat()
    runtime.store.connection.execute(
        "UPDATE review_candidates SET updated_at=? WHERE response_id=?", (old, response.response_id)
    )
    takeover = runtime.app._review_api.claim(
        tokens["other-teacher"], response.response_id, claimed.revision
    )
    assert takeover.claimed_by == "fixture-other-teacher"
    assert takeover.revision == claimed.revision + 1
    from aicefr.review.service import InvalidReviewTransition

    with pytest.raises(InvalidReviewTransition):
        runtime.app._review_api.decide(
            tokens["teacher"],
            response.response_id,
            ReviewActionRequest(action=ReviewAction.APPROVE, expected_revision=takeover.revision),
        )


def test_new_cli_account_backup_and_qc_score_flow(portal_runtime, tmp_path, monkeypatch, capsys):
    import io

    import numpy as np
    import soundfile as sf

    from aicefr.local.__main__ import main

    runtime, _ = portal_runtime
    config = tmp_path / "config.json"
    config.write_text(json.dumps(runtime.control.config))
    common = [
        "--data-dir",
        str(runtime.store.data_dir),
        "--config",
        str(config),
        "--password-stdin",
    ]
    monkeypatch.setattr("sys.stdin", io.StringIO("fixture-password\n"))
    assert main(["accounts", "list", "--actor-id", "fixture-admin", *common]) == 0
    listed = capsys.readouterr().out
    assert (
        "fixture-admin" in listed
        and "fixture-password" not in listed
        and "password_hash" not in listed
    )
    monkeypatch.setattr("sys.stdin", io.StringIO("fixture-password\n"))
    assert (
        main(
            [
                "maintenance",
                "backup",
                "--actor-id",
                "fixture-admin",
                "--destination",
                str(tmp_path / "cli-backup"),
                *common,
            ]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out)["includes"] == ["metadata", "blobs"]
    audio = tmp_path / "fixture.wav"
    samples = np.zeros(32000, dtype=np.float32)
    samples[24000:] = 0.2
    sf.write(audio, samples, 16000)
    monkeypatch.setattr("sys.stdin", io.StringIO("fixture-password\n"))
    assert (
        main(
            [
                "score",
                "--actor-id",
                "fixture-a",
                "--audio",
                str(audio),
                "--task-id",
                "demo-speaking",
                "--task-version",
                "1",
                *common,
            ]
        )
        == 0
    )
    scored = json.loads(capsys.readouterr().out)
    assert scored["status"]["status"] == "REVIEW_REQUIRED"
    assert scored["report"]["overall_score"] is None
    assert scored["report"]["reasons"] == ["QC_SILENCE_REVIEW"]


def test_review_reopen_preserves_previous_decision_and_records_real_before_after(portal_runtime):
    from aicefr.portal.contracts import ReviewReopen

    runtime, tokens = portal_runtime
    response = submit_completed(runtime, tokens["a"])
    repository = runtime.app._reviews
    candidate = runtime.portal.request_review(
        tokens["teacher"], response.response_id, response.revision, repository
    )
    runtime.app._review_api.decide(
        tokens["teacher"],
        response.response_id,
        ReviewActionRequest(
            action=ReviewAction.OVERRIDE,
            final_band=Band.B1,
            reason="Fixture first correction",
            expected_revision=candidate.revision,
        ),
    )
    current = repository.get(response.response_id)
    old = runtime.app._reports.get(response.response_id)
    reopened = runtime.portal.reopen_review(
        tokens["teacher"],
        response.response_id,
        ReviewReopen(expected_revision=current.revision, reason="Fixture second look"),
        repository,
    )
    assert runtime.app._reports.get(response.response_id) == old
    runtime.app._review_api.decide(
        tokens["other-teacher"],
        response.response_id,
        ReviewActionRequest(
            action=ReviewAction.OVERRIDE,
            final_band=Band.A2,
            reason="Fixture follow-up correction",
            expected_revision=reopened.revision,
        ),
    )
    assert runtime.app._reports.get(response.response_id).teacher_final.overall_band is Band.A2
    changes = [
        entry
        for entry in runtime.portal.history(tokens["teacher"], response.response_id)
        if entry["after_state"] is not None
    ]
    assert [(row["before_band"], row["after_band"]) for row in changes] == [
        ("B2", "B1"),
        ("B1", "A2"),
    ]
    assert (
        runtime.store.connection.execute("SELECT COUNT(*) FROM review_decisions").fetchone()[0] == 2
    )
    assert (
        http(
            runtime,
            f"/api/teacher/reviews/{response.response_id}/reopen",
            tokens["a"],
            method="POST",
            payload={"expected_revision": 1, "reason": "denied"},
        )["code"]
        == 403
    )


@pytest.mark.parametrize(
    "requested,code,expected",
    [
        ("bytes=1-3", 206, b"bcd"),
        ("bytes=2-", 206, b"cdef"),
        ("bytes=-2", 206, b"ef"),
        ("bytes=0-999", 206, b"abcdef"),
        ("bytes=99-", 416, b""),
        ("bytes=3-1", 416, b""),
        ("bytes=-0", 416, b""),
        ("bytes=1-2,4-5", 416, b""),
        ("garbage", 416, b""),
    ],
)
def test_audio_range_uses_bounded_standard_http_semantics(requested, code, expected):
    from aicefr.api.wsgi import StudentTeacherApp

    response = StudentTeacherApp._audio_response({"HTTP_RANGE": requested}, b"abcdef", "audio/wav")
    assert response.status == code and response.body == expected
    assert dict(response.headers)["Accept-Ranges"] == "bytes"
    assert ("Content-Range", "bytes */6") in response.headers if code == 416 else True
