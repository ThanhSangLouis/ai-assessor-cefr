"""Measure each practice mission on one recording. D023.

Every rule here is a count the learner can redo by listening to the recording:
from which second to which second they spoke, where the longest silence was,
which words they used. No model, no weights, no hidden threshold. Each result
carries the places in the recording it rests on (`MissionHit`), so a sentence
like "you used 3 linking words" can always point at those three words and the
second each one starts.

Limits the learner must be told, and the result page tells them:

* The counts run on the MACHINE'S TRANSCRIPT. The recogniser may drop or
  rewrite words, so "not heard" can be the machine's fault, not the speaker's.
* Grammar missions only check whether the learner USED a structure; they do
  not mark it right or wrong. Whisper tends to correct grammar while
  transcribing, so counting errors on its transcript is wrong from the start.
* Silences are measured by VAD on the waveform, not by Whisper's timestamps
  (see `features/extract.py`: 92.7% of Whisper's inter-word gaps are 0).
"""

from __future__ import annotations

import difflib
from collections.abc import Sequence
from typing import Protocol

from aicefr.contracts import (
    MISSION_RULES_VERSION,
    Mission,
    MissionCheck,
    MissionHit,
    MissionKind,
    PracticeResult,
    ReasonCode,
    Transcript,
)
from aicefr.features.extract import FILLERS
from aicefr.formatting import vi_decimal as _num

# Cap on evidence per mission: enough for the learner to listen back, without
# turning the result page into a copy of the whole transcript.
MAX_HITS = 8

# Irregular simple-past verbs. Forms identical to the present (put, cut, let,
# read, set, hit, cost, hurt, shut, quit) are left out: a transcript cannot tell
# them apart, and counting them would reward a speaker using the present tense.
IRREGULAR_PAST = frozenset(
    """was were went had did saw made came took got gave found thought told became left
    felt brought began kept held wrote stood heard met ran paid sat spoke led grew lost
    fell sent built understood drew broke spent drove bought wore chose sang swam ate drank
    slept woke won taught caught sold fought flew forgot hid rode rang shook threw knew
    meant said""".split()
)

# Words ending in "-ed" that are not past verbs, or are adjectives common in the
# present tense ("I am interested"). Counting them would let a response in the
# present tense pass the past-tense mission.
ED_NOT_PAST = frozenset(
    """bed red shed speed seed feed need indeed hundred sacred naked wicked kindred
    interested excited tired bored worried surprised married scared confused amazed
    pleased satisfied crowded talented related based detailed limited skilled""".split()
)

MODALS = frozenset({"will", "would", "can", "could", "might", "may", "should", "'ll", "'d"})
# Largest distance, in words, between "if" and the modal verb of the other clause.
CONDITIONAL_WINDOW = 12

_STRIP = '.,?!;:"()[]{}…“”‘’«»'


class PracticeTaskLike(Protocol):
    """What the checker needs from a task: its id, its missions, its reference passage."""

    task_id: str
    missions: tuple[Mission, ...]
    reference_text: str | None


def normalize(text: str) -> list[str]:
    """Split text into lower-case words, stripping punctuation at both ends and splitting hyphens.

    Apostrophes inside a word ("don't", "I'll") are kept: that is one word.
    Hyphens are split because the recogniser writes "first-year" one time and
    "first year" the next; both spellings must give the same words, or the
    learner loses a word because of how the machine wrote it.
    """
    out: list[str] = []
    for raw in text.replace("’", "'").replace("‘", "'").lower().split():
        for part in raw.split("-"):
            tok = part.strip(_STRIP).strip("'")
            if tok:
                out.append(tok)
    return out


_SENTENCE_END = (".", "?", "!", "…")


def _timed_tokens(transcript: Transcript) -> list[tuple[str, float | None, int]]:
    """Each transcript word with its start second and the index of its sentence.

    A word split at a hyphen keeps the start of the original word. Sentences
    end at the full stop, question mark or exclamation mark the recogniser puts
    after a word: the conditional rule needs to know whether "would" is in the
    same sentence as "if".
    """
    raw = (
        [(w.text, w.start_s) for w in transcript.words]
        if transcript.words
        else [(t, None) for t in transcript.text.split()]
    )
    out: list[tuple[str, float | None, int]] = []
    sentence = 0
    for text, start in raw:
        out += [(tok, start, sentence) for tok in normalize(text)]
        if text.rstrip("\"”’')]").endswith(_SENTENCE_END):
            sentence += 1
    return out


def _speaking_span(segments: Sequence[tuple[float, float]], transcript: Transcript) -> float | None:
    """From the first speech to the last; silence at either end does not count."""
    if segments:
        return max(e for _, e in segments) - min(s for s, _ in segments)
    if transcript.words:
        return transcript.words[-1].end_s - transcript.words[0].start_s
    return None


def _longest_gap(segments: Sequence[tuple[float, float]]) -> tuple[float, float | None]:
    """The longest silence BETWEEN two speech segments, and the second it starts.

    Only gaps in the middle count: silence before the first word or after the
    last one is the learner not having started yet or having finished, not
    getting stuck.
    """
    seg = sorted(segments)
    best, at = 0.0, None
    for (_, prev_end), (next_start, _) in zip(seg, seg[1:], strict=False):
        gap = next_start - prev_end
        if gap > best:
            best, at = gap, prev_end
    return best, at


def _find_phrase(
    tokens: list[tuple[str, float | None, int]], phrase: list[str]
) -> tuple[bool, float | None]:
    n = len(phrase)
    words = [t for t, _, _ in tokens]
    for i in range(len(words) - n + 1):
        if words[i : i + n] == phrase:
            return True, tokens[i][1]
    return False, None


def _unmeasured(m: Mission, reason: ReasonCode) -> MissionCheck:
    return MissionCheck(kind=m.kind, label=m.label, target=m.target, reason=reason)


def _measured(m: Mission, value: float, met: bool, hits: list[MissionHit]) -> MissionCheck:
    return MissionCheck(
        kind=m.kind,
        label=m.label,
        target=m.target,
        measured=round(value, 3),
        met=met,
        hits=hits[:MAX_HITS],
    )


class MissionChecker:
    """Measure every mission of a practice task on the transcript and the VAD segments.

    It does not take a FeatureSet: missions need what features throw away --
    which segment, which word at which second -- while features keep only
    aggregate ratios.
    """

    rules_version = MISSION_RULES_VERSION

    def check(
        self,
        task: PracticeTaskLike,
        transcript: Transcript,
        segments: Sequence[tuple[float, float]],
    ) -> PracticeResult:
        tokens = _timed_tokens(transcript)
        checks = [self._one(m, task, transcript, tokens, segments) for m in task.missions]
        return PracticeResult(task_id=task.task_id, checks=checks, rules_version=self.rules_version)

    def _one(
        self,
        m: Mission,
        task: PracticeTaskLike,
        transcript: Transcript,
        tokens: list[tuple[str, float | None, int]],
        segments: Sequence[tuple[float, float]],
    ) -> MissionCheck:
        if m.kind is MissionKind.SPEAK_SECONDS:
            span = _speaking_span(segments, transcript)
            if span is None:
                return _unmeasured(m, ReasonCode.FEATURE_NOT_COMPUTABLE)
            return _measured(m, span, span >= m.target, [])

        if m.kind is MissionKind.MAX_PAUSE:
            if not segments:
                return _unmeasured(m, ReasonCode.FEATURE_NOT_COMPUTABLE)
            gap, at = _longest_gap(segments)
            hits = (
                [MissionHit(text=f"Khoảng lặng dài nhất {_num(gap)} giây", start_s=at)]
                if at is not None
                else []
            )
            return _measured(m, gap, gap <= m.target, hits)

        if m.kind is MissionKind.USE_WORDS:
            hits: list[MissionHit] = []
            for item in m.words:
                found, at = _find_phrase(tokens, normalize(item))
                if found:
                    hits.append(MissionHit(text=item, start_s=at))
            return _measured(m, len(hits), len(hits) >= m.target, hits)

        if m.kind is MissionKind.UNIQUE_WORDS:
            distinct = {t for t, _, _ in tokens if t not in FILLERS}
            return _measured(m, len(distinct), len(distinct) >= m.target, [])

        if m.kind is MissionKind.PAST_VERBS:
            seen: dict[str, float | None] = {}
            for tok, at, _ in tokens:
                if tok in seen:
                    continue
                regular = len(tok) >= 4 and tok.endswith("ed") and tok not in ED_NOT_PAST
                if tok in IRREGULAR_PAST or regular:
                    seen[tok] = at
            hits = [MissionHit(text=t, start_s=at) for t, at in seen.items()]
            return _measured(m, len(seen), len(seen) >= m.target, hits)

        if m.kind is MissionKind.CONDITIONALS:
            words = [t for t, _, _ in tokens]
            hits = []
            for i, (tok, at, sentence) in enumerate(tokens):
                if tok != "if":
                    continue
                lo, hi = max(0, i - CONDITIONAL_WINDOW), i + CONDITIONAL_WINDOW + 1
                around = [
                    w for j, (w, _, s) in enumerate(tokens[lo:hi], lo) if j != i and s == sentence
                ]
                if any(w in MODALS or w.endswith(("'ll", "'d")) for w in around):
                    snippet = " ".join(words[i : min(len(words), i + 8)])
                    hits.append(MissionHit(text=f"{snippet}…", start_s=at))
            return _measured(m, len(hits), len(hits) >= m.target, hits)

        if m.kind is MissionKind.READ_ALOUD:
            reference = normalize(task.reference_text or "")
            if not reference:
                return _unmeasured(m, ReasonCode.FEATURE_NOT_COMPUTABLE)
            said = [t for t, _, _ in tokens]
            sm = difflib.SequenceMatcher(a=reference, b=said, autojunk=False)
            covered = [False] * len(reference)
            for block in sm.get_matching_blocks():
                for k in range(block.a, block.a + block.size):
                    covered[k] = True
            ratio = sum(covered) / len(reference)
            missed: list[MissionHit] = []
            for word, ok in zip(reference, covered, strict=True):
                if not ok and all(h.text != word for h in missed):
                    missed.append(MissionHit(text=word))
            return _measured(m, ratio, ratio >= m.target, missed)

        raise ValueError(f"no rule measures mission {m.kind.value}")  # pragma: no cover


def describe_measure(check: MissionCheck) -> str:
    """A short sentence saying what was measured, shared by the result page and exports."""
    if check.measured is None:
        return "Chưa đo được"
    v = check.measured
    if check.kind is MissionKind.SPEAK_SECONDS:
        return f"Bạn nói {_num(v)} giây"
    if check.kind is MissionKind.MAX_PAUSE:
        return f"Khoảng lặng dài nhất {_num(v)} giây"
    if check.kind is MissionKind.READ_ALOUD:
        return f"Máy nhận ra {round(v * 100)}% số từ"
    if check.kind is MissionKind.UNIQUE_WORDS:
        return f"Bạn dùng {int(v)} từ khác nhau"
    return f"Đếm được {int(v)}"
