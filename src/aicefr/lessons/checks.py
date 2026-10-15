"""Confidence-aware step evaluation with persistent token-level evidence locators."""

from __future__ import annotations

import math
from collections.abc import Sequence

from aicefr.contracts import AsrStatus, Transcript
from aicefr.lessons.align import MAX_ALIGNMENT_TOKENS, AlignmentOp, align
from aicefr.lessons.model import (
    MAX_STEP_SPEAKING_SECONDS,
    FreePayload,
    GapPayload,
    KeywordsPayload,
    LessonStep,
    LookUpPayload,
    OutlinePayload,
    PicturePayload,
    ReadAloudPayload,
    RepeatPayload,
    StarterPayload,
    StepEvidenceOperation,
    StepEvidenceState,
    StepResult,
    StepResultStatus,
)
from aicefr.lessons.rules import SUPPORTED_LESSON_RULES_VERSIONS
from aicefr.lessons.text import normalize_text, same_word
from aicefr.practice.contracts import TimeSpan

VAD_SLACK_S = 0.3
MIN_CONFIDENCE = 0.5
MAX_ASR_TEXT_CHARS = 32_768
MAX_ASR_WORD_TEXT_CHARS = 1_024


class _HeardToken:
    __slots__ = ("text", "source_index", "prob", "start_s", "end_s")

    def __init__(
        self,
        text: str,
        source_index: int | None,
        prob: float | None,
        start_s: float | None,
        end_s: float | None,
    ) -> None:
        self.text, self.source_index, self.prob = text, source_index, prob
        self.start_s, self.end_s = start_s, end_s


def _heard(transcript: Transcript, spans: Sequence[TimeSpan]) -> list[_HeardToken]:
    result: list[_HeardToken] = []
    if transcript.words:
        if len(transcript.words) > MAX_ALIGNMENT_TOKENS:
            raise ValueError(f"ASR transcript is limited to {MAX_ALIGNMENT_TOKENS} words")
        for index, word in enumerate(transcript.words):
            if len(word.text) > MAX_ASR_WORD_TEXT_CHARS:
                raise ValueError(
                    f"ASR word text is limited to {MAX_ASR_WORD_TEXT_CHARS} characters"
                )
            if not any(
                word.start_s < span.end_s + VAD_SLACK_S and word.end_s > span.start_s - VAD_SLACK_S
                for span in spans
            ):
                continue
            tokens = normalize_text(word.text)
            if len(result) + len(tokens) > MAX_ALIGNMENT_TOKENS:
                raise ValueError(f"ASR hypothesis is limited to {MAX_ALIGNMENT_TOKENS} tokens")
            result.extend(
                _HeardToken(token, index, word.prob, word.start_s, word.end_s) for token in tokens
            )
    else:
        if len(transcript.text) > MAX_ASR_TEXT_CHARS:
            raise ValueError(f"ASR transcript text is limited to {MAX_ASR_TEXT_CHARS} characters")
        tokens = normalize_text(transcript.text)
        if len(tokens) > MAX_ALIGNMENT_TOKENS:
            raise ValueError(f"ASR hypothesis is limited to {MAX_ALIGNMENT_TOKENS} tokens")
        result.extend(_HeardToken(token, None, None, None, None) for token in tokens)
    return result


def _step_evidence(reference: Sequence[str], heard: Sequence[_HeardToken]):
    alignment = align(reference, [token.text for token in heard])
    evidence = []
    states: list[StepEvidenceState] = []
    for pair in alignment.pairs:
        expected = reference[pair.ref_index]
        token = heard[pair.hyp_index] if pair.hyp_index is not None else None
        if pair.operation is AlignmentOp.DELETE:
            operation = StepEvidenceOperation.DELETE
            # ASR gives no confidence for an absent word; absence is uncertainty.
            state = StepEvidenceState.UNSURE
        else:
            assert token is not None
            operation = (
                StepEvidenceOperation.MATCH
                if pair.operation is AlignmentOp.MATCH
                else StepEvidenceOperation.SUBSTITUTE
            )
            if token.prob is None or token.prob < MIN_CONFIDENCE:
                state = StepEvidenceState.UNSURE
            elif same_word(expected, token.text) and token.text != expected:
                # Lemma-equivalent substitutions are evidence, not a wrong answer.
                state = StepEvidenceState.UNSURE
            elif operation is StepEvidenceOperation.MATCH and token.text == expected:
                state = StepEvidenceState.HEARD
            else:
                state = StepEvidenceState.MISSED
        evidence.append(
            {
                "reference_index": pair.ref_index,
                "source_word_index": token.source_index if token is not None else None,
                "expected_token": expected,
                "heard_token": token.text if token is not None else None,
                "operation": operation,
                "confidence": token.prob if token is not None else None,
                "state": state,
            }
        )
        states.append(state)
    for hyp_index in alignment.inserted_indices:
        token = heard[hyp_index]
        state = (
            StepEvidenceState.UNSURE
            if token.prob is None or token.prob < MIN_CONFIDENCE
            else StepEvidenceState.HEARD
        )
        evidence.append(
            {
                "reference_index": len(reference),
                "source_word_index": token.source_index,
                "expected_token": "",
                "heard_token": token.text,
                "operation": StepEvidenceOperation.INSERT,
                "confidence": token.prob,
                "state": state,
            }
        )
        states.append(state)
    if StepEvidenceState.UNSURE in states:
        status = StepResultStatus.UNSURE
    elif StepEvidenceState.MISSED in states:
        status = StepResultStatus.FAIL
    else:
        status = StepResultStatus.PASS
    return status, evidence, states


def _result(
    step: LessonStep,
    status: StepResultStatus,
    heard: Sequence[_HeardToken],
    *,
    evidence: Sequence[dict] = (),
    target: int | None = None,
    round_index: int | None = None,
    round_count: int | None = None,
    elapsed_seconds: float | None = None,
    speaking_s: float = 0.0,
    time_evidence: Sequence[TimeSpan] = (),
    feedback: str = "Đã ghi nhận lượt luyện tập.",
    transcript_word_count: int = 0,
) -> StepResult:
    matched = sum(
        item["state"] is StepEvidenceState.HEARD
        and item["operation"] is StepEvidenceOperation.MATCH
        for item in evidence
    )
    return StepResult(
        step_id=step.step_id,
        kind=step.kind,
        status=status,
        rules_version=step.rules_version,
        heard_text=" ".join(token.text for token in heard),
        matched_count=matched if evidence else None,
        target_count=target,
        evidence=tuple(evidence),
        round_index=round_index,
        round_count=round_count,
        elapsed_seconds=elapsed_seconds,
        speaking_s=speaking_s,
        time_evidence=tuple(time_evidence),
        word_count=transcript_word_count,
        feedback=feedback,
    )


def _phrase_evidence(phrase: Sequence[str], heard: Sequence[_HeardToken]):
    """Return token evidence for an exact contiguous answer phrase, if present."""
    words = [token.text for token in heard]
    for start in range(len(words) - len(phrase) + 1):
        if all(
            same_word(expected, words[start + offset]) for offset, expected in enumerate(phrase)
        ):
            evidence = []
            uncertain = False
            for offset, expected in enumerate(phrase):
                token = heard[start + offset]
                variant = token.text != expected
                unsure = variant or token.prob is None or token.prob < MIN_CONFIDENCE
                uncertain |= unsure
                evidence.append(
                    {
                        "reference_index": offset,
                        "source_word_index": token.source_index,
                        "expected_token": expected,
                        "heard_token": token.text,
                        "operation": StepEvidenceOperation.MATCH,
                        "confidence": token.prob,
                        "state": StepEvidenceState.UNSURE if unsure else StepEvidenceState.HEARD,
                    }
                )
            return evidence, uncertain
    return None


def _active_duration(spans: Sequence[TimeSpan]) -> float:
    """Measure VAD union duration so overlapping intervals are not double-counted."""
    intervals = sorted((span.start_s, span.end_s) for span in spans)
    total = 0.0
    start: float | None = None
    end = 0.0
    for left, right in intervals:
        if start is None:
            start, end = left, right
        elif left <= end:
            end = max(end, right)
        else:
            total += end - start
            start, end = left, right
    if start is not None:
        total += end - start
    if total > MAX_STEP_SPEAKING_SECONDS:
        raise ValueError(f"VAD speech duration exceeds {MAX_STEP_SPEAKING_SECONDS} seconds")
    return total


def evaluate_step(
    step: LessonStep,
    transcript: Transcript,
    vad_spans: Sequence[TimeSpan],
    *,
    round_index: int | None = None,
    elapsed_seconds: float | None = None,
) -> StepResult:
    """Evaluate one attempt; no speech is unmeasured, never a failed answer."""
    if step.rules_version not in SUPPORTED_LESSON_RULES_VERSIONS:
        raise ValueError(f"unsupported lesson rules version: {step.rules_version}")
    word_count = len(transcript.words)
    speaking_s = _active_duration(vad_spans)
    if elapsed_seconds is not None and (
        speaking_s > elapsed_seconds or any(span.end_s > elapsed_seconds for span in vad_spans)
    ):
        raise ValueError("VAD speech evidence exceeds the supplied clip duration")
    if not vad_spans:
        return _result(
            step,
            StepResultStatus.UNMEASURED,
            (),
            feedback="Chưa phát hiện lời nói để đo.",
            transcript_word_count=word_count,
            speaking_s=speaking_s,
        )
    heard = _heard(transcript, vad_spans)
    if not heard or transcript.status is not AsrStatus.OK:
        return _result(
            step,
            StepResultStatus.UNMEASURED,
            heard,
            feedback="Chưa có bản nhận dạng đủ tin cậy để đo.",
            transcript_word_count=word_count,
            speaking_s=speaking_s,
        )
    payload = step.payload
    if isinstance(payload, (ReadAloudPayload, RepeatPayload, LookUpPayload)):
        reference = normalize_text(payload.text)
        status, evidence, _states = _step_evidence(reference, heard)
        return _result(
            step,
            status,
            heard,
            evidence=evidence,
            target=len(reference),
            feedback="Có từ chưa chắc; hãy nghe lại."
            if StepResultStatus.UNSURE is status
            else "Đã đối chiếu với câu mẫu.",
            transcript_word_count=word_count,
            speaking_s=speaking_s,
        )
    if isinstance(payload, GapPayload):
        answers = [normalize_text(answer) for answer in payload.answers]
        matches = [match for answer in answers if (match := _phrase_evidence(answer, heard))]
        if not matches:
            if answers:
                _alignment_status, evidence, states = _step_evidence(answers[0], heard)
                # A missing expected word has no ASR confidence of its own, so a
                # partial answer is uncertain. Interleaved or confidently wrong
                # words still fail the exact-phrase rule.
                status = (
                    StepResultStatus.UNSURE
                    if StepEvidenceState.UNSURE in states
                    else StepResultStatus.FAIL
                )
            else:
                status, evidence = StepResultStatus.FAIL, []
        else:
            evidence, uncertain = max(
                matches,
                key=lambda item: sum(row["state"] is StepEvidenceState.HEARD for row in item[0]),
            )
            status = StepResultStatus.UNSURE if uncertain else StepResultStatus.PASS
        return _result(
            step,
            status,
            heard,
            evidence=evidence,
            target=1,
            feedback="Đã kiểm tra trọn vẹn từ/cụm từ trả lời.",
            transcript_word_count=word_count,
            speaking_s=speaking_s,
        )
    if isinstance(payload, KeywordsPayload):
        evidence, hits = [], 0
        uncertain = False
        for index, keyword in enumerate(payload.keywords):
            phrase = normalize_text(keyword)
            match = _phrase_evidence(phrase, heard)
            if match:
                hits += 1
                rows, unsure = match
                uncertain |= unsure
                evidence.extend({**row, "reference_index": index} for row in rows)
        if len([token for token in heard]) < payload.min_words:
            status = StepResultStatus.FAIL
        elif uncertain:
            status = StepResultStatus.UNSURE
        else:
            status = (
                StepResultStatus.PASS if hits == len(payload.keywords) else StepResultStatus.FAIL
            )
        return _result(
            step,
            status,
            heard,
            evidence=evidence,
            target=len(payload.keywords),
            feedback="Đã kiểm tra từ khóa và độ dài câu trả lời.",
            transcript_word_count=word_count,
            speaking_s=speaking_s,
        )
    if isinstance(payload, StarterPayload):
        prefix = normalize_text(payload.starter)
        status, evidence, _ = _step_evidence(prefix, heard[: len(prefix)])
        enough = len(heard) >= payload.min_words
        if status is StepResultStatus.UNSURE:
            final_status = StepResultStatus.UNSURE
        else:
            final_status = (
                StepResultStatus.PASS
                if status is StepResultStatus.PASS and enough
                else StepResultStatus.FAIL
            )
        return _result(
            step,
            final_status,
            heard,
            evidence=evidence,
            target=1,
            feedback="Đã kiểm tra khung câu và số từ.",
            transcript_word_count=word_count,
            speaking_s=speaking_s,
        )
    if isinstance(payload, PicturePayload):
        status = StepResultStatus.PASS if len(heard) >= payload.min_words else StepResultStatus.FAIL
        evidence = [
            {
                "reference_index": index,
                "source_word_index": token.source_index,
                "expected_token": "",
                "heard_token": token.text,
                "operation": StepEvidenceOperation.INSERT,
                "confidence": token.prob,
                "state": StepEvidenceState.UNSURE
                if token.prob is None or token.prob < MIN_CONFIDENCE
                else StepEvidenceState.HEARD,
            }
            for index, token in enumerate(heard)
        ]
        if any(item["state"] is StepEvidenceState.UNSURE for item in evidence):
            status = StepResultStatus.UNSURE
        return _result(
            step,
            status,
            heard,
            evidence=evidence,
            target=payload.min_words,
            feedback="Đã ghi nhận phần mô tả tranh.",
            transcript_word_count=word_count,
            speaking_s=speaking_s,
        )
    if isinstance(payload, OutlinePayload):
        spoken = sum(span.end_s - span.start_s for span in vad_spans)
        marker_evidence = []
        missing_marker = False
        for index, marker in enumerate(payload.markers):
            match = _phrase_evidence(normalize_text(marker), heard)
            if match:
                marker_evidence.extend({**row, "reference_index": index} for row in match[0])
            else:
                missing_marker = True
        enough = spoken >= payload.min_seconds and not missing_marker
        uncertain = any(row["state"] is StepEvidenceState.UNSURE for row in marker_evidence)
        status = (
            StepResultStatus.UNSURE
            if uncertain
            else (StepResultStatus.PASS if enough else StepResultStatus.FAIL)
        )
        return _result(
            step,
            status,
            heard,
            evidence=marker_evidence,
            target=len(payload.markers),
            feedback="Đã kiểm tra thời lượng nói và các từ nối.",
            transcript_word_count=word_count,
            speaking_s=speaking_s,
        )
    if isinstance(payload, FreePayload):
        if round_index is None or not 0 <= round_index < len(payload.rounds):
            raise ValueError("FREE evaluation requires a valid zero-based round_index")
        if elapsed_seconds is None or not math.isfinite(elapsed_seconds) or elapsed_seconds < 0:
            raise ValueError("FREE evaluation requires finite elapsed_seconds")
        budget = payload.rounds[round_index].duration_seconds
        if speaking_s < 1.0:
            status = StepResultStatus.UNMEASURED
        elif elapsed_seconds > budget:
            status = StepResultStatus.FAIL
        else:
            status = StepResultStatus.PASS
        return _result(
            step,
            status,
            heard,
            target=1,
            round_index=round_index,
            round_count=len(payload.rounds),
            elapsed_seconds=elapsed_seconds,
            speaking_s=speaking_s,
            time_evidence=vad_spans,
            feedback=f"Đã ghi nhận lượt {round_index + 1} trên {len(payload.rounds)}.",
            transcript_word_count=word_count,
        )
    raise TypeError(f"unsupported step payload {type(payload).__name__}")
