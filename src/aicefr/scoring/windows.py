"""Candidate aggregation for long responses; never bypasses per-window gates."""

from __future__ import annotations

import hashlib
import json
import math
from statistics import median

from aicefr.contracts import AssessmentStatus, DecodedAudio, ReasonCode
from aicefr.scoring.ridge import to_band

WINDOW_POLICY = "median-windows-v1"


def window_ranges(duration: float, *, minimum: float = 30, maximum: float = 60):
    if not math.isfinite(duration) or not 0 < minimum <= maximum or duration > 300:
        raise ValueError("invalid window duration")
    count = math.ceil(duration / maximum)
    if duration / count < minimum:
        raise ValueError("response cannot be fully covered by valid windows")
    return tuple(
        (duration * index / count, duration * (index + 1) / count) for index in range(count)
    )


def score_windows(audio, transcript, extractor, scorer):
    """Use real PCM slices and relative word times; retain absolute ranges in provenance.

    An invalid window invalidates the overall candidate instead of dropping that
    window. Equal non-overlapping windows cover the entire input, including tails.
    The unchanged artifact maps the median score to its original band thresholds.
    """
    artifact = scorer.artifact
    if artifact is None or "total_dur" not in artifact.feature_order:
        raise ValueError("window scoring needs a duration-aware artifact")
    position = artifact.feature_order.index("total_dur")
    minimum = max(30.0, artifact.feature_lo[position])
    maximum = min(60.0, artifact.feature_hi[position])
    rows, estimates = [], []
    for start, end in window_ranges(audio.duration_s, minimum=minimum, maximum=maximum):
        left, right = round(start * 16000), round(end * 16000)
        samples = audio.samples[left:right].copy()
        digest = hashlib.sha256(samples.tobytes()).hexdigest()
        segment = DecodedAudio(
            samples=samples,
            sample_rate_hz=16000,
            duration_s=len(samples) / 16000,
            audio_sha256=digest,
        )
        # Do not fabricate or duplicate words crossing a boundary.
        words = tuple(
            word.model_copy(update={"start_s": word.start_s - start, "end_s": word.end_s - start})
            for word in transcript.words
            if start <= word.start_s <= word.end_s <= end
        )
        local_transcript = transcript.model_copy(
            update={
                "words": words,
                "text": " ".join(word.text for word in words),
                "audio_sha256": digest,
            }
        )
        features = extractor.extract(local_transcript, segment)
        estimate = scorer.score(features, local_transcript)
        estimates.append(estimate)
        rows.append(
            {
                "start_s": start,
                "end_s": end,
                "score": estimate.overall_score,
                "band": estimate.overall_band.value if estimate.overall_band else None,
                "status": estimate.status.value,
                "reasons": [reason.value for reason in estimate.reasons],
            }
        )
    reasons = tuple(
        dict.fromkeys(
            (
                ReasonCode.SCORE_AGGREGATED,
                *(reason for item in estimates for reason in item.reasons),
            )
        )
    )
    base = estimates[0]
    valid = all(
        item.overall_score is not None and item.status is not AssessmentStatus.NOT_EVALUATED
        for item in estimates
    )
    value = median(item.overall_score for item in estimates) if valid else None
    candidate = base.model_copy(
        update={
            "status": AssessmentStatus.REVIEW_REQUIRED if valid else AssessmentStatus.NOT_EVALUATED,
            "overall_score": value,
            "overall_band": to_band(value, artifact.band_thresholds) if valid else None,
            "reasons": reasons,
        }
    )
    return candidate, {
        "aggregation": WINDOW_POLICY,
        "window_results": json.dumps(rows, separators=(",", ":"), sort_keys=True),
    }
