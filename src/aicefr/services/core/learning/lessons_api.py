"""HTTP API of the lesson path (D025): learners study, teachers author and follow.

The learning service (D043). A recorded step goes into the blob store and the
speech service measures it (`speech.step`, request-reply) while the learner
waits; the forwarded account says whether the terms were accepted (D058), a
learner's latest result comes from assessment,
the plan in force from billing. Wired once at start-up through `configure`.
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Form, HTTPException, Request, UploadFile
from fastapi import Response as HttpResponse
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from aicefr.api.deps import (
    STAFF_ONLY,
    STUDENT_ONLY,
    require_login,
    require_plan,
)
from aicefr.audio.decoder import SNIFF_BYTES, sniff
from aicefr.billing.plans import PlanFeature
from aicefr.contracts import Band, Criterion
from aicefr.lessons.checks import compare_rounds
from aicefr.lessons.generate import build_lesson, build_word_lesson
from aicefr.lessons.lint import lint_lesson
from aicefr.lessons.model import (
    KIND_NAMES,
    TEXT_KINDS,
    Lesson,
    Step,
    StepKind,
    StepResult,
    Topic,
    WordStatus,
)
from aicefr.lessons.progress import (
    AttemptInfo,
    is_complete,
    lesson_state,
    next_lesson,
    today_summary,
)
from aicefr.lessons.review import SESSION_TALKS, SESSION_WORDS, after_review, first_schedule
from aicefr.lessons.text import same_word
from aicefr.platform.bus import BusTimeout, MessageBus
from aicefr.ports import BlobStore
from aicefr.practice.achievements import (
    BY_CODE,
    CATALOG,
    GROUPS,
    Facts,
    Standing,
    Take,
    nearest,
    reached,
    standings,
)
from aicefr.practice.achievements import count as count_facts
from aicefr.practice.streak import LOCAL_TZ
from aicefr.pronunciation.vietnamese import profile as pronunciation_profile
from aicefr.services import Peers
from aicefr.services.speech.worker import PROBE_QUEUE, STEP_QUEUE, STEP_TIMEOUT_S
from aicefr.storage.audit_repository import AuditLog
from aicefr.storage.auth_repository import Account, Role
from aicefr.storage.lesson_repository import LessonRepository, NotFound

router = APIRouter()
logger = logging.getLogger(__name__)


AUDIO_TYPES = {
    "wav": "audio/wav",
    "flac": "audio/flac",
    "mp3": "audio/mpeg",
    "m4a": "audio/mp4",
    "mp4": "audio/mp4",
    "webm": "audio/webm",
    "ogg": "audio/ogg",
}
IMAGE_TYPES = {"png": "image/png", "jpg": "image/jpeg", "webp": "image/webp"}
MAX_IMAGE_BYTES = 3 * 1024 * 1024
# Kinds whose missed words come back in a review.
WORD_REVIEW_KINDS = {StepKind.READ_ALOUD, StepKind.GAP, StepKind.KEYWORDS, StepKind.STARTER}


@dataclass
class Services:
    lessons: LessonRepository
    blobs: BlobStore
    bus: MessageBus
    audit_log: AuditLog
    max_bytes: int
    # The other services. `peers.billing` decides whether staff may write lesson
    # paths and read class insights (D034); learners are never affected. None
    # there: no plans, as before D033.
    peers: Peers


_services: Services | None = None


def configure(services: Services) -> None:
    global _services
    _services = services


def svc() -> Services:
    if _services is None:  # pragma: no cover - configured at import of main
        raise RuntimeError("lessons API used before configure()")
    return _services


def _now() -> datetime:
    return datetime.now(UTC)


def _plan_allows(feature: PlanFeature) -> None:
    require_plan(svc().peers.billing, feature)


def _authoring(account: Account = STAFF_ONLY) -> Account:
    """Writing lesson paths is a staff tool of the plan (D034); reading them never is."""
    _plan_allows(PlanFeature.LESSON_AUTHORING)
    return account


AUTHORING = Depends(_authoring)


def _today():
    return _now().astimezone(LOCAL_TZ).date()


# ---------------------------------------------------------------- uploads


async def _read_upload(upload: UploadFile, limit: int) -> tuple[bytes, bytes]:
    data = b""
    while chunk := await upload.read(256 * 1024):
        data += chunk
        if len(data) > limit:
            raise HTTPException(413, f"file vượt quá {limit // (1024 * 1024)} MiB")
    if not data:
        raise HTTPException(415, "file rỗng")
    return data, data[:SNIFF_BYTES]


async def _read_audio(upload: UploadFile) -> tuple[bytes, str]:
    data, head = await _read_upload(upload, svc().max_bytes)
    kind = sniff(head)
    if kind is None:
        raise HTTPException(
            415, "không nhận ra định dạng audio. Hãy ghi lại ngay trên trang hoặc dùng wav, mp3"
        )
    return data, kind


def _image_kind(head: bytes) -> str | None:
    if head.startswith(b"\x89PNG"):
        return "png"
    if head[:3] == b"\xff\xd8\xff":
        return "jpg"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "webp"
    return None


def _measure(
    step: Step,
    data: bytes,
    kind: str,
    round_index: int | None,
    answers: list[str] | None,
    keep: str | None = None,
) -> StepResult:
    """Have the speech service measure one recording of `step`.

    The recording goes into the blob store first -- under `keep` when it is the
    attempt's own recording, under a throwaway key otherwise -- and the speech
    service reads it from there. A recording it cannot read is a 415, and is not
    kept.
    """
    answer = _ask(
        STEP_QUEUE,
        {
            "step": step.model_dump(mode="json"),
            "size": len(data),
            "round_index": round_index,
            "answers": answers,
        },
        data,
        kind,
        keep,
    )
    return StepResult.model_validate(answer["result"])


def _probe(data: bytes, kind: str) -> None:
    """415 unless the speech service can read the recording; nothing is kept."""
    _ask(PROBE_QUEUE, {}, data, kind, None)


def _ask(queue: str, request: dict, data: bytes, kind: str, keep: str | None) -> dict:
    """Put the recording where the speech service reads it, ask, and clean up.

    The recording stays only under `keep` and only when the answer is good:
    whatever goes wrong -- no answer, an unreadable file, a broker down, a
    malformed answer -- no voice file is left behind without a row pointing at it.
    """
    key = keep or f"lesson-probe-{_rand()}.{kind}"
    svc().blobs.put(key, data)
    ok = False
    try:
        try:
            answer = svc().bus.call(queue, {**request, "audio_key": key}, timeout=STEP_TIMEOUT_S)
        except BusTimeout as e:
            raise HTTPException(503, "máy chấm đang bận, hãy thử lại sau ít phút") from e
        except Exception as e:
            logger.exception("speech service unreachable for %s", queue)
            raise HTTPException(503, "chưa liên lạc được máy chấm, hãy thử lại sau ít phút") from e
        if "error" in answer:
            if answer["error"] == "decode":
                raise HTTPException(415, f"không đọc được bản ghi: {answer.get('detail', '')}")
            raise HTTPException(503, "máy chấm gặp lỗi khi đo bước này, hãy thử lại")
        ok = keep is not None
        return answer
    finally:
        if not ok:
            svc().blobs.delete(key)


# ---------------------------------------------------------------- shared reads


def _choose_path(path_id: str | None, published_only: bool) -> dict | None:
    lessons = svc().lessons
    if path_id:
        try:
            p = lessons.path(path_id)
        except NotFound:
            raise HTTPException(404, "không tìm thấy lộ trình") from None
        if published_only and p["status"] != "published":
            raise HTTPException(404, "không tìm thấy lộ trình")
        return p
    paths = lessons.paths(published_only=published_only)
    return paths[0] if paths else None


def _infos(rows: list[dict]) -> list[AttemptInfo]:
    return [
        AttemptInfo(
            lesson_id=r["lesson_id"],
            step_id=r["step_id"],
            passed=bool(r["passed"]),
            created_at=r["created_at"],
            speaking_s=r["speaking_s"],
        )
        for r in rows
    ]


def _criterion(lesson: Lesson, unit: dict) -> Criterion | None:
    if lesson.criterion:
        return lesson.criterion
    return Criterion(unit["criterion"]) if unit.get("criterion") else None


def _audio_url(attempt_id: str) -> str:
    return f"/api/v1/learn/attempts/{attempt_id}/audio"


def _media_url(key: str | None) -> str | None:
    return f"/api/v1/learn/media/{key}" if key else None


def _step_view(step: Step) -> dict:
    data = step.for_student()
    data["model_audio_url"] = _media_url(step.model_audio)
    data["image_url"] = _media_url(step.image)
    return data


def _lesson_view(lesson: Lesson) -> dict:
    data = lesson.for_student()
    data["steps"] = [_step_view(s) for s in lesson.steps]
    return data


# ================================================================= learners


@router.get("/api/v1/learn", tags=["student"])
def learn_home(path_id: str | None = None, account: Account = Depends(require_login)) -> dict:
    """The learner's path: units and lessons with progress, today, reviews, what next."""
    lessons_repo = svc().lessons
    paths = lessons_repo.paths(published_only=True)
    chosen = _choose_path(path_id, published_only=True)
    if chosen is None:
        return {"paths": [], "path": None, "next": None, "today": None, "reviews_due": 0}
    outline = lessons_repo.outline(chosen["path_id"], published_only=True)
    ids = [item["lesson"].lesson_id for u in outline for item in u["lessons"]]
    rows = lessons_repo.attempts(account_id=account.account_id, lesson_ids=ids)
    infos = _infos(rows)
    states = {}
    ordered = []
    units = []
    done_total = 0
    for u in outline:
        items = []
        for item in u["lessons"]:
            lesson = item["lesson"]
            st = lesson_state(lesson, infos)
            states[lesson.lesson_id] = st
            ordered.append((lesson, _criterion(lesson, u)))
            complete = is_complete(lesson, st)
            done_total += int(complete)
            items.append(
                {
                    "lesson_id": lesson.lesson_id,
                    "title": lesson.title,
                    "summary": lesson.summary,
                    "band": lesson.band.value,
                    "criterion": lesson.criterion.value if lesson.criterion else None,
                    "steps": st.total,
                    "passed": st.passed,
                    "status": "completed" if complete else st.status,
                    "sample": lesson.sample,
                    "kinds": [s.kind.value for s in lesson.steps],
                }
            )
        units.append(
            {
                "unit_id": u["unit_id"],
                "title": u["title"],
                "function": u["function"],
                "band": u["band"],
                "criterion": u["criterion"],
                "topic": u["topic"],
                "lessons": items,
            }
        )

    latest = svc().peers.assessment.latest_assessment(account_id=account.account_id)
    weakest = [Criterion(c) for c in (latest or {}).get("weakest_criteria", []) if c]
    band = (
        Band(latest["band"]) if latest and latest.get("band") in Band._value2member_map_ else None
    )
    nxt = next_lesson(ordered, states, weakest, band)
    title = {ls.lesson_id: ls.title for ls, _ in ordered}
    all_rows = lessons_repo.attempts(account_id=account.account_id)
    # The learner's own daily goal (D029), chosen on the account page.
    today = today_summary(_infos(all_rows), _now(), goal_seconds=account.daily_goal_s)
    facts, have, _new = _award(account, all_rows)
    return {
        "paths": [
            {"path_id": p["path_id"], "title": p["title"], "sample": bool(p["sample"])}
            for p in paths
        ],
        "path": {
            "path_id": chosen["path_id"],
            "title": chosen["title"],
            "description": chosen["description"],
            "band_from": chosen["band_from"],
            "band_to": chosen["band_to"],
            "sample": bool(chosen["sample"]),
            "units": units,
            "lessons_total": len(ordered),
            "lessons_completed": done_total,
        },
        "next": (
            {
                "lesson_id": nxt.lesson_id,
                "title": title.get(nxt.lesson_id, ""),
                "basis": nxt.basis,
                "reason": nxt.reason,
            }
            if nxt
            else None
        ),
        "assessment": (
            {
                "band": latest["band"],
                "created_at": latest["created_at"],
                "teacher_verified": latest["teacher_verified"],
            }
            if latest
            else None
        ),
        "today": {
            "seconds": today.seconds,
            "goal_seconds": today.goal_seconds,
            "goal_met": today.goal_met,
            "streak": today.streak,
            "week": [{"date": d.isoformat(), "seconds": s} for d, s in today.week],
            # D032: the record, the rest days on the dots, this week against the last.
            "best_streak": today.best_streak,
            "rest_days": [d.isoformat() for d in today.rest_days],
            "week_seconds": today.week_seconds,
            "last_week_seconds": today.last_week_seconds,
        },
        "achievements": _achievement_summary(facts, have),
        # What today's review session holds, the same count the review page
        # starts from (and items of archived lessons closed on the way).
        "reviews_due": reviews_due(account.account_id),
    }


def _lesson_context(lesson_id: str) -> tuple[dict, dict, list]:
    """The unit and path of a lesson, and the path's published lessons in order."""
    lessons_repo = svc().lessons
    try:
        _, meta = lessons_repo.draft(lesson_id)
    except NotFound:
        raise HTTPException(404, "không tìm thấy bài học") from None
    unit = lessons_repo.unit(meta["unit_id"])
    path = lessons_repo.path(meta["path_id"])
    order = [
        item["lesson"]
        for u in lessons_repo.outline(path["path_id"], published_only=True)
        for item in u["lessons"]
    ]
    return unit, path, order


def _live(lesson_id: str) -> tuple[Lesson, int]:
    """The published version of a lesson whose path is published too, or 404.

    The same gate as the lesson page: a lesson of a path still in draft must
    not take attempts from someone who guessed or kept its address.
    """
    lessons_repo = svc().lessons
    found = lessons_repo.published(lesson_id)
    try:
        _, meta = lessons_repo.draft(lesson_id)
    except NotFound:
        raise HTTPException(404, "không tìm thấy bài học") from None
    if found is None or lessons_repo.path(meta["path_id"])["status"] != "published":
        raise HTTPException(404, "không tìm thấy bài học")
    return found


def _attempt_view(row: dict) -> dict:
    return {
        "attempt_id": row["attempt_id"],
        "step_id": row["step_id"],
        "round": row["round"],
        "passed": row["passed"],
        "created_at": row["created_at"],
        "result": row["result"].model_dump(mode="json"),
        "audio_url": _audio_url(row["attempt_id"]) if row.get("audio_key") else None,
    }


@router.get("/api/v1/learn/lessons/{lesson_id}", tags=["student"])
def learn_lesson(lesson_id: str, account: Account = Depends(require_login)) -> dict:
    lessons_repo = svc().lessons
    found = lessons_repo.published(lesson_id)
    unit, path, order = _lesson_context(lesson_id)
    if found is None or path["status"] != "published":
        raise HTTPException(404, "không tìm thấy bài học")
    lesson, version = found
    rows = lessons_repo.attempts(account_id=account.account_id, lesson_id=lesson_id)
    st = lesson_state(lesson, _infos(rows))
    latest: dict[str, dict] = {}
    for row in rows:
        latest[row["step_id"]] = _attempt_view(row)
    ids = [ls.lesson_id for ls in order]
    nxt = order[ids.index(lesson_id) + 1] if lesson_id in ids and ids[-1] != lesson_id else None
    return {
        "lesson": _lesson_view(lesson),
        "version": version,
        "preview": False,
        "path": {"path_id": path["path_id"], "title": path["title"]},
        "unit": {
            "unit_id": unit["unit_id"],
            "title": unit["title"],
            "band": unit["band"],
            "topic": unit.get("topic"),
        },
        "progress": {
            "passed": st.passed,
            "total": st.total,
            "free_done": st.free_done,
            "completed": is_complete(lesson, st),
        },
        "latest": latest,
        # A step counts as passed once any attempt passed, as in lesson_state;
        # the latest attempt alone would show a step passed yesterday as failed.
        "passed_steps": sorted({r["step_id"] for r in rows if r["passed"]}),
        "next_lesson": {"lesson_id": nxt.lesson_id, "title": nxt.title} if nxt else None,
    }


def _schedule_reviews(account: Account, lesson: Lesson, step: Step, result: StepResult) -> None:
    if not result.measured:
        return
    due = first_schedule(_today()).due
    repo = svc().lessons
    if step.kind in WORD_REVIEW_KINDS:
        for word in result.missed_words()[:6]:
            repo.schedule(account.account_id, "word", lesson.lesson_id, step.step_id, word, due)
    if step.kind is StepKind.FREE:
        limits = step.round_limits()
        if (result.round or 1) >= len(limits):
            repo.schedule(account.account_id, "talk", lesson.lesson_id, step.step_id, "", due)


def _compare_with_first_round(account: Account, lesson_id: str, step_id: str, result: StepResult):
    if result.round is None or result.round <= 1:
        return
    rows = svc().lessons.attempts(account_id=account.account_id, lesson_id=lesson_id)
    firsts = [r for r in rows if r["step_id"] == step_id and (r["round"] or 1) == 1]
    if firsts:
        result.changes = compare_rounds(firsts[-1]["result"], result)


# ---------------------------------------------------------------- retell (D069)
# The same task again, right after its report, three times under a shrinking
# time limit (4/3/2, Nation 1989; task repetition: Bygate 2018). Each round is
# measured like a lesson's free step and compared with the first: pace and
# pauses, what repeating under time pressure trains (Thai & Boers 2016).

RETELL_STEP = "retell"
RETELL_MAX_S = 90  # a P5 talk is retold as its first ninety seconds
RETELL_FLOOR_S = 20


def _retell_lesson(response_id: str) -> str:
    return f"retell-{response_id}"


def _retell_step(source: dict) -> Step:
    base = max(RETELL_FLOOR_S, min(int(source["max_seconds"]), RETELL_MAX_S))
    rounds = [base, max(RETELL_FLOOR_S, round(base * 0.75)), max(RETELL_FLOOR_S, round(base * 0.5))]
    return Step(
        step_id=RETELL_STEP,
        kind=StepKind.FREE,
        title="Nói lại đề này",
        instruction=source["prompt"],
        max_seconds=base,
        rounds=rounds,
    )


def _retell_source(account: Account, response_id: str) -> dict:
    source = svc().peers.assessment.retell_source(
        account_id=account.account_id, response_id=response_id
    )
    if source is None:
        raise HTTPException(404, "không tìm thấy bài này")
    return source


@router.get("/api/v1/learn/retell/{response_id}", tags=["student"])
def retell(response_id: str, account: Account = STUDENT_ONLY) -> dict:
    """The task, its three rounds, and what this learner already recorded of them."""
    source = _retell_source(account, response_id)
    step = _retell_step(source)
    rows = svc().lessons.attempts(
        account_id=account.account_id, lesson_id=_retell_lesson(response_id)
    )
    return {
        **source,
        "rounds": step.round_limits(),
        "done": [
            {
                "attempt_id": r["attempt_id"],
                "round": r["round"] or 1,
                "result": r["result"].model_dump(mode="json"),
                "audio_url": _audio_url(r["attempt_id"]),
            }
            for r in rows
            if r["step_id"] == RETELL_STEP
        ],
    }


@router.post("/api/v1/learn/retell/{response_id}/rounds", tags=["student"])
async def retell_round(
    response_id: str,
    audio: UploadFile,
    round: int = Form(1),  # noqa: A002 - the form field is called round
    account: Account = STUDENT_ONLY,
) -> dict:
    source = _retell_source(account, response_id)
    step = _retell_step(source)
    round_index = min(max(round, 1), len(step.round_limits()))
    data, kind = await _read_audio(audio)

    # The speech service answers in seconds; not on the event loop (D066).
    def measure_and_store() -> dict:
        attempt_id = f"a{datetime.now(UTC).strftime('%y%m%d')}{_rand()}"
        audio_key = f"lesson-audio-{attempt_id}.{kind}"
        result = _measure(step, data, kind, round_index, None, keep=audio_key)
        lesson_id = _retell_lesson(response_id)
        _compare_with_first_round(account, lesson_id, RETELL_STEP, result)
        svc().lessons.add_attempt(
            account.account_id, lesson_id, 0, result, audio_key=audio_key, attempt_id=attempt_id
        )
        return {
            "attempt_id": attempt_id,
            "result": result.model_dump(mode="json"),
            "audio_url": _audio_url(attempt_id),
        }

    return await run_in_threadpool(measure_and_store)


@router.post("/api/v1/learn/lessons/{lesson_id}/steps/{step_id}/attempts", tags=["student"])
async def learn_attempt(
    lesson_id: str,
    step_id: str,
    request: Request,
    audio: UploadFile,
    round: int | None = Form(None),  # noqa: A002 - the form field is called round
    account: Account = STUDENT_ONLY,
) -> dict:
    """Record one step and measure it right away. FR-46."""
    lessons_repo = svc().lessons
    lesson, version = _live(lesson_id)
    step = lesson.step(step_id)
    if step is None:
        raise HTTPException(404, "không tìm thấy bước này")
    limits = step.round_limits()
    round_index = min(max(round or 1, 1), len(limits)) if step.kind is StepKind.FREE else None

    data, kind = await _read_audio(audio)

    # The speech service answers in seconds; waiting for it on the event loop
    # stalled every other request of this service meanwhile (D066).
    def measure_and_store() -> dict:
        before = lesson_state(
            lesson,
            _infos(lessons_repo.attempts(account_id=account.account_id, lesson_id=lesson_id)),
        )
        attempt_id = f"a{datetime.now(UTC).strftime('%y%m%d')}{_rand()}"
        audio_key = f"lesson-audio-{attempt_id}.{kind}"
        result = _measure(step, data, kind, round_index, step.answers, keep=audio_key)
        _compare_with_first_round(account, lesson_id, step_id, result)

        lessons_repo.add_attempt(
            account.account_id,
            lesson_id,
            version,
            result,
            audio_key=audio_key,
            attempt_id=attempt_id,
        )
        _schedule_reviews(account, lesson, step, result)

        after = lesson_state(
            lesson,
            _infos(lessons_repo.attempts(account_id=account.account_id, lesson_id=lesson_id)),
        )
        return {
            "attempt_id": attempt_id,
            "result": result.model_dump(mode="json"),
            "audio_url": _audio_url(attempt_id),
            "progress": {
                "passed": after.passed,
                "total": after.total,
                "free_done": after.free_done,
                "completed": is_complete(lesson, after),
            },
            "completed_now": is_complete(lesson, after) and not is_complete(lesson, before),
            "achievements": _just_reached(account),
        }

    return await run_in_threadpool(measure_and_store)


def _rand() -> str:
    import uuid

    return uuid.uuid4().hex[:8]


@router.get("/api/v1/learn/attempts/{attempt_id}/audio", tags=["student"])
def attempt_audio(attempt_id: str, account: Account = Depends(require_login)) -> HttpResponse:
    try:
        row = svc().lessons.attempt(attempt_id)
    except NotFound:
        raise HTTPException(404, "không tìm thấy bản ghi") from None
    # 404 rather than 403 for someone else's attempt: a 403 would confirm it exists.
    if not _may_see(account, row["account_id"]):
        raise HTTPException(404, "không tìm thấy bản ghi")
    key = row.get("audio_key")
    if not key:
        raise HTTPException(404, "không có bản ghi âm")
    # A voice recording identifies its speaker: every access is recorded, as for
    # assessment recordings, so "who listened to this, and when" has an answer.
    svc().audit_log.write(account.account_id, "AUDIO_ACCESS", attempt_id, "lesson")
    try:
        data = svc().blobs.get(key)
    except (FileNotFoundError, KeyError, OSError):
        raise HTTPException(404, "không có bản ghi âm") from None
    ext = key.rsplit(".", 1)[-1]
    return HttpResponse(
        data,
        media_type=AUDIO_TYPES.get(ext, "application/octet-stream"),
        headers={"Cache-Control": "private, no-store"},
    )


@router.delete("/api/v1/learn/attempts/{attempt_id}", tags=["student"])
def delete_attempt(attempt_id: str, account: Account = Depends(require_login)) -> dict:
    """A learner removes one of their own recordings (FR-35, learner side)."""
    lessons_repo = svc().lessons
    try:
        row = lessons_repo.attempt(attempt_id)
    except NotFound:
        raise HTTPException(404, "không tìm thấy bản ghi") from None
    if row["account_id"] != account.account_id:
        raise HTTPException(404, "không tìm thấy bản ghi")
    key = lessons_repo.delete_attempt(attempt_id)
    if key:
        try:
            svc().blobs.delete(key)
        except (FileNotFoundError, OSError):
            pass
    # Who asked and what went, never what it contained (AC-35.5).
    svc().audit_log.write(account.account_id, "ERASE_OWN_LESSON_ATTEMPT", attempt_id, None)
    return {"status": "ok"}


@router.get("/api/v1/learn/media/{key}", tags=["student"])
def lesson_media(key: str, account: Account = Depends(require_login)) -> HttpResponse:
    try:
        media = svc().lessons.media(key)
        data = svc().blobs.get(media["blob_key"])
    except (NotFound, FileNotFoundError, KeyError, OSError):
        raise HTTPException(404, "không tìm thấy tệp") from None
    return HttpResponse(
        data, media_type=media["content_type"], headers={"Cache-Control": "private, max-age=3600"}
    )


# ---------------------------------------------------------------- review


def reviews_due(account_id: str) -> int:
    """Items in today's review session, the count the sidebar shows (D028)."""
    return sum(len(s["items"]) for s in _review_steps(account_id))


def _review_steps(account_id: str) -> list[dict]:
    """Due review items turned into speaking steps: words in threes, one free talk."""
    lessons_repo = svc().lessons
    due = lessons_repo.due_reviews(account_id, _today())
    words = [i for i in due if i["kind"] == "word"][:SESSION_WORDS]
    talks = [i for i in due if i["kind"] == "talk"][:SESSION_TALKS]
    steps = []
    for k in range(0, len(words), 3):
        batch = words[k : k + 3]
        step = Step(
            step_id="w-" + "-".join(i["item_id"] for i in batch),
            kind=StepKind.KEYWORDS,
            instruction=(
                "Ôn từ: nói một hay hai câu của riêng bạn có các từ dưới đây. Đừng đọc lại "
                "câu cũ, hãy tự đặt câu mới."
            ),
            keywords=[i["word"] for i in batch],
            min_words=len(batch) + 4,
            max_seconds=35,
        )
        steps.append(
            {
                "review_id": step.step_id,
                "items": [i["item_id"] for i in batch],
                "step": _step_view(step),
                "source": "words",
            }
        )
    for item in talks:
        found = lessons_repo.published(item["lesson_id"])
        free = found[0].step(item["step_id"]) if found else None
        if free is None:
            # The lesson was archived or its free step removed: there is nothing
            # left to review, so the item is closed instead of counted forever.
            lessons_repo.reschedule(item["item_id"], item["box"], None)
            continue
        lesson = found[0]
        limits = free.round_limits()
        step = free.model_copy(
            update={
                "step_id": "t-" + item["item_id"],
                "rounds": [limits[1] if len(limits) > 1 else limits[0]],
                "instruction": (
                    f"Ôn bài «{lesson.title}»: nói lại về đề này một lượt. Không cần nhớ "
                    "nguyên văn lần trước."
                ),
            }
        )
        steps.append(
            {
                "review_id": step.step_id,
                "items": [item["item_id"]],
                "step": _step_view(step),
                "source": "talk",
                "lesson_title": lesson.title,
            }
        )
    return steps


@router.get("/api/v1/learn/review", tags=["student"])
def learn_review(account: Account = Depends(require_login)) -> dict:
    steps = _review_steps(account.account_id)
    upcoming = svc().lessons.open_reviews(account.account_id)
    return {
        "steps": steps,
        "due": len(svc().lessons.due_reviews(account.account_id, _today())),
        "open": len(upcoming),
        "next_due": upcoming[0]["due_date"] if upcoming else None,
    }


@router.post("/api/v1/learn/review/attempts", tags=["student"])
async def learn_review_attempt(
    request: Request,
    audio: UploadFile,
    review_id: str = Form(...),
    account: Account = STUDENT_ONLY,
) -> dict:
    session = {s["review_id"]: s for s in _review_steps(account.account_id)}
    entry = session.get(review_id)
    if entry is None:
        raise HTTPException(404, "mục ôn này không còn đến hạn")
    step = Step.model_validate({k: v for k, v in entry["step"].items() if k in Step.model_fields})
    data, kind = await _read_audio(audio)

    # The speech service answers in seconds; waiting for it on the event loop
    # stalled every other request of this service meanwhile (D066).
    def measure_and_store() -> dict:
        attempt_id = f"a{datetime.now(UTC).strftime('%y%m%d')}{_rand()}"
        audio_key = f"lesson-audio-{attempt_id}.{kind}"
        result = _measure(
            step, data, kind, 1 if step.kind is StepKind.FREE else None, None, keep=audio_key
        )

        lessons_repo = svc().lessons
        items = [lessons_repo.review(i) for i in entry["items"]]
        if entry["source"] == "talk":
            item = items[0]
            found = lessons_repo.published(item["lesson_id"])
            lesson_id, version = item["lesson_id"], found[1] if found else 0
            step_id = item["step_id"]
        else:
            lesson_id, version, step_id = "review", 0, "review-words"
        result = result.model_copy(update={"step_id": step_id})
        lessons_repo.add_attempt(
            account.account_id,
            lesson_id,
            version,
            result,
            audio_key=audio_key,
            review_item_id=",".join(entry["items"]),
            attempt_id=attempt_id,
        )
        today = _today()
        outcome = []
        found_words = [h.text for h in result.found]
        for item in items:
            if not result.measured:
                continue
            if item["kind"] == "word":
                ok = any(same_word(item["word"].lower(), w.lower()) for w in found_words)
            else:
                ok = result.passed
            nxt = after_review(item["box"], ok, today)
            lessons_repo.reschedule(item["item_id"], nxt.box, nxt.due)
            outcome.append(
                {
                    "item_id": item["item_id"],
                    "word": item["word"],
                    "passed": ok,
                    "done": nxt.done,
                    "due": nxt.due.isoformat() if nxt.due else None,
                }
            )
        return {
            "attempt_id": attempt_id,
            "result": result.model_dump(mode="json"),
            "audio_url": _audio_url(attempt_id),
            "items": outcome,
            "achievements": _just_reached(account),
        }

    return await run_in_threadpool(measure_and_store)


# ---------------------------------------------------------------- achievements (D032)


def _takes(rows: list[dict]) -> list[Take]:
    return [
        Take(
            lesson_id=r["lesson_id"],
            step_id=r["step_id"],
            created_at=r["created_at"],
            speaking_s=r["speaking_s"],
            passed=bool(r["passed"]),
            free=r["result"].kind is StepKind.FREE,
            review=bool(r["review_item_id"]),
        )
        for r in rows
    ]


def _completed(infos: list[AttemptInfo]) -> tuple[int, int]:
    """Lessons and units completed, over every published path."""
    lessons_repo = svc().lessons
    by_lesson: dict[str, list[AttemptInfo]] = defaultdict(list)
    for info in infos:
        by_lesson[info.lesson_id].append(info)
    lessons_done = units_done = 0
    for p in lessons_repo.paths(published_only=True):
        for u in lessons_repo.outline(p["path_id"], published_only=True):
            done = []
            for item in u["lessons"]:
                lesson = item["lesson"]
                done.append(is_complete(lesson, lesson_state(lesson, by_lesson[lesson.lesson_id])))
            lessons_done += sum(done)
            units_done += int(bool(done) and all(done))
    return lessons_done, units_done


def _facts(account: Account, rows: list[dict] | None = None) -> Facts:
    if rows is None:
        rows = svc().lessons.attempts(account_id=account.account_id)
    lessons_done, units_done = _completed(_infos(rows))
    # Assessments that came back with a result: the rows the progress page draws.
    scored = svc().peers.assessment.progress_series(account_id=account.account_id)
    return count_facts(
        _takes(rows),
        goal_seconds=account.daily_goal_s,
        lessons_completed=lessons_done,
        units_completed=units_done,
        assessments=len(scored),
    )


def _award(
    account: Account, rows: list[dict] | None = None
) -> tuple[Facts, dict[str, dict], list[str]]:
    """Count the facts, store what was reached since last time, return all three."""
    facts = _facts(account, rows)
    lessons_repo = svc().lessons
    have = lessons_repo.achievements(account.account_id)
    now_reached = reached(facts)
    fresh = [a.code for a in CATALOG if a.code in now_reached and a.code not in have]
    new = lessons_repo.unlock(account.account_id, fresh) if fresh else []
    if new:
        have = lessons_repo.achievements(account.account_id)
    return facts, have, new


def _just_reached(account: Account) -> list[dict]:
    """Achievements a recording just reached, for the lesson page to congratulate.

    The attempt is stored before this runs; a fault here must not turn a
    recorded attempt into an error the learner would answer by recording again.
    """
    try:
        _facts_, _have, new = _award(account)
    except Exception:  # noqa: BLE001 - see the docstring
        logger.exception("achievements: could not count for %s", account.pseudonym)
        return []
    return [{"code": c, "title": BY_CODE[c].title, "icon": BY_CODE[c].icon} for c in new]


def _achievement_view(standing: Standing, stored: dict | None) -> dict:
    a = standing.achievement
    return {
        "code": a.code,
        "group": a.group,
        "title": a.title,
        "description": a.description,
        "icon": a.icon,
        "target": a.target,
        "unit": a.unit,
        # Reached once is reached for good, whatever the attempts say today.
        "value": a.target if stored else standing.value,
        "unlocked": stored is not None,
        "unlocked_at": stored["unlocked_at"] if stored else None,
        "new": stored is not None and stored["seen_at"] is None,
    }


def _achievement_summary(facts: Facts, have: dict[str, dict]) -> dict:
    """The practice page's card: how many, which are new, the last three, the nearest."""
    known = [(code, v) for code, v in have.items() if code in BY_CODE]
    near = nearest(facts, have)
    return {
        "unlocked": len(known),
        "total": len(CATALOG),
        "new": sum(1 for _code, v in known if v["seen_at"] is None),
        "recent": [
            {"code": code, "title": BY_CODE[code].title, "icon": BY_CODE[code].icon}
            for code, _v in reversed(known)
        ][:3],
        "next": (
            {
                "code": near.achievement.code,
                "title": near.achievement.title,
                "icon": near.achievement.icon,
                "value": near.value,
                "target": near.achievement.target,
                "unit": near.achievement.unit,
            }
            if near
            else None
        ),
    }


@router.get("/api/v1/me/achievements", tags=["student"])
def my_achievements(account: Account = Depends(require_login)) -> dict:
    """Every achievement and how far the learner is towards it. FR-65.

    Reached ones are stored on the way, so one reached by an assessment that
    finished in the background shows up here without a lesson in between.
    Private: there is no route by which anyone else reads them.
    """
    facts, have, _new = _award(account)
    items = [_achievement_view(s, have.get(s.achievement.code)) for s in standings(facts)]
    return {
        "groups": [{"key": key, "name": name} for key, name in GROUPS.items()],
        "items": items,
        "unlocked": sum(1 for i in items if i["unlocked"]),
        "total": len(items),
        "best_streak": facts.best_streak,
    }


# ---------------------------------------------------------------- pronunciation (D039)

# The newest attempts a profile reads: enough to see a habit, few enough that an
# old habit already fixed fades out.
PRONUNCIATION_WINDOW = 400


@router.get("/api/v1/me/pronunciation", tags=["student"])
def my_pronunciation(account: Account = STUDENT_ONLY) -> dict:
    """The learner's Vietnamese-learner pronunciation patterns, each against its chances. FR-75.

    Read from the word marks of their own read-aloud, repeat, look-up and gap
    steps; a pattern with fewer than `min_opportunities` chances says "not
    enough yet" rather than a rate.
    """
    rows = svc().lessons.attempts(account_id=account.account_id, limit=PRONUNCIATION_WINDOW)
    return pronunciation_profile(rows)


@router.get("/api/v1/teach/pronunciation", tags=["teacher"])
def class_pronunciation(account: Account = STAFF_ONLY) -> dict:
    """The same patterns over every learner's attempts, for planning a lesson. FR-76.

    A class figure only: examples keep the word and what was heard, never the
    attempt, the date or anything else that leads back to one learner.
    """
    rows = _in_view(account, svc().lessons.attempts(limit=PRONUNCIATION_WINDOW * 10))
    out = pronunciation_profile(rows)
    for item in out["patterns"]:
        item["examples"] = [{"word": e["word"], "said": e["said"]} for e in item["examples"]]
    out["learners"] = len({r.get("account_id") for r in rows if r.get("account_id")})
    return out


class SeenIn(BaseModel):
    codes: list[str] | None = Field(default=None, max_length=len(CATALOG))


@router.post("/api/v1/me/achievements/seen", tags=["student"])
def achievements_seen(
    body: SeenIn | None = None, account: Account = Depends(require_login)
) -> dict:
    """The learner has seen these achievements (all new ones without a body)."""
    codes = body.codes if body else None
    return {"seen": svc().lessons.mark_seen(account.account_id, codes)}


# ================================================================= teachers


class PathIn(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    description: str = Field(default="", max_length=1000)
    band_from: Band | None = None
    band_to: Band | None = None


class PathPatch(BaseModel):
    title: str | None = Field(default=None, max_length=160)
    description: str | None = Field(default=None, max_length=1000)
    band_from: Band | None = None
    band_to: Band | None = None
    status: str | None = None


class UnitIn(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    function: str = Field(default="", max_length=300)
    band: Band | None = None
    criterion: Criterion | None = None
    topic: Topic | None = None


class MoveIn(BaseModel):
    direction: int = Field(ge=-1, le=1)


class LessonIn(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    band: Band = Band.A2
    criterion: Criterion | None = None
    summary: str = Field(default="", max_length=600)
    model_text: str = Field(default="", max_length=3000)
    keywords: list[str] = Field(default_factory=list, max_length=12)
    free_prompt: str = Field(default="", max_length=600)


class OverrideIn(BaseModel):
    words: dict[int, WordStatus] = Field(default_factory=dict)
    passed: bool | None = None
    note: str = Field(default="", max_length=500)


def _audit(account: Account, action: str, target: str, detail: str = "") -> None:
    svc().audit_log.write(account.pseudonym, action, target, detail or None)


def _lesson_summary(item: dict) -> dict:
    lesson = item["lesson"]
    return {
        "lesson_id": lesson.lesson_id,
        "title": lesson.title,
        "band": lesson.band.value,
        "criterion": lesson.criterion.value if lesson.criterion else None,
        "steps": len(lesson.steps),
        "kinds": [s.kind.value for s in lesson.steps],
        "published_version": item["published_version"],
        "draft_changed": item["draft_changed"],
        "sample": lesson.sample,
    }


@router.get("/api/v1/teach/paths", tags=["teacher"])
def teach_paths(account: Account = STAFF_ONLY) -> list[dict]:
    lessons_repo = svc().lessons
    out = []
    for p in lessons_repo.paths():
        units = []
        for u in lessons_repo.outline(p["path_id"], published_only=False):
            units.append(
                {
                    "unit_id": u["unit_id"],
                    "title": u["title"],
                    "function": u["function"],
                    "band": u["band"],
                    "criterion": u["criterion"],
                    "topic": u["topic"],
                    "lessons": [_lesson_summary(i) for i in u["lessons"]],
                }
            )
        out.append({**p, "sample": bool(p["sample"]), "units": units})
    return out


@router.post("/api/v1/teach/paths", tags=["teacher"], dependencies=[AUTHORING])
def teach_new_path(body: PathIn, account: Account = STAFF_ONLY) -> dict:
    pid = svc().lessons.create_path(
        body.title, body.description, body.band_from, body.band_to, by=account.pseudonym
    )
    _audit(account, "lesson.path.create", pid)
    return {"path_id": pid}


@router.patch("/api/v1/teach/paths/{path_id}", tags=["teacher"], dependencies=[AUTHORING])
def teach_patch_path(path_id: str, body: PathPatch, account: Account = STAFF_ONLY) -> dict:
    try:
        svc().lessons.update_path(path_id, **body.model_dump(exclude_none=True))
    except NotFound:
        raise HTTPException(404, "không tìm thấy lộ trình") from None
    except ValueError as e:
        raise HTTPException(422, str(e)) from e
    _audit(account, "lesson.path.update", path_id, ",".join(body.model_dump(exclude_none=True)))
    return {"status": "ok"}


@router.get("/api/v1/teach/paths/{path_id}/export", tags=["teacher"])
def teach_export(path_id: str, account: Account = STAFF_ONLY) -> JSONResponse:
    try:
        data = svc().lessons.export_path(path_id)
    except NotFound:
        raise HTTPException(404, "không tìm thấy lộ trình") from None
    return JSONResponse(
        data, headers={"Content-Disposition": f'attachment; filename="path-{path_id}.json"'}
    )


@router.post("/api/v1/teach/paths/import", tags=["teacher"], dependencies=[AUTHORING])
async def teach_import(request: Request, account: Account = STAFF_ONLY) -> dict:
    raw = await request.body()
    if len(raw) > 2 * 1024 * 1024:
        raise HTTPException(413, "tệp lộ trình quá lớn")
    try:
        data = json.loads(raw)
        pid = svc().lessons.import_path(data, by=account.pseudonym)
    except (ValueError, TypeError, KeyError) as e:
        raise HTTPException(422, f"tệp lộ trình không hợp lệ: {e}") from e
    _audit(account, "lesson.path.import", pid)
    return {"path_id": pid}


@router.post("/api/v1/teach/paths/{path_id}/units", tags=["teacher"], dependencies=[AUTHORING])
def teach_new_unit(path_id: str, body: UnitIn, account: Account = STAFF_ONLY) -> dict:
    try:
        uid = svc().lessons.add_unit(
            path_id, body.title, body.function, body.band, body.criterion, topic=body.topic
        )
    except NotFound:
        raise HTTPException(404, "không tìm thấy lộ trình") from None
    return {"unit_id": uid}


@router.patch("/api/v1/teach/units/{unit_id}", tags=["teacher"], dependencies=[AUTHORING])
def teach_patch_unit(unit_id: str, body: UnitIn, account: Account = STAFF_ONLY) -> dict:
    try:
        svc().lessons.update_unit(unit_id, **body.model_dump())
    except NotFound:
        raise HTTPException(404, "không tìm thấy chặng") from None
    return {"status": "ok"}


@router.delete("/api/v1/teach/units/{unit_id}", tags=["teacher"], dependencies=[AUTHORING])
def teach_delete_unit(unit_id: str, account: Account = STAFF_ONLY) -> dict:
    try:
        svc().lessons.delete_unit(unit_id)
    except ValueError as e:
        raise HTTPException(409, str(e)) from e
    return {"status": "ok"}


@router.post("/api/v1/teach/units/{unit_id}/move", tags=["teacher"], dependencies=[AUTHORING])
def teach_move_unit(unit_id: str, body: MoveIn, account: Account = STAFF_ONLY) -> dict:
    try:
        svc().lessons.move("lesson_unit", unit_id, body.direction)
    except NotFound:
        raise HTTPException(404, "không tìm thấy chặng") from None
    return {"status": "ok"}


@router.post("/api/v1/teach/units/{unit_id}/lessons", tags=["teacher"], dependencies=[AUTHORING])
def teach_new_lesson(unit_id: str, body: LessonIn, account: Account = STAFF_ONLY) -> dict:
    """A new lesson: from a model text and key words, from key words alone, or one free step."""
    if body.model_text.strip():
        lesson = build_lesson(
            body.title,
            body.band,
            body.model_text,
            body.keywords,
            body.free_prompt or "Nói tự do về chủ đề của bài.",
            criterion=body.criterion,
            summary=body.summary,
        )
    elif body.keywords:
        lesson = build_word_lesson(
            body.title,
            body.band,
            body.keywords,
            body.free_prompt or "Nói tự do về chủ đề của bài.",
            criterion=body.criterion,
            summary=body.summary,
        )
    else:
        lesson = Lesson(
            title=body.title,
            band=body.band,
            criterion=body.criterion,
            summary=body.summary,
            keywords=body.keywords,
            steps=[
                Step(
                    kind=StepKind.FREE,
                    text=body.free_prompt or "Nói tự do về chủ đề của bài.",
                    rounds=[60, 45, 35],
                )
            ],
        )
    try:
        svc().lessons.add_lesson(unit_id, lesson, by=account.pseudonym)
    except NotFound:
        raise HTTPException(404, "không tìm thấy chặng") from None
    _audit(account, "lesson.create", lesson.lesson_id)
    return {"lesson_id": lesson.lesson_id}


def _draft_or_404(lesson_id: str) -> tuple[Lesson, dict]:
    try:
        return svc().lessons.draft(lesson_id)
    except NotFound:
        raise HTTPException(404, "không tìm thấy bài học") from None


@router.get("/api/v1/teach/lessons/{lesson_id}", tags=["teacher"])
def teach_lesson(lesson_id: str, account: Account = STAFF_ONLY) -> dict:
    lesson, meta = _draft_or_404(lesson_id)
    lessons_repo = svc().lessons
    unit = lessons_repo.unit(meta["unit_id"])
    path = lessons_repo.path(meta["path_id"])
    data = lesson.model_dump(mode="json")
    for step in data["steps"]:
        step["model_audio_url"] = _media_url(step.get("model_audio"))
        step["image_url"] = _media_url(step.get("image"))
    return {
        "lesson": data,
        "meta": meta,
        "unit": {
            "unit_id": unit["unit_id"],
            "title": unit["title"],
            "band": unit["band"],
            "topic": unit.get("topic"),
        },
        "path": {"path_id": path["path_id"], "title": path["title"]},
        "lint": [i.as_dict() for i in lint_lesson(lesson)],
        "kinds": {k.value: KIND_NAMES[k] for k in StepKind},
    }


@router.put("/api/v1/teach/lessons/{lesson_id}", tags=["teacher"], dependencies=[AUTHORING])
def teach_save_lesson(lesson_id: str, body: Lesson, account: Account = STAFF_ONLY) -> dict:
    current, _ = _draft_or_404(lesson_id)
    if body.lesson_id != lesson_id:
        raise HTTPException(422, "mã bài học không khớp")
    # Media keys can only come from an upload through this API, never from the form.
    known = {s.step_id: s for s in current.steps}
    for step in body.steps:
        old = known.get(step.step_id)
        step.model_audio = old.model_audio if old and step.model_audio else None
        step.image = old.image if old and step.image else None
    svc().lessons.save_draft(lesson_id, body, by=account.pseudonym)
    return {"status": "ok", "lint": [i.as_dict() for i in lint_lesson(body)]}


@router.post(
    "/api/v1/teach/lessons/{lesson_id}/publish", tags=["teacher"], dependencies=[AUTHORING]
)
def teach_publish(lesson_id: str, account: Account = STAFF_ONLY) -> dict:
    lesson, _ = _draft_or_404(lesson_id)
    if not lesson.steps:
        raise HTTPException(422, "bài học chưa có bước nào")
    version = svc().lessons.publish(lesson_id, by=account.pseudonym)
    _audit(account, "lesson.publish", lesson_id, f"version={version}")
    return {"version": version}


@router.post("/api/v1/teach/lessons/{lesson_id}/move", tags=["teacher"], dependencies=[AUTHORING])
def teach_move_lesson(lesson_id: str, body: MoveIn, account: Account = STAFF_ONLY) -> dict:
    try:
        svc().lessons.move("lesson", lesson_id, body.direction)
    except NotFound:
        raise HTTPException(404, "không tìm thấy bài học") from None
    return {"status": "ok"}


@router.delete("/api/v1/teach/lessons/{lesson_id}", tags=["teacher"], dependencies=[AUTHORING])
def teach_archive_lesson(lesson_id: str, account: Account = STAFF_ONLY) -> dict:
    _draft_or_404(lesson_id)
    svc().lessons.archive_lesson(lesson_id)
    _audit(account, "lesson.archive", lesson_id)
    return {"status": "ok"}


def _set_step_media(lesson_id: str, step_id: str, field: str, key: str, by: str) -> Lesson:
    lesson, _ = _draft_or_404(lesson_id)
    step = lesson.step(step_id)
    if step is None:
        raise HTTPException(404, "không tìm thấy bước này")
    setattr(step, field, key)
    svc().lessons.save_draft(lesson_id, lesson, by=by)
    return lesson


@router.post(
    "/api/v1/teach/lessons/{lesson_id}/steps/{step_id}/model-audio",
    tags=["teacher"],
    dependencies=[AUTHORING],
)
async def teach_model_audio(
    lesson_id: str, step_id: str, audio: UploadFile, account: Account = STAFF_ONLY
) -> dict:
    """Store a teacher's model recording and check it says the step's text. FR-47."""
    lesson, _ = _draft_or_404(lesson_id)
    step = lesson.step(step_id)
    if step is None:
        raise HTTPException(404, "không tìm thấy bước này")
    data, kind = await _read_audio(audio)
    # Checked before anything is stored: an unreadable file is a 415 and the
    # lesson keeps the model audio it had.
    measured = None
    if step.kind in TEXT_KINDS and step.text.strip() and step.kind is not StepKind.GAP:
        probe = Step(kind=StepKind.READ_ALOUD, text=step.text, step_id=step.step_id)
        measured = _measure(probe, data, kind, None, None)
    else:
        _probe(data, kind)
    blob_key = f"lesson-media-{lesson_id}-{step_id}-{_rand()}.{kind}"
    svc().blobs.put(blob_key, data)
    key = svc().lessons.add_media(
        lesson_id, "audio", AUDIO_TYPES.get(kind, "audio/wav"), blob_key, account.pseudonym
    )
    _set_step_media(lesson_id, step_id, "model_audio", key, account.pseudonym)
    check = None
    if measured is not None:
        result = measured
        heard = sum(1 for w in result.words if w.status is not WordStatus.MISSED)
        total = len(result.words)
        ratio = heard / total if total else 0.0
        check = {
            "heard": heard,
            "total": total,
            "ratio": round(ratio, 3),
            "warning": (
                f"Máy chép giọng mẫu chỉ khớp {heard}/{total} từ của văn bản. Nghe lại bản ghi "
                "và đối chiếu văn bản trước khi xuất bản."
                if ratio < 0.8
                else ""
            ),
        }
    _audit(account, "lesson.model_audio", lesson_id, step_id)
    return {"media_key": key, "url": _media_url(key), "check": check}


@router.post(
    "/api/v1/teach/lessons/{lesson_id}/steps/{step_id}/image",
    tags=["teacher"],
    dependencies=[AUTHORING],
)
async def teach_image(
    lesson_id: str, step_id: str, image: UploadFile, account: Account = STAFF_ONLY
) -> dict:
    data, head = await _read_upload(image, MAX_IMAGE_BYTES)
    kind = _image_kind(head)
    if kind is None:
        raise HTTPException(415, "chỉ nhận ảnh png, jpg hoặc webp")
    blob_key = f"lesson-media-{lesson_id}-{step_id}-{_rand()}.{kind}"
    svc().blobs.put(blob_key, data)
    key = svc().lessons.add_media(
        lesson_id, "image", IMAGE_TYPES[kind], blob_key, account.pseudonym
    )
    _set_step_media(lesson_id, step_id, "image", key, account.pseudonym)
    return {"media_key": key, "url": _media_url(key)}


@router.get("/api/v1/teach/lessons/{lesson_id}/preview", tags=["teacher"])
def teach_preview_lesson(lesson_id: str, account: Account = STAFF_ONLY) -> dict:
    """The draft as a learner would see it, without progress. Nothing is stored."""
    lesson, meta = _draft_or_404(lesson_id)
    lessons_repo = svc().lessons
    unit = lessons_repo.unit(meta["unit_id"])
    path = lessons_repo.path(meta["path_id"])
    return {
        "lesson": _lesson_view(lesson),
        "version": meta["published_version"],
        "preview": True,
        "path": {"path_id": path["path_id"], "title": path["title"]},
        "unit": {
            "unit_id": unit["unit_id"],
            "title": unit["title"],
            "band": unit["band"],
            "topic": unit.get("topic"),
        },
        "progress": {
            "passed": 0,
            "total": len(lesson.steps),
            "free_done": False,
            "completed": False,
        },
        "latest": {},
        "passed_steps": [],
        "next_lesson": None,
    }


@router.post("/api/v1/teach/preview", tags=["teacher"])
async def teach_preview_attempt(
    audio: UploadFile,
    lesson_id: str = Form(...),
    step_id: str = Form(...),
    round: int | None = Form(None),  # noqa: A002
    account: Account = STAFF_ONLY,
) -> dict:
    """A teacher tries a draft step. The recording is measured and thrown away."""
    lesson, _ = _draft_or_404(lesson_id)
    step = lesson.step(step_id)
    if step is None:
        raise HTTPException(404, "không tìm thấy bước này")
    data, kind = await _read_audio(audio)

    # The speech service answers in seconds; waiting for it on the event loop
    # stalled every other request of this service meanwhile (D066).
    def measure_and_store() -> dict:
        limits = step.round_limits()
        round_index = min(max(round or 1, 1), len(limits)) if step.kind is StepKind.FREE else None
        result = _measure(step, data, kind, round_index, step.answers)
        return {
            "attempt_id": None,
            "result": result.model_dump(mode="json"),
            "audio_url": None,
            "preview": True,
        }

    return await run_in_threadpool(measure_and_store)


# ---------------------------------------------------------------- insights


@router.get("/api/v1/teach/insights", tags=["teacher"])
def teach_insights(
    request: Request, path_id: str | None = None, account: Account = STAFF_ONLY
) -> dict:
    """How the class moves through a path. Totals per lesson; no ranking of people. FR-49."""
    _plan_allows(PlanFeature.CLASS_INSIGHTS)
    lessons_repo = svc().lessons
    chosen = _choose_path(path_id, published_only=False)
    if chosen is None:
        return {"path": None, "lessons": [], "missed_words": [], "recent": []}
    outline = lessons_repo.outline(chosen["path_id"], published_only=True)
    order = [(item["lesson"], u) for u in outline for item in u["lessons"]]
    ids = [ls.lesson_id for ls, _ in order]
    rows = _in_view(account, lessons_repo.attempts(lesson_ids=ids))
    by_lesson: dict[str, list[dict]] = {}
    for r in rows:
        by_lesson.setdefault(r["lesson_id"], []).append(r)

    lessons_out = []
    missed: dict[str, dict] = {}
    for lesson, unit in order:
        mine = by_lesson.get(lesson.lesson_id, [])
        learners = sorted({r["account_id"] for r in mine})
        completed = 0
        for acc in learners:
            st = lesson_state(lesson, _infos([r for r in mine if r["account_id"] == acc]))
            completed += int(is_complete(lesson, st))
        steps = []
        for step in lesson.steps:
            tries = [r for r in mine if r["step_id"] == step.step_id]
            passed = sum(1 for r in tries if r["passed"])
            steps.append(
                {
                    "step_id": step.step_id,
                    "title": step.display_title,
                    "kind": step.kind.value,
                    "attempts": len(tries),
                    "learners": len({r["account_id"] for r in tries}),
                    "pass_rate": round(passed / len(tries), 3) if tries else None,
                }
            )
        tried = [s for s in steps if s["attempts"] >= 3 and s["pass_rate"] is not None]
        stall = min(tried, key=lambda s: s["pass_rate"]) if tried else None
        lessons_out.append(
            {
                "lesson_id": lesson.lesson_id,
                "title": lesson.title,
                "unit": unit["title"],
                "band": lesson.band.value,
                "learners": len(learners),
                "completed": completed,
                "attempts": len(mine),
                "steps": steps,
                "stall_step": stall["title"] if stall and stall["pass_rate"] < 0.6 else None,
            }
        )
        for r in mine:
            for word in r["result"].missed_words():
                key = word.lower()
                entry = missed.setdefault(key, {"word": word, "count": 0, "lessons": set()})
                entry["count"] += 1
                entry["lessons"].add(lesson.title)

    names = svc().peers.identity.display_names(account_ids=[r["account_id"] for r in rows[-60:]])
    titles = {ls.lesson_id: ls for ls, _ in order}
    recent = []
    for r in reversed(rows[-60:]):
        lesson = titles.get(r["lesson_id"])
        step = lesson.step(r["step_id"]) if lesson else None
        recent.append(
            {
                "attempt_id": r["attempt_id"],
                "learner": names.get(r["account_id"], "?"),
                "lesson": lesson.title if lesson else r["lesson_id"],
                "step": step.display_title if step else r["step_id"],
                "kind": step.kind.value if step else None,
                "round": r["round"],
                "passed": r["passed"],
                "teacher_reviewed": r["result"].teacher_reviewed,
                "created_at": r["created_at"],
            }
        )
    top = sorted(missed.values(), key=lambda e: (-e["count"], e["word"]))[:20]
    return {
        "path": {"path_id": chosen["path_id"], "title": chosen["title"]},
        "paths": [{"path_id": p["path_id"], "title": p["title"]} for p in lessons_repo.paths()],
        "lessons": lessons_out,
        "missed_words": [
            {"word": e["word"], "count": e["count"], "lessons": sorted(e["lessons"])} for e in top
        ],
        "recent": recent,
    }


def _in_view(account: Account, rows: list[dict]) -> list[dict]:
    """A teacher's figures count their classes' students only (D071); an admin's, everyone."""
    if account.role is Role.ADMIN:
        return rows
    mine = set(svc().peers.assessment.students_of(teacher_id=account.account_id))
    return [r for r in rows if r.get("account_id") in mine]


def _may_see(account: Account, owner_id: str) -> bool:
    """D071: the owner, an administrator, or a teacher of one of the owner's classes."""
    if owner_id == account.account_id or account.role is Role.ADMIN:
        return True
    return account.role is Role.TEACHER and bool(
        svc().peers.assessment.teaches(teacher_id=account.account_id, student_id=owner_id)
    )


@router.get("/api/v1/teach/attempts/{attempt_id}", tags=["teacher"])
def teach_attempt(attempt_id: str, request: Request, account: Account = STAFF_ONLY) -> dict:
    lessons_repo = svc().lessons
    try:
        row = lessons_repo.attempt(attempt_id)
    except NotFound:
        raise HTTPException(404, "không tìm thấy lượt luyện") from None
    if not _may_see(account, row["account_id"]):
        raise HTTPException(404, "không tìm thấy lượt luyện")
    found = lessons_repo.published(row["lesson_id"], row["lesson_version"])
    lesson = found[0] if found else None
    step = lesson.step(row["step_id"]) if lesson else None
    names = svc().peers.identity.display_names(account_ids=[row["account_id"]])
    name = names.get(row["account_id"], "?")
    return {
        **_attempt_view(row),
        "learner": name,
        "lesson": {"lesson_id": row["lesson_id"], "title": lesson.title if lesson else ""},
        "step": _step_view(step) if step else None,
        "overridden_by": row.get("overridden_by"),
        "overridden_at": row.get("overridden_at"),
        "machine_passed": row["machine_passed"],
        "override": row.get("override"),
    }


@router.post("/api/v1/teach/attempts/{attempt_id}/override", tags=["teacher"])
def teach_override(attempt_id: str, body: OverrideIn, account: Account = STAFF_ONLY) -> dict:
    """A teacher corrects the machine on one attempt. Never a score, never blocking. FR-49."""
    lessons_repo = svc().lessons
    try:
        row = lessons_repo.attempt(attempt_id)
    except NotFound:
        raise HTTPException(404, "không tìm thấy lượt luyện") from None
    if not _may_see(account, row["account_id"]):
        raise HTTPException(404, "không tìm thấy lượt luyện")
    valid = {m.index for m in row["result"].words}
    words = {i: s.value for i, s in body.words.items() if i in valid}
    override = {"words": words, "note": body.note}
    if body.passed is not None:
        override["passed"] = body.passed
    lessons_repo.set_override(attempt_id, override, account.pseudonym)
    _audit(
        account,
        "lesson.override",
        attempt_id,
        f"words={len(words)} passed={'' if body.passed is None else body.passed}",
    )
    return _attempt_view(lessons_repo.attempt(attempt_id))
