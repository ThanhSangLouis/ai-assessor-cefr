"""Write the synthetic scoring artifacts the tests run on (W7-S01).

    .venv/bin/python tools/make_fake_models.py [OUT_DIR]

The real artifacts are statistics derived from the Speak & Improve Corpus 2025
and live outside Git (`AICEFR_MODEL_DIR`, `aicefr.scoring.artifacts`). Tests
need files of the same shape, so this script invents a population of spoken
responses -- a latent proficiency per speaker, each measurement a noisy linear
function of it, ranges chosen by hand for a one-minute answer -- and runs the
SAME procedures as the real tools on it:

* `ridge_resp_v1`: RidgeCV on 19 standardised features, GroupKFold by speaker;
* `ridge_resp_v2`: v1 with `filler_ratio` dropped and its term folded into the
  intercept (`tools/derive_model_v2.py`);
* `ridge_resp_v2_cal`: v2 stretched around its mean with refitted thresholds
  (`tools/calibrate_bands.py`);
* `conformal_resp_v2`, `conformal_resp_v2_cal`: CV+ folds, residuals, a
  coverage curve measured on a held-out synthetic set
  (`tools/calibrate_conformal.py`);
* `ridge_v3`: a whole-exam model with no `unit_of_inference`, so the guard
  that refuses it has something to refuse.

No number here comes from the corpus. The output, and a SHA256SUMS file the
test configuration pins, go to `tests/fixtures/models` by default.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import sys
from pathlib import Path

import numpy as np
from sklearn.linear_model import RidgeCV
from sklearn.model_selection import GroupKFold
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "tests/fixtures/models"

SEED = 20261032
SPEAKERS, PER_SPEAKER = 220, 4
ALPHAS = np.logspace(-2, 4, 40)
N_FOLDS = 5
ALPHA_GRID = (0.05, 0.10, 0.15, 0.20, 0.25, 0.30)
SCORE_MIN, SCORE_MAX = 1.0, 6.0
CENTRE = 3.3
STAMP = "2026-10-25T00:00:00+00:00"
LICENCE = "Dữ liệu tổng hợp (tools/make_fake_models.py), không lấy từ Speak & Improve."

# name: (value at CENTRE, change per point of proficiency, noise sd, floor, ceiling)
FEATURES: dict[str, tuple[float, float, float, float, float]] = {
    "n_words": (95.0, 28.0, 25.0, 8.0, 260.0),
    "words_per_sec": (1.7, 0.45, 0.35, 0.2, 4.0),
    "total_dur": (45.0, 3.0, 9.0, 8.0, 62.0),
    "mean_word_len": (4.1, 0.15, 0.3, 2.8, 6.0),
    "ttr": (0.6, -0.03, 0.08, 0.2, 1.0),
    "log_uniq": (3.9, 0.3, 0.3, 1.5, 5.5),
    "asr_conf_mean": (0.78, 0.06, 0.06, 0.3, 0.99),
    "asr_conf_geo": (0.72, 0.07, 0.07, 0.2, 0.99),
    "vad_silence_ratio": (0.3, -0.05, 0.08, 0.02, 0.8),
    "vad_mean_pause": (0.75, -0.15, 0.35, 0.1, 3.0),
    "vad_pause_per_min": (18.0, -2.0, 5.0, 2.0, 50.0),
    "vad_long_pause_ratio": (0.22, -0.07, 0.08, 0.0, 0.8),
    "vad_pause_sd": (0.55, -0.1, 0.3, 0.02, 2.5),
    "vad_mean_seg_len": (6.0, 2.0, 4.0, 0.5, 25.0),
    "vad_n_seg_per_min": (10.0, -1.5, 4.0, 1.0, 40.0),
    "vad_articulation_rate": (2.9, 0.35, 0.4, 1.0, 6.0),
    "vad_onset_delay": (0.9, -0.2, 0.6, 0.0, 6.0),
    "vad_speech_sec": (33.0, 4.0, 8.0, 3.0, 58.0),
}
V1_ORDER = list(FEATURES)[:2] + ["filler_ratio"] + list(FEATURES)[2:]
V2_ORDER = list(FEATURES)

# The metadata the real training script writes (`tools/train_scorer.py`): which
# recogniser and detector, band thresholds, margins. Configuration, not
# statistics, and the tests check the two agree.
_spec = importlib.util.spec_from_file_location("train_scorer", ROOT / "tools/train_scorer.py")
_train = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_train)
META = _train.ARTIFACT_META


def population(rng: np.random.Generator, speakers: int, noise: float = 1.0):
    """Feature rows (V1_ORDER), labels and speaker groups for `speakers` people."""
    level = rng.normal(CENTRE, 0.8, speakers)
    p = np.repeat(level, PER_SPEAKER) + rng.normal(0, 0.25, speakers * PER_SPEAKER)
    columns = {}
    for name, (mid, slope, sd, lo, hi) in FEATURES.items():
        raw = mid + slope * (p - CENTRE) + rng.normal(0, sd * noise, p.size)
        columns[name] = np.clip(raw, lo, hi)
    # The recogniser drops hesitation words: zero but for a handful of rows.
    filler = np.zeros(p.size)
    filler[rng.choice(p.size, 5, replace=False)] = rng.uniform(0.01, 0.1, 5)
    columns["filler_ratio"] = filler
    X = np.column_stack([columns[n] for n in V1_ORDER])
    y = np.clip(p + rng.normal(0, 0.45, p.size), SCORE_MIN, SCORE_MAX)
    return X, y, np.repeat(np.arange(speakers), PER_SPEAKER)


def fit(X: np.ndarray, y: np.ndarray) -> dict:
    sc = StandardScaler().fit(X)
    m = RidgeCV(alphas=ALPHAS).fit(sc.transform(X), y)
    return {
        "mean": [float(v) for v in sc.mean_],
        "scale": [float(v) for v in sc.scale_],
        "coef": [float(v) for v in m.coef_],
        "intercept": float(m.intercept_),
        "alpha": float(m.alpha_),
    }


def drop_filler(m: dict) -> dict:
    """`tools/derive_model_v2.py`: remove the term, fold its value at zero into the intercept."""
    j = V1_ORDER.index("filler_ratio")
    shift = m["coef"][j] * ((0.0 - m["mean"][j]) / m["scale"][j])
    out = {k: [v for i, v in enumerate(m[k]) if i != j] for k in ("mean", "scale", "coef")}
    out["intercept"] = m["intercept"] + shift
    return out


def rank(v: np.ndarray) -> np.ndarray:
    return np.argsort(np.argsort(v))


def predict(m: dict, X: np.ndarray) -> np.ndarray:
    z = (X - np.array(m["mean"])) / np.array(m["scale"])
    return np.clip(z @ np.array(m["coef"]) + m["intercept"], SCORE_MIN, SCORE_MAX)


def stretch(m: dict, mu: float, lam: float) -> dict:
    """`tools/calibrate_bands.py`: y' = mu + lam * (y - mu), applied to the coefficients."""
    out = dict(m)
    out["coef"] = [c * lam for c in m["coef"]]
    out["intercept"] = mu + lam * (m["intercept"] - mu)
    return out


def cv_plus(preds: np.ndarray, residuals: np.ndarray, fold_of: np.ndarray, alpha: float):
    n = residuals.size
    centres = preds[fold_of]
    lows = np.sort(centres - residuals[:, None], axis=0)
    highs = np.sort(centres + residuals[:, None], axis=0)
    lo_rank, hi_rank = math.floor(alpha * (n + 1)), math.ceil((1 - alpha) * (n + 1))
    lo = lows[lo_rank - 1] if lo_rank >= 1 else np.full(lows.shape[1], SCORE_MIN)
    hi = highs[hi_rank - 1] if hi_rank <= n else np.full(highs.shape[1], SCORE_MAX)
    return np.clip(lo, SCORE_MIN, SCORE_MAX), np.clip(hi, SCORE_MIN, SCORE_MAX)


def band_index(score: np.ndarray, th: dict) -> np.ndarray:
    return (score >= th["A2_B1"]).astype(int) + (score >= th["B1_B2"]).astype(int)


def write(name: str, payload: dict) -> str:
    path = OUT / f"{name}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def response_model(X, y, groups, version: str) -> tuple[dict, list]:
    """v1: the fitted model plus its metadata, and the GroupKFold splits it used."""
    splits = list(GroupKFold(n_splits=N_FOLDS).split(X, y, groups))
    oof = np.zeros(y.size)
    for tr, te in splits:
        oof[te] = predict(fit(X[tr], y[tr]), X[te])
    full = fit(X, y)
    lo, hi = np.percentile(X, 2, axis=0), np.percentile(X, 98, axis=0)
    return {
        "model_version": version,
        **{k: META[k] for k in ("feature_version", "band_map_version", "calibration_version")},
        "trained_with": META["trained_with"],
        "unit_of_inference": "mot bai noi (mot file audio), khong phai ca bai thi",
        "feature_order": V1_ORDER,
        "mean": full["mean"],
        "scale": full["scale"],
        "coef": full["coef"],
        "intercept": full["intercept"],
        "alpha": full["alpha"],
        "train_n": int(y.size),
        "train_set": LICENCE,
        "cv_scheme": "GroupKFold 5 theo nguoi noi",
        "cv_rmse": round(float(np.sqrt(np.mean((y - oof) ** 2))), 4),
        "cv_pcc": round(float(np.corrcoef(y, oof)[0, 1]), 4),
        "cv_src": round(float(np.corrcoef(rank(y), rank(oof))[0, 1]), 4),
        "band_thresholds": META["band_thresholds"],
        "boundary_margin": META["boundary_margin"],
        "feature_lo": [float(v) for v in lo],
        "feature_hi": [float(v) for v in hi],
        "ood_tolerance": META["ood_tolerance"],
    }, splits


def conformal(
    model_name, model_sha, folds, X, y, fold_of, curve, reference, version, alpha_default=0.10
):
    oof = np.zeros(y.size)
    for k, f in enumerate(folds):
        oof[fold_of == k] = predict(f, X[fold_of == k])
    return {
        "conformal_version": version,
        "model_version": model_name,
        "model_sha256": model_sha,
        "method": "cv+",
        "method_ref": "Barber, Candes, Ramdas, Tibshirani (2021), Annals of Statistics 49(1)",
        "alpha_default": alpha_default,
        "n": int(y.size),
        "n_folds": N_FOLDS,
        "fold_scheme": "GroupKFold theo nguoi noi",
        "feature_order": V2_ORDER,
        "folds": folds,
        "fold_of": [int(v) for v in fold_of],
        "residuals": [round(float(v), 6) for v in np.abs(y - oof)],
        "alpha_curve": curve,
        "curve_note": "Đo trên một tập tổng hợp giữ riêng, không phải dữ liệu thật.",
        "indicator_reference": reference,
        "data": LICENCE,
        "license_note": LICENCE,
        "created_at": STAMP,
    }


def coverage_curve(folds, X, y, fold_of, X_test, y_test, th) -> list[dict]:
    oof = np.zeros(y.size)
    for k, f in enumerate(folds):
        oof[fold_of == k] = predict(f, X[fold_of == k])
    residuals = np.abs(y - oof)
    preds = np.stack([predict(f, X_test) for f in folds])
    curve = []
    for alpha in ALPHA_GRID:
        lo, hi = cv_plus(preds, residuals, fold_of, alpha)
        one = band_index(lo, th) == band_index(hi, th)
        wrong = one & (band_index(y_test, th) != band_index(lo, th))
        curve.append(
            {
                "alpha": alpha,
                "coverage": round(float(np.mean((y_test >= lo) & (y_test <= hi))), 4),
                "mean_width": round(float(np.mean(hi - lo)), 4),
                "auto_band_rate": round(float(np.mean(one)), 4),
                "teacher_load": round(1 - float(np.mean(one)), 4),
                "gross_error_rate_in_auto": (
                    round(float(wrong.sum() / one.sum()), 4) if one.any() else None
                ),
            }
        )
    return curve


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(SEED)
    X19, y, groups = population(rng, SPEAKERS)
    X19_test, y_test, _ = population(rng, 4 * SPEAKERS)
    keep = [V1_ORDER.index(n) for n in V2_ORDER]
    X, X_test = X19[:, keep], X19_test[:, keep]
    sums: dict[str, str] = {}

    v1, splits = response_model(X19, y, groups, "ridge_resp_v1")
    sums["ridge_resp_v1"] = write("ridge_resp_v1", v1)

    v2 = dict(v1, **drop_filler(v1))
    v2["feature_order"] = V2_ORDER
    j = V1_ORDER.index("filler_ratio")
    v2["feature_lo"] = [v for i, v in enumerate(v1["feature_lo"]) if i != j]
    v2["feature_hi"] = [v for i, v in enumerate(v1["feature_hi"]) if i != j]
    v2.update(
        model_version="ridge_resp_v2",
        derived_from="ridge_resp_v1",
        derivation=(
            "Bỏ đặc trưng filler_ratio: nó là hằng số 0 trong toàn bộ tập huấn luyện"
            " (feature_lo = feature_hi = 0) nên hệ số của nó không xác định được."
            " Số hạng cũ được cộng vào intercept nên điểm TRÙNG KHỚP TUYỆT ĐỐI với"
            " ridge_resp_v1 ở mọi đầu vào có filler_ratio = 0."
        ),
        derived_at=STAMP,
        cv_note="PCC và RMSE giữ nguyên của ridge_resp_v1 vì không huấn luyện lại.",
    )
    sums["ridge_resp_v2"] = write("ridge_resp_v2", v2)

    fold_of = np.zeros(y.size, dtype=int)
    folds = []
    for k, (tr, te) in enumerate(splits):
        f = fit(X19[tr], y[tr])
        f.pop("alpha")
        folds.append(drop_filler(f))
        fold_of[te] = k

    reference = {}
    for i, name in enumerate(V2_ORDER):
        col = X[:, i]
        r = float(np.corrcoef(col, y)[0, 1])
        reference[name] = {
            "deciles": [round(float(v), 6) for v in np.percentile(col, range(0, 101, 10))],
            "higher_is_better": r > 0,
            "pearson_r": round(r, 4),
        }
    curve = coverage_curve(folds, X, y, fold_of, X_test, y_test, META["band_thresholds"])
    sums["conformal_resp_v2"] = write(
        "conformal_resp_v2",
        conformal(
            "ridge_resp_v2",
            sums["ridge_resp_v2"],
            folds,
            X,
            y,
            fold_of,
            curve,
            reference,
            "cvplus_resp_v2_fake",
        ),
    )

    mu, lam = float(np.mean(y)), 1.3
    cal_th = {"A2_B1": 2.7, "B1_B2": 3.8}
    cal = dict(v2, **stretch(v2, mu, lam))
    cal.update(
        model_version="ridge_resp_v2_cal",
        calibration_version="lambda-band-tong-hop-chua-kiem-tren-giong-viet",
        band_thresholds=cal_th,
        derived_from="ridge_resp_v2",
        derived_from_sha256=sums["ridge_resp_v2"],
        derivation=f"ridge_resp_v2 kéo giãn quanh mu với lambda = {lam}; ngưỡng band ước lại.",
        calibration={
            "method": "lambda-band",
            "guard_rails": {"min_a2_precision": 0.4, "max_accuracy_drop": 0.02},
            "mu": mu,
            "lambda": lam,
            "band_thresholds_before": META["band_thresholds"],
            "fitted_on": LICENCE,
            "nested_evaluation": {"note": "không đánh giá: dữ liệu tổng hợp"},
            "limits": "Chỉ để kiểm thử.",
        },
        created_at=STAMP,
    )
    sums["ridge_resp_v2_cal"] = write("ridge_resp_v2_cal", cal)
    cal_folds = [stretch(f, mu, lam) for f in folds]
    sums["conformal_resp_v2_cal"] = write(
        "conformal_resp_v2_cal",
        conformal(
            "ridge_resp_v2_cal",
            sums["ridge_resp_v2_cal"],
            cal_folds,
            X,
            y,
            fold_of,
            [],
            reference,
            "cvplus_resp_v2_cal_fake",
        ),
    )

    # Whole exam sittings: longer, so less noisy, so a better-looking correlation.
    Xe, ye, ge = population(rng, SPEAKERS, noise=0.4)
    exam = response_model(Xe, ye, ge, "ridge_v3")[0]
    v3 = {
        k: exam[k]
        for k in (
            "model_version",
            "feature_version",
            "feature_order",
            "mean",
            "scale",
            "coef",
            "intercept",
            "alpha",
            "train_n",
            "train_set",
            "cv_rmse",
            "cv_pcc",
            "cv_src",
            "band_thresholds",
            "boundary_margin",
        )
    }
    sums["ridge_v3"] = write("ridge_v3", v3)

    (OUT / "SHA256SUMS").write_text(
        "".join(f"{digest}  {name}.json\n" for name, digest in sorted(sums.items())),
        encoding="utf-8",
    )
    print(
        f"v1 PCC {v1['cv_pcc']}, v3 PCC {v3['cv_pcc']}; curve "
        + ", ".join(f"{c['alpha']}:{c['coverage']}/{c['gross_error_rate_in_auto']}" for c in curve)
    )
    print(f"đã ghi {len(sums)} artifact vào {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
