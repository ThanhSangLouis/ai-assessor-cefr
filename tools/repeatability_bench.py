"""How much does one recording's result move from run to run? (HUONG_PHAT_TRIEN_TIEP §2.2)

Runs the same pipeline the web app builds -- quality check, recogniser,
detector, scorer -- several times on each recording, once per decoding
temperature, and reports:

- sigma_r, the repeatability standard deviation of the 0-6 score (ISO 5725
  sense; not an SEM, see aicefr.research.repeatability);
- the share of run pairs whose band differs;
- the widest max - min spread on one recording;
- how many runs the repetition detector had to cut a loop from. Report this
  column next to the others: the fallback schedule that temperature 0 turns
  off is also what re-decodes hallucination loops.

    AICEFR_ASR=whisper python tools/repeatability_bench.py ghi_am/ --runs 5 \\
        --temperatures fallback,0 --out bao_cao_lap_lai.md

Needs the real recogniser and the recordings on this machine; nothing leaves
it, and the output names files, not people. Do not commit recordings or a
report about real people's recordings.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

from aicefr.contracts import ProcessingRequest, ReasonCode
from aicefr.research.repeatability import Run, summarise

AUDIO = {".wav", ".webm", ".m4a", ".mp3", ".ogg", ".flac", ".aac"}


def temperatures(raw: str) -> list[float | None]:
    """'fallback,0' -> [None, 0.0]."""
    out: list[float | None] = []
    for part in raw.split(","):
        part = part.strip().lower()
        out.append(None if part == "fallback" else float(part))
    return out


def label(temperature: float | None) -> str:
    return "fallback" if temperature is None else f"temperature={temperature}"


def bench(paths: list[pathlib.Path], temperature, runs: int, task: str, model) -> dict:
    from aicefr.asr.whisper_adapter import WhisperEngine
    from aicefr.audio.decoder import FirstMatchDecoder
    from aicefr.pipeline import ResponseProcessor
    from aicefr.scoring.scorer import RidgeScorer

    processor = ResponseProcessor(
        WhisperEngine(model=model, temperature=temperature), scorer=RidgeScorer()
    )
    decoder = FirstMatchDecoder()
    results: dict[str, list[Run]] = {}
    for path in paths:
        pcm, sr = decoder.decode(path.read_bytes(), str(path))
        for i in range(runs):
            request = ProcessingRequest(
                response_id=f"bench-{path.stem}-{i}",
                speaker_id="SV-000",
                task_id=task,
                audio_path=str(path),
                prompt_version="v1",
                config_version="v1",
            )
            report = processor.process(request, pcm, sr)
            a = report.assessment
            results.setdefault(path.name, []).append(
                Run(
                    score=a.overall_0_6 if a else None,
                    band=a.overall_band.value if a and a.overall_band else None,
                    hallucination=ReasonCode.ASR_HALLUCINATION in report.reasons,
                )
            )
            print(f"{label(temperature)}  {path.name}  lần {i + 1}/{runs}", file=sys.stderr)
    return results


def _f(value, digits: int = 3) -> str:
    return "—" if value is None else f"{value:.{digits}f}"


def markdown(summaries: dict[str, dict], runs: int) -> str:
    rows = [
        ("σ_r, độ lệch chuẩn lặp lại của điểm 0–6", "sigma_r", 3),
        ("Tỷ lệ cặp lần chạy đổi band", "band_change_rate", 3),
        ("Biên độ lớn nhất trên một bản ghi (max − min)", "largest_range", 2),
        ("Biên độ trung vị", "median_range", 2),
    ]
    names = list(summaries)
    lines = [
        "# Độ lặp lại của dụng cụ đo",
        "",
        f"Mỗi bản ghi chạy {runs} lần qua đúng pipeline của ứng dụng, ở từng cấu hình giải mã.",
        "",
        "| Chỉ số | " + " | ".join(names) + " |",
        "|---|" + "---:|" * len(names),
    ]
    for title, key, digits in rows:
        lines.append(
            f"| {title} | " + " | ".join(_f(summaries[n][key], digits) for n in names) + " |"
        )
    for title, key in (
        ("Số bản ghi có ít nhất hai lần được chấm", "files_with_two_scores"),
        ("Lần chạy không ra điểm", "unscored_runs"),
        ("Lần chạy bộ dò lặp phải cắt một đoạn", "hallucination_runs"),
    ):
        lines.append(f"| {title} | " + " | ".join(str(summaries[n][key]) for n in names) + " |")
    lines += [
        "",
        "Đặt cạnh: RMSE của mô hình so với nhãn người (`cv_rmse` trong artifact) và bề rộng "
        'một band = 1,0 điểm. Không gọi σ_r là SEM; không viết "tất định" khi lịch dự phòng '
        "còn chạy.",
    ]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Đo độ lặp lại của điểm khi chạy lại cùng bản ghi")
    ap.add_argument("folder", help="thư mục chứa bản ghi")
    ap.add_argument("--runs", type=int, default=5, help="số lần chạy mỗi bản ghi (mặc định 5)")
    ap.add_argument("--temperatures", default="fallback,0", help="ví dụ: fallback,0")
    ap.add_argument("--task", default="P3", help="mã đề bài khi chấm")
    ap.add_argument("--model", default=None, help="mô hình Whisper; bỏ trống là mặc định")
    ap.add_argument("--out", help="tệp Markdown; bản JSON nằm cạnh với đuôi .json")
    args = ap.parse_args(argv)

    paths = sorted(p for p in pathlib.Path(args.folder).iterdir() if p.suffix.lower() in AUDIO)
    if not paths:
        ap.error("thư mục không có bản ghi nào")
    if args.runs < 2:
        ap.error("cần ít nhất hai lần chạy mỗi bản ghi")
    summaries = {
        label(t): summarise(bench(paths, t, args.runs, args.task, args.model))
        for t in temperatures(args.temperatures)
    }
    text = markdown(summaries, args.runs)
    if not args.out:
        sys.stdout.write(text)
        return 0
    out = pathlib.Path(args.out)
    out.write_text(text, encoding="utf-8")
    out.with_suffix(".json").write_text(
        json.dumps({"runs": args.runs, "summaries": summaries}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Đã ghi {out} và {out.with_suffix('.json')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
