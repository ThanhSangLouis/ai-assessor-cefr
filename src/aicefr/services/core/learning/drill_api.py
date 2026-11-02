"""Say again the words the machine heard unclearly in a recording (D089, FR-97).

Only the learner who recorded a response practises from it, and only once it
has a score. The words are worked out from the stored transcript each time
(`lessons.drill.pick`); a take is measured by the speech service as a
read-aloud step and not kept -- the recording to listen to is the response's
own. A take where the word did not come through clearly sends it to spaced
review, the same Leitner boxes as a word missed in a lesson (D025).
"""

from __future__ import annotations

from fastapi import APIRouter, Form, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool

from aicefr.api.deps import STUDENT_ONLY
from aicefr.contracts import Word
from aicefr.lessons.drill import (
    DRILL_VERSION,
    PASS_STREAK,
    DrillWord,
    judge,
    pick,
    step_for,
    unsure_share,
)
from aicefr.lessons.review import first_schedule
from aicefr.pronunciation.vietnamese import PATTERN_NAMES, PATTERN_TIPS
from aicefr.services.core.learning.lessons_api import _measure, _read_audio, _today, svc
from aicefr.storage.auth_repository import Account

router = APIRouter()

NOTE = (
    "Từ màu cam là từ máy nghe chưa rõ, chưa chắc là bạn phát âm sai: tiếng ồn, nói nhanh hay "
    "từ hiếm cũng làm máy nghe kém đi. Giọng có chất Việt không bị coi là lỗi."
)


def _words(account: Account, response_id: str) -> list[Word]:
    source = svc().peers.assessment.drill_source(
        account_id=account.account_id, response_id=response_id
    )
    if source is None:
        raise HTTPException(404, "không tìm thấy bài này")
    return [Word.model_validate(w) for w in source["words"]]


def _drills():
    drills = svc().drills
    if drills is None:  # pragma: no cover - configured in app.build
        raise HTTPException(503, "chưa bật luyện lại từ")
    return drills


@router.get("/api/v1/learn/drill/{response_id}", tags=["student"])
def drill(response_id: str, account: Account = STUDENT_ONLY) -> dict:
    """The words to say again from this recording, each with where this learner is."""
    words = _words(account, response_id)
    done = _drills().of_response(account.account_id, response_id)
    blank = {"drill_id": None, "streak": 0, "passed": False, "takes": 0, "last_said": None}
    return {
        "response_id": response_id,
        "words": [
            {**d.view(), **(done[d.word].view() if d.word in done else blank)} for d in pick(words)
        ],
        "pass_streak": PASS_STREAK,
        "unsure_share": unsure_share(words),
        "version": DRILL_VERSION,
        "note": NOTE,
    }


@router.post("/api/v1/learn/drill/{response_id}/takes", tags=["student"])
async def drill_take(
    response_id: str,
    audio: UploadFile,
    word: str = Form(..., max_length=40),
    account: Account = STUDENT_ONLY,
) -> dict:
    """Say the phrase of one word again; clear twice in a row closes the word."""
    found: DrillWord | None = next(
        (d for d in pick(_words(account, response_id)) if d.word == word.strip().lower()), None
    )
    if found is None:
        raise HTTPException(404, "từ này không có trong danh sách luyện của bài")
    data, kind = await _read_audio(audio)

    # The speech service answers in seconds; not on the event loop (D066).
    def measure_and_record() -> dict:
        result = _measure(step_for(found), data, kind, None, None)
        verdict = judge(result, found.target)
        out: dict = {
            "measured": verdict.measured,
            "passed": verdict.passed,
            "said": verdict.said,
            "transcript": result.transcript,
            "tip": result.tip,
            "pattern_name": PATTERN_NAMES[verdict.pattern] if verdict.pattern else None,
            "pattern_tip": PATTERN_TIPS[verdict.pattern] if verdict.pattern else None,
            "review_due": None,
        }
        if not verdict.measured:
            return out  # nothing heard, or not English: say it again, nothing counts
        drills = _drills()
        made = drills.record(
            account.account_id,
            response_id,
            found.word,
            found.index,
            found.phrase,
            verdict.passed,
            verdict.said,
        )
        if not verdict.passed:
            due = first_schedule(_today()).due
            svc().lessons.schedule(
                account.account_id, "word", "", "", found.word, due, drill_id=made.drill_id
            )
            out["review_due"] = due.isoformat()
        out["drill"] = made.view()
        return out

    return await run_in_threadpool(measure_and_record)


@router.get("/api/v1/learn/drill", tags=["student"])
def my_drill_words(account: Account = STUDENT_ONLY) -> dict:
    """The words said again but not yet clear twice in a row, for the progress page."""
    drills = _drills()
    return {
        "open": [
            {**d.view(), "response_id": d.response_id, "phrase": d.phrase}
            for d in drills.open_words(account.account_id)
        ],
        **drills.counts(account.account_id),
        "pass_streak": PASS_STREAK,
    }
