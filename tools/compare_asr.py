#!/usr/bin/env python3
"""Score the same recordings through two recognisers, side by side (D066).

    .venv/bin/python tools/compare_asr.py REC.wav [REC2.webm ...] \
        [--models small large-v3] [--labels labels.csv] [--threads 2] [--json]

Production scores with Whisper small, the recogniser the scoring model was
fitted on. Large-v3 (or any other) is for comparison only: this runs the full
pipeline -- QC, VAD, recognition, features, the active scoring artifact,
routing -- once per recogniser and reports, per recording and in total:

* seconds per recording (model loading excluded: it happens once at start-up);
* score, band and the reasons a response goes to a teacher;
* `asr_conf_mean`, the feature a recogniser moves most;
* how far the two transcripts differ (word edit distance / words);
* with `--labels` (a CSV of `file,score` with a teacher's 0-6 score), the mean
  absolute error of each recogniser against it -- the number that decides.

Needs the `[asr,vad]` extras and the real artifacts (`AICEFR_MODEL_DIR`). Run it
on recordings without personal data or with the speaker's consent, and never
commit them or their transcripts.
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
import time
from pathlib import Path


def _edit_distance(a: list[str], b: list[str]) -> int:
    prev = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        cur = [i]
        for j, y in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (x != y)))
        prev = cur
    return prev[-1]


def _words(text: str) -> list[str]:
    return ["".join(c for c in w.lower() if c.isalnum() or c == "'") for w in text.split()]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("recordings", nargs="+")
    ap.add_argument("--models", nargs="+", default=["small", "large-v3"])
    ap.add_argument("--labels", help="CSV file,score: a teacher's 0-6 score per recording")
    ap.add_argument("--threads", type=int, default=2, help="CPU threads, as on the server")
    ap.add_argument("--task", default="P3")
    ap.add_argument("--json", action="store_true", help="print JSON instead of a table")
    args = ap.parse_args()

    from aicefr.asr.whisper_adapter import WhisperEngine
    from aicefr.audio.decoder import FirstMatchDecoder
    from aicefr.contracts import ProcessingRequest
    from aicefr.pipeline import ResponseProcessor, default_vad

    labels: dict[str, float] = {}
    if args.labels:
        with open(args.labels, encoding="utf-8") as f:
            labels = {Path(r["file"]).name: float(r["score"]) for r in csv.DictReader(f)}

    decoder = FirstMatchDecoder()
    audio = {}
    for path in args.recordings:
        audio[path] = decoder.decode(Path(path).read_bytes(), path)

    rows = []
    for model in args.models:
        engine = WhisperEngine(backend="ct2", model=model, cpu_threads=args.threads)
        engine.warm_up()
        processor = ResponseProcessor(engine, vad=default_vad())
        for path, (pcm, sr) in audio.items():
            request = ProcessingRequest(
                response_id="compare", speaker_id="compare", task_id=args.task,
                audio_path=path, prompt_version="v1", config_version="v1",
            )  # fmt: skip
            t0 = time.perf_counter()
            response = processor.process(request, pcm, sr)
            seconds = time.perf_counter() - t0
            a = response.assessment
            features = response.features
            rows.append(
                {
                    "model": model,
                    "file": Path(path).name,
                    "seconds": round(seconds, 1),
                    "status": response.status.value,
                    "score": a.overall_0_6 if a else None,
                    "band": a.overall_band.value if a and a.overall_band else None,
                    "reasons": [r.value for r in (a.reasons if a else response.reasons)],
                    "asr_conf_mean": features.value_of("asr_conf_mean") if features else None,
                    "text": response.asr.text if response.asr else "",
                    "human": labels.get(Path(path).name),
                }
            )

    # Transcript difference against the first recogniser, recording by recording.
    base = {r["file"]: _words(r["text"]) for r in rows if r["model"] == args.models[0]}
    for r in rows:
        ref = base.get(r["file"], [])
        r["text_diff"] = round(_edit_distance(ref, _words(r["text"])) / max(1, len(ref)), 3)

    summary = []
    for model in args.models:
        mine = [r for r in rows if r["model"] == model]
        scored = [r for r in mine if r["score"] is not None]
        judged = [r for r in scored if r["human"] is not None]
        summary.append(
            {
                "model": model,
                "seconds_mean": round(statistics.mean(r["seconds"] for r in mine), 1),
                "scored": f"{len(scored)}/{len(mine)}",
                "to_teacher": sum(r["status"] == "REVIEW_REQUIRED" for r in mine),
                "asr_mismatch": sum("ASR_VERSION_MISMATCH" in r["reasons"] for r in mine),
                "text_diff_mean": round(statistics.mean(r["text_diff"] for r in mine), 3),
                "mae_vs_teacher": round(
                    statistics.mean(abs(r["score"] - r["human"]) for r in judged), 3
                )
                if judged
                else None,
            }
        )

    if args.json:
        print(json.dumps({"rows": rows, "summary": summary}, ensure_ascii=False, indent=1))
        return 0
    print(f"{'model':<12}{'file':<28}{'giây':>6}{'điểm':>7}  band  conf   lệch chữ  lý do")
    for r in rows:
        score = f"{r['score']:.2f}" if r["score"] is not None else "—"
        conf = f"{r['asr_conf_mean']:.3f}" if r["asr_conf_mean"] is not None else "—"
        print(
            f"{r['model']:<12}{r['file'][:27]:<28}{r['seconds']:>6}{score:>7}  "
            f"{r['band'] or '—':<4}  {conf}  {r['text_diff']:>7}   {','.join(r['reasons'])}"
        )
    print()
    for s in summary:
        print(json.dumps(s, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
