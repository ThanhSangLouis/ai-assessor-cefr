from __future__ import annotations

from dataclasses import dataclass

import pytest

from aicefr.contracts import Word
from aicefr.features.relevance import THRESHOLD_VERSION, ValidityShield
from aicefr.trust.contracts import GuardDecision, GuardKind


@dataclass(frozen=True)
class Task:
    prompt_text: str
    topic_keywords: tuple[str, ...]


def test_empty_or_short_transcript_has_no_suspicion_and_no_spans() -> None:
    task = Task("Describe a process you know well.", ("process", "steps"))
    evidence = ValidityShield().evaluate(task, "short answer")
    assert [item.decision for item in evidence] == [
        GuardDecision.INSUFFICIENT_EVIDENCE,
        GuardDecision.INSUFFICIENT_EVIDENCE,
    ]
    assert all(not item.spans for item in evidence)


def test_long_off_topic_response_is_suspected_with_pinned_version() -> None:
    task = Task("Describe a process you know well.", ("process", "steps"))
    response = "football match team players goal stadium supporters " * 6
    evidence = ValidityShield().evaluate(task, response)
    off_topic = next(item for item in evidence if item.kind is GuardKind.OFF_TOPIC)
    assert off_topic.decision is GuardDecision.SUSPECTED
    assert off_topic.threshold_version == THRESHOLD_VERSION
    assert off_topic.value == 0.0
    assert off_topic.spans and off_topic.spans[0].start_word == 0


def test_reading_english_prompt_emits_only_bounded_index_spans() -> None:
    prompt = "Describe a process you know well and explain each step in order."
    task = Task(prompt, ())
    evidence = ValidityShield().evaluate(task, f"{prompt} {prompt}")
    reading = next(item for item in evidence if item.kind is GuardKind.PROMPT_READING)
    assert reading.decision is GuardDecision.SUSPECTED
    assert reading.spans
    assert all(0 <= span.start_word < span.end_word <= 5000 for span in reading.spans)
    assert THRESHOLD_VERSION == "lexical-3gram-d022-v1"


def test_vietnamese_prompt_is_not_used_for_copy_detection_and_no_topic_keywords_abstains() -> None:
    task = Task("Hãy mô tả một quy trình bạn quen thuộc.", ())
    response = " ".join(["today", "I", "talk", "about", "my", "daily", "routine"] * 5)
    evidence = ValidityShield().evaluate(task, response)
    assert evidence[0].decision is GuardDecision.INSUFFICIENT_EVIDENCE
    assert evidence[1].decision is GuardDecision.INSUFFICIENT_EVIDENCE


def test_on_topic_keyword_variants_clear_off_topic_guard() -> None:
    task = Task("Describe how you prepare a process.", ("process", "travel"))
    response = "I am travelling with my family and this process helps us plan every day " * 3
    evidence = ValidityShield().evaluate(task, response)
    assert evidence[0].value == 1.0
    assert evidence[0].decision is GuardDecision.CLEAR


def test_mapping_task_and_word_sequence_inputs_are_supported() -> None:
    task = {"prompt_text": "Describe a process you know well.", "topic_keywords": ["process"]}
    words = tuple(
        Word(text=token, start_s=index * 0.2, end_s=index * 0.2 + 0.1)
        for index, token in enumerate(
            "I explain a process I know well with many clear steps today".split()
        )
    )
    evidence = ValidityShield().evaluate(task, words)
    assert len(evidence) == 2
    assert evidence[0].decision is GuardDecision.INSUFFICIENT_EVIDENCE


def test_invalid_min_word_configuration_is_rejected() -> None:
    with pytest.raises(ValueError):
        ValidityShield(min_words=0)
    with pytest.raises(ValueError):
        ValidityShield().evaluate("Describe a process", "some words", min_words=True)


def test_prompt_without_english_words_and_open_prompt_abstain_safely() -> None:
    shield = ValidityShield()
    vietnamese = shield.evaluate("!!!", "today I will share an idea with my friend and teacher")
    short_english = shield.evaluate("Hi.", "today I will share an idea with my friend and teacher")
    assert all(item.decision is GuardDecision.INSUFFICIENT_EVIDENCE for item in vietnamese)
    assert short_english[0].decision is GuardDecision.INSUFFICIENT_EVIDENCE
    assert short_english[1].decision is GuardDecision.CLEAR


def test_copy_evidence_is_capped_at_eight_runs() -> None:
    prompt = "Describe a process you know well"
    task = Task(prompt, ())
    response = " um ".join([prompt] * 10)
    copy = ValidityShield().evaluate(task, response)[1]
    assert copy.decision is GuardDecision.SUSPECTED
    assert len(copy.spans) == 8
