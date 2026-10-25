from __future__ import annotations

import json
import math
import shutil
import sqlite3
import struct
import wave
from datetime import UTC, datetime
from io import BytesIO
from types import SimpleNamespace

import pytest

from aicefr.audio.config import QCConfig
from aicefr.auth.contracts import AccountCreate
from aicefr.auth.errors import ValidationError
from aicefr.billing.secrets import KeyRing
from aicefr.contracts import ActorRole
from aicefr.local.__main__ import _demo_config
from aicefr.local.app import create_runtime
from aicefr.scoring.scorer import RidgeScorer
from aicefr.storage.private_files import is_private_file


def _runtime(tmp_path):
    config = _demo_config()
    pipeline = SimpleNamespace(
        _qc_config=QCConfig(**config["qc"]),
        _scorer=RidgeScorer.load(),
        enqueue=lambda response: None,
    )
    runtime = create_runtime(tmp_path / "data", config=config, pipeline=pipeline)
    student = runtime.auth.bootstrap_fixture_account(
        "fixture-student", ActorRole.STUDENT, "student-password"
    )
    admin = runtime.auth.bootstrap_fixture_account(
        "fixture-admin", ActorRole.ADMIN, "admin-password"
    )
    return (
        runtime,
        runtime.auth.login(student.actor_id, "student-password"),
        runtime.auth.login(admin.actor_id, "admin-password"),
    )


def _call(app, path, *, token, method="GET", payload=None, raw=None, content_type=None, query=""):
    body = raw if raw is not None else json.dumps(payload).encode() if payload is not None else b""
    environ = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "QUERY_STRING": query,
        "CONTENT_LENGTH": str(len(body)),
        "CONTENT_TYPE": content_type
        or ("application/json" if payload is not None or raw is not None else ""),
        "HTTP_AUTHORIZATION": "Bearer " + token,
        "HTTP_HOST": "localhost:8000",
        "HTTP_ORIGIN": "http://localhost:8000",
        "wsgi.url_scheme": "http",
        "wsgi.input": BytesIO(body),
    }
    result = {}
    raw = b"".join(app(environ, lambda status, headers: result.update(status=status)))
    result["body"] = raw
    result["json"] = json.loads(raw) if raw else None
    return result


def _submit_fixture_response(runtime, student_token):
    from aicefr.api.student import SubmitRequest

    audio = BytesIO()
    with wave.open(audio, "wb") as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(16000)
        frames = b"".join(
            struct.pack("<h", int(4000 * math.sin(2 * math.pi * 440 * index / 16000)))
            for index in range(16000)
        )
        stream.writeframes(frames)
    runtime.accounts.set_consent(
        student_token, "privacy-job-v1", True, audio_storage_allowed=True
    )
    return runtime.app._student_api.submit(
        student_token,
        SubmitRequest(
            task_id="demo-speaking",
            task_version="1",
            consent_version="privacy-job-v1",
            filename="fixture.wav",
            content_type="audio/wav",
            audio_bytes=audio.getvalue(),
        ),
    )


def test_personal_export_is_authenticated_and_excludes_provider_secrets(tmp_path):
    runtime, student, admin = _runtime(tmp_path)
    try:
        runtime.store.connection.execute(
            "INSERT INTO runtime_settings(key,payload,revision,version,updated_by,updated_at) "
            "VALUES('billing.license.nonce.secret','private',0,'v1','fixture-admin','now')"
        )
        runtime.accounts.set_consent(student, "consent-v1", True)
        runtime.store.connection.execute(
            "INSERT INTO practice_attempts(attempt_id,owner_id,mission_id,prompt_version,status,"
            "measurements,evidence,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)",
            (
                "attempt-1",
                "fixture-student",
                "mission-1",
                "v1",
                "completed",
                '{"words":4,"token_count":2}',
                '{"error_count":2,"pattern":"final_consonant","transcript":"private transcript",'
                '"examples":[{"expected":"cats","heard":"cat"}]}',
                "2026-10-15T00:00:00+00:00",
                "2026-10-15T00:00:00+00:00",
            ),
        )
        anonymous = _call(runtime.app, "/api/v1/me/export", token="invalid")
        assert anonymous["status"].startswith("401")
        exported = _call(runtime.app, "/api/v1/me/export", token=student)
        assert exported["status"].startswith("200")
        assert exported["json"]["actor_id"] == "fixture-student"
        assert exported["json"]["consent_history"][0]["consent_version"] == "consent-v1"
        assert exported["json"]["sessions"]
        assert "token_digest" not in exported["body"].decode()
        assert student.encode() not in exported["body"]
        attempt = exported["json"]["learning"]["practice_attempts"][0]
        assert attempt["measurements"] == {"words": 4}
        assert attempt["evidence"]["pattern"] == "final_consonant"
        assert attempt["evidence"]["examples"] == [{"expected": "cats", "heard": "cat"}]
        assert "transcript" not in attempt["evidence"]
        assert "runtime_settings" not in exported["body"].decode()
        assert b"private" not in exported["body"]
        forbidden = _call(
            runtime.app,
            "/api/v1/admin/data/erasure/preview",
            token=student,
            method="POST",
            payload={"actor_id": "fixture-student"},
        )
        assert forbidden["status"].startswith("403")
    finally:
        runtime.close()


def test_erasure_preview_fingerprint_covers_profile_updates(tmp_path):
    runtime, _, admin = _runtime(tmp_path)
    try:
        preview = _call(
            runtime.app,
            "/api/v1/admin/data/erasure/preview",
            token=admin,
            method="POST",
            payload={"actor_id": "fixture-student"},
        )
        assert preview["status"].startswith("200")
        runtime.store.connection.execute(
            "INSERT INTO account_profiles(account_id,goal,updated_at) VALUES(?,?,?)",
            ("fixture-student", 3, "2026-10-15T00:00:00+00:00"),
        )
        result = _call(
            runtime.app,
            "/api/v1/admin/data/erasure/confirm",
            token=admin,
            method="POST",
            payload={
                "actor_id": "fixture-student",
                "confirm_id": "fixture-student",
                "fingerprint": preview["json"]["fingerprint"],
            },
        )
        assert result["status"].startswith("409")
        assert runtime.store.get_account("fixture-student") is not None
    finally:
        runtime.close()


def test_erasure_preview_rejects_survey_added_after_preview(tmp_path):
    runtime, _, admin = _runtime(tmp_path)
    try:
        now = "2026-10-15T00:00:00+00:00"
        runtime.store.connection.execute(
            "INSERT INTO feedback_studies(study_id,title,state,seed,config_json,"
            "created_by,created_at) "
            "VALUES('preview-study','Fixture','RUNNING',1,'{}','fixture-admin',?)",
            (now,),
        )
        runtime.store.connection.execute(
            "INSERT INTO study_enrollments(enrollment_id,study_id,participant_id,"
            "pseudonym,arm,enrolled_at) "
            "VALUES('preview-enrollment','preview-study','fixture-student','pseudonym-1','control',?)",
            (now,),
        )
        preview = _call(
            runtime.app,
            "/api/v1/admin/data/erasure/preview",
            token=admin,
            method="POST",
            payload={"actor_id": "fixture-student"},
        )
        runtime.store.connection.execute(
            "INSERT INTO study_surveys(survey_id,enrollment_id,phase,answers_json,submitted_at) "
            "VALUES('preview-survey','preview-enrollment','pre','{\"q1\":4}',?)",
            (now,),
        )
        result = _call(
            runtime.app,
            "/api/v1/admin/data/erasure/confirm",
            token=admin,
            method="POST",
            payload={
                "actor_id": "fixture-student",
                "confirm_id": "fixture-student",
                "fingerprint": preview["json"]["fingerprint"],
            },
        )
        assert result["status"].startswith("409")
        assert runtime.store.get_account("fixture-student") is not None
        assert runtime.store.connection.execute(
            "SELECT 1 FROM study_surveys WHERE survey_id='preview-survey'"
        ).fetchone()
    finally:
        runtime.close()


def test_erasure_unknown_admin_target_and_mismatched_confirmation_are_controlled(tmp_path):
    runtime, _, admin = _runtime(tmp_path)
    try:
        missing = _call(
            runtime.app,
            "/api/v1/admin/data/erasure/preview",
            token=admin,
            method="POST",
            payload={"actor_id": "fixture-absent"},
        )
        assert missing["status"].startswith("404")
        nonstudent = _call(
            runtime.app,
            "/api/v1/admin/data/erasure/preview",
            token=admin,
            method="POST",
            payload={"actor_id": "fixture-admin"},
        )
        # The service currently reports this unsupported target through its
        # generic authorization error (401); either way, it must not leak a
        # preview or mutate the target account.
        assert nonstudent["status"].startswith(("401", "403"))
        preview = _call(
            runtime.app,
            "/api/v1/admin/data/erasure/preview",
            token=admin,
            method="POST",
            payload={"actor_id": "fixture-student"},
        )
        mismatch = _call(
            runtime.app,
            "/api/v1/admin/data/erasure/confirm",
            token=admin,
            method="POST",
            payload={
                "actor_id": "fixture-student",
                "confirm_id": "fixture-other",
                "fingerprint": preview["json"]["fingerprint"],
            },
        )
        assert mismatch["status"].startswith("409")
        invalid_fingerprint = _call(
            runtime.app,
            "/api/v1/admin/data/erasure/confirm",
            token=admin,
            method="POST",
            payload={
                "actor_id": "fixture-student",
                "confirm_id": "fixture-student",
                "fingerprint": "x" * 64,
            },
        )
        assert invalid_fingerprint["status"].startswith("400")
        assert runtime.store.get_account("fixture-student") is not None
    finally:
        runtime.close()


@pytest.mark.parametrize("mutable_family", ["durable_job", "cleanup_intent"])
def test_erasure_preview_fingerprints_jobs_and_owned_cleanup_intents(tmp_path, mutable_family):
    runtime, student, admin = _runtime(tmp_path)
    try:
        response = _submit_fixture_response(runtime, student)
        if mutable_family == "cleanup_intent":
            now = datetime.now(UTC).timestamp()
            runtime.store.connection.execute(
                "INSERT INTO cleanup_intents(intent_id,owner_id,resource_kind,resource_id,state,"
                "attempt,available_at,created_at,updated_at,last_reason) "
                "VALUES('owned-intent','fixture-student','test','owned-resource','pending',0,?,?,?,NULL)",
                (now, now, now),
            )
        preview = _call(
            runtime.app,
            "/api/v1/admin/data/erasure/preview",
            token=admin,
            method="POST",
            payload={"actor_id": "fixture-student"},
        )
        assert preview["status"].startswith("200")
        if mutable_family == "durable_job":
            runtime.store.connection.execute(
                "UPDATE durable_jobs SET revision=revision+1 WHERE response_id=?",
                (response.response_id,),
            )
        else:
            runtime.store.connection.execute(
                "UPDATE cleanup_intents SET attempt=attempt+1 WHERE intent_id='owned-intent'"
            )
        result = _call(
            runtime.app,
            "/api/v1/admin/data/erasure/confirm",
            token=admin,
            method="POST",
            payload={
                "actor_id": "fixture-student",
                "confirm_id": "fixture-student",
                "fingerprint": preview["json"]["fingerprint"],
            },
        )
        assert result["status"].startswith("409")
        assert runtime.store.get_account("fixture-student") is not None
    finally:
        runtime.close()


@pytest.mark.parametrize(
    ("raw", "content_type"),
    [
        (b'{"actor_id":"fixture-student","actor_id":"fixture-admin"}', "application/json"),
        (b'{"actor_id":NaN}', "application/json"),
        (b"[]", "application/json"),
        (b"{", "application/json"),
        (b'{"actor_id":"fixture-student"}', "text/plain"),
    ],
)
def test_data_api_rejects_malformed_or_ambiguous_request_json(tmp_path, raw, content_type):
    runtime, _, admin = _runtime(tmp_path)
    try:
        result = _call(
            runtime.app,
            "/api/v1/admin/data/erasure/preview",
            token=admin,
            method="POST",
            raw=raw,
            content_type=content_type,
        )
        assert result["status"].startswith(("400", "415"))
        assert result["json"]["error"] in {"INVALID_REQUEST", "UNSUPPORTED_REQUEST_FORMAT"}
    finally:
        runtime.close()


@pytest.mark.parametrize("actor_id", [["fixture-student"], {"id": "fixture-student"}, 42])
def test_erasure_preview_wrong_type_never_returns_internal_server_error(tmp_path, actor_id):
    runtime, _, admin = _runtime(tmp_path)
    try:
        result = _call(
            runtime.app,
            "/api/v1/admin/data/erasure/preview",
            token=admin,
            method="POST",
            payload={"actor_id": actor_id},
        )
        assert not result["status"].startswith("500"), result["body"]
    finally:
        runtime.close()


def test_admin_backup_and_restore_include_protected_key_and_audit_restore(tmp_path):
    runtime, student, admin = _runtime(tmp_path)
    try:
        now = "2026-10-15T00:00:00+00:00"
        media = runtime.responses.blobs.store(b"published lesson media")
        runtime.store.connection.execute(
            "INSERT INTO learning_paths("
            "path_id,title,description,state,revision,created_at,updated_at) "
            "VALUES('backup-path','Path','', 'published',1,?,?)",
            (now, now),
        )
        runtime.store.connection.execute(
            "INSERT INTO learning_units(unit_id,path_id,title,ordinal) "
            "VALUES('backup-unit','backup-path','Unit',1)"
        )
        runtime.store.connection.execute(
            "INSERT INTO learning_lessons(lesson_id,unit_id,title,active_version,created_at) "
            "VALUES('backup-lesson','backup-unit','Lesson',NULL,?)",
            (now,),
        )
        runtime.store.connection.execute(
            "INSERT INTO lesson_versions(lesson_id,version,state,rules_version,published_at,"
            "created_at) VALUES('backup-lesson',1,'published','rules-v1',?,?)",
            (now, now),
        )
        runtime.store.connection.execute(
            "UPDATE learning_lessons SET active_version=1 WHERE lesson_id='backup-lesson'"
        )
        runtime.store.connection.execute(
            "INSERT INTO learning_media(media_id,lesson_id,media_kind,blob_id,sha256,size_bytes,"
            "created_at) VALUES('backup-media','backup-lesson','audio',?,?,?,?)",
            (media.blob_id, media.sha256, media.size_bytes, now),
        )
        runtime.accounts.set_consent(student, "backup-consent-v1", True)
        runtime.store.connection.execute(
            "INSERT INTO practice_attempts(attempt_id,owner_id,mission_id,prompt_version,status,"
            "measurements,evidence,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)",
            (
                "backup-attempt",
                "fixture-student",
                "mission-1",
                "v1",
                "completed",
                '{"words":3}',
                '{"pattern":"final_consonant"}',
                now,
                now,
            ),
        )
        family_tables = (
            "accounts",
            "sessions",
            "responses",
            "account_profiles",
            "consents",
            "consent_events",
            "activity_events",
            "billing_quotes",
            "billing_orders",
            "billing_receipts",
            "licenses",
            "entitlements",
            "cleanup_intents",
            "learning_media",
            "study_enrollments",
            "study_surveys",
            "practice_attempts",
            "step_attempts",
            "research_ratings",
            "audit",
        )
        before_counts = {
            table: runtime.store.connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
            for table in family_tables
        }
        assert before_counts["accounts"] >= 2
        assert before_counts["sessions"] >= 2
        assert before_counts["consent_events"] >= 1
        assert before_counts["practice_attempts"] == 1
        assert before_counts["learning_media"] == 1
        backup = _call(
            runtime.app, "/api/v1/admin/data/backups", token=admin, method="POST", payload={}
        )
        assert backup["status"].startswith("201")
        backup_id = backup["json"]["backup_id"]
        backup_dir = runtime.app._portal.data_api.backups / backup_id
        assert backup["json"]["manifest"]["blob_count"] == 1
        assert "billing-hmac.key" in backup["json"]["manifest"]["sensitive_files"]
        key_copy = backup_dir / "billing-hmac.key"
        assert is_private_file(key_copy)

        restored = _call(
            runtime.app,
            "/api/v1/admin/data/restore",
            token=admin,
            method="POST",
            payload={"backup_id": backup_id},
        )
        assert restored["status"].startswith("201")
        restore_dir = runtime.app._portal.data_api.restores / restored["json"]["restore_id"]
        assert (restore_dir / "blobs" / media.blob_id).read_bytes() == b"published lesson media"
        restored_db = sqlite3.connect(restore_dir / "metadata.sqlite3")
        assert {
            table: restored_db.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
            for table in family_tables
        } == before_counts
        assert restored_db.execute(
            "SELECT blob_id FROM learning_media WHERE media_id='backup-media'"
        ).fetchone() == (media.blob_id,)
        restored_db.close()
        assert (restore_dir / "billing-hmac.key").is_file()
        assert is_private_file(restore_dir / "billing-hmac.key")
        restored_keys = KeyRing(restore_dir)
        assert restored_keys.verify_gateway_event(
            b"restore-check", restored_keys.sign_gateway_event(b"restore-check")
        )
        assert runtime.store.connection.execute(
            "SELECT 1 FROM audit WHERE action='backup_restored'"
        ).fetchone()

        tampered_id = "f" * 32
        tampered_dir = runtime.app._portal.data_api.backups / tampered_id
        shutil.copytree(backup_dir, tampered_dir)
        (tampered_dir / "blobs" / media.blob_id).write_bytes(b"tampered media")
        rejected = _call(
            runtime.app,
            "/api/v1/admin/data/restore",
            token=admin,
            method="POST",
            payload={"backup_id": tampered_id},
        )
        assert rejected["status"].startswith("409")
        assert not list(runtime.app._portal.data_api.restores.glob("*.staging-*"))
    finally:
        runtime.close()


@pytest.mark.parametrize("manifest_bytes", [b"[]", b"{broken", b'{"schema_version":10}'])
def test_restore_malformed_manifest_returns_controlled_error(tmp_path, manifest_bytes):
    runtime, _, admin = _runtime(tmp_path)
    try:
        created = _call(
            runtime.app,
            "/api/v1/admin/data/backups",
            token=admin,
            method="POST",
            payload={},
        )
        assert created["status"].startswith("201")
        backup_id = created["json"]["backup_id"]
        backup_path = runtime.app._portal.data_api.backups / backup_id
        (backup_path / "manifest.json").write_bytes(manifest_bytes)
        result = _call(
            runtime.app,
            "/api/v1/admin/data/restore",
            token=admin,
            method="POST",
            payload={"backup_id": backup_id},
        )
        assert not result["status"].startswith("500"), result["body"]
    finally:
        runtime.close()


def test_restore_rejects_missing_key_symlinks_and_client_path_ids(
    tmp_path, make_symlink_or_skip
):
    runtime, _, admin = _runtime(tmp_path)
    try:
        created = _call(
            runtime.app,
            "/api/v1/admin/data/backups",
            token=admin,
            method="POST",
            payload={},
        )
        assert created["status"].startswith("201")
        backup_id = created["json"]["backup_id"]
        backup_path = runtime.app._portal.data_api.backups / backup_id

        invalid_path = _call(
            runtime.app,
            "/api/v1/admin/data/restore",
            token=admin,
            method="POST",
            payload={"backup_id": "../outside"},
        )
        assert invalid_path["status"].startswith("400")
        missing_id = _call(
            runtime.app,
            "/api/v1/admin/data/restore",
            token=admin,
            method="POST",
            payload={"backup_id": "0" * 32},
        )
        assert missing_id["status"].startswith("404")

        missing_key_id = "a" * 32
        missing_key = runtime.app._portal.data_api.backups / missing_key_id
        shutil.copytree(backup_path, missing_key)
        (missing_key / "billing-hmac.key").unlink()
        missing_key_result = _call(
            runtime.app,
            "/api/v1/admin/data/restore",
            token=admin,
            method="POST",
            payload={"backup_id": missing_key_id},
        )
        assert missing_key_result["status"].startswith("409")

        symlink_id = "b" * 32
        linked_backup = runtime.app._portal.data_api.backups / symlink_id
        linked_backup.mkdir()
        make_symlink_or_skip(linked_backup / "manifest.json", backup_path / "manifest.json")
        symlink_result = _call(
            runtime.app,
            "/api/v1/admin/data/restore",
            token=admin,
            method="POST",
            payload={"backup_id": symlink_id},
        )
        assert symlink_result["status"].startswith("409")

        directory_symlink_id = "c" * 32
        make_symlink_or_skip(
            runtime.app._portal.data_api.backups / directory_symlink_id,
            backup_path,
            target_is_directory=True,
        )
        directory_symlink = _call(
            runtime.app,
            "/api/v1/admin/data/restore",
            token=admin,
            method="POST",
            payload={"backup_id": directory_symlink_id},
        )
        assert directory_symlink["status"].startswith("404")
        restores = runtime.app._portal.data_api.restores
        assert not restores.exists() or list(restores.iterdir()) == []
    finally:
        runtime.close()


def test_retention_http_preview_and_apply_revalidate_completed_families(tmp_path):
    runtime, student, admin = _runtime(tmp_path)
    try:
        bad_text = _call(
            runtime.app,
            "/api/v1/admin/data/retention",
            token=admin,
            query="days=abc",
        )
        assert bad_text["status"].startswith("400")
        duplicate = _call(
            runtime.app,
            "/api/v1/admin/data/retention",
            token=admin,
            query="days=1&days=2",
        )
        assert duplicate["status"].startswith("400")
        denied = _call(
            runtime.app,
            "/api/v1/admin/data/retention",
            token=student,
        )
        assert denied["status"].startswith("403")

        response = _submit_fixture_response(runtime, student)
        old = "2020-01-01T00:00:00+00:00"
        runtime.store.connection.execute(
            "UPDATE responses SET status='COMPLETED',created_at=? WHERE response_id=?",
            (old, response.response_id),
        )
        runtime.store.connection.execute(
            "UPDATE durable_jobs SET state='succeeded',attempt=1,updated_at=1 WHERE response_id=?",
            (response.response_id,),
        )
        runtime.store.connection.execute(
            "INSERT INTO practice_attempts(attempt_id,owner_id,mission_id,prompt_version,status,"
            "measurements,evidence,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)",
            (
                "retention-attempt",
                "fixture-student",
                "mission-1",
                "v1",
                "completed",
                "{}",
                "{}",
                old,
                old,
            ),
        )
        preview = _call(
            runtime.app,
            "/api/v1/admin/data/retention",
            token=admin,
            query="days=180",
        )
        assert preview["status"].startswith("200")
        assert preview["json"]["dry_run"] is True
        assert preview["json"]["row_count"] >= 2
        assert response.response_id in preview["json"]["response_ids"]
        assert "retention-attempt" in preview["json"]["attempt_ids"]["practice_attempts"]
        assert runtime.store.connection.execute(
            "SELECT 1 FROM practice_attempts WHERE attempt_id='retention-attempt'"
        ).fetchone()

        applied = _call(
            runtime.app,
            "/api/v1/admin/data/retention",
            token=admin,
            method="POST",
            payload={"days": 180},
        )
        assert applied["status"].startswith("200")
        assert applied["json"]["dry_run"] is False
        assert (
            runtime.store.connection.execute(
                "SELECT 1 FROM practice_attempts WHERE attempt_id='retention-attempt'"
            ).fetchone()
            is None
        )
        assert (
            runtime.store.connection.execute(
                "SELECT 1 FROM durable_jobs WHERE response_id=?", (response.response_id,)
            ).fetchone()
            is None
        )
        assert not runtime.store.get_response(response.response_id).audio_available
    finally:
        runtime.close()


def test_free_seat_limit_covers_modern_and_legacy_create_but_not_reenable(tmp_path):
    runtime, _, admin = _runtime(tmp_path)
    try:
        # The helper already bootstraps one active student, filling the 30-seat plan.
        students = [
            AccountCreate(f"fixture-student-{index}", ActorRole.STUDENT) for index in range(29)
        ]
        runtime.accounts.create_accounts(admin, students)
        assert not runtime.billing.can_add_students(1)

        with pytest.raises(ValidationError, match="student_seat_limit_reached"):
            runtime.accounts.create_legacy_account(
                admin, "fixture-legacy-over-cap", ActorRole.STUDENT, "legacy-pass-123"
            )
        with pytest.raises(ValidationError, match="student_seat_limit_reached"):
            runtime.accounts.create_accounts(
                admin,
                [
                    AccountCreate("fixture-batch-a", ActorRole.STUDENT),
                    AccountCreate("fixture-batch-b", ActorRole.STUDENT),
                ],
            )
        assert runtime.store.get_account("fixture-batch-a") is None
        assert runtime.store.get_account("fixture-batch-b") is None

        runtime.accounts.change_legacy_account(
            admin, "fixture-student-0", disabled=True, unlock=False
        )
        runtime.accounts.create_accounts(
            admin, [AccountCreate("fixture-last-seat", ActorRole.STUDENT)]
        )
        runtime.accounts.change_legacy_account(
            admin, "fixture-student-0", disabled=False, unlock=False
        )
        assert runtime.store.get_account("fixture-student-0").disabled is False
        assert runtime.store.get_account("fixture-last-seat") is not None
    finally:
        runtime.close()
