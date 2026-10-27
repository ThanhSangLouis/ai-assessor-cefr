#!/usr/bin/env python3
"""Refusal benchmark: he thong co "dam tu choi" dung luc khong? D022.

    # tao bo clip tong hop (im lang, on, nhac, qua ngan) de chay thu
    .venv/bin/python tools/refusal_benchmark.py --synthesize bench/clips

    # chay pipeline that tren mot thu muc clip, moi nhom mot thu muc con
    AICEFR_ASR=whisper .venv/bin/python tools/refusal_benchmark.py --root bench/clips \\
        --engine whisper --out bench/ket_qua.json

Cau truc thu muc `--root`: moi thu muc con la mot NHOM, ten nhom quyet dinh ky
vong:

  * nhom PHAI TU CHOI (khong duoc phat band ma khong qua giang vien):
    silence, noise, music, non_english, off_topic, prompt_copy, too_short
  * nhom HOP LE: valid -- bai noi tieng Anh that, co quyen su dung.

Hai chi so, moi chi so kem khoang tin cay Wilson 95%:

  * ty le LOT (false score rate): trong nhom phai tu choi, bao nhieu bai van
    duoc phat band ma khong qua giang vien (status COMPLETED);
  * ty le TU CHOI NHAM (false refusal rate): trong nhom hop le, bao nhieu bai
    khong duoc cham chut nao (khong co diem).

Bai hop le bi CHUYEN giang vien KHONG tinh la tu choi nham -- do la thiet ke
(Trust Layer chuyen moi bai co khoang cham hon mot band); ty le chuyen duoc bao
cao rieng.

Nguon clip goi y (kiem giay phep truoc khi dung): MUSAN (on, nhac, CC BY 4.0),
Common Voice tieng Viet (CC0), ban ghi cua nhom co dong y. Giong TTS la HAN CHE
DA BIET (chua co bo phat hien), do va bao cao rieng, khong gop vao ty le lot.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import tempfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from aicefr.contracts import ProcessingRequest, Status  # noqa: E402

SR = 16_000
MUST_REFUSE = (
    "silence",
    "noise",
    "music",
    "non_english",
    "off_topic",
    "prompt_copy",
    "too_short",
)
VALID = ("valid",)
AUDIO = {".wav", ".flac", ".mp3", ".m4a", ".webm", ".ogg"}


def wilson(k: int, n: int, z: float = 1.959964) -> tuple[float, float] | None:
    """Khoang tin cay Wilson cho ty le k/n. Dung tot ca khi k = 0 hoac n nho."""
    if n == 0:
        return None
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return round(max(0.0, centre - half), 4), round(min(1.0, centre + half), 4)


def synthesize(out: Path, n: int = 5, seed: int = 0) -> None:
    """Clip TONG HOP, khong co nguoi that: im lang, on trang, 'nhac' (hop am), qua ngan."""
    import soundfile as sf

    rng = np.random.default_rng(seed)
    t = np.arange(SR * 40) / SR
    makers = {
        "silence": lambda i: np.zeros(SR * 40, dtype=np.float32),
        "noise": lambda i: (0.05 * (i + 1) * rng.standard_normal(SR * 40)).astype(np.float32),
        "music": lambda i: (
            0.15 * sum(np.sin(2 * np.pi * f * (1 + 0.1 * i) * t) for f in (262, 330, 392)) / 3
        ).astype(np.float32),
        "too_short": lambda i: (0.2 * np.sin(2 * np.pi * 220 * t[: SR * (3 + i)])).astype(
            np.float32
        ),
    }
    for cat, make in makers.items():
        (out / cat).mkdir(parents=True, exist_ok=True)
        for i in range(n):
            sf.write(out / cat / f"{cat}_{i:02d}.wav", make(i), SR)


def run(root: Path, processor, task_id: str = "P4") -> dict:
    from aicefr.audio.decoder import FirstMatchDecoder

    decoder = FirstMatchDecoder()
    rows = []
    for cat_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        cat = cat_dir.name
        if cat not in MUST_REFUSE + VALID:
            print(f"bo qua nhom la: {cat}", file=sys.stderr)
            continue
        for clip in sorted(p for p in cat_dir.iterdir() if p.suffix.lower() in AUDIO):
            pcm, sr = decoder.decode(clip.read_bytes(), clip.name)
            req = ProcessingRequest(
                response_id=f"bench-{cat}-{clip.stem}",
                speaker_id="bench",
                task_id=task_id,
                audio_path=str(clip),
                prompt_version="bench",
                config_version="bench",
            )
            r = processor.process(req, pcm, sr)
            scored = r.assessment is not None and r.assessment.overall_0_6 is not None
            rows.append(
                {
                    "category": cat,
                    "clip": clip.name,
                    "status": r.status.value,
                    "scored": scored,
                    "issued": r.status is Status.COMPLETED and scored,
                    "reasons": [x.value for x in r.reasons],
                }
            )

    refuse = [x for x in rows if x["category"] in MUST_REFUSE]
    valid = [x for x in rows if x["category"] in VALID]
    leaked = sum(x["issued"] for x in refuse)
    wrongly_refused = sum(not x["scored"] for x in valid)
    to_teacher = sum(x["status"] == Status.REVIEW_REQUIRED.value for x in valid)
    per_cat = {}
    for x in rows:
        c = per_cat.setdefault(x["category"], {"n": 0, "issued": 0, "scored": 0})
        c["n"] += 1
        c["issued"] += x["issued"]
        c["scored"] += x["scored"]
    return {
        "n_clips": len(rows),
        "false_score_rate": {
            "k": leaked,
            "n": len(refuse),
            "rate": round(leaked / len(refuse), 4) if refuse else None,
            "wilson95": wilson(leaked, len(refuse)),
        },
        "false_refusal_rate": {
            "k": wrongly_refused,
            "n": len(valid),
            "rate": round(wrongly_refused / len(valid), 4) if valid else None,
            "wilson95": wilson(wrongly_refused, len(valid)),
        },
        "valid_sent_to_teacher": round(to_teacher / len(valid), 4) if valid else None,
        "per_category": per_cat,
        "rows": rows,
    }


def build_processor(engine: str):
    from aicefr.pipeline import ResponseProcessor
    from aicefr.storage.task_repository import TaskRepository

    if engine == "whisper":
        from aicefr.asr.whisper_adapter import WhisperEngine

        asr = WhisperEngine()
    else:
        from aicefr.asr.fake import FakeAsrEngine

        asr = FakeAsrEngine()
    tasks = TaskRepository(Path(tempfile.mkdtemp()) / "bench_tasks.db")
    return ResponseProcessor(asr, task_lookup=tasks.get)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", type=Path)
    ap.add_argument("--synthesize", type=Path)
    ap.add_argument("--engine", choices=("fake", "whisper"), default="fake")
    ap.add_argument("--task", default="P4")
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()

    if args.synthesize:
        synthesize(args.synthesize)
        print(f"da tao clip tong hop o {args.synthesize}")
        if not args.root:
            return 0
    if not args.root:
        ap.error("can --root")
    result = run(args.root, build_processor(args.engine), args.task)
    fsr, frr = result["false_score_rate"], result["false_refusal_rate"]
    print(f"{result['n_clips']} clip")
    print(f"ty le lot        {fsr['k']}/{fsr['n']}  Wilson95 {fsr['wilson95']}")
    print(f"ty le tu choi nham {frr['k']}/{frr['n']}  Wilson95 {frr['wilson95']}")
    if args.engine == "fake":
        print("CANH BAO: engine gia lap chep moi clip thanh cung mot cau -- chi kiem co che.")
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, indent=1, ensure_ascii=False), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
