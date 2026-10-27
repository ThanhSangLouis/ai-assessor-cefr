"""Cutting a long recording into windows the model can actually score.

The scoring model was fitted on responses of 26.7 to 60.7 seconds and refuses
anything beyond about 78. That limit is real and cannot be argued away: a model
never shown a three-minute response has no basis for scoring one. Until there is
training data covering longer speech -- planned for weeks 10-11 in
`docs/plan/KE_HOACH_KHAO_SAT.md` -- the only honest way to accept a long
recording is to score the parts, each of which IS the length the model knows,
and say plainly that the combination has not been validated.

Three rules shape the cut, and each one exists to stop a specific way of getting
a wrong number:

**Cut at silence, never mid-word.** A window boundary that lands inside a word
truncates it in one window and orphans it in the next, and every count-based
feature moves. Boundaries are chosen from the pauses the voice activity detector
already found.

**Every window stays inside the trained range.** A window of 12 seconds is not a
short window, it is a window outside the model's experience -- the same fault
the whole mechanism exists to avoid. A tail too short to stand alone is merged
into the window before it, even when that makes the last window longer than the
target.

**Windows never overlap and never drop audio.** The union of the windows is the
whole recording, so a speaker cannot lose a sentence at a boundary or have one
counted twice.
"""

from __future__ import annotations

from aicefr.contracts import AnalysisWindow

# Target and bounds for one analysis window, in seconds. The target sits in the
# middle of the trained range rather than at its top: a window at 60 seconds
# leaves no room for the boundary to move to the nearest pause.
TARGET_WINDOW_S = 45.0
MIN_WINDOW_S = 30.0
MAX_WINDOW_S = 60.0

# A trailing piece shorter than this is merged backwards instead of scored.
MIN_TAIL_S = 20.0

# Beyond this many windows the submission is no longer one spoken response to
# one prompt, and averaging across it stops meaning anything.
MAX_WINDOWS = 10

# How far a cut may move to land on a pause. Beyond this the pause is not
# "nearby" in any useful sense and the even cut is the lesser evil.
SNAP_TOLERANCE_S = 8.0


def _pause_midpoints(segments: list[tuple[float, float]]) -> list[float]:
    """Candidate cut points: the middle of every silence between speech segments."""
    return [
        (segments[i][1] + segments[i + 1][0]) / 2.0
        for i in range(len(segments) - 1)
        if segments[i + 1][0] > segments[i][1]
    ]


def plan_windows(
    total_dur_s: float,
    segments: list[tuple[float, float]],
    *,
    target_s: float = TARGET_WINDOW_S,
    min_s: float = MIN_WINDOW_S,
    max_s: float = MAX_WINDOW_S,
    min_tail_s: float = MIN_TAIL_S,
    max_windows: int = MAX_WINDOWS,
) -> list[AnalysisWindow]:
    """Plan the cut. Returns one window covering everything when no cut is needed.

    `segments` are the voice activity segments on the ORIGINAL recording clock.
    With no segments the cut falls back to even division, which is worse but
    still better than refusing to score at all.
    """
    if total_dur_s <= max_s:
        return [AnalysisWindow(index=0, start_s=0.0, end_s=total_dur_s)]

    wanted = max(1, round(total_dur_s / target_s))
    wanted = min(wanted, max_windows)
    # Never let the arithmetic produce a window longer than the model accepts.
    while total_dur_s / wanted > max_s and wanted < max_windows:
        wanted += 1

    ideal = [total_dur_s * i / wanted for i in range(1, wanted)]
    candidates = _pause_midpoints(segments)

    cuts: list[float] = []
    for point in ideal:
        # Snap to a pause only if one is genuinely near the ideal cut. Snapping
        # to the nearest pause at any distance is how a stretch with no pauses
        # drags a boundary tens of seconds away and leaves one window far longer
        # than the model accepts -- which defeats the cut entirely.
        near = [
            c
            for c in candidates
            if abs(c - point) <= SNAP_TOLERANCE_S and c - (cuts[-1] if cuts else 0.0) >= min_s
        ]
        cuts.append(min(near, key=lambda c: abs(c - point)) if near else point)

    cuts = sorted({round(c, 3) for c in cuts if 0.0 < c < total_dur_s})

    bounds = [0.0, *cuts, total_dur_s]
    windows = [
        AnalysisWindow(index=i, start_s=bounds[i], end_s=bounds[i + 1])
        for i in range(len(bounds) - 1)
        if bounds[i + 1] > bounds[i]
    ]

    # Snapping to pauses can leave a window shorter than the model's range, and
    # a 12-second window is not a small window -- it is a window outside what the
    # model has ever seen, which is the exact fault this whole mechanism exists
    # to avoid. Merge any short window into its neighbour, smaller neighbour
    # first so the merge does not immediately create an over-long window.
    changed = True
    while changed and len(windows) > 1:
        changed = False
        for i, w in enumerate(windows):
            floor = min_tail_s if i == len(windows) - 1 else min_s
            if w.duration_s >= floor:
                continue
            if i == 0:
                merged = AnalysisWindow(index=0, start_s=windows[0].start_s, end_s=windows[1].end_s)
                windows = [merged, *windows[2:]]
            elif i == len(windows) - 1:
                merged = AnalysisWindow(index=0, start_s=windows[i - 1].start_s, end_s=w.end_s)
                windows = [*windows[: i - 1], merged]
            else:
                left, right = windows[i - 1].duration_s, windows[i + 1].duration_s
                if left <= right:
                    merged = AnalysisWindow(index=0, start_s=windows[i - 1].start_s, end_s=w.end_s)
                    windows = [*windows[: i - 1], merged, *windows[i + 1 :]]
                else:
                    merged = AnalysisWindow(index=0, start_s=w.start_s, end_s=windows[i + 1].end_s)
                    windows = [*windows[:i], merged, *windows[i + 2 :]]
            changed = True
            break

    # Last guard: nothing leaves this function longer than the model accepts.
    # Everything above is heuristic; this is the invariant.
    final: list[AnalysisWindow] = []
    for w in windows:
        if w.duration_s <= max_s:
            final.append(w)
            continue
        pieces = int(w.duration_s // max_s) + 1
        step = w.duration_s / pieces
        final.extend(
            AnalysisWindow(
                index=0,
                start_s=round(w.start_s + i * step, 3),
                end_s=round(w.start_s + (i + 1) * step, 3),
            )
            for i in range(pieces)
        )

    return [AnalysisWindow(index=i, start_s=w.start_s, end_s=w.end_s) for i, w in enumerate(final)]


def clip_segments(
    segments: list[tuple[float, float]], window: AnalysisWindow
) -> list[tuple[float, float]]:
    """Voice segments inside one window, re-based to that window's own clock.

    Re-basing matters for `vad_onset_delay`, which measures the delay before the
    speaker starts. Inside a window that is a real measurement of how the
    speaker resumed after a pause; left on the original clock it would report
    "started talking 132 seconds in" for every window after the first.
    """
    out = []
    for start, end in segments:
        s, e = max(start, window.start_s), min(end, window.end_s)
        if e > s:
            out.append((round(s - window.start_s, 3), round(e - window.start_s, 3)))
    return out
