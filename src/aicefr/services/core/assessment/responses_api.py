"""The student's side of the assessment service: submit, report, progress, practice, own data.

FR-01..FR-05, FR-27, FR-35, FR-38, D023 (practice), D042 (reliable change). Moved out of
the single application with D043; the rules are unchanged.
"""

from __future__ import annotations

import logging
import os
import tempfile
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, Depends, Form, HTTPException, Query, UploadFile
from fastapi import Response as HttpResponse
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse, JSONResponse

from aicefr.api.deps import require_login
from aicefr.api.schemas import QueueItem, SubmitResponse
from aicefr.audio.decoder import SNIFF_BYTES, sniff
from aicefr.contracts import (
    ProcessingRequest,
    ReasonCode,
    Response,
    ResponseStatus,
    TaskPurpose,
)
from aicefr.infra.blobs import audio_response
from aicefr.observability import count
from aicefr.practice.achievements import BY_CODE
from aicefr.practice.bank import CRITERION_NAMES
from aicefr.practice.feedback import previous_measures, takeaway
from aicefr.practice.missions import describe_measure
from aicefr.practice.streak import summarize
from aicefr.qc import audio_qc
from aicefr.research.reliable_change import reliable_change
from aicefr.scoring.band_map import position, thresholds_of
from aicefr.services.core.assessment import replay_api, scoring
from aicefr.services.core.assessment.context import (
    CONFIG_VERSION,
    active_model_name,
    can_view,
    measurement_error,
    svc,
)
from aicefr.storage.auth_repository import Account
from aicefr.storage.repository import InvalidStateError
from aicefr.storage.task_repository import Task

logger = logging.getLogger(__name__)
router = APIRouter()


# ================================================================= submit and read


@router.post("/api/v1/responses", response_model=SubmitResponse, tags=["student"])
async def submit_response(
    audio: UploadFile,
    response: HttpResponse,
    task_id: str = Form(...),
    account: Account = Depends(require_login),
) -> SubmitResponse:
    """Accept one audio file, queue it for scoring and return the response id right away.

    Returns HTTP 202 rather than 200: the response has only been accepted, it
    has no result yet.
    """
    s = svc()
    # The pseudonym comes from the session, never from the form: a form field
    # let a student submit under somebody else's pseudonym.
    speaker_id = account.pseudonym

    task = s.tasks.get(task_id)
    if task is None:
        raise HTTPException(422, "đề bài không tồn tại")

    rid = uuid.uuid4().hex[:12]

    # Stream the upload to a temporary file instead of reading it into memory:
    # counting while writing enforces the size limit against what has actually
    # arrived. The recording reaches the blob store (D051: disk or object
    # storage) only once it is known to be audio.
    head = b""
    written = 0
    fd, tmp_name = tempfile.mkstemp(prefix=f"aicefr-{rid}-", suffix=".part")
    os.close(fd)
    tmp_path = Path(tmp_name)
    try:
        with tmp_path.open("wb") as out:
            while chunk := await audio.read(256 * 1024):
                written += len(chunk)
                # AICEFR_MAX_UPLOAD, read where QC reads it: one source for the limit.
                if written > audio_qc.MAX_BYTES:
                    raise HTTPException(413, "file vượt quá 25 MiB")
                if len(head) < SNIFF_BYTES:
                    head += chunk[: SNIFF_BYTES - len(head)]
                out.write(chunk)
    except HTTPException:
        tmp_path.unlink(missing_ok=True)
        raise

    # Decide the format from the bytes, never from the name the browser sent.
    kind = sniff(head)
    if kind is None or written == 0:
        tmp_path.unlink(missing_ok=True)
        raise HTTPException(
            415, "không nhận ra định dạng audio. Hãy nộp file wav, flac, mp3, m4a hoặc webm"
        )

    # The rest -- the blob store, the database, the bus, the metering call --
    # blocks. Run on the event loop, it held every other request of this
    # service while one upload was being stored and queued (D066).
    def accept() -> SubmitResponse:
        # The stored name comes from the sniffed type, so the uploaded filename never
        # influences the path written to disk. It is also the recording's key in the
        # blob store the speech service reads from.
        audio_key = f"{rid}.{kind}"

        # D049: on the metered channel, hold what the longest recording the task
        # allows would cost; settled on the real length once there is a result.
        # Off (the school deployment, BR-29/BR-30) this always allows.
        metering = getattr(s.peers, "metering", None)
        action = task.purpose.value
        refusal = (
            metering.hold(
                account_id=account.account_id, action=action, key=rid, max_seconds=task.max_seconds
            )
            if metering is not None
            else None
        )
        if refusal:
            tmp_path.unlink(missing_ok=True)
            raise HTTPException(402, refusal)
        try:
            s.blobs.put(audio_key, tmp_path.read_bytes())
        finally:
            tmp_path.unlink(missing_ok=True)
        # What the response keeps: the file's path on disk, the bare key in object
        # storage (D051). `key_of` reads the key back out of either.
        local = s.blobs.local_path(audio_key)
        audio_ref = str(local) if local is not None else audio_key

        req = ProcessingRequest(
            response_id=rid,
            speaker_id=speaker_id,
            task_id=task_id,
            audio_path=audio_ref,
            prompt_version=task.prompt_version,
            config_version=CONFIG_VERSION,
        )

        # Persist immediately in the QUEUED state and reply, instead of waiting for
        # the pipeline to finish: AC-05.1 wants the 202 back in under 300 ms, while
        # NFR-01 allows the pipeline up to 60 seconds.
        s.repo.save(
            Response(
                response_id=rid,
                status=ResponseStatus.QUEUED,
                config_version=CONFIG_VERSION,
                prompt_version=req.prompt_version,
            ),
            speaker_id,
            task_id,
            account_id=account.account_id,
            audio_path=audio_ref,
            purpose=task.purpose,
        )
        count("submissions_total")
        try:
            scoring.dispatch(req, audio_key, task, account.account_id)
        except Exception as e:
            # The response is saved and nothing will score it: close it now rather
            # than leave the student watching a QUEUED page until the next restart.
            logger.exception("could not hand %s to the speech service", rid)
            s.repo.set_status(
                rid,
                ResponseStatus.FAILED,
                [ReasonCode.PROCESSING_INTERRUPTED],
                only_from=(ResponseStatus.QUEUED,),
            )
            scoring.settle_charge(rid)
            raise HTTPException(
                503, "chưa gửi được bài tới máy chấm, hãy nộp lại sau ít phút"
            ) from e

        response.status_code = 202
        return SubmitResponse(
            response_id=rid,
            status=ResponseStatus.QUEUED.value,
            message="Đã nhận bài, đang xử lý.",
        )

    return await run_in_threadpool(accept)


@router.get("/api/v1/responses/{response_id}", tags=["student"])
def get_report(response_id: str, account: Account = Depends(require_login)) -> JSONResponse:
    """Read the report of one response.

    FR-04: someone else's response returns 404, not 403. A 403 would confirm
    that the response exists, which still leaks information to a caller who has
    no right to it.
    """
    repo = svc().repo
    report = repo.get(response_id)
    owner = repo.owner_of(response_id)
    if report is None or not can_view(account, owner):
        raise HTTPException(404, "không tìm thấy bài này")
    out = report.model_dump(mode="json")
    a = out.get("assessment")
    if a and a.get("overall_0_6") is not None:
        a["band_position"] = position(a["overall_0_6"], a.get("overall_band"), _band_thresholds())
    return JSONResponse(out)


def _band_thresholds() -> dict[str, float]:
    """The band boundaries of the model in force (D059)."""
    from aicefr.scoring.scorer import load_model

    return thresholds_of(load_model(active_model_name()).get("band_thresholds"))


@router.delete("/api/v1/responses/{response_id}", tags=["student"])
def delete_my_response(response_id: str, account: Account = Depends(require_login)) -> dict:
    """A student deletes one of their own recordings. FR-35.

    Ownership is checked before anything else, and a response belonging to
    someone else answers **404, not 403**: 403 would confirm that the id exists.
    The everyday case -- one bad recording somebody wants gone -- must not wait
    on a request to staff.
    """
    repo = svc().repo
    if repo.owner_of(response_id) != account.account_id:
        raise HTTPException(404, "không tìm thấy bài này")
    try:
        deleted = repo.erase_one_response(response_id, account.account_id)
    except InvalidStateError as e:
        # 409, not 403: the request is well formed and the caller is entitled to
        # it; the response is simply in a state that no longer accepts deletion.
        raise HTTPException(409, str(e)) from e
    if not deleted:
        raise HTTPException(404, "không tìm thấy bài này")
    if svc().replays is not None:
        svc().replays.forget_response(response_id)
    return {"deleted": response_id}


@router.get("/api/v1/responses/{response_id}/audio", tags=["student"])
def get_audio(response_id: str, account: Account = Depends(require_login)) -> FileResponse:
    """Play back the recording. Needed by FR-24: clicking a piece of evidence seeks to it.

    The permission check is identical to the report endpoint: the audio must not
    become a side door to data the report already blocks. A voice identifies a
    person, so every access is audited.
    """
    repo = svc().repo
    if not can_view(account, repo.owner_of(response_id)):
        raise HTTPException(404, "không tìm thấy bài này")
    repo.write_audit(account.account_id, "AUDIO_ACCESS", response_id, None)
    # The returned filename uses the response id, not the original name:
    # AC-02.4 forbids keeping a name that usually holds a real name.
    return audio_response(svc().blobs, repo.audio_path_of(response_id), f"{response_id}.wav")


@router.get("/api/v1/responses/{response_id}/status", tags=["student"])
def response_status(response_id: str, account: Account = Depends(require_login)) -> dict:
    """A lightweight status for the progress page to poll. FR-05."""
    repo = svc().repo
    status_info = repo.status_of(response_id)
    if status_info is None or not can_view(account, repo.owner_of(response_id)):
        raise HTTPException(404, "không tìm thấy bài này")
    status_info["is_pending"] = ResponseStatus(status_info["status"]).is_pending
    return status_info


@router.get("/api/v1/me/responses", response_model=list[QueueItem], tags=["student"])
def my_responses(
    account: Account = Depends(require_login),
    limit: int = Query(200, ge=1, le=500),
) -> list[QueueItem]:
    """The caller's own responses. Serves FR-04."""
    return [QueueItem(**r) for r in svc().repo.list_by_account(account.account_id, limit)]


@router.get("/api/v1/tasks", tags=["student"])
def list_tasks(account: Account = Depends(require_login)) -> list[dict]:
    """Speaking prompts a student can answer, each with its band. FR-01, D076."""
    return [
        {
            "task_id": t.task_id,
            "title": t.title,
            "prompt_text": t.prompt_text,
            "prompt_version": t.prompt_version,
            "band": t.band.value if t.band else None,
            "min_seconds": t.min_seconds,
            "max_seconds": t.max_seconds,
        }
        for t in svc().tasks.list_active()
    ]


# ================================================================= own data


@router.get("/api/v1/me/profile.json", tags=["student"])
def speaking_profile(account: Account = Depends(require_login)) -> JSONResponse:
    """Export the learner's own verified results. FR-38.

    Only teacher-verified rows. If none exist the array is empty and the note
    says so: never guess a band to fill the file.
    """
    rows = svc().repo.speaking_profile(account.account_id)
    return JSONResponse(
        {
            "pseudonym": account.pseudonym,
            "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
            "results": rows,
            "note": (
                "Kết quả này là ước lượng do hệ thống hỗ trợ tạo ra nhằm phục vụ đánh giá "
                "quá trình. Đây không phải chứng chỉ CEFR và không được dùng làm căn cứ duy "
                "nhất cho bất kỳ quyết định học vụ nào. Giảng viên là người quyết định cuối cùng."
                if rows
                else "Chưa có kết quả nào được giảng viên xác nhận."
            ),
        },
        headers={"Content-Disposition": 'attachment; filename="speaking_profile.json"'},
    )


# FR-34. Two things make this different from "dump the tables": a `fields`
# block saying what each piece of data is FOR, and it is the student's own
# export, reachable without asking an administrator.
FIELD_PURPOSES: dict[str, str] = {
    "speaker_id": "Bút danh gắn bài nói với tài khoản. Không chứa họ tên hay MSSV.",
    "response_id": "Mã bài nói, dùng để tra cứu và để xoá đúng bản ghi khi bạn yêu cầu.",
    "task_id": "Đề bài đã nói, để so sánh các bài cùng đề.",
    "status": "Trạng thái xử lý của bài.",
    "created_at": "Thời điểm nộp, dùng để áp chính sách lưu trữ 12 tháng.",
    "overall_0_6": "Điểm ước lượng của hệ thống trên thang 0-6.",
    "overall_band": "Band ước lượng A1–C2. Không phải chứng chỉ.",
    "teacher_verified": "Giảng viên đã xác nhận kết quả này hay chưa.",
    "model_version": "Phiên bản mô hình đã chấm bài, để truy lại khi kết quả bị nghi ngờ.",
    "transcript": "Bản chép lời do máy nhận dạng, dùng để trích bằng chứng.",
    "features": "Các số đo trích từ bản ghi (nhịp nói, ngừng nghỉ, từ vựng).",
    "evidence": "Các đoạn cụ thể trong bản ghi dùng làm căn cứ cho nhận xét.",
    "comments": "Nhận xét sinh từ số đo, mỗi câu kèm bằng chứng.",
    "priorities": "Gợi ý luyện tập, xếp theo mức ảnh hưởng tới điểm.",
    "review_history": "Mỗi lần giảng viên sửa điểm: trước, sau, lý do, thời điểm.",
    "practice": "Kết quả luyện tập: từng mục tiêu đo được gì, kèm chỗ trong bản ghi"
    " làm căn cứ. Bài luyện tập không có điểm và không chuyển giảng viên.",
    "audio": "Tệp ghi âm KHÔNG nằm trong tệp này vì kích thước; tải riêng ở"
    " /api/v1/responses/{id}/audio.",
    "achievements": "Thành tựu bạn đã đạt và ngày đạt. Chỉ bạn thấy, không dựa vào điểm,"
    " không dùng để xếp hạng; xoá dữ liệu là xoá luôn.",
    "replay_labels": "Câu trả lời của bạn khi nghe lại bài của mình (D056): đoạn nào, bạn thấy"
    " đoạn đó thế nào, bạn định nói gì. Hiện lại cho bạn trên trang Tiến độ; chỉ được phân tích"
    " khi bạn cho phép dùng cho nghiên cứu; xoá dữ liệu là xoá luôn.",
    "learning_plans": "Lộ trình riêng bạn đã nhờ hệ thống ghép: mục tiêu bạn nhập và các bài"
    " được chọn. Chỉ dùng để hiện trên trang Luyện tập; xoá dữ liệu là xoá luôn.",
}


@router.get("/api/v1/me/export.json", tags=["student"])
def export_my_data(account: Account = Depends(require_login)) -> JSONResponse:
    """Everything the system holds about the caller, and what it is used for.

    Lesson attempts and achievements come from the learning service (D043);
    the export is still one file.
    """
    s = svc()
    responses = []
    for row in s.repo.list_by_account(account.account_id):
        report = s.repo.get(row["response_id"])
        if report is None:
            continue
        item = report.model_dump(mode="json")
        item["created_at"] = row["created_at"]
        item["task_id"] = row["task_id"]
        item["review_history"] = [
            r.model_dump(mode="json") for r in s.repo.review_history(row["response_id"])
        ]
        responses.append(item)

    lesson_attempts = [
        {
            k: a[k]
            for k in (
                "attempt_id",
                "lesson_id",
                "lesson_version",
                "step_id",
                "round",
                "created_at",
                "result",
            )
        }
        for a in s.peers.learning.attempts(account_id=account.account_id)
    ]
    achievements = s.peers.learning.achievements(account_id=account.account_id)
    s.repo.write_audit(account.pseudonym, "export.personal", None, f"responses={len(responses)}")
    return JSONResponse(
        {
            "exported_at": datetime.now(UTC).isoformat(timespec="seconds"),
            "speaker_id": account.pseudonym,
            "fields": FIELD_PURPOSES,
            "response_count": len(responses),
            "responses": responses,
            "lesson_attempt_count": len(lesson_attempts),
            "lesson_attempts": lesson_attempts,
            "learning_plans": s.peers.learning.plans_of(account_id=account.account_id),
            "replay_labels": replay_api.my_labels(account.account_id) if s.replays else [],
            "achievements": [
                {
                    "code": code,
                    "title": BY_CODE[code].title if code in BY_CODE else code,
                    "unlocked_at": stored["unlocked_at"],
                    "seen_at": stored["seen_at"],
                }
                for code, stored in achievements.items()
            ],
        },
        headers={"Content-Disposition": 'attachment; filename="du-lieu-cua-toi.json"'},
    )


# ================================================================= progress (FR-27, D042)

# Below this many results there is no trend to speak of, only two points and a
# line drawn between them.
MIN_RESULTS_FOR_TREND = 5


@router.get("/api/v1/me/progress", tags=["student"])
def my_progress(account: Account = Depends(require_login)) -> dict:
    """The learner's own results in time order, with the trend named plainly. FR-27.

    The trend is the difference between the first and last third of the series,
    and it is reported only from five results onward: two attempts a week apart
    differ by measurement noise as much as by learning (`ridge_resp_v2` has an
    RMSE of 0.53 on its own validation data).
    """
    from aicefr.report.habits import NAMES as HABIT_NAMES
    from aicefr.report.habits import habit_series
    from aicefr.scoring.scorer import load_model

    # The instrument's own error, read from the artifact rather than typed in
    # twice: retrain the model and the bar for calling something progress moves
    # with it.
    rmse = float(load_model(active_model_name()).get("cv_rmse") or 0.53)

    rows = svc().repo.progress_series(account.account_id)
    scores = [r["overall_0_6"] for r in rows if r["overall_0_6"] is not None]

    trend: dict = {"direction": "chua_du_du_lieu", "delta": None, "note": ""}
    if len(scores) >= MIN_RESULTS_FOR_TREND:
        cut = max(1, len(scores) // 3)
        delta = (sum(scores[-cut:]) / cut) - (sum(scores[:cut]) / cut)
        if abs(delta) < rmse:
            trend = {
                "direction": "chua_ro",
                "delta": round(delta, 2),
                "note": (
                    f"Thay đổi {delta:+.2f} điểm còn nhỏ hơn sai số của chính mô hình"
                    f" (RMSE {rmse:.2f}), nên chưa kết luận được là tiến bộ hay chưa."
                ),
            }
        else:
            trend = {
                "direction": "tang" if delta > 0 else "giam",
                "delta": round(delta, 2),
                "note": (
                    f"Trung bình {cut} bài gần nhất so với {cut} bài đầu:"
                    f" {delta:+.2f} điểm. Vẫn là ước lượng của máy, không phải kết quả thi."
                ),
            }
    else:
        trend["note"] = (
            f"Cần ít nhất {MIN_RESULTS_FOR_TREND} bài có điểm mới nói được về xu hướng."
            f" Hiện có {len(scores)} bài."
        )

    error = measurement_error()
    change = reliable_change(scores, error["sem"] if error else None)
    change["sem_source"] = error["source"] if error else None
    change["sem_pairs"] = error.get("pairs") if error else None

    limits = _band_thresholds()
    for r in rows:
        r["band_position"] = (
            position(r["overall_0_6"], r.get("overall_band"), limits)
            if r["overall_0_6"] is not None
            else None
        )
    return {
        "pseudonym": account.pseudonym,
        "band_thresholds": limits,
        "results": rows,
        "verified_count": sum(1 for r in rows if r["teacher_verified"]),
        "trend": trend,
        "reliable_change": change,
        # D070: the habits the next-band targets name, over the same assessments.
        "habits": habit_series(svc().repo.feature_series(account.account_id, HABIT_NAMES)),
        "note": (
            "Điểm chưa được giảng viên xác nhận chỉ là ước lượng của máy."
            " Biểu đồ vẽ cả hai loại nhưng phân biệt rõ."
        ),
    }


# ================================================================= practice (D023)


@dataclass(frozen=True)
class TaskProgress:
    """How far a learner has got with one practice task."""

    attempts: int = 0
    completed: bool = False
    last_attempt_at: str | None = None
    last_completed: bool | None = None


def _practice_progress(attempts: list[dict]) -> dict[str, TaskProgress]:
    """Per-task progress from the attempts (oldest first). Only processed attempts count."""
    out: dict[str, TaskProgress] = {}
    for a in attempts:
        if a["status"] != ResponseStatus.COMPLETED.value:
            continue
        prev = out.get(a["task_id"], TaskProgress())
        out[a["task_id"]] = TaskProgress(
            attempts=prev.attempts + 1,
            completed=prev.completed or a["completed"] is True,
            last_attempt_at=a["created_at"],
            last_completed=a["completed"],
        )
    return out


def _task_card(t: Task, progress: dict[str, TaskProgress]) -> dict:
    p = progress.get(t.task_id, TaskProgress())
    return {
        "task_id": t.task_id,
        "title": t.title,
        "criterion": t.criterion.value if t.criterion else None,
        "criterion_name": CRITERION_NAMES.get(t.criterion, "") if t.criterion else "",
        "band": t.band.value if t.band else None,
        "status": "completed" if p.completed else ("tried" if p.attempts else "new"),
        "attempts": p.attempts,
    }


def _practice_state(account_id: str) -> tuple[list[Task], list[dict], dict[str, TaskProgress]]:
    bank = svc().tasks.list_active(TaskPurpose.PRACTICE)
    attempts = svc().repo.practice_attempts(account_id)
    return bank, attempts, _practice_progress(attempts)


def _daily_view(attempts: list[dict]) -> dict:
    d = summarize(
        [a["created_at"] for a in attempts if a["status"] == ResponseStatus.COMPLETED.value],
        datetime.now(UTC),
    )
    return {
        "today": d.today,
        "goal": d.goal,
        "goal_met": d.goal_met,
        "streak": d.streak,
        "practiced_today": d.practiced_today,
        "week": [{"date": day.isoformat(), "count": n} for day, n in d.week],
    }


@router.get("/api/v1/practice/attempts/{response_id}", tags=["student"])
def practice_attempt(response_id: str, account: Account = Depends(require_login)) -> dict:
    """One practice attempt's result, with the daily goal after it. D023.

    Only the owner may see it: a practice attempt is the learner's draft, not a
    submission for anyone to mark.
    """
    repo = svc().repo
    owner = repo.owner_of(response_id)
    info = repo.status_of(response_id)
    if info is None or owner != account.account_id or info["purpose"] != "practice":
        raise HTTPException(404, "không tìm thấy lần luyện này")
    report = repo.get(response_id)
    t = svc().tasks.get(info["task_id"])
    if report is None or t is None:
        raise HTTPException(404, "không tìm thấy lần luyện này")

    _, attempts, progress = _practice_state(account.account_id)
    result = report.practice
    # The previous processed attempt at the SAME task, submitted before this one:
    # found by position in the list (already in submission order), not by
    # comparing created_at -- two attempts in one second share it.
    position = next(
        (i for i, a in enumerate(attempts) if a["response_id"] == response_id), len(attempts)
    )
    earlier = [
        a
        for a in attempts[:position]
        if a["task_id"] == info["task_id"] and a["status"] == ResponseStatus.COMPLETED.value
    ]
    previous = repo.get(earlier[-1]["response_id"]) if earlier else None
    before = previous_measures(result, previous.practice if previous else None) if result else []
    return {
        "response_id": response_id,
        "status": info["status"],
        "is_pending": ResponseStatus(info["status"]).is_pending,
        "created_at": info["created_at"],
        "reasons": [r.value for r in report.reasons],
        "task": {
            **_task_card(t, progress),
            "prompt_text": t.prompt_text,
            "reference_text": t.reference_text,
        },
        "result": (
            {
                "completed": result.completed,
                "met_count": result.met_count,
                "total": len(result.checks),
                "rules_version": result.rules_version,
                "takeaway": takeaway(result, t.missions),
                "previous_response_id": earlier[-1]["response_id"] if earlier else None,
                "checks": [
                    {
                        **c.model_dump(mode="json"),
                        "measured_text": describe_measure(c),
                        "previous": prev,
                    }
                    for c, prev in zip(result.checks, before, strict=True)
                ],
            }
            if result
            else None
        ),
        "daily": _daily_view(attempts),
    }
