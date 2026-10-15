"""Versioned lexical/3-gram validity shields with bounded word-index evidence."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Protocol

from aicefr.contracts import Word
from aicefr.trust.contracts import (
    EvidenceSpan,
    GuardDecision,
    GuardEvidence,
    GuardKind,
)

MIN_WORDS_FOR_OFF_TOPIC = 30
MIN_WORDS_FOR_COPY = 10
MIN_WORDS = MIN_WORDS_FOR_COPY
COPY_RATIO_FLAG = 0.5
THRESHOLD_VERSION = "lexical-3gram-d022-v1"
_TOKEN_RE = re.compile(r"[a-z]+(?:'[a-z]+)?")


class TaskLike(Protocol):
    prompt_text: str
    topic_keywords: tuple[str, ...]


def _tokens(text: str) -> list[str]:
    return [token.casefold() for token in _TOKEN_RE.findall(text.casefold())]


def _ngrams(tokens: Sequence[str], size: int = 3) -> set[tuple[str, ...]]:
    if len(tokens) < size:
        return set()
    return {tuple(tokens[index : index + size]) for index in range(len(tokens) - size + 1)}


def _stem(word: str) -> str:
    word = word.replace("our", "or")
    for suffix in ("ing", "ed", "s"):
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            word = word[: -len(suffix)]
            break
    if len(word) >= 4 and word[-1] == word[-2]:
        word = word[:-1]
    if len(word) >= 4 and word.endswith("e"):
        word = word[:-1]
    return word


def _is_english(text: str, threshold: float = 0.9) -> bool:
    letters = [char for char in text if char.isalpha()]
    return bool(letters) and sum(char.isascii() for char in letters) / len(letters) >= threshold


def _spans_for_prompt_runs(
    prompt: Sequence[str], response: Sequence[str], *, max_spans: int = 8
) -> tuple[EvidenceSpan, ...]:
    spans: list[EvidenceSpan] = []
    prompt_ngrams = _ngrams(prompt)
    if not prompt_ngrams:
        return ()
    start: int | None = None
    end = 0
    for index in range(min(max(0, len(response) - 2), 4998)):
        if tuple(response[index : index + 3]) in prompt_ngrams:
            if start is None:
                start = index
            end = index + 3
        elif start is not None:
            spans.append(EvidenceSpan(start_word=start, end_word=end))
            start = None
            if len(spans) >= max_spans:
                break
    if start is not None and len(spans) < max_spans:
        spans.append(EvidenceSpan(start_word=start, end_word=end))
    return tuple(spans)


class ValidityShield:
    """Detects suspicion only; returned evidence never modifies assessment scores."""

    def __init__(self, *, min_words: int = MIN_WORDS) -> None:
        if type(min_words) is not int or min_words < 1:
            raise ValueError("min_words must be a positive integer")
        self.min_words = min_words

    def evaluate(
        self,
        task: str | TaskLike | Mapping[str, object],
        transcript: str | Sequence[Word],
        *,
        min_words: int | None = None,
    ) -> tuple[GuardEvidence, ...]:
        if isinstance(task, str):
            prompt, keywords = task, ()
        elif isinstance(task, Mapping):
            prompt_value = task.get("prompt_text", "")
            keyword_value = task.get("topic_keywords", ())
            prompt = prompt_value if isinstance(prompt_value, str) else ""
            keywords = (
                tuple(value for value in keyword_value if isinstance(value, str))
                if isinstance(keyword_value, Sequence)
                and not isinstance(keyword_value, (str, bytes))
                else ()
            )
        else:
            prompt, keywords = task.prompt_text, task.topic_keywords
        prompt_tokens = _tokens(prompt)
        response_tokens = (
            _tokens(transcript)
            if isinstance(transcript, str)
            else _tokens(" ".join(word.text for word in transcript))
        )
        required_words = self.min_words if min_words is None else min_words
        if type(required_words) is not int or required_words < 1:
            raise ValueError("min_words must be a positive integer")
        if not prompt_tokens:
            return (
                GuardEvidence(
                    kind=GuardKind.OFF_TOPIC,
                    value=0.0,
                    threshold_version=THRESHOLD_VERSION,
                    decision=GuardDecision.INSUFFICIENT_EVIDENCE,
                ),
                GuardEvidence(
                    kind=GuardKind.PROMPT_READING,
                    value=0.0,
                    threshold_version=THRESHOLD_VERSION,
                    decision=GuardDecision.INSUFFICIENT_EVIDENCE,
                ),
            )

        response_grams = [
            tuple(response_tokens[index : index + 3])
            for index in range(max(0, len(response_tokens) - 2))
        ]
        prompt_grams = _ngrams(prompt_tokens)
        copied_grams = [gram for gram in response_grams if gram in prompt_grams]
        copy_ratio = len(copied_grams) / len(response_grams) if response_grams else 0.0
        copy_spans = _spans_for_prompt_runs(prompt_tokens, response_tokens)
        wanted = {_stem(keyword.lower()) for keyword in keywords if keyword.strip()}
        said = {_stem(token) for token in response_tokens}
        keyword_ratio = len(wanted & said) / len(wanted) if wanted else None
        off_topic_suspected = keyword_ratio == 0.0 and len(response_tokens) >= max(
            self.min_words, MIN_WORDS_FOR_OFF_TOPIC
        )
        off_topic_spans = (
            (EvidenceSpan(start_word=0, end_word=min(len(response_tokens), 10)),)
            if off_topic_suspected
            else ()
        )
        prompt_copy_suspected = (
            _is_english(prompt)
            and len(response_tokens) >= MIN_WORDS_FOR_COPY
            and copy_ratio >= COPY_RATIO_FLAG
        )
        return (
            GuardEvidence(
                kind=GuardKind.OFF_TOPIC,
                value=0.0 if keyword_ratio is None else keyword_ratio,
                threshold_version=THRESHOLD_VERSION,
                spans=off_topic_spans,
                decision=(
                    GuardDecision.SUSPECTED
                    if off_topic_suspected
                    else (
                        GuardDecision.INSUFFICIENT_EVIDENCE
                        if keyword_ratio is None
                        or len(response_tokens) < max(self.min_words, MIN_WORDS_FOR_OFF_TOPIC)
                        else GuardDecision.CLEAR
                    )
                ),
            ),
            GuardEvidence(
                kind=GuardKind.PROMPT_READING,
                value=copy_ratio,
                threshold_version=THRESHOLD_VERSION,
                spans=copy_spans if prompt_copy_suspected else (),
                decision=(
                    GuardDecision.SUSPECTED
                    if prompt_copy_suspected
                    else (
                        GuardDecision.INSUFFICIENT_EVIDENCE
                        if not _is_english(prompt) or len(response_tokens) < MIN_WORDS_FOR_COPY
                        else GuardDecision.CLEAR
                    )
                ),
            ),
        )


__all__ = ["ValidityShield", "THRESHOLD_VERSION"]
