"""La chan hop le (D022): ngon ngu khac, nghi lac de, nghi doc lai de bai."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from aicefr.asr.fake import FakeAsrEngine
from aicefr.asr.vad import EnergyVad
from aicefr.asr.whisper_adapter import WhisperEngine
from aicefr.contracts import ProcessingRequest, ReasonCode, Status
from aicefr.features.relevance import (
    MIN_WORDS_FOR_OFF_TOPIC,
    is_english,
    keyword_relevance,
    prompt_copy_ratio,
    validity_flags,
)
from aicefr.pipeline import ResponseProcessor
from aicefr.storage.task_repository import DEFAULT_TOPIC_KEYWORDS, TaskRepository

FOOTBALL = (
    "my favourite football team is manchester united and i watch every match on "
    "saturday night with my friends we cheer loudly when the striker scores a goal "
    "and we argue about the referee after the game the stadium is huge and the fans "
    "sing songs for ninety minutes"
)
EXAM = (
    "when i prepare for an exam i first make a schedule then i review my notes every "
    "morning and practise old questions finally i sleep early the night before the "
    "test so that my mind is fresh and i can remember the material"
)


@dataclass(frozen=True)
class FakeTask:
    prompt_text: str
    topic_keywords: tuple[str, ...]


P4 = FakeTask(
    prompt_text="Hãy mô tả một quy trình bạn quen thuộc.",
    topic_keywords=tuple(k.strip() for k in DEFAULT_TOPIC_KEYWORDS["P4"].split(",")),
)


@pytest.fixture
def request_obj() -> ProcessingRequest:
    return ProcessingRequest(
        response_id="r1",
        speaker_id="SV-001",
        task_id="P4",
        audio_path="khong-dung-den.wav",
        prompt_version="v1",
        config_version="v1",
    )


# ------------------------------------------------------------------ cac phep do


def test_spelling_and_inflection_variants_match() -> None:
    assert keyword_relevance("my favorite places", ("favourite", "place")) == 1.0
    assert keyword_relevance("i travelled a lot", ("travel",)) == 1.0


def test_an_open_prompt_has_no_relevance_check() -> None:
    assert keyword_relevance(FOOTBALL, ()) is None


def test_vietnamese_prompts_are_not_used_for_copy_detection() -> None:
    assert not is_english("Hãy mô tả một quy trình bạn quen thuộc, ví dụ cách bạn chuẩn bị.")
    assert is_english("Describe a process you know well.")


def test_reading_the_prompt_aloud_scores_a_high_copy_ratio() -> None:
    prompt = "Describe a process you know well and explain each step in order."
    assert prompt_copy_ratio(prompt.lower(), prompt) == 1.0
    assert prompt_copy_ratio(EXAM, prompt) < 0.2


def test_an_on_topic_answer_raises_no_flag() -> None:
    assert validity_flags(EXAM, P4) == []


def test_a_long_off_topic_answer_is_flagged() -> None:
    assert len(FOOTBALL.split()) >= MIN_WORDS_FOR_OFF_TOPIC
    assert validity_flags(FOOTBALL, P4) == ["OFF_TOPIC_SUSPECTED"]


def test_a_short_answer_is_never_called_off_topic() -> None:
    """Bai A2 ngan khong du can cu de ket luan lac de."""
    short = " ".join(FOOTBALL.split()[: MIN_WORDS_FOR_OFF_TOPIC - 1])
    assert validity_flags(short, P4) == []


def test_reading_an_english_prompt_is_flagged() -> None:
    task = FakeTask(
        prompt_text="Describe a process you know well and explain each step in order please.",
        topic_keywords=(),
    )
    assert validity_flags(task.prompt_text.lower(), task) == ["PROMPT_COPY_SUSPECTED"]


# ------------------------------------------------------------------ pipeline


def _run(engine, request_obj, tone, sr, task=P4):
    return ResponseProcessor(engine, vad=EnergyVad(), task_lookup=lambda _tid: task).process(
        request_obj, tone, sr
    )


def test_speech_detected_as_vietnamese_is_not_scored(request_obj, tone, sr) -> None:
    r = _run(FakeAsrEngine(language="vi", language_probability=0.92), request_obj, tone, sr)
    assert r.status is Status.REVIEW_REQUIRED
    assert r.reasons == [ReasonCode.LANGUAGE_NOT_ENGLISH]
    assert r.assessment is None


def test_an_unsure_language_guess_does_not_block(request_obj, tone, sr) -> None:
    """Giong Viet noi tieng Anh co the lam may phan van; phan van thi khong chan."""
    r = _run(FakeAsrEngine(language="vi", language_probability=0.3), request_obj, tone, sr)
    assert ReasonCode.LANGUAGE_NOT_ENGLISH not in r.reasons


def test_no_language_information_means_no_language_flag(request_obj, tone, sr) -> None:
    r = _run(FakeAsrEngine(), request_obj, tone, sr)
    assert ReasonCode.LANGUAGE_NOT_ENGLISH not in r.reasons


def test_off_topic_keeps_the_score_and_goes_to_a_teacher(request_obj, tone, sr) -> None:
    on = _run(FakeAsrEngine(transcript=EXAM), request_obj, tone, sr)
    off = _run(FakeAsrEngine(transcript=FOOTBALL), request_obj, tone, sr)
    assert ReasonCode.OFF_TOPIC_SUSPECTED not in on.reasons
    assert ReasonCode.OFF_TOPIC_SUSPECTED in off.reasons
    assert off.status is Status.REVIEW_REQUIRED
    if off.assessment is not None and off.assessment.overall_0_6 is not None:
        # Khong tru diem: co chi la co.
        assert off.assessment.overall_0_6 > 0


def test_without_a_task_lookup_the_shield_is_skipped(request_obj, tone, sr) -> None:
    r = ResponseProcessor(FakeAsrEngine(transcript=FOOTBALL), vad=EnergyVad()).process(
        request_obj, tone, sr
    )
    assert ReasonCode.OFF_TOPIC_SUSPECTED not in r.reasons


def test_a_failing_language_detector_does_not_break_recognition(monkeypatch) -> None:
    import numpy as np

    engine = WhisperEngine(backend="ct2", model="tiny")

    def boom(_pcm):
        raise RuntimeError("model hong")

    monkeypatch.setattr(engine, "_ct2_language", boom)
    assert engine.detect_language(np.zeros(16_000, dtype=np.float32)) is None


# ------------------------------------------------------------------ du lieu de bai


def test_default_tasks_carry_topic_keywords(tmp_path) -> None:
    repo = TaskRepository(tmp_path / "t.db")
    assert repo.get("P3").topic_keywords and repo.get("P4").topic_keywords
    assert repo.get("P5").topic_keywords == ()


def test_keywords_an_admin_edited_are_kept(tmp_path) -> None:
    db = tmp_path / "t.db"
    TaskRepository(db).col("task").update_one(
        {"task_id": "P4"}, {"$set": {"topic_keywords": "robot, factory"}}
    )
    assert TaskRepository(db).get("P4").topic_keywords == ("robot", "factory")
