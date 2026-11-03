"""Say again the words the machine heard unclearly in a recording (D089, FR-97).

Only the learner who recorded a response practises from it, and only once it
has a score. The words are worked out from the stored transcript each time
(`lessons.drill.pick`); a take is measured by the speech service as a
read-aloud step and not kept -- the recording to listen to is the response's
own. A take where the word did not come through clearly sends it to spaced
review, the same Leitner boxes as a word missed in a lesson (D025).

D090: the words still open can be read in a passage written around them --
by the language model, paid by the learner once per set of words, or put
together from their own phrases for free. A reading counts as one take of
each word in it.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Literal

from fastapi import APIRouter, Form, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel

from aicefr.api.deps import STUDENT_ONLY
from aicefr.coach import passage as passages
from aicefr.coach.upgrade import UpgradeError
from aicefr.contracts import Word
from aicefr.lessons.drill import (
    DRILL_VERSION,
    PASS_STREAK,
    DrillWord,
    judge,
    judge_passage,
    passage_step,
    pick,
    step_for,
    unsure_share,
)
from aicefr.lessons.model import new_id
from aicefr.lessons.review import first_schedule
from aicefr.pronunciation.vietnamese import PATTERN_NAMES, PATTERN_TIPS
from aicefr.services.core.learning.lessons_api import _measure, _now, _read_audio, _today, svc
from aicefr.storage.auth_repository import Account
from aicefr.storage.drill_repository import DrillPassage, PassageTake, WordDrill

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


# ================================================================= reading passages (D090)


def _passage_words(account: Account) -> list[WordDrill]:
    """The open drills a passage is written for: the latest, one per spelling, at most five."""
    chosen: list[WordDrill] = []
    for d in _drills().open_words(account.account_id):
        if d.word not in {c.word for c in chosen}:
            chosen.append(d)
        if len(chosen) == passages.MAX_WORDS:
            break
    return chosen


def _band(account: Account) -> str:
    latest = svc().peers.assessment.latest_assessment(account_id=account.account_id)
    return passages.band_of((latest or {}).get("band"))


def _daily_left(account: Account) -> int:
    since = (_now() - timedelta(days=1)).isoformat(timespec="seconds")
    used = _drills().model_passages_since(account.account_id, since)
    return max(0, svc().passage_daily - used)


@router.get("/api/v1/learn/passage", tags=["student"])
def passage_state(account: Account = STUDENT_ONLY) -> dict:
    """The words a passage would be written for, the one already written, and the offer."""
    chosen = _passage_words(account)
    ids = [d.drill_id for d in chosen]
    kept = _drills().passage_for(account.account_id, ids) if chosen else None
    return {
        "words": [{**d.view(), "phrase": d.phrase} for d in chosen],
        "min_words": passages.MIN_WORDS,
        "enough": len(chosen) >= passages.MIN_WORDS,
        "passage": kept.view() if kept else None,
        "offer": svc().peers.assessment.passage_offer(),
        "daily_left": _daily_left(account),
        "pass_streak": PASS_STREAK,
    }


class PassageIn(BaseModel):
    # "model": written by the language model, paid; "phrases": the learner's own, free.
    source: Literal["model", "phrases"] = "model"
    # A new passage even when one was written for these words already.
    fresh: bool = False


@router.post("/api/v1/learn/passage", tags=["student"])
def make_passage(body: PassageIn, account: Account = STUDENT_ONLY) -> dict:
    """A passage for the open words: the one kept for them, or a new one."""
    drills = _drills()
    chosen = _passage_words(account)
    if len(chosen) < passages.MIN_WORDS:
        raise HTTPException(
            409, f"cần ít nhất {passages.MIN_WORDS} từ đang luyện dở để viết đoạn đọc"
        )
    ids = [d.drill_id for d in chosen]
    words = [d.word for d in chosen]
    kept = drills.passage_for(account.account_id, ids)
    if kept is not None and not body.fresh and kept.source == body.source:
        return kept.view()
    passage_id = new_id("p")
    band = _band(account)
    if body.source == "phrases":
        try:
            made = passages.from_phrases([d.phrase for d in chosen], words)
        except UpgradeError as e:  # pragma: no cover - each phrase holds its word
            raise HTTPException(409, str(e)) from e
        saved = DrillPassage(passage_id, account.account_id, band, words, ids, made.text, "phrases")
        return drills.save_passage(saved).view()
    if _daily_left(account) <= 0:
        raise HTTPException(
            429, f"mỗi ngày AI viết được tối đa {svc().passage_daily} đoạn cho bạn, hãy thử lại sau"
        )
    written = svc().peers.assessment.write_passage(
        account_id=account.account_id, band=band, words=words, key=f"passage-{passage_id}"
    )
    if "refused" in written:
        raise HTTPException(int(written.get("status") or 502), written["refused"])
    saved = DrillPassage(
        passage_id,
        account.account_id,
        band,
        words,
        ids,
        written["text"],
        "model",
        provider=written.get("provider"),
        model=written.get("model"),
        prompt_version=written.get("prompt_version"),
        input_tokens=written.get("input_tokens"),
        output_tokens=written.get("output_tokens"),
    )
    svc().audit_log.write(account.account_id, "drill.passage", passage_id, f"words={len(words)}")
    return drills.save_passage(saved).view()


@router.post("/api/v1/learn/passage/{passage_id}/takes", tags=["student"])
async def passage_take(passage_id: str, audio: UploadFile, account: Account = STUDENT_ONLY) -> dict:
    """Read the passage aloud: one take of each of its words."""
    drills = _drills()
    found = drills.passage(account.account_id, passage_id)
    if found is None:
        raise HTTPException(404, "không tìm thấy đoạn đọc này")
    data, kind = await _read_audio(audio)

    def measure_and_record() -> dict:
        result = _measure(passage_step(found.text, found.words), data, kind, None, None)
        verdicts = judge_passage(result, passages.places(found.text, found.words))
        out: dict = {
            "measured": result.measured,
            "transcript": result.transcript,
            "tip": result.tip,
            "marks": [m.model_dump(mode="json") for m in result.words],
            "words": [],
        }
        if not result.measured:
            return out  # nothing heard, or not English: read it again, nothing counts
        by_word = {d.word: d for d in drills.by_ids(account.account_id, found.drill_ids)}
        due = first_schedule(_today()).due
        for word in found.words:
            verdict = verdicts[word]
            item: dict = {
                "word": word,
                "passed": verdict.passed,
                "said": verdict.said,
                "pattern_name": PATTERN_NAMES[verdict.pattern] if verdict.pattern else None,
                "pattern_tip": PATTERN_TIPS[verdict.pattern] if verdict.pattern else None,
                "review_due": None,
                "drill": None,
            }
            d = by_word.get(word)
            if d is not None:  # a drill erased since: the reading still shows, nothing to count
                made = drills.record(
                    account.account_id, d.response_id, d.word, d.word_index, d.phrase,
                    verdict.passed, verdict.said,
                )  # fmt: skip
                item["drill"] = made.view()
                if not verdict.passed:
                    svc().lessons.schedule(
                        account.account_id, "word", "", "", d.word, due, drill_id=d.drill_id
                    )
                    item["review_due"] = due.isoformat()
            out["words"].append(item)
        clear = [w["word"] for w in out["words"] if w["passed"]]
        unclear = [w["word"] for w in out["words"] if not w["passed"]]
        take = PassageTake(clear=clear, unclear=unclear, created_at=_now().isoformat())
        drills.record_passage_take(account.account_id, passage_id, take)
        return out

    return await run_in_threadpool(measure_and_record)
