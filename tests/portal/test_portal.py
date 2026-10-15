from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import time
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from aicefr.auth.errors import ConflictError
from aicefr.auth.service import AuthorizationError
from aicefr.billing.secrets import KeyStoreError
from aicefr.contracts import Band, ReviewAction
from aicefr.local.app import create_runtime
from aicefr.portal.contracts import AccountChange, DeleteRequest, PageQuery, QCChange, TaskRecord
from aicefr.report.contracts import DiagnosticReport
from aicefr.review.service import ReviewActionRequest
from aicefr.storage.blob import BlobIntegrityError
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
    assert original.topic_keywords == ("learning", "education")
    changed = original.model_copy(update={"title": "Changed wording"})
    with pytest.raises(ConcurrentResponseUpdate):
        runtime.portal.save_task(tokens["admin"], changed, original.revision)
    with pytest.raises(ConcurrentResponseUpdate):
        runtime.portal.save_task(
            tokens["admin"],
            original.model_copy(update={"topic_keywords": ("science",)}),
            original.revision,
        )
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
    assert created["topic_keywords"] == []
    second_version = runtime.portal.save_task(
        tokens["admin"],
        TaskRecord(
            task_id="demo-speaking",
            task_version="2",
            title="Learning and science",
            prompt_text="Talk about science and learning.",
            topic_keywords=("science", "learning"),
        ),
        0,
    )
    assert second_version["topic_keywords"] == ["science", "learning"]
    assert created["revision"] == 1
    changed_seed = deepcopy(runtime.control.config)
    changed_seed["tasks"][0]["topic_keywords"] = ("weather",)
    reopened = create_runtime(runtime.store.data_dir, config=changed_seed)
    try:
        assert reopened.portal.tasks.get("demo-speaking", "1").active is False
        assert reopened.portal.tasks.get("demo-speaking", "1").topic_keywords == (
            "learning",
            "education",
        )
        assert reopened.portal.tasks.get("demo-speaking", "2").topic_keywords == (
            "science",
            "learning",
        )
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


def test_blob_cleanup_preserves_live_blob_and_retries_failed_unlink(portal_runtime, monkeypatch):
    runtime, tokens = portal_runtime
    response = submit_completed(runtime, tokens["a"])
    runtime.data._queue_blob(response)
    live = runtime.data.cleanup_pending()
    assert live == {"removed": 0, "pending": 0}
    assert runtime.responses.blobs._path(response.blob.blob_id).is_file()
    state = runtime.store.connection.execute(
        "SELECT state FROM cleanup_intents WHERE resource_kind='blob' AND resource_id=?",
        (response.blob.blob_id,),
    ).fetchone()
    assert state == ("complete",)

    orphan = runtime.responses.blobs.store(b"retry this blob")
    runtime.data._queue_blob(SimpleNamespace(blob=orphan))
    real_path = runtime.data.blobs._path

    class FailingUnlink:
        def unlink(self, *, missing_ok=False):
            raise OSError("fixture unlink failure")

    monkeypatch.setattr(runtime.data.blobs, "_path", lambda _blob_id: FailingUnlink())
    failed = runtime.data.cleanup_pending()
    assert failed == {"removed": 0, "pending": 1}
    intent = runtime.store.connection.execute(
        "SELECT state,attempt,last_reason FROM cleanup_intents "
        "WHERE resource_kind='blob' AND resource_id=?",
        (orphan.blob_id,),
    ).fetchone()
    assert intent == ("pending", 1, "OSError")
    assert runtime.store.connection.execute(
        "SELECT 1 FROM blob_deletions WHERE blob_id=?", (orphan.blob_id,)
    ).fetchone()

    monkeypatch.setattr(runtime.data.blobs, "_path", real_path)
    runtime.store.connection.execute(
        "UPDATE cleanup_intents SET available_at=0 WHERE resource_kind='blob' AND resource_id=?",
        (orphan.blob_id,),
    )
    retried = runtime.data.cleanup_pending()
    assert retried == {"removed": 1, "pending": 0}
    assert not runtime.data.blobs._path(orphan.blob_id).exists()
    assert (
        runtime.store.connection.execute(
            "SELECT 1 FROM cleanup_intents WHERE resource_kind='blob' AND resource_id=?",
            (orphan.blob_id,),
        ).fetchone()
        is None
    )


def test_data_control_paths_and_protected_files_fail_closed(tmp_path, monkeypatch):
    from aicefr.portal.data import DataControl

    valid_path = tmp_path / "valid.key"
    valid_path.write_bytes(b"protected fixture")
    valid_path.chmod(0o600)
    assert DataControl._read_protected_file(valid_path) == b"protected fixture"
    assert DataControl._safe_path(valid_path, must_exist=True) == valid_path.resolve()
    with pytest.raises(FileNotFoundError):
        DataControl._safe_path(tmp_path / "missing", must_exist=True)

    linked_file = tmp_path / "linked.key"
    linked_file.symlink_to(valid_path)
    with pytest.raises(ValueError, match="protected key file is unsafe"):
        DataControl._read_protected_file(linked_file)
    with pytest.raises(ValueError, match="filesystem path cannot contain symlinks"):
        DataControl._safe_path(linked_file)
    dangling = tmp_path / "dangling"
    dangling.symlink_to(tmp_path / "absent")
    with pytest.raises(ValueError, match="filesystem path cannot contain symlinks"):
        DataControl._safe_path(dangling)

    broad = tmp_path / "broad.key"
    broad.write_bytes(b"protected fixture")
    broad.chmod(0o644)
    with pytest.raises(ValueError, match="protected key file is unsafe"):
        DataControl._read_protected_file(broad)
    linked = tmp_path / "hardlinked.key"
    os.link(valid_path, linked)
    with pytest.raises(ValueError, match="protected key file is unsafe"):
        DataControl._read_protected_file(valid_path)

    oversized = tmp_path / "oversized.key"
    oversized.write_bytes(b"x" * 4097)
    oversized.chmod(0o600)
    with pytest.raises(ValueError, match="protected key file is unsafe"):
        DataControl._read_protected_file(oversized)
    with pytest.raises(ValueError, match="protected key file is unavailable"):
        DataControl._read_protected_file(tmp_path / "absent.key")

    monkeypatch.setattr(os, "getuid", lambda: valid_path.stat().st_uid + 1)
    with pytest.raises(ValueError, match="protected key file is unsafe"):
        DataControl._read_protected_file(valid_path)


def test_orphan_scan_requires_age_and_rechecks_published_media(portal_runtime):
    runtime, tokens = portal_runtime
    orphan = runtime.responses.blobs.store(b"orphan fixture")
    orphan_path = runtime.data.blobs._path(orphan.blob_id)
    os.utime(orphan_path, (time.time() - 7200, time.time() - 7200))
    fresh = runtime.responses.blobs.store(b"fresh orphan")
    first = runtime.data.orphans(tokens["admin"])
    assert orphan.blob_id in first["blob_ids"]
    assert fresh.blob_id not in first["blob_ids"]
    applied = runtime.data.orphans(tokens["admin"], apply=True)
    assert applied["dry_run"] is False
    assert not orphan_path.exists()
    assert runtime.data.blobs._path(fresh.blob_id).exists()


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
    assert runtime.store.get_account("fixture-a") is None
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
    stale_account_fks = []
    for (table,) in runtime.store.connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    ):
        quoted = '"' + table.replace('"', '""') + '"'
        for foreign_key in runtime.store.connection.execute(f"PRAGMA foreign_key_list({quoted})"):
            if foreign_key[2] == "accounts" and foreign_key[4] == "actor_id":
                column = '"' + str(foreign_key[3]).replace('"', '""') + '"'
                if runtime.store.connection.execute(
                    f"SELECT 1 FROM {quoted} WHERE {column}='fixture-a' LIMIT 1"
                ).fetchone():
                    stale_account_fks.append((table, foreign_key[3]))
    assert stale_account_fks == []
    assert runtime.portal.statistics(tokens["admin"], PageQuery())["total"] == 0
    assert runtime.store.list_audit()
    with pytest.raises(AuthorizationError):
        runtime.auth.resolve(tokens["a"])


def test_backup_includes_verified_blobs_and_safe_orphan_preview(portal_runtime, tmp_path):
    runtime, tokens = portal_runtime
    response = submit_completed(runtime, tokens["a"])
    now = datetime.now(UTC).isoformat()
    runtime.store.connection.execute(
        "INSERT INTO learning_paths VALUES('path-1','Path','', 'published',1,?,?)",
        (now, now),
    )
    runtime.store.connection.execute(
        "INSERT INTO learning_units VALUES('unit-1','path-1','Unit',1)"
    )
    runtime.store.connection.execute(
        "INSERT INTO learning_lessons VALUES('lesson-1','unit-1','Lesson',1,?)", (now,)
    )
    runtime.store.connection.execute(
        "INSERT INTO lesson_versions VALUES('lesson-1',1,'published','rules-v1',?,?)",
        (now, now),
    )
    runtime.store.connection.execute(
        "INSERT INTO learning_media VALUES('media-1','lesson-1','audio',?,?,?,?)",
        (response.blob.blob_id, response.blob.sha256, response.blob.size_bytes, now),
    )
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
    manifest = runtime.data.backup(tokens["admin"], destination)
    assert manifest["response_count"] == 1
    assert manifest["blob_count"] == 1
    assert manifest["media_families"] == ["responses", "learning_media"]
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
    runtime.data.delete_response(
        tokens["a"],
        response.response_id,
        DeleteRequest(confirm_id=response.response_id, expected_revision=response.revision),
    )
    assert (
        runtime.responses.blobs.read(response.blob)
        == runtime.responses.blobs._path(response.blob.blob_id).read_bytes()
    )
    assert runtime.store.connection.execute(
        "SELECT blob_id FROM learning_media WHERE media_id='media-1'"
    ).fetchone() == (response.blob.blob_id,)


def test_backup_missing_referenced_blob_fails_closed_and_removes_partial_snapshot(
    portal_runtime, tmp_path
):
    runtime, tokens = portal_runtime
    response = submit_completed(runtime, tokens["a"])
    runtime.responses.blobs._path(response.blob.blob_id).unlink()
    destination = tmp_path / "incomplete-backup"

    with pytest.raises(BlobIntegrityError):
        runtime.data.backup(tokens["admin"], destination)

    assert not destination.exists()


@pytest.mark.parametrize("failure", ["audit", "revoked_admin"])
def test_backup_final_audit_failure_or_revoked_admin_removes_snapshot(
    portal_runtime, tmp_path, monkeypatch, failure
):
    runtime, tokens = portal_runtime
    submit_completed(runtime, tokens["a"])
    destination = tmp_path / f"backup-{failure}"
    if failure == "audit":

        def fail_audit(*args, **kwargs):
            raise sqlite3.OperationalError("audit unavailable")

        monkeypatch.setattr(runtime.store, "record_audit", fail_audit)
        expected = sqlite3.OperationalError
    else:
        original_read = runtime.data.blobs.read

        def revoke_during_snapshot(blob):
            result = original_read(blob)
            runtime.auth.logout(tokens["admin"])
            return result

        monkeypatch.setattr(runtime.data.blobs, "read", revoke_during_snapshot)
        expected = AuthorizationError

    with pytest.raises(expected):
        runtime.data.backup(tokens["admin"], destination)

    assert not destination.exists()


def test_backup_rejects_conflicting_shared_media_metadata_and_fk_damage(portal_runtime, tmp_path):
    runtime, tokens = portal_runtime
    response = submit_completed(runtime, tokens["a"])
    now = datetime.now(UTC).isoformat()
    runtime.store.connection.execute(
        "INSERT INTO learning_paths VALUES('conflict-path','Path','', 'published',1,?,?)",
        (now, now),
    )
    runtime.store.connection.execute(
        "INSERT INTO learning_units VALUES('conflict-unit','conflict-path','Unit',1)"
    )
    runtime.store.connection.execute(
        "INSERT INTO learning_lessons VALUES('conflict-lesson','conflict-unit','Lesson',1,?)",
        (now,),
    )
    runtime.store.connection.execute(
        "INSERT INTO learning_media VALUES('conflict-media','conflict-lesson','audio',?,?,?,?)",
        (response.blob.blob_id, "0" * 64, response.blob.size_bytes, now),
    )
    conflict_destination = tmp_path / "conflicting-media-backup"
    with pytest.raises(ValueError, match="shared media metadata conflict"):
        runtime.data.backup(tokens["admin"], conflict_destination)
    assert not conflict_destination.exists()

    runtime.store.connection.execute("DELETE FROM learning_media WHERE media_id='conflict-media'")
    runtime.store.connection.execute("PRAGMA foreign_keys=OFF")
    runtime.store.connection.execute(
        "INSERT INTO activity_events(event_id,account_id,kind,object_id,recorded_at,detail_code) "
        "VALUES('broken-fk','missing-account','test',NULL,?,'fixture')",
        (now,),
    )
    damaged_destination = tmp_path / "foreign-key-backup"
    with pytest.raises(ValueError, match="foreign-key violations"):
        runtime.data.backup(tokens["admin"], damaged_destination)
    assert not damaged_destination.exists()


def _refresh_backup_file_hashes(backup_path):
    manifest_path = backup_path / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["files"] = {
        path.relative_to(backup_path).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(backup_path.rglob("*"))
        if path.is_file() and path.name != "manifest.json"
    }
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    return manifest


@pytest.mark.parametrize("damage", ["schema", "foreign_key"])
def test_restore_rejects_database_schema_and_foreign_key_damage(portal_runtime, tmp_path, damage):
    runtime, tokens = portal_runtime
    source = tmp_path / f"damaged-{damage}-backup"
    runtime.data.backup(tokens["admin"], source)
    database = source / "metadata.sqlite3"
    connection = sqlite3.connect(database)
    if damage == "schema":
        connection.execute("PRAGMA user_version=9")
    else:
        connection.execute("PRAGMA foreign_keys=OFF")
        connection.execute("DELETE FROM accounts WHERE actor_id='fixture-a'")
    connection.commit()
    connection.close()
    _refresh_backup_file_hashes(source)
    destination = tmp_path / f"restore-{damage}"
    expected = "schema version mismatch" if damage == "schema" else "foreign-key check failed"

    with pytest.raises(ValueError, match=expected):
        runtime.data.restore_backup(source, destination, tokens["admin"])
    assert not destination.exists()


def test_restore_rejects_invalid_manifest_entries_and_corrupt_protected_key(
    portal_runtime, tmp_path
):
    runtime, tokens = portal_runtime
    source = tmp_path / "valid-source"
    runtime.data.backup(tokens["admin"], source)
    cases = {
        "files_type": lambda manifest: manifest.update(files=[]),
        "digest_format": lambda manifest: manifest["files"].update(
            {"metadata.sqlite3": "not-a-sha256"}
        ),
        "sensitive_type": lambda manifest: manifest.update(sensitive_files="billing-hmac.key"),
        "unknown_sensitive": lambda manifest: manifest.update(sensitive_files=["secret.key"]),
    }
    for name, mutate in cases.items():
        candidate = tmp_path / f"manifest-{name}"
        shutil.copytree(source, candidate)
        manifest_path = candidate / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        mutate(manifest)
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        with pytest.raises(ValueError):
            runtime.data.restore_backup(candidate, tmp_path / f"restore-{name}", tokens["admin"])

    corrupt_key = tmp_path / "corrupt-key"
    shutil.copytree(source, corrupt_key)
    (corrupt_key / "billing-hmac.key").write_bytes(b"malformed protected key")
    _refresh_backup_file_hashes(corrupt_key)
    rejected_destination = tmp_path / "restore-corrupt-key"
    with pytest.raises(KeyStoreError, match="key"):
        runtime.data.restore_backup(corrupt_key, rejected_destination, tokens["admin"])
    assert not rejected_destination.exists()
    assert not list(tmp_path.glob("restore-corrupt-key.staging-*"))


def test_restore_rejects_media_hash_mismatch_after_manifest_checksum_is_updated(
    portal_runtime, tmp_path
):
    runtime, tokens = portal_runtime
    response = submit_completed(runtime, tokens["a"])
    source = tmp_path / "media-mismatch-source"
    runtime.data.backup(tokens["admin"], source)
    (source / "blobs" / response.blob.blob_id).write_bytes(b"different length and content")
    _refresh_backup_file_hashes(source)

    with pytest.raises(ValueError, match="media does not match database reference"):
        runtime.data.restore_backup(source, tmp_path / "restore-media-mismatch", tokens["admin"])


@pytest.mark.parametrize("manifest_kind", ["oversized", "directory"])
def test_restore_rejects_oversized_or_nonregular_manifest(portal_runtime, tmp_path, manifest_kind):
    runtime, tokens = portal_runtime
    source = tmp_path / f"bad-manifest-{manifest_kind}"
    runtime.data.backup(tokens["admin"], source)
    manifest_path = source / "manifest.json"
    if manifest_kind == "oversized":
        manifest_path.write_bytes(b" " * (1_048_577))
    else:
        manifest_path.unlink()
        manifest_path.mkdir()

    with pytest.raises(ValueError, match="manifest is unsafe|manifest is invalid"):
        runtime.data.restore_backup(source, tmp_path / f"restore-{manifest_kind}", tokens["admin"])


def test_restore_rejects_symlink_overlap_and_existing_destination(portal_runtime, tmp_path):
    runtime, tokens = portal_runtime
    source = tmp_path / "safe-source"
    runtime.data.backup(tokens["admin"], source)
    linked_source = tmp_path / "source-link"
    linked_source.symlink_to(source, target_is_directory=True)
    with pytest.raises(ValueError, match="backup source cannot be a symlink"):
        runtime.data.restore_backup(linked_source, tmp_path / "restore-link", tokens["admin"])
    with pytest.raises(ValueError, match="overlap protected data"):
        runtime.data.restore_backup(source, runtime.store.data_dir, tokens["admin"])
    existing = tmp_path / "existing-restore"
    existing.mkdir()
    with pytest.raises(FileExistsError, match="destination must be fresh"):
        runtime.data.restore_backup(source, existing, tokens["admin"])


def test_restore_missing_referenced_media_and_audit_failure_leave_no_destination(
    portal_runtime, tmp_path, monkeypatch
):
    runtime, tokens = portal_runtime
    response = submit_completed(runtime, tokens["a"])
    source = tmp_path / "source-backup"
    runtime.data.backup(tokens["admin"], source)
    blob_path = source / "blobs" / response.blob.blob_id
    blob_path.unlink()
    manifest_path = source / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["files"].pop(f"blobs/{response.blob.blob_id}")
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    missing_media_destination = tmp_path / "missing-media-restore"

    with pytest.raises(ValueError, match="missing referenced media"):
        runtime.data.restore_backup(source, missing_media_destination, tokens["admin"])
    assert not missing_media_destination.exists()

    complete_source = tmp_path / "complete-backup"
    runtime.data.backup(tokens["admin"], complete_source)
    audit_failure_destination = tmp_path / "audit-failure-restore"

    def fail_audit(*args, **kwargs):
        raise RuntimeError("audit unavailable")

    monkeypatch.setattr(runtime.store, "record_audit", fail_audit)
    with pytest.raises(RuntimeError, match="audit unavailable"):
        runtime.data.restore_backup(complete_source, audit_failure_destination, tokens["admin"])
    assert not audit_failure_destination.exists()
    assert not list(tmp_path.glob("audit-failure-restore.staging-*"))


def test_retention_rechecks_newly_active_response_inside_write_transaction(
    portal_runtime, monkeypatch
):
    from contextlib import contextmanager

    runtime, tokens = portal_runtime
    response = submit_completed(runtime, tokens["a"])
    old_date = (datetime.now(UTC) - timedelta(days=200)).isoformat()
    runtime.store.connection.execute(
        "UPDATE responses SET created_at=? WHERE response_id=?", (old_date, response.response_id)
    )
    assert runtime.data.retention(tokens["admin"])["row_count"] == 1
    original_transaction = runtime.store.transaction

    @contextmanager
    def race_before_recheck():
        with original_transaction() as connection:
            connection.execute(
                "UPDATE responses SET status='RUNNING' WHERE response_id=?",
                (response.response_id,),
            )
            yield connection

    monkeypatch.setattr(runtime.store, "transaction", race_before_recheck)
    result = runtime.data.retention(tokens["admin"], apply=True)
    assert result["response_ids"] == []
    current = runtime.store.get_response(response.response_id)
    assert current is not None and current.status.value == "RUNNING"
    assert current.audio_available


def test_erasure_removes_identity_and_consent_history(portal_runtime):
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
    runtime.store.connection.execute(
        "INSERT INTO study_surveys(survey_id,enrollment_id,phase,answers_json,submitted_at) "
        "VALUES('fixture-survey','fixture-enrollment','pre','{\"q1\":4}',?)",
        (now,),
    )
    preview = runtime.data.erasure_preview(tokens["admin"], "fixture-a")
    consent_count = runtime.store.connection.execute(
        "SELECT COUNT(*) FROM consent_events WHERE account_id='fixture-a'"
    ).fetchone()[0]
    assert consent_count > 0

    runtime.data.erase(tokens["admin"], "fixture-a", "fixture-a", preview["fingerprint"])

    assert runtime.store.get_account("fixture-a") is None
    assert original
    assert (
        runtime.store.connection.execute(
            "SELECT COUNT(*) FROM consent_events WHERE account_id='fixture-a'"
        ).fetchone()[0]
        == 0
    )
    pseudonym, participant_id = runtime.store.connection.execute(
        "SELECT pseudonym,participant_id FROM study_enrollments "
        "WHERE enrollment_id='fixture-enrollment'"
    ).fetchone()
    assert pseudonym.startswith("privacy:") and pseudonym != "pseudonym-a"
    assert participant_id.startswith("erased-")
    assert (
        runtime.store.connection.execute(
            "SELECT 1 FROM study_surveys WHERE survey_id='fixture-survey'"
        ).fetchone()
        is None
    )
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


def test_erasure_removes_research_links_without_redacting_shared_resource_audit(portal_runtime):
    runtime, tokens = portal_runtime
    response = submit_completed(runtime, tokens["a"])
    now = datetime.now(UTC).isoformat()
    runtime.store.connection.execute(
        "INSERT INTO rating_batches(batch_id,state,seed,criteria_version,created_by,created_at) "
        "VALUES('privacy-batch','OPEN',1,'v1','fixture-admin',?)",
        (now,),
    )
    runtime.store.connection.execute(
        "INSERT INTO rating_assignments VALUES('privacy-assignment','privacy-batch',?,"
        "'blind-token',1,'rater-hash','SUBMITTED',?)",
        (response.response_id, now),
    )
    runtime.store.connection.execute(
        "INSERT INTO research_ratings VALUES('privacy-rating','privacy-assignment','{}',"
        "4.0,NULL,'private rationale',?)",
        (now,),
    )
    with pytest.raises(sqlite3.IntegrityError, match="authorized privacy erasure"):
        runtime.store.connection.execute(
            "DELETE FROM research_ratings WHERE rating_id='privacy-rating'"
        )
    runtime.store.connection.execute(
        "INSERT INTO audit VALUES('shared-resource-audit','fixture-teacher','viewed',?,?,NULL)",
        (response.task_id, now),
    )
    runtime.store.connection.execute(
        "INSERT INTO audit VALUES('owned-response-audit','fixture-a','submitted',?,?,"
        "'private detail')",
        (response.response_id, now),
    )

    preview = runtime.data.erasure_preview(tokens["admin"], "fixture-a")
    runtime.data.erase(tokens["admin"], "fixture-a", "fixture-a", preview["fingerprint"])

    assert (
        runtime.store.connection.execute(
            "SELECT 1 FROM research_ratings WHERE rating_id='privacy-rating'"
        ).fetchone()
        is None
    )
    shared = runtime.store.connection.execute(
        "SELECT actor_id,object_id,reason FROM audit WHERE event_id='shared-resource-audit'"
    ).fetchone()
    assert shared == ("fixture-teacher", response.task_id, None)
    erased = runtime.store.connection.execute(
        "SELECT actor_id,object_id,reason FROM audit WHERE event_id='owned-response-audit'"
    ).fetchone()
    assert erased[0].startswith("privacy:") and erased[1].startswith("privacy:")
    assert erased[2] is None
    erasure_event = runtime.store.connection.execute(
        "SELECT actor_id,object_id,reason FROM audit WHERE action='participant_erased'"
    ).fetchone()
    assert erasure_event == ("fixture-admin", erasure_event[1], None)
    assert erasure_event[1].startswith("privacy:")
    assert "fixture-a" not in erasure_event[1]


def test_erasure_failure_rolls_back_rows_and_privacy_intent(portal_runtime, monkeypatch):
    runtime, tokens = portal_runtime
    preview = runtime.data.erasure_preview(tokens["admin"], "fixture-a")
    before = {
        table: runtime.store.connection.execute(
            f"SELECT COUNT(*) FROM {table} WHERE "
            + ("actor_id='fixture-a'" if table == "sessions" else "account_id='fixture-a'")
        ).fetchone()[0]
        for table in ("sessions", "account_profiles", "consent_events")
    }

    def fail(*args, **kwargs):
        raise sqlite3.OperationalError("fixture audit failure")

    monkeypatch.setattr(runtime.portal, "audit", fail)
    with pytest.raises(sqlite3.OperationalError, match="fixture audit failure"):
        runtime.data.erase(tokens["admin"], "fixture-a", "fixture-a", preview["fingerprint"])

    assert runtime.store.get_account("fixture-a") is not None
    assert {
        table: runtime.store.connection.execute(
            f"SELECT COUNT(*) FROM {table} WHERE "
            + ("actor_id='fixture-a'" if table == "sessions" else "account_id='fixture-a'")
        ).fetchone()[0]
        for table in before
    } == before
    assert (
        runtime.store.connection.execute(
            "SELECT COUNT(*) FROM cleanup_intents WHERE resource_kind='privacy_erasure'"
        ).fetchone()[0]
        == 0
    )


def test_audit_privacy_exception_allows_only_exact_owned_redaction(portal_runtime):
    runtime, _ = portal_runtime
    now = datetime.now(UTC).isoformat()
    stamp = datetime.now(UTC).timestamp()
    runtime.store.connection.execute(
        "INSERT INTO audit VALUES('audit-target','fixture-a','submitted','response-x',?,'private')",
        (now,),
    )
    runtime.store.connection.execute(
        "INSERT INTO audit VALUES('audit-shared','fixture-teacher','viewed',"
        "'lesson-shared',?,NULL)",
        (now,),
    )
    runtime.store.connection.execute(
        "INSERT INTO cleanup_intents(intent_id,owner_id,resource_kind,resource_id,state,attempt,"
        "available_at,created_at,updated_at,last_reason) VALUES(?,?,?,?,?,?,?,?,?,NULL)",
        (
            "audit-intent",
            "fixture-a",
            "privacy_erasure",
            "privacy-audit",
            "running",
            0,
            stamp,
            stamp,
            stamp,
        ),
    )
    with pytest.raises(sqlite3.IntegrityError, match="exact privacy redaction"):
        runtime.store.connection.execute(
            "UPDATE audit SET action='changed' WHERE event_id='audit-target'"
        )
    with pytest.raises(sqlite3.IntegrityError, match="exact privacy redaction"):
        runtime.store.connection.execute(
            "UPDATE audit SET actor_id='privacy:audit-intent' WHERE event_id='audit-shared'"
        )
    with pytest.raises(sqlite3.IntegrityError, match="exact privacy redaction"):
        runtime.store.connection.execute(
            "UPDATE audit SET recorded_at='changed' WHERE event_id='audit-target'"
        )
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        runtime.store.connection.execute("DELETE FROM audit WHERE event_id='audit-target'")
    runtime.store.connection.execute(
        "UPDATE audit SET actor_id='privacy:audit-intent',reason=NULL WHERE event_id='audit-target'"
    )
    assert runtime.store.connection.execute(
        "SELECT actor_id,action,object_id,reason FROM audit WHERE event_id='audit-target'"
    ).fetchone() == ("privacy:audit-intent", "submitted", "response-x", None)


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
    pipeline = runtime.app._student_api._service._pipeline
    assert pipeline._trust_evaluator.ready
    activated = runtime.control.activate_model(tokens["admin"], "ridge_resp_v2", 0)
    assert activated["revision"] == 1
    assert pipeline._trust_evaluator.ready is False
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
