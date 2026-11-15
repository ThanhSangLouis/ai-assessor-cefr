#!/usr/bin/env python3
"""Build the Ridge v4 and fusion (Ridge v4 + DeBERTa-v3 LoRA) scoring artifacts.

    .venv/bin/python tools/build_fusion_artifact.py [SANDI_WORK_V4]

Inputs (outside Git, from the experiment folder `sandi-work/v4`):

* `dev_app.jsonl`: the app's own 18 features for S&I dev P3/P4, extracted with
  this code base (`extract_app.py`), so training sees what production sees;
* `kaggle_out/adapter_run/app_preds_deberta_lora_s42.json`: the DeBERTa scores
  of the app's transcripts, from the SAME run whose adapter is deployed, with
  that run's manifest and reload check (label normalisation, eval error).

Outputs, in `$AICEFR_MODEL_DIR` (W7-S01: corpus statistics never enter Git):

* `ridge_resp_v4.json`: z-score + ridge on the 18 features, alpha chosen by a
  4-fold speaker-grouped inner CV, refitted on all usable rows. Same shape as
  `ridge_resp_v2`, so every reader of an artifact works unchanged.
* `fusion_resp_v4.json`: a superset of `ridge_resp_v4` (the same ridge fields,
  so band thresholds, the duration range and the practice advice keep
  working) plus the stacking weights, the interval width and where the text
  model lives. Read by `aicefr.scoring.fusion.DebertaScorer`.

Method, identical to the experiment (`sandi-work/v4/evaluate.py`, chapter
"Thực nghiệm" section 6.4): five speaker-grouped folds; ridge predictions
out-of-fold and clipped to 1-6; a linear regression of the label on
[ridge, DeBERTa] fitted on those out-of-fold columns. The 90 % interval is
score +/- the finite-sample (1 - alpha) quantile of the out-of-fold absolute
residuals; the same for ridge alone, used when the text model is unavailable.

No timestamp is written, so rebuilding from the same inputs gives the same
bytes and the same SHA-256 pins in `aicefr.scoring.artifacts`.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import sys
from pathlib import Path

import numpy as np
from scipy.stats import pearsonr
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.model_selection import GroupKFold
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parent.parent
MODELS = Path(os.getenv("AICEFR_MODEL_DIR") or ROOT.parent / "aicefr-models")
WORK = Path(sys.argv[1] if len(sys.argv) > 1 else ROOT.parent / "sandi-work" / "v4").resolve()

ALPHAS = np.logspace(-2, 4, 40)
N_FOLDS, N_INNER = 5, 4
ALPHA_CONF = 0.10
OOD_PCT = (1.0, 99.0)
SCORE_MIN, SCORE_MAX = 1.0, 6.0
TEXT_VERSION = "deberta_lora_s42"
BASE_DIR, ADAPTER_DIR = "deberta-v3-base", "deberta_lora_s42"
UNIT = "mot bai noi (mot file audio), khong phai ca bai thi"
LICENCE = (
    "Thống kê dẫn xuất từ Speak & Improve Corpus 2025; không công bố khi chưa có phép của CUP&A."
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ridge_fit(X: np.ndarray, y: np.ndarray, groups: np.ndarray) -> tuple[StandardScaler, Ridge]:
    sc = StandardScaler().fit(X)
    Z = sc.transform(X)
    inner = list(GroupKFold(n_splits=N_INNER).split(Z, y, groups))
    best = min(
        ALPHAS,
        key=lambda a: np.mean(
            [np.mean((Ridge(alpha=a).fit(Z[i], y[i]).predict(Z[j]) - y[j]) ** 2) for i, j in inner]
        ),
    )
    return sc, Ridge(alpha=float(best)).fit(Z, y)


def q_level(residuals: np.ndarray) -> float:
    n = len(residuals)
    return float(
        np.quantile(np.abs(residuals), min(1.0, math.ceil((1 - ALPHA_CONF) * (n + 1)) / n))
    )


def stats(y: np.ndarray, p: np.ndarray) -> dict:
    return {
        "rmse": round(float(np.sqrt(np.mean((p - y) ** 2))), 4),
        "pcc": round(float(pearsonr(p, y)[0]), 4),
    }


def main() -> int:
    v2 = json.loads((MODELS / "ridge_resp_v2.json").read_text(encoding="utf-8"))
    order = v2["feature_order"]
    rows = [json.loads(x) for x in (WORK / "dev_app.jsonl").read_text().splitlines() if x.strip()]
    usable = [r for r in rows if all(r["features"].get(n) is not None for n in order)]
    X = np.array([[r["features"][n] for n in order] for r in usable], dtype=float)
    y = np.array([r["mark"] for r in usable], dtype=float)
    spk = np.array([r["speaker"] for r in usable])
    run = json.loads((WORK / "kaggle_out/adapter_run/run_manifest_lora_adapter.json").read_text())
    check = json.loads((WORK / "kaggle_out/adapter_run/adapter_check.json").read_text())[0]
    text_preds = json.loads(
        (WORK / "kaggle_out/adapter_run/app_preds_deberta_lora_s42.json").read_text()
    )
    t = np.array([text_preds[r["id"]] for r in usable], dtype=float)

    folds = list(GroupKFold(n_splits=N_FOLDS).split(X, y, spk))
    ridge_oof = np.empty(len(y))
    for tr, te in folds:
        sc, m = ridge_fit(X[tr], y[tr], spk[tr])
        ridge_oof[te] = m.predict(sc.transform(X[te]))
    ridge_oof = np.clip(ridge_oof, SCORE_MIN, SCORE_MAX)

    cols = np.column_stack([ridge_oof, t])
    fusion_oof = np.empty(len(y))
    for tr, te in folds:
        fusion_oof[te] = LinearRegression().fit(cols[tr], y[tr]).predict(cols[te])
    fusion_oof = np.clip(fusion_oof, SCORE_MIN, SCORE_MAX)

    # Deployed models: ridge refitted on every usable row; the stacker fitted on
    # the out-of-fold columns (the standard stacking recipe).
    sc, ridge = ridge_fit(X, y, spk)
    stacker = LinearRegression().fit(cols, y)
    q_fusion, q_ridge = q_level(y - fusion_oof), q_level(y - ridge_oof)

    meta = {
        "feature_version": v2["feature_version"],
        "band_map_version": v2["band_map_version"],
        "trained_with": {
            "asr_model": "whisper-small",
            "asr_source": "chuoi xu ly cua app (extract_app.py, mlx-community/whisper-small-mlx)",
            "vad_name": "silero",
        },
        "unit_of_inference": UNIT,
        "feature_order": order,
        "mean": sc.mean_.tolist(),
        "scale": sc.scale_.tolist(),
        "coef": ridge.coef_.tolist(),
        "intercept": float(ridge.intercept_),
        "alpha": float(ridge.alpha),
        "train_n": int(len(y)),
        "train_set": (
            "Speak & Improve 2025 dev P3+P4, đặc trưng do app trích "
            "(chỉ lưu hệ số, không lưu dữ liệu)"
        ),
        "cv_scheme": (
            "GroupKFold 5 theo nguoi noi; alpha chon bang GroupKFold 4 long trong fold huan luyen"
        ),
        "band_thresholds": v2["band_thresholds"],
        "boundary_margin": v2["boundary_margin"],
        "feature_lo": np.percentile(X, OOD_PCT[0], axis=0).tolist(),
        "feature_hi": np.percentile(X, OOD_PCT[1], axis=0).tolist(),
        "ood_tolerance": v2["ood_tolerance"],
        "licence": LICENCE,
    }
    r_stats = stats(y, ridge_oof)
    ridge_art = {
        "model_version": "ridge_resp_v4",
        "calibration_version": "chua-hieu-chuan",
        **meta,
        "cv_rmse": r_stats["rmse"],
        "cv_pcc": r_stats["pcc"],
    }
    ridge_path = MODELS / "ridge_resp_v4.json"
    ridge_path.write_text(json.dumps(ridge_art, indent=2, ensure_ascii=False), encoding="utf-8")

    reference = {}
    for j, name in enumerate(order):
        col = X[:, j]
        if np.ptp(col) == 0:
            continue
        r = float(pearsonr(col, y)[0])
        reference[name] = {
            "deciles": [round(float(v), 6) for v in np.percentile(col, range(0, 101, 10))],
            "higher_is_better": r > 0,
            "pearson_r": round(r, 4),
        }

    base, adapter = MODELS / BASE_DIR, MODELS / ADAPTER_DIR
    f_stats = stats(y, fusion_oof)
    lo, hi = np.clip(fusion_oof - q_fusion, 1, 6), np.clip(fusion_oof + q_fusion, 1, 6)
    fusion_art = {
        "model_version": "fusion_resp_v4",
        "calibration_version": "oofq90_fusion_resp_v4",
        **meta,
        "cv_rmse": f_stats["rmse"],
        "cv_pcc": f_stats["pcc"],
        "ridge_model": "ridge_resp_v4",
        "ridge_model_sha256": sha256(ridge_path),
        "ridge_cv_rmse": r_stats["rmse"],
        "fusion": {
            "intercept": float(stacker.intercept_),
            "w_ridge": float(stacker.coef_[0]),
            "w_text": float(stacker.coef_[1]),
            "inputs": "ridge cat ve 1-6; diem van ban giu nguyen, khong cat",
        },
        "interval": {
            "method": "oof-residual-quantile",
            "alpha": ALPHA_CONF,
            "q_fusion": round(q_fusion, 4),
            "q_ridge": round(q_ridge, 4),
            "oof_coverage": round(float(np.mean((y >= lo) & (y <= hi))), 4),
            "oof_mean_width": round(float(np.mean(hi - lo)), 4),
        },
        "indicator_reference": reference,
        "text_model": {
            "version": TEXT_VERSION,
            "base_dir": BASE_DIR,
            "base_revision": "microsoft/deberta-v3-base@8ccc9b6f36199bec6961081d44eb72fb3f7353f3",
            "base_sha256": {f: sha256(base / f) for f in ("config.json", "model.safetensors")},
            "adapter_dir": ADAPTER_DIR,
            "adapter_sha256": {
                f: sha256(adapter / f)
                for f in (
                    "adapter_config.json",
                    "adapter_model.safetensors",
                    "tokenizer.json",
                    "tokenizer_config.json",
                )
            },
            "lora_r": 16,
            "lora_alpha": 32,
            "max_length": run["max_len"],
            "target_norm": run["target_norm"],
            "trained_on": "S&I 2025 train P3+P4, ban chep CTM; epoch chon theo dev",
            "eval_rmse": round(check["eval_after_reload"]["rmse"], 4),
        },
    }
    fusion_path = MODELS / "fusion_resp_v4.json"
    fusion_path.write_text(json.dumps(fusion_art, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"usable rows {len(y)} / {len(rows)}; ridge alpha {ridge.alpha:.4g}")
    print(f"ridge v4 OOF {r_stats}; fusion OOF {f_stats}")
    print(
        f"stacker intercept {stacker.intercept_:.4f}, "
        f"w_ridge {stacker.coef_[0]:.4f}, w_text {stacker.coef_[1]:.4f}"
    )
    print(
        f"q90 fusion {q_fusion:.4f}, ridge {q_ridge:.4f}; fusion interval {fusion_art['interval']}"
    )
    for p in (ridge_path, fusion_path):
        print(f"{p.stem}: {sha256(p)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
