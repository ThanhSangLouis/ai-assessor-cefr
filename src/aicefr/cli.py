"""Command-line interface. Run:  aicefr path/to/file.wav"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

import numpy as np

from aicefr.asr.fake import FakeAsrEngine
from aicefr.audio.decoder import DecodeError, FirstMatchDecoder
from aicefr.contracts import ProcessingRequest
from aicefr.pipeline import ResponseProcessor


def _load(path: str) -> tuple[np.ndarray, int]:
    """Read any format the web interface accepts, not just what libsndfile opens.

    Going through the same decoder as the server means the command line and the
    web path agree about what a file is and what sample rate it ends up at.
    """
    return FirstMatchDecoder().decode(pathlib.Path(path).read_bytes(), path)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Chấm sơ bộ một bài nói theo CEFR")
    ap.add_argument("audio", help="đường dẫn tệp âm thanh")
    ap.add_argument("--speaker", default="SV-000", help="mã bút danh, không dùng MSSV")
    ap.add_argument("--task", default="P1", help="mã đề bài")
    ap.add_argument("--engine", choices=["fake", "whisper"], default="fake")
    ap.add_argument("--model", default="mlx-community/whisper-small-mlx")
    ap.add_argument(
        "--temperature",
        type=float,
        default=None,
        help="nhiệt độ giải mã cố định, thường là 0; bỏ trống là lịch dự phòng của thư viện",
    )
    args = ap.parse_args(argv)

    if args.engine == "whisper":
        from aicefr.asr.whisper_adapter import WhisperEngine

        engine = WhisperEngine(model=args.model, temperature=args.temperature)
    else:
        engine = FakeAsrEngine()

    try:
        pcm, sr = _load(args.audio)
    except (DecodeError, OSError) as e:
        print(f"Không đọc được tệp: {e}", file=sys.stderr)
        return 2
    req = ProcessingRequest(
        response_id="cli-1",
        speaker_id=args.speaker,
        task_id=args.task,
        audio_path=args.audio,
        prompt_version="v1",
        config_version="v1",
    )
    report = ResponseProcessor(engine).process(req, pcm, sr)
    json.dump(report.model_dump(mode="json"), sys.stdout, ensure_ascii=False, indent=2)
    print()
    return 0 if report.status.value != "FAILED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
