#!/usr/bin/env python3
"""Machine seconds and cost of one recording on the machine this runs on (D057).

    python tools/bench_asr.py RECORDING.wav MODEL_DIR --usd-per-hour 0.2058 [--threads 4]

Run it on the instance being priced (an EC2 c7i.xlarge, a g4dn.xlarge, ...):
the price of a request depends on the hardware, and an estimate made on a
laptop is not that number. It times what the speech service does with a
recording -- the transcription with word timestamps and the language check --
the way `asr/whisper_adapter.py` calls faster-whisper, three times each, and
keeps the fastest. QC, voice activity, features and scoring take about two
seconds more on a small CPU and are added as `--other-seconds`.

Prints JSON: seconds per recording, recordings an hour on one worker, and the
cost of one recording at full load and at the utilisation given. Use a
recording without personal data (a synthetic voice, a consented sample).
"""

from __future__ import annotations

import argparse
import json
import time


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("recording")
    ap.add_argument("model_dir")
    ap.add_argument("--usd-per-hour", type=float, required=True)
    ap.add_argument("--vnd-per-usd", type=float, default=26_100)
    ap.add_argument("--threads", type=int, default=4)
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--compute-type", default="int8")
    ap.add_argument("--other-seconds", type=float, default=2.0)
    ap.add_argument("--utilisation", type=float, default=0.3)
    args = ap.parse_args()

    import soundfile as sf
    from faster_whisper import WhisperModel

    pcm, sr = sf.read(args.recording, dtype="float32")
    if sr != 16_000:
        raise SystemExit("the recording must be 16 kHz mono, as the pipeline feeds Whisper")
    model = WhisperModel(
        args.model_dir, device=args.device, compute_type=args.compute_type,
        cpu_threads=args.threads,
    )  # fmt: skip
    model.transcribe(pcm[: 5 * sr], language="en")  # load and warm up, not timed

    best = None
    for _ in range(3):
        t0 = time.perf_counter()
        segments = list(model.transcribe(pcm, language="en", word_timestamps=True, beam_size=5)[0])
        t1 = time.perf_counter()
        model.transcribe(pcm[: 30 * sr], language=None, word_timestamps=False)
        t2 = time.perf_counter()
        run = (t1 - t0, t2 - t1, sum(len(s.tokens) for s in segments))
        best = run if best is None or sum(run[:2]) < sum(best[:2]) else best

    seconds = best[0] + best[1] + args.other_seconds
    per_recording = args.usd_per_hour / 3600 * seconds * args.vnd_per_usd
    print(
        json.dumps(
            {
                "audio_seconds": round(len(pcm) / sr, 1),
                "asr_seconds": round(best[0], 2),
                "language_check_seconds": round(best[1], 2),
                "other_seconds": args.other_seconds,
                "seconds_per_recording": round(seconds, 2),
                "output_tokens": best[2],
                "recordings_per_hour_one_worker": round(3600 / seconds),
                "vnd_per_recording_full_load": round(per_recording, 1),
                "vnd_per_recording_at_utilisation": round(per_recording / args.utilisation, 1),
                "assumptions": {
                    "usd_per_hour": args.usd_per_hour,
                    "vnd_per_usd": args.vnd_per_usd,
                    "threads": args.threads,
                    "device": args.device,
                    "compute_type": args.compute_type,
                    "utilisation": args.utilisation,
                },
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
