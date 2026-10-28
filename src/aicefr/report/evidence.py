"""Builds the evidence for each criterion. Implements FR-24 to FR-27."""

from __future__ import annotations

from aicefr.contracts import Criterion, Evidence, EvidenceKind, FeatureSet, Transcript, Word

LOW_PROB = 0.50
LONG_PAUSE_S = 1.00
MAX_PER_KIND = 3
FILLERS = {"um", "uh", "hmm", "mm", "erm", "ah", "eh", "er"}


def _pauses(
    segments: list[tuple[float, float]],
    long_pause_s: float = LONG_PAUSE_S,
) -> list[tuple[float, float, float]]:
    seg = sorted(segments)
    out = []
    for i in range(len(seg) - 1):
        gap = seg[i + 1][0] - seg[i][1]
        if gap > long_pause_s:
            out.append((seg[i][1], seg[i + 1][0], gap))
    return sorted(out, key=lambda x: -x[2])


def _snippet(words: list[Word], at_s: float, span: int = 4) -> str:
    idx = min(range(len(words)), key=lambda i: abs(words[i].start_s - at_s)) if words else 0
    lo, hi = max(idx - span, 0), min(idx + span + 1, len(words))
    return " ".join(w.text for w in words[lo:hi])


class EvidenceBuilder:
    """Turns ASR output and features into the evidence list for a report.

    A hard rule: every piece of evidence must trace back to real data, either a
    real timestamp or a real transcript excerpt. Generating a vague comment such
    as "needs more practice" without pointing at a specific place is not
    allowed.

    A class rather than a bare function because the thresholds that decide what
    counts as evidence — how improbable a word has to be, how long a silence has
    to last, how many items of each kind a report may carry — are configuration,
    not arguments. They belong to the object, so one builder produces one
    consistent reading of a whole batch of recordings.
    """

    def __init__(
        self,
        low_prob: float = LOW_PROB,
        long_pause_s: float = LONG_PAUSE_S,
        max_per_kind: int = MAX_PER_KIND,
    ) -> None:
        self.low_prob = low_prob
        self.long_pause_s = long_pause_s
        self.max_per_kind = max_per_kind

    def build(
        self,
        asr: Transcript,
        features: FeatureSet,
        segments: list[tuple[float, float]],
    ) -> list[Evidence]:
        """Return the evidence list, most problematic items first."""
        ev: list[Evidence] = []

        for start, end, gap in _pauses(segments, self.long_pause_s)[: self.max_per_kind]:
            ev.append(
                Evidence(
                    criterion=Criterion.FLUENCY,
                    kind=EvidenceKind.PAUSE,
                    start_s=round(start, 2),
                    end_s=round(end, 2),
                    snippet=_snippet(asr.words, start),
                    note=f"Ngừng {gap:.1f} giây giữa chừng.",
                )
            )

        if asr.is_verbatim:
            fillers = [w for w in asr.words if w.text.strip("[]").lower() in FILLERS]
            for w in fillers[: self.max_per_kind]:
                ev.append(
                    Evidence(
                        criterion=Criterion.FLUENCY,
                        kind=EvidenceKind.FILLER,
                        start_s=w.start_s,
                        end_s=w.end_s,
                        snippet=_snippet(asr.words, w.start_s),
                        note=f"Từ ngập ngừng {w.text!r}.",
                    )
                )

        low = sorted(
            (w for w in asr.words if w.prob is not None and w.prob < self.low_prob),
            key=lambda w: w.prob,
        )
        for w in low[: self.max_per_kind]:
            ev.append(
                Evidence(
                    criterion=Criterion.PHONOLOGY,
                    kind=EvidenceKind.LOW_CONFIDENCE_WORD,
                    start_s=w.start_s,
                    end_s=w.end_s,
                    snippet=_snippet(asr.words, w.start_s),
                    note=(
                        f"Máy nhận dạng từ {w.text!r} với độ tin cậy {w.prob:.2f}. "
                        "Có thể do phát âm chưa rõ hoặc do bản ghi."
                    ),
                )
            )

        uniq = features.value_of("log_uniq")
        nwords = features.value_of("n_words")
        if uniq is not None and nwords:
            ev.append(
                Evidence(
                    criterion=Criterion.RANGE,
                    kind=EvidenceKind.LEXICAL,
                    snippet=None,
                    note=(
                        f"Bài nói dùng {int(nwords)} từ, trong đó khoảng "
                        f"{int(round(2.718**uniq - 1))} từ khác nhau."
                    ),
                )
            )
        # Stable ids, assigned in the order the evidence was built. FR-25 lets a
        # comment cite evidence; without an id it can only cite it vaguely, and
        # a vague citation cannot be checked by a test.
        return [e.model_copy(update={"evidence_id": f"ev-{i:02d}"}) for i, e in enumerate(ev, 1)]
