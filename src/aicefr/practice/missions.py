"""Evidence-linked, deterministic rule checks for practice missions."""

from __future__ import annotations

from collections.abc import Sequence

from aicefr.contracts import AsrStatus, Transcript
from aicefr.lessons.text import normalize_text, same_word
from aicefr.practice.contracts import (
    MissionGoal,
    MissionKind,
    MissionMeasurement,
    PracticeMission,
    PracticePurpose,
    PracticeReason,
    PracticeResult,
    PracticeStatus,
    TimeSpan,
    WordEvidence,
)
from aicefr.practice.rules import MISSION_RULES_VERSION, SUPPORTED_MISSION_RULES_VERSIONS

RULES_VERSION = MISSION_RULES_VERSION
VAD_SLACK_S = 0.3
MIN_CONFIDENCE = 0.5
_FILLERS = frozenset({"uh", "um", "erm", "ah", "hmm", "well"})
_IRREGULAR_PAST = frozenset(
    (
        "was were went had did saw made came took got gave found thought told became left felt "
        "brought began kept held wrote stood heard met ran paid sat spoke led grew lost fell "
        "sent built understood drew broke spent drove bought wore chose sang swam ate drank slept "
        "woke won taught caught sold fought flew forgot hid rode rang shook threw knew meant said"
    ).split()
)
_NOT_PAST_ED = frozenset(
    "bed red shed speed seed feed need indeed hundred sacred naked wicked kindred interested "
    "excited tired bored worried surprised married scared confused amazed pleased satisfied "
    "crowded talented related based detailed limited skilled".split()
)
_MODALS = frozenset({"will", "would", "can", "could", "might", "may", "should"})


class _Token:
    __slots__ = ("text", "source_index", "confidence", "start_s", "end_s")

    def __init__(
        self,
        text: str,
        source_index: int | None,
        confidence: float | None,
        start_s: float | None,
        end_s: float | None,
    ) -> None:
        self.text = text
        self.source_index = source_index
        self.confidence = confidence
        self.start_s = start_s
        self.end_s = end_s


def _overlap(word_start: float, word_end: float, spans: Sequence[TimeSpan]) -> bool:
    return any(
        word_start < span.end_s + VAD_SLACK_S and word_end > span.start_s - VAD_SLACK_S
        for span in spans
    )


def _tokens(transcript: Transcript, vad_spans: Sequence[TimeSpan]) -> tuple[list[_Token], bool]:
    """Return normalized heard tokens and whether any text confidence is uncertain.

    Timed token indices remain positions in the original transcript.words tuple;
    words rejected by VAD are omitted without renumbering later evidence.
    """
    out: list[_Token] = []
    uncertain = False
    if transcript.words:
        for source_index, word in enumerate(transcript.words):
            if not _overlap(word.start_s, word.end_s, vad_spans):
                continue
            if word.prob is None or word.prob < MIN_CONFIDENCE:
                uncertain = True
            for token in normalize_text(word.text):
                out.append(_Token(token, source_index, word.prob, word.start_s, word.end_s))
    else:
        uncertain = bool(transcript.text.strip())
        for token in normalize_text(transcript.text):
            out.append(_Token(token, None, None, None, None))
    return out, uncertain


def _evidence(tokens: Sequence[_Token]) -> tuple[WordEvidence, ...]:
    spans: list[WordEvidence] = []
    indices = sorted({token.source_index for token in tokens if token.source_index is not None})
    for index in indices:
        assert index is not None
        spans.append(WordEvidence(start_word_index=index, end_word_index=index + 1))
    return tuple(spans)


def _text_measurement(
    goal: MissionGoal,
    value: float,
    tokens: Sequence[_Token],
    uncertain: bool,
    evidence_tokens: Sequence[_Token] = (),
) -> MissionMeasurement:
    status = (
        PracticeStatus.UNSURE
        if uncertain
        else (PracticeStatus.PASS if value >= goal.target else PracticeStatus.FAIL)
    )
    return MissionMeasurement(
        goal_id=goal.goal_id,
        measured_value=None if uncertain else value,
        target=goal.target,
        status=status,
        evidence=_evidence(evidence_tokens),
    )


def _phrase_hits(tokens: Sequence[_Token], phrases: Sequence[str]) -> list[_Token]:
    found: list[_Token] = []
    words = [token.text for token in tokens]
    for phrase in phrases:
        expected = normalize_text(phrase)
        for start in range(len(words) - len(expected) + 1):
            if all(
                same_word(words[start + offset], token) for offset, token in enumerate(expected)
            ):
                found.extend(tokens[start : start + len(expected)])
                break
    return found


def _past_verbs(tokens: Sequence[_Token]) -> list[_Token]:
    seen: set[str] = set()
    hits: list[_Token] = []
    for token in tokens:
        word = token.text
        regular = len(word) >= 4 and word.endswith("ed") and word not in _NOT_PAST_ED
        if (word in _IRREGULAR_PAST or regular) and word not in seen:
            hits.append(token)
            seen.add(word)
    return hits


def _conditional_hits(tokens: Sequence[_Token]) -> list[_Token]:
    found: list[_Token] = []
    words = [token.text for token in tokens]
    for index, token in enumerate(tokens):
        if token.text != "if":
            continue
        left, right = max(0, index - 12), min(len(tokens), index + 13)
        if any(words[j] in _MODALS for j in range(left, right) if j != index):
            found.append(token)
    return found


def _read_aloud_hits(goal: MissionGoal, tokens: Sequence[_Token]) -> tuple[float, list[_Token]]:
    from aicefr.lessons.align import AlignmentOp, align

    reference = normalize_text(goal.reference_text or "")
    if not reference:
        return 0.0, [], False
    alignment = align(reference, [token.text for token in tokens])
    pairs = [
        pair
        for pair in alignment.pairs
        if pair.operation in (AlignmentOp.MATCH, AlignmentOp.SUBSTITUTE)
        and same_word(reference[pair.ref_index], tokens[pair.hyp_index].text)
        if pair.hyp_index is not None
    ]
    evidence = [tokens[pair.hyp_index] for pair in pairs if pair.hyp_index is not None]
    lemma_equivalent = any(pair.operation is AlignmentOp.SUBSTITUTE for pair in pairs)
    return len(pairs) / len(reference), evidence, lemma_equivalent


def _measure_goal(
    goal: MissionGoal,
    tokens: Sequence[_Token],
    uncertain: bool,
    vad_spans: Sequence[TimeSpan],
    transcript: Transcript,
) -> MissionMeasurement:
    if goal.kind is MissionKind.SPEAK_SECONDS:
        value = max(span.end_s for span in vad_spans) - min(span.start_s for span in vad_spans)
        status = PracticeStatus.PASS if value >= goal.target else PracticeStatus.FAIL
        return MissionMeasurement(
            goal_id=goal.goal_id,
            measured_value=value,
            target=goal.target,
            status=status,
            time_evidence=tuple(vad_spans),
        )
    if goal.kind is MissionKind.MAX_PAUSE:
        ordered = sorted(vad_spans, key=lambda span: (span.start_s, span.end_s))
        gaps = [
            (right.start_s - left.end_s, left.end_s)
            for left, right in zip(ordered, ordered[1:], strict=False)
        ]
        value = max((gap for gap, _ in gaps), default=0.0)
        biggest = max(gaps, default=(0.0, 0.0))
        status = PracticeStatus.PASS if value <= goal.target else PracticeStatus.FAIL
        evidence = (
            (TimeSpan(start_s=biggest[1], end_s=biggest[1] + value),)
            if len(ordered) >= 2 and value > 0
            else ()
        )
        return MissionMeasurement(
            goal_id=goal.goal_id,
            measured_value=value,
            target=goal.target,
            status=status,
            time_evidence=evidence,
        )
    if transcript.status is not AsrStatus.OK or not tokens:
        return MissionMeasurement(
            goal_id=goal.goal_id,
            measured_value=None,
            target=goal.target,
            status=PracticeStatus.UNMEASURED,
        )
    if goal.kind is MissionKind.USE_WORDS:
        hits = _phrase_hits(tokens, goal.words)
        return _text_measurement(goal, float(len(hits)), tokens, uncertain, hits)
    if goal.kind is MissionKind.UNIQUE_WORDS:
        unique = {token.text: token for token in tokens if token.text not in _FILLERS}
        return _text_measurement(
            goal, float(len(unique)), tokens, uncertain, tuple(unique.values())
        )
    if goal.kind is MissionKind.PAST_VERBS:
        hits = _past_verbs(tokens)
        return _text_measurement(goal, float(len(hits)), tokens, uncertain, hits)
    if goal.kind is MissionKind.CONDITIONALS:
        hits = _conditional_hits(tokens)
        return _text_measurement(goal, float(len(hits)), tokens, uncertain, hits)
    if goal.kind is MissionKind.READ_ALOUD:
        value, hits, lemma_equivalent = _read_aloud_hits(goal, tokens)
        if lemma_equivalent:
            return MissionMeasurement(
                goal_id=goal.goal_id,
                measured_value=None,
                target=goal.target,
                status=PracticeStatus.UNSURE,
                evidence=_evidence(hits),
                reason=PracticeReason.LEMMA_EQUIVALENT,
            )
        return _text_measurement(goal, value, tokens, uncertain, hits)
    raise ValueError(f"no rule for {goal.kind.value}")


class MissionChecker:
    """Measure catalogue goals using VAD and ASR evidence without scoring speech."""

    rules_version = RULES_VERSION

    def check(
        self,
        mission: PracticeMission,
        transcript: Transcript,
        vad_spans: Sequence[TimeSpan],
        *,
        purpose: PracticePurpose = PracticePurpose.PRACTICE,
    ) -> PracticeResult:
        if mission.rules_version not in SUPPORTED_MISSION_RULES_VERSIONS:
            raise ValueError(f"unsupported mission rules version: {mission.rules_version}")
        duration = max(
            (span.end_s for span in vad_spans),
            default=transcript.words[-1].end_s if transcript.words else 0.0,
        )
        speaking_s = _vad_union_duration(vad_spans)
        if not vad_spans:
            measurements = tuple(
                MissionMeasurement(
                    goal_id=goal.goal_id,
                    measured_value=None,
                    target=goal.target,
                    status=PracticeStatus.UNMEASURED,
                )
                for goal in mission.goals
            )
            return PracticeResult(
                mission_id=mission.mission_id,
                purpose=purpose,
                status=PracticeStatus.UNMEASURED,
                measurements=measurements,
                rules_version=mission.rules_version,
                reasons=(PracticeReason.NO_SPEECH,),
                word_count=len(transcript.words),
                audio_duration_s=duration,
            )
        tokens, uncertain = _tokens(transcript, vad_spans)
        measurements = tuple(
            _measure_goal(goal, tokens, uncertain, vad_spans, transcript) for goal in mission.goals
        )
        statuses = {item.status for item in measurements}
        status = (
            PracticeStatus.FAIL
            if PracticeStatus.FAIL in statuses
            else PracticeStatus.UNSURE
            if PracticeStatus.UNSURE in statuses
            else PracticeStatus.UNMEASURED
            if PracticeStatus.UNMEASURED in statuses
            else PracticeStatus.PASS
        )
        reasons: list[PracticeReason] = []
        if any(item.status is PracticeStatus.UNMEASURED for item in measurements):
            reasons.append(PracticeReason.TRANSCRIPT_UNAVAILABLE)
        if uncertain and any(item.status is PracticeStatus.UNSURE for item in measurements):
            reasons.append(PracticeReason.LOW_ASR_CONFIDENCE)
        reasons.extend(
            item.reason
            for item in measurements
            if item.reason is not None and item.reason not in reasons
        )
        return PracticeResult(
            mission_id=mission.mission_id,
            purpose=purpose,
            status=status,
            measurements=measurements,
            rules_version=mission.rules_version,
            reasons=tuple(reasons),
            word_count=len(transcript.words),
            audio_duration_s=duration,
            speaking_s=speaking_s,
        )


def _vad_union_duration(spans: Sequence[TimeSpan]) -> float:
    """Count total active VAD time without double-counting overlapping spans."""
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
    return total
