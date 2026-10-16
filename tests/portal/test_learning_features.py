from __future__ import annotations

import json
from datetime import UTC, datetime

from aicefr.contracts import ActorRole, Band
from conftest import http


def add_step_attempt(
    runtime,
    owner_id: str,
    attempt_id: str,
    created_at: str,
    *,
    speaking_s: float = 60,
    words: list[dict] | None = None,
    status: str = "PASSED",
    evidence: dict | None = None,
    teacher_override: dict | None = None,
) -> None:
    evidence = {**(evidence or {})}
    if words is not None:
        evidence["words"] = words
    from aicefr.lessons.model import (
        FreePayload,
        FreeRound,
        KeywordsPayload,
        Lesson,
        LessonStage,
        LessonStep,
        LookUpPayload,
        PublishedLessonVersion,
        ReadAloudPayload,
        StepKind,
    )
    from aicefr.lessons.rules import LESSON_RULES_VERSION

    lesson = Lesson(
        lesson_id="lesson-1",
        title="Fixture lesson",
        summary="Synthetic fixture used by learning feature tests.",
        band=Band.A2,
        revision=1,
        content_version="fixture-v1",
        steps=(
            LessonStep(
                step_id="step-1",
                ordinal=1,
                stage=LessonStage.MODEL,
                kind=StepKind.READ_ALOUD,
                instruction="Read the sample aloud.",
                payload=ReadAloudPayload(
                    kind=StepKind.READ_ALOUD,
                    text="Hello world.",
                    max_seconds=30,
                ),
                rules_version=LESSON_RULES_VERSION,
            ),
            LessonStep(
                step_id="step-2",
                ordinal=2,
                stage=LessonStage.CONTROLLED,
                kind=StepKind.LOOK_UP,
                instruction="Read and repeat.",
                payload=LookUpPayload(
                    kind=StepKind.LOOK_UP, text="A short sample.", show_seconds=6, max_seconds=30
                ),
                rules_version=LESSON_RULES_VERSION,
            ),
            LessonStep(
                step_id="step-3",
                ordinal=3,
                stage=LessonStage.GUIDED,
                kind=StepKind.KEYWORDS,
                instruction="Use the keywords.",
                payload=KeywordsPayload(
                    kind=StepKind.KEYWORDS, keywords=("hello",), min_words=1, max_seconds=30
                ),
                rules_version=LESSON_RULES_VERSION,
            ),
            LessonStep(
                step_id="step-4",
                ordinal=4,
                stage=LessonStage.FREE,
                kind=StepKind.FREE,
                instruction="Speak freely.",
                payload=FreePayload(
                    kind=StepKind.FREE,
                    rounds=(
                        FreeRound(duration_seconds=30, prompt="Talk about your day."),
                        FreeRound(duration_seconds=20, prompt="Talk about your day."),
                    ),
                    max_seconds=30,
                ),
                rules_version=LESSON_RULES_VERSION,
            ),
        ),
    )
    snapshot = PublishedLessonVersion.from_lesson(
        lesson, version=1, published_at=datetime.fromisoformat(created_at)
    )
    with runtime.store.transaction() as connection:
        connection.execute(
            "INSERT OR IGNORE INTO learning_paths "
            "(path_id,title,description,state,revision,created_at,updated_at,"
            "band_from,band_to,content_version,content_hash) "
            "VALUES('path-1','Fixture path','', 'published',1,?,?, 'A2','A2','fixture-v1',?)",
            (created_at, created_at, "0" * 64),
        )
        connection.execute(
            "INSERT OR IGNORE INTO learning_units(unit_id,path_id,title,ordinal,band,revision) "
            "VALUES('unit-1','path-1','Fixture unit',1,'A2',1)"
        )
        connection.execute(
            "INSERT OR IGNORE INTO learning_lessons "
            "(lesson_id,unit_id,title,active_version,created_at,summary,band,revision,"
            "content_version,ordinal) "
            "VALUES('lesson-1','unit-1','Fixture lesson',NULL,?,?, 'A2',1,'fixture-v1',1)",
            (created_at, lesson.summary),
        )
        version_exists = connection.execute(
            "SELECT 1 FROM lesson_versions WHERE lesson_id='lesson-1' "
            "AND version=1 AND state='published'"
        ).fetchone()
        if not version_exists:
            connection.execute(
                "INSERT OR IGNORE INTO lesson_versions "
                "(lesson_id,version,state,rules_version,published_at,created_at,"
                "title,summary,band,revision,content_hash) "
                "VALUES('lesson-1',1,'draft',?,NULL,?, ?, ?, 'A2',1,NULL)",
                (snapshot.rules_version, created_at, snapshot.title, snapshot.summary),
            )
            for step in snapshot.steps:
                payload = json.dumps(
                    step.payload.model_dump(mode="json"),
                    ensure_ascii=False,
                    sort_keys=True,
                )
                connection.execute(
                    "INSERT OR IGNORE INTO lesson_steps "
                    "(lesson_id,version,step_id,kind,ordinal,payload,stage,instruction,"
                    "rules_version) "
                    "VALUES('lesson-1',1,?,?,?,?,?,?,?)",
                    (
                        step.step_id,
                        step.kind.value,
                        step.ordinal,
                        payload,
                        step.stage.value,
                        step.instruction,
                        step.rules_version,
                    ),
                )
            connection.execute(
                "UPDATE lesson_versions SET state='published',published_at=?,title=?,"
                "summary=?,band=?,revision=?,content_hash=?,rules_version=? "
                "WHERE lesson_id='lesson-1' AND version=1 AND state='draft'",
                (
                    created_at,
                    snapshot.title,
                    snapshot.summary,
                    snapshot.band.value,
                    snapshot.revision,
                    snapshot.content_hash,
                    snapshot.rules_version,
                ),
            )
        connection.execute(
            "UPDATE learning_lessons SET active_version=1 WHERE lesson_id='lesson-1'"
        )
        connection.execute(
            "INSERT INTO step_attempts "
            "(attempt_id,owner_id,lesson_id,lesson_version,step_id,rules_version,status,"
            "measurements,evidence,teacher_override,created_at,idempotency_key) "
            "VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                attempt_id,
                owner_id,
                "lesson-1",
                1,
                "step-1",
                "rules-v1",
                status,
                json.dumps({"speaking_s": speaking_s}),
                json.dumps(evidence),
                json.dumps(teacher_override) if teacher_override is not None else None,
                created_at,
                "fixture:" + attempt_id,
            ),
        )


def test_progress_uses_vietnamese_day_and_compares_the_previous_week(portal_runtime):
    runtime, tokens = portal_runtime
    add_step_attempt(runtime, "fixture-a", "a1", "2026-10-15T18:00:00+00:00", speaking_s=90)
    add_step_attempt(runtime, "fixture-a", "a2", "2026-10-08T18:00:00+00:00", speaking_s=45)
    runtime.learning.clock = lambda: datetime(2026, 10, 16, 0, 30, tzinfo=UTC)

    result = http(runtime, "/api/v1/me/learning/progress", tokens["a"])

    assert result["code"] == 200
    assert result["json"]["timezone"] == "Asia/Ho_Chi_Minh"
    assert result["json"]["today_seconds"] == 90
    assert result["json"]["week_seconds"] == 90
    assert result["json"]["previous_week_seconds"] == 45
    assert result["json"]["week_change_seconds"] == 45


def test_achievement_unlock_is_idempotent_owner_seen_and_survives_attempt_deletion(portal_runtime):
    runtime, tokens = portal_runtime
    add_step_attempt(runtime, "fixture-a", "a1", "2026-10-15T18:00:00+00:00")

    first = http(runtime, "/api/v1/me/learning/achievements", tokens["a"])
    item = next(value for value in first["json"]["items"] if value["code"] == "take_1")
    assert first["json"]["total"] == 17
    assert item["unlocked_at"]
    unlocked_at = item["unlocked_at"]
    assert item["is_new"] is True

    seen = http(
        runtime,
        "/api/v1/me/learning/achievements/seen",
        tokens["a"],
        method="POST",
        payload={"codes": ["take_1"]},
    )
    assert seen["json"] == {"seen": 1}
    assert http(runtime, "/api/v1/me/learning/achievements", tokens["b"])["json"]["unlocked"] == 0

    with runtime.store.transaction() as connection:
        connection.execute("DELETE FROM step_attempts WHERE attempt_id='a1'")
    again = http(runtime, "/api/v1/me/learning/achievements", tokens["a"])
    item = next(value for value in again["json"]["items"] if value["code"] == "take_1")
    assert item["unlocked_at"] == unlocked_at
    assert item["is_new"] is False


def test_achievement_export_and_account_erasure_cover_learning_state(portal_runtime):
    runtime, tokens = portal_runtime
    add_step_attempt(runtime, "fixture-a", "a1", "2026-10-15T18:00:00+00:00")
    http(runtime, "/api/v1/me/learning/achievements", tokens["a"])
    http(
        runtime,
        "/api/v1/me/learning/achievements/seen",
        tokens["a"],
        method="POST",
        payload={"codes": ["take_1"]},
    )

    exported = runtime.portal.export_own(tokens["a"])
    learning = exported["learning"]
    assert len(learning["achievements"]) == 1
    assert learning["achievements"][0]["code"] == "take_1"
    assert learning["achievements"][0]["seen_at"]
    assert learning["streak_days"]

    preview = runtime.data.erasure_preview(tokens["admin"], "fixture-a")
    runtime.data.erase(tokens["admin"], "fixture-a", "fixture-a", preview["fingerprint"])

    assert (
        runtime.store.connection.execute(
            "SELECT COUNT(*) FROM achievements WHERE owner_id='fixture-a'"
        ).fetchone()[0]
        == 0
    )
    assert (
        runtime.store.connection.execute(
            "SELECT COUNT(*) FROM streak_days WHERE owner_id='fixture-a'"
        ).fetchone()[0]
        == 0
    )


def test_pronunciation_profile_uses_only_lesson_words_and_caps_examples(portal_runtime):
    runtime, tokens = portal_runtime
    for index in range(7):
        add_step_attempt(
            runtime,
            "fixture-a",
            f"p{index}",
            f"2026-10-{8 + index:02d}T10:00:00+00:00",
            words=[{"text": "worked", "said": "work", "status": "missed"}],
        )

    below_threshold = http(runtime, "/api/v1/me/learning/pronunciation", tokens["a"])
    pattern = next(
        item for item in below_threshold["json"]["patterns"] if item["pattern"] == "ed_ending"
    )
    assert (pattern["opportunities"], pattern["errors"], pattern["rate"]) == (7, 7, None)

    add_step_attempt(
        runtime,
        "fixture-a",
        "p7",
        "2026-10-15T10:00:00+00:00",
        words=[{"text": "worked", "said": "work", "status": "missed"}],
    )
    result = http(runtime, "/api/v1/me/learning/pronunciation", tokens["a"])

    assert result["code"] == 200
    pattern = next(item for item in result["json"]["patterns"] if item["pattern"] == "ed_ending")
    assert (pattern["opportunities"], pattern["errors"], pattern["rate"]) == (8, 8, 1.0)
    assert len(pattern["examples"]) == 5
    assert "owner_id" not in result["json"]


def test_pronunciation_excludes_teacher_corrections_and_foreign_examples(portal_runtime):
    runtime, tokens = portal_runtime
    add_step_attempt(
        runtime,
        "fixture-a",
        "corrected",
        "2026-10-15T18:00:00+00:00",
        words=[{"text": "worked", "said": "work", "status": "missed", "teacher_corrected": True}],
    )

    own = http(
        runtime,
        "/api/v1/me/learning/pronunciation/examples/corrected",
        tokens["a"],
    )
    foreign = http(
        runtime,
        "/api/v1/me/learning/pronunciation/examples/corrected",
        tokens["b"],
    )
    result = http(runtime, "/api/v1/me/learning/pronunciation", tokens["a"])

    pattern = next(item for item in result["json"]["patterns"] if item["pattern"] == "ed_ending")
    assert pattern["opportunities"] == 1
    assert pattern["errors"] == 0
    assert own["code"] == 200
    assert foreign["code"] == 404


def test_pronunciation_applies_persisted_teacher_word_override(portal_runtime):
    runtime, tokens = portal_runtime
    add_step_attempt(
        runtime,
        "fixture-a",
        "teacher-corrected",
        "2026-10-15T18:00:00+00:00",
        words=[{"index": 0, "text": "worked", "said": "work", "status": "missed"}],
        teacher_override={"words": {"0": "heard"}},
    )

    result = http(runtime, "/api/v1/me/learning/pronunciation", tokens["a"])
    pattern = next(item for item in result["json"]["patterns"] if item["pattern"] == "ed_ending")

    assert (pattern["opportunities"], pattern["errors"]) == (1, 0)


def test_cohort_pronunciation_is_staff_only_consent_gated_and_anonymous(portal_runtime):
    runtime, tokens = portal_runtime
    student_ids = ["fixture-a", "fixture-b"]
    for index in range(3):
        actor_id = f"fixture-extra-{index}"
        actor = runtime.auth.bootstrap_fixture_account(
            actor_id, ActorRole.STUDENT, "fixture-password"
        )
        runtime.consents.activate(actor, "demo-v1", research_allowed=True)
        student_ids.append(actor_id)
    for actor_id in student_ids[:2]:
        actor = runtime.auth.resolve(tokens["a"] if actor_id == "fixture-a" else tokens["b"])
        runtime.consents.activate(actor, "demo-v1", research_allowed=True)
    for index, owner_id in enumerate(student_ids):
        for attempt in range(8):
            add_step_attempt(
                runtime,
                owner_id,
                f"cohort-{index}-{attempt}",
                f"2026-10-{8 + attempt:02d}T10:00:00+00:00",
                words=[{"text": "worked", "said": "work", "status": "missed"}],
            )

    denied = http(runtime, "/api/v1/teacher/learning/pronunciation-cohort", tokens["a"])
    result = http(runtime, "/api/v1/teacher/learning/pronunciation-cohort", tokens["teacher"])

    assert denied["code"] == 403
    assert result["code"] == 200
    assert result["json"]["participants"] == 5
    assert all(not pattern["examples"] for pattern in result["json"]["patterns"])
    assert "fixture-a" not in json.dumps(result["json"])
