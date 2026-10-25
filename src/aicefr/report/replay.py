"""Guided listening with random control moments (D056, HUONG_PHAT_TRIEN_TIEP 3.4).

After an assessment, the learner listens again to a few six-second moments of
their own recording and says, for each, how that stretch went. Some moments are
where the machine measured something -- a long pause, a hesitation word, a word
it could not hear clearly; one or two are CONTROL moments drawn at random from
stretches with speech and nothing flagged. The order is shuffled and the learner
is never told which is which, and every moment offers the same four answers:
changing the answers by kind of moment would feed the learner the answer.

The measure is the difference: how much more often learners confirm a
difficulty at the machine's moments than at the random ones. A rate at the
machine's moments alone proves nothing -- any picker of moments in a learner's
speech finds some difficulty. The headline is that difference, with a 95%
interval from a cluster bootstrap over learners.

What this is NOT: a pronunciation check. A "low confidence word" is a word the
recogniser could not hear clearly (Whisper's probability below 0.50); the
interface says exactly that, and `tests/test_replay.py` refuses any wording
that calls it a pronunciation error.
"""

from __future__ import annotations

import hashlib
import random
from collections import defaultdict
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
CONFIRMS = frozenset({"hesitant", "hard"})
HEADLINE_GAP = 0.20
BOOTSTRAP = 2000


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


def _rates(labels: list[dict]) -> dict[str, tuple[int, int]]:
    """(confirmed, answered) per source; "unsure" is not an answer either way."""
    out = {MACHINE: [0, 0], CONTROL: [0, 0]}
    for x in labels:
        if x["choice"] == "unsure":
            continue
        out[x["source"]][1] += 1
        out[x["source"]][0] += x["choice"] in CONFIRMS
    return {k: (v[0], v[1]) for k, v in out.items()}


def _gap(labels: list[dict]) -> float | None:
    r = _rates(labels)
    if not r[MACHINE][1] or not r[CONTROL][1]:
        return None
    return r[MACHINE][0] / r[MACHINE][1] - r[CONTROL][0] / r[CONTROL][1]


def analyse(labels: list[dict], seed: int = 20261024) -> dict:
    """Confirmation at the machine's moments against the random ones, by learner.

    `labels` carry `account_id`, `source` and `choice`. The interval resamples
    learners, not labels: one learner's answers are not independent.
    """
    by_learner: dict[str, list[dict]] = defaultdict(list)
    for x in labels:
        by_learner[x["account_id"]].append(x)
    rates = _rates(labels)
    gap = _gap(labels)
    learners = sorted(by_learner)
    rng = random.Random(seed)
    gaps = []
    if gap is not None and len(learners) > 1:
        for _ in range(BOOTSTRAP):
            sample = [x for _ in learners for x in by_learner[rng.choice(learners)]]
            g = _gap(sample)
            if g is not None:
                gaps.append(g)
    gaps.sort()
    ci = (
        [round(gaps[int(0.025 * len(gaps))], 4), round(gaps[int(0.975 * len(gaps)) - 1], 4)]
        if len(gaps) >= 100
        else None
    )
    return {
        "learners": len(learners),
        "labels": len(labels),
        "machine": {"confirmed": rates[MACHINE][0], "answered": rates[MACHINE][1]},
        "control": {"confirmed": rates[CONTROL][0], "answered": rates[CONTROL][1]},
        "gap": round(gap, 4) if gap is not None else None,
        "gap_ci95": ci,
        "headline_met": bool(ci and gap is not None and gap >= HEADLINE_GAP and ci[0] > 0),
        "headline_rule": (
            f"tỷ lệ xác nhận ở mốc máy chọn cao hơn mốc ngẫu nhiên ≥ {HEADLINE_GAP:.0%}"
            " và KTC 95% (bootstrap theo người học) không chứa 0"
        ),
    }
