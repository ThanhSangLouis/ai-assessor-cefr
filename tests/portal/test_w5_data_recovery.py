from __future__ import annotations

import os
import time
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from tests.portal.conftest import submit_completed


def _publishable_media_reference(runtime, blob):
    now = datetime.now(UTC).isoformat()
    runtime.store.connection.execute(
        "INSERT INTO learning_paths(path_id,title,state,created_at,updated_at) "
        "VALUES('recovery-path','Recovery','published',?,?)",
        (now, now),
    )
    runtime.store.connection.execute(
        "INSERT INTO learning_units(unit_id,path_id,title,ordinal) "
        "VALUES('recovery-unit','recovery-path','Recovery unit',1)"
    )
    runtime.store.connection.execute(
        "INSERT INTO learning_lessons(lesson_id,unit_id,title,active_version,created_at) "
        "VALUES('recovery-lesson','recovery-unit','Recovery lesson',NULL,?)",
        (now,),
    )
    runtime.store.connection.execute(
        "INSERT INTO lesson_versions(lesson_id,version,state,rules_version,published_at,"
        "created_at) "
        "VALUES('recovery-lesson',1,'published','rules-v1',?,?)",
        (now, now),
    )
    runtime.store.connection.execute(
        "UPDATE learning_lessons SET active_version=1 WHERE lesson_id='recovery-lesson'"
    )
    runtime.store.connection.execute(
        "INSERT INTO learning_media(media_id,lesson_id,media_kind,blob_id,sha256,size_bytes,"
        "created_at) "
        "VALUES('recovery-media','recovery-lesson','audio',?,?,?,?)",
        (blob.blob_id, blob.sha256, blob.size_bytes, now),
    )


def test_unlink_failure_keeps_durable_intent_until_retry_succeeds(portal_runtime, monkeypatch):
    runtime, _ = portal_runtime
    blob = runtime.responses.blobs.store(b"retain until unlink retry")
    runtime.data._queue_blob(SimpleNamespace(blob=blob))
    real_path = runtime.data.blobs._path

    class TransientUnlinkFailure:
        def unlink(self, *, missing_ok=False):
            raise OSError("temporary filesystem failure")

    monkeypatch.setattr(runtime.data.blobs, "_path", lambda _blob_id: TransientUnlinkFailure())
    assert runtime.data.cleanup_pending() == {"removed": 0, "pending": 1}
    intent = runtime.store.connection.execute(
        "SELECT state,attempt,last_reason FROM cleanup_intents "
        "WHERE resource_kind='blob' AND resource_id=?",
        (blob.blob_id,),
    ).fetchone()
    assert intent == ("pending", 1, "OSError")
    assert runtime.store.connection.execute(
        "SELECT 1 FROM blob_deletions WHERE blob_id=?", (blob.blob_id,)
    ).fetchone() == (1,)
    assert real_path(blob.blob_id).read_bytes() == b"retain until unlink retry"

    monkeypatch.setattr(runtime.data.blobs, "_path", real_path)
    runtime.store.connection.execute(
        "UPDATE cleanup_intents SET available_at=0 WHERE resource_kind='blob' AND resource_id=?",
        (blob.blob_id,),
    )
    assert runtime.data.cleanup_pending() == {"removed": 1, "pending": 0}
    assert not real_path(blob.blob_id).exists()
    assert (
        runtime.store.connection.execute(
            "SELECT 1 FROM cleanup_intents WHERE resource_kind='blob' AND resource_id=?",
            (blob.blob_id,),
        ).fetchone()
        is None
    )


def test_cleanup_intent_preserves_blob_still_referenced_by_shared_lesson_media(portal_runtime):
    runtime, _ = portal_runtime
    blob = runtime.responses.blobs.store(b"shared lesson audio")
    _publishable_media_reference(runtime, blob)
    runtime.data._queue_blob(SimpleNamespace(blob=blob))

    assert runtime.data.cleanup_pending() == {"removed": 0, "pending": 0}
    assert runtime.data.blobs._path(blob.blob_id).read_bytes() == b"shared lesson audio"
    assert runtime.store.connection.execute(
        "SELECT state FROM cleanup_intents WHERE resource_kind='blob' AND resource_id=?",
        (blob.blob_id,),
    ).fetchone() == ("complete",)
    assert (
        runtime.store.connection.execute(
            "SELECT 1 FROM blob_deletions WHERE blob_id=?", (blob.blob_id,)
        ).fetchone()
        is None
    )


def test_retention_prunes_old_completed_attempts_and_jobs_but_keeps_active_work(portal_runtime):
    runtime, tokens = portal_runtime
    response = submit_completed(runtime, tokens["a"])
    old = (datetime.now(UTC) - timedelta(days=200)).isoformat()
    runtime.store.connection.execute(
        "UPDATE responses SET created_at=? WHERE response_id=?", (old, response.response_id)
    )
    runtime.store.connection.execute(
        "DELETE FROM durable_jobs WHERE response_id=?", (response.response_id,)
    )
    runtime.store.connection.execute(
        "INSERT INTO durable_jobs(job_id,response_id,kind,state,attempt,max_attempts,"
        "idempotency_key,created_at,updated_at,available_at) "
        "VALUES('old-failed-job',?,'assessment','failed',1,3,'old-failed-job-key',0,0,0)",
        (response.response_id,),
    )
    runtime.store.connection.execute(
        "INSERT INTO practice_attempts(attempt_id,owner_id,mission_id,prompt_version,status,"
        "created_at,updated_at,idempotency_key) "
        "VALUES('old-practice','fixture-a','mission-v1','prompt-v1','completed',?,?,"
        "'retention-old-practice')",
        (old, old),
    )
    runtime.store.connection.execute(
        "INSERT INTO practice_attempts(attempt_id,owner_id,mission_id,prompt_version,status,"
        "created_at,updated_at,idempotency_key) "
        "VALUES('active-practice','fixture-a','mission-v1','prompt-v1','in_progress',?,?,"
        "'retention-active-practice')",
        (old, old),
    )
    runtime.store.connection.execute(
        "INSERT INTO review_items(review_id,owner_id,source_attempt,content_key,box,due_at,state,"
        "updated_at) VALUES('old-review','fixture-a','old-practice','word-1',0,?,'due',?)",
        (old, old),
    )
    runtime.store.connection.execute(
        "INSERT INTO learning_paths(path_id,title,state,created_at,updated_at) "
        "VALUES('retention-path','Retention','published',?,?)",
        (old, old),
    )
    runtime.store.connection.execute(
        "INSERT INTO learning_units(unit_id,path_id,title,ordinal) "
        "VALUES('retention-unit','retention-path','Retention unit',1)"
    )
    runtime.store.connection.execute(
        "INSERT INTO learning_lessons(lesson_id,unit_id,title,active_version,created_at) "
        "VALUES('retention-lesson','retention-unit','Retention lesson',NULL,?)",
        (old,),
    )
    runtime.store.connection.execute(
        "INSERT INTO lesson_versions(lesson_id,version,state,rules_version,published_at,"
        "created_at) "
        "VALUES('retention-lesson',1,'draft','rules-v1',NULL,?)",
        (old,),
    )
    runtime.store.connection.execute(
        "INSERT INTO lesson_steps(lesson_id,version,step_id,kind,ordinal,payload) "
        "VALUES('retention-lesson',1,'step-1','practice',1,'{}')"
    )
    runtime.store.connection.executemany(
        "INSERT INTO step_attempts(attempt_id,owner_id,lesson_id,lesson_version,step_id,"
        "rules_version,status,created_at,idempotency_key) VALUES(?,?,?,?,?,?,?,?,?)",
        [
            (
                "old-step",
                "fixture-a",
                "retention-lesson",
                1,
                "step-1",
                "rules-v1",
                "completed",
                old,
                "retention-old-step",
            ),
            (
                "active-step",
                "fixture-a",
                "retention-lesson",
                1,
                "step-1",
                "rules-v1",
                "active",
                old,
                "retention-active-step",
            ),
        ],
    )
    stamp = time.time() - 200 * 86400
    runtime.store.connection.executemany(
        "INSERT INTO cleanup_intents(intent_id,resource_kind,resource_id,state,attempt,"
        "available_at,created_at,updated_at) VALUES(?, 'blob', ?, ?, 0, ?, ?, ?)",
        [
            ("old-complete-intent", "old-complete-blob", "complete", stamp, stamp, stamp),
            (
                "failed-intent-protected",
                "failed-blob-preserved",
                "failed",
                time.time() + 86400,
                stamp,
                stamp,
            ),
        ],
    )

    preview = runtime.data.retention(tokens["admin"], days=180)
    assert preview["dry_run"] is True
    assert preview["response_ids"] == [response.response_id]
    assert preview["attempt_ids"] == {
        "practice_attempts": ["old-practice"],
        "step_attempts": ["old-step"],
    }
    assert preview["obsolete_job_ids"]
    assert preview["completed_cleanup_ids"] == ["old-complete-intent"]
    assert runtime.store.connection.execute(
        "SELECT 1 FROM practice_attempts WHERE attempt_id='old-practice'"
    ).fetchone()

    applied = runtime.data.retention(tokens["admin"], days=180, apply=True)
    assert applied["row_count"] == preview["row_count"]
    for table, attempt_id in (
        ("practice_attempts", "old-practice"),
        ("step_attempts", "old-step"),
    ):
        assert (
            runtime.store.connection.execute(
                f"SELECT 1 FROM {table} WHERE attempt_id=?", (attempt_id,)
            ).fetchone()
            is None
        )
    for table, attempt_id in (
        ("practice_attempts", "active-practice"),
        ("step_attempts", "active-step"),
    ):
        assert runtime.store.connection.execute(
            f"SELECT 1 FROM {table} WHERE attempt_id=?", (attempt_id,)
        ).fetchone()
    assert (
        runtime.store.connection.execute(
            "SELECT 1 FROM review_items WHERE review_id='old-review'"
        ).fetchone()
        is None
    )
    assert (
        runtime.store.connection.execute(
            "SELECT 1 FROM durable_jobs WHERE response_id=?", (response.response_id,)
        ).fetchone()
        is None
    )
    assert (
        runtime.store.connection.execute(
            "SELECT 1 FROM cleanup_intents WHERE intent_id='old-complete-intent'"
        ).fetchone()
        is None
    )
    assert runtime.store.connection.execute(
        "SELECT state FROM cleanup_intents WHERE intent_id='failed-intent-protected'"
    ).fetchone() == ("failed",)


def test_orphan_apply_removes_old_unreferenced_blob_but_dry_run_is_read_only(portal_runtime):
    runtime, tokens = portal_runtime
    orphan = runtime.responses.blobs.store(b"unreferenced orphan")
    path = runtime.data.blobs._path(orphan.blob_id)
    old_time = time.time() - 7200
    os.utime(path, (old_time, old_time))

    preview = runtime.data.orphans(tokens["admin"])
    assert preview["dry_run"] is True
    assert preview["blob_ids"] == [orphan.blob_id]
    assert path.is_file()

    applied = runtime.data.orphans(tokens["admin"], apply=True)
    assert applied["dry_run"] is False
    assert applied["blob_ids"] == [orphan.blob_id]
    assert not path.exists()


@pytest.mark.parametrize("days", [0, 36501])
def test_retention_rejects_out_of_range_days(portal_runtime, days):
    runtime, tokens = portal_runtime
    with pytest.raises(ValueError, match="retention days"):
        runtime.data.retention(tokens["admin"], days=days)
