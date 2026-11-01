"""Guided listening with random control moments (D056, HUONG_PHAT_TRIEN_TIEP 3.4).

After an assessment, the learner listens again to a few six-second moments of
their own recording and says, for each, how that stretch went. Some moments are
where the machine measured something -- a long pause, a hesitation word, a word
it could not hear clearly; one or two are CONTROL moments drawn at random from
stretches with speech and nothing flagged. The order is shuffled and the learner
is never told which is which, and every moment offers the same four answers:
changing the answers by kind of moment would feed the learner the answer.

The learner reads their answers back on their progress page (D078: the
analysis comparing the machine's moments with the random ones, a research
measure, is gone).

What this is NOT: a pronunciation check. A "low confidence word" is a word the
recogniser could not hear clearly (Whisper's probability below 0.50); the
interface says exactly that, and `tests/test_replay.py` refuses any wording
that calls it a pronunciation error.
"""

from __future__ import annotations

import hashlib
import random
from collections.abc import Callable
from dataclasses import dataclass

from aicefr.contracts import EvidenceKind, Response

WINDOW_S = 6.0
LEAD_S = 2.0  # a moment starts this long before what was measured
MAX_MACHINE = 4
MIN_WORDS_IN_CONTROL = 3
MACHINE_KINDS = (EvidenceKind.PAUSE, EvidenceKind.FILLER, EvidenceKind.LOW_CONFIDENCE_WORD)
MACHINE, CONTROL = "machine", "control"

# The same four answers at every moment, control ones included.
CHOICES: dict[str, str] = {
    "smooth": "Trôi chảy, mình nói được điều mình muốn",
    "hesitant": "Hơi ngập ngừng hoặc phải tìm từ",
    "hard": "Khó khăn rõ: bí từ, phải nói lại hoặc nói chưa rõ ý",
    "unsure": "Không chắc",
}


@dataclass(frozen=True)
class Moment:
    moment_id: str
    start_s: float
    end_s: float
    source: str  # machine | control -- never sent to the learner
    kind: str  # the evidence kind, or "control"

    def public(self) -> dict:
        return {"moment_id": self.moment_id, "start_s": self.start_s, "end_s": self.end_s}


def _rng(response_id: str) -> random.Random:
    """The same moments every time the same response is opened."""
    return random.Random(int(hashlib.sha256(response_id.encode()).hexdigest()[:12], 16))


def _overlaps(a: tuple[float, float], b: tuple[float, float], gap: float = 1.0) -> bool:
    return a[0] < b[1] + gap and b[0] < a[1] + gap


Span = tuple[float, float]


def moments(report: Response) -> list[Moment]:
    """The moments of one response, shuffled; empty when the machine flagged nothing."""
    if report.asr is None or report.assessment is None or not report.asr.words:
        return []
    window = _windower(report.asr.words)
    machine = _machine_spans(report, window)
    if not machine:
        return []
    rng = _rng(report.response_id)
    controls = _control_spans(report, window, [span for span, _ in machine], rng)
    picked = [(w, MACHINE, kind) for w, kind in machine] + [(w, CONTROL, CONTROL) for w in controls]
    rng.shuffle(picked)
    return [
        Moment(f"m{i}", w[0], w[1], source, kind) for i, (w, source, kind) in enumerate(picked, 1)
    ]


def _windower(words) -> Callable[[float], Span]:
    """A six-second span starting at a time, kept inside the recording."""
    duration = max(w.end_s for w in words)
    last_start = max(0.0, duration - WINDOW_S)

    def window(at: float) -> Span:
        start = min(max(0.0, at), last_start)
        return round(start, 2), round(min(duration, start + WINDOW_S), 2)

    return window


def _machine_spans(report: Response, window: Callable[[float], Span]) -> list[tuple[Span, str]]:
    """Up to MAX_MACHINE spans around what the machine flagged, in time order, not overlapping."""
    flagged = sorted(
        (
            e
            for e in report.assessment.evidence
            if e.start_s is not None and e.kind in MACHINE_KINDS
        ),
        key=lambda e: e.start_s,
    )
    machine: list[tuple[Span, str]] = []
    for e in flagged:
        w = window(e.start_s - LEAD_S)
        if all(not _overlaps(w, m, gap=0.0) for m, _ in machine):
            machine.append((w, e.kind.value))
        if len(machine) == MAX_MACHINE:
            break
    return machine


def _control_spans(
    report: Response, window: Callable[[float], Span], machine: list[Span], rng: random.Random
) -> list[Span]:
    """One or two random spans with speech, clear of every flag and of the machine's spans."""
    words = report.asr.words
    flagged = [e.start_s for e in report.assessment.evidence if e.start_s is not None]
    candidates = []
    for word in words:
        w = window(word.start_s)
        inside = sum(1 for x in words if w[0] <= x.start_s < w[1])
        if (
            inside >= MIN_WORDS_IN_CONTROL
            and all(not _overlaps(w, m) for m in machine)
            and not any(w[0] - 1.0 <= t <= w[1] + 1.0 for t in flagged)
        ):
            candidates.append(w)
    rng.shuffle(candidates)
    wanted = 1 if len(machine) <= 2 else 2
    controls: list[Span] = []
    for w in candidates:
        if all(not _overlaps(w, c) for c in controls):
            controls.append(w)
        if len(controls) == wanted:
            break
    return controls
