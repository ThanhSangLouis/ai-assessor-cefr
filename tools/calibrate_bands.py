#!/usr/bin/env python3
"""Variance restoration and refitted band thresholds for ridge_resp_v2 (D052).

    .venv/bin/python tools/calibrate_bands.py [path-to-sandi-work]

Outputs, next to the model they derive from:

* `$AICEFR_MODEL_DIR/ridge_resp_v2_cal.json` -- a scoring artifact like
  any other, so an administrator activates it on the models screen (FR-36) and
  deactivates it the same way. Nothing in the pipeline changes;
* `$AICEFR_MODEL_DIR/conformal_resp_v2_cal.json` -- its CV+ intervals.

WHY. Ridge with a strong penalty shrinks the spread of its predictions well below
the spread of the labels, and its intercept sits in B2, so the model almost
never says A2 (HUONG_PHAT_TRIEN_TIEP 2.3). The fix has one parameter and two
thresholds:

1. variance restoration: y' = mu + lambda * (y_hat - mu), lambda in
   [1, 1/cv_pcc], chosen to maximise QWK;
2. the two band thresholds refitted for that lambda, maximising macro-recall
   (every band weighted equally, so A2 counts as much as B1).

The transform is linear, so the calibrated model IS a ridge model: every
coefficient times lambda and a new intercept. `contributions()` keeps its
meaning (points on the score shown), and the artifact carries its own
thresholds, so a teacher's corrected score is checked against the thresholds
of the model that graded the response.

HONEST EVALUATION. The table printed is nested: lambda and the thresholds are
fitted only on the inner folds of each outer training set and measured on the
held-out speakers. The parameters written to the artifact are then fitted on
all the out-of-fold predictions. Differences carry a 95% interval from a
cluster bootstrap over speakers.

The calibration_version keeps the word "chua" (not yet): the parameters come
from Speak & Improve learners, not Vietnamese students, so the report keeps its
"not calibrated" warning until the W11 data says otherwise (SRS 11.3).

LICENCE. Both outputs are statistics derived from the Speak & Improve Corpus
2025: they stay in this private repository and are never published without
CUP&A's permission.
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import calibrate_conformal as C  # noqa: E402 - same folds, same refit as the conformal tool

ROOT = C.ROOT
MODELS = C.MODELS
BASE = "ridge_resp_v2"
OUT_MODEL = MODELS / "ridge_resp_v2_cal.json"
OUT_CONFORMAL = MODELS / "conformal_resp_v2_cal.json"

LAMBDAS = np.round(np.arange(1.0, 1.436 + 1e-9, 0.01), 3)
T1_GRID = np.round(np.arange(2.0, 3.5 + 1e-9, 0.05), 2)
T2_GRID = np.round(np.arange(3.0, 4.6 + 1e-9, 0.05), 2)
BOOTSTRAP = 2000
# Guard rails from HUONG_PHAT_TRIEN_TIEP 2.3, applied while choosing thresholds
# (with a margin, since the fitting set flatters its own thresholds).
MIN_PRECISION_A2 = 0.40
MAX_ACCURACY_DROP = 0.02
CALIBRATION_VERSION = "lambda-band-sandi-dev-2026-10-chua-kiem-tren-giong-viet"


def bands(score: np.ndarray, t1: float, t2: float) -> np.ndarray:
    return (score >= t1).astype(int) + (score >= t2).astype(int)


def stretch(pred: np.ndarray, mu: float, lam: float) -> np.ndarray:
    return np.clip(mu + lam * (pred - mu), C.SCORE_MIN, C.SCORE_MAX)


def qwk(a: np.ndarray, b: np.ndarray, k: int = 3) -> float:
    o = np.zeros((k, k))
    for i, j in zip(a, b, strict=True):
        o[i, j] += 1
    w = np.array([[(i - j) ** 2 for j in range(k)] for i in range(k)]) / (k - 1) ** 2
    e = np.outer(o.sum(1), o.sum(0)) / o.sum()
    return float(1 - (w * o).sum() / (w * e).sum()) if (w * e).sum() else 0.0


def macro_recall(truth: np.ndarray, pred: np.ndarray) -> float:
    return float(np.mean([np.mean(pred[truth == c] == c) for c in range(3) if np.any(truth == c)]))


def fit_calibration(pred: np.ndarray, y: np.ndarray, th: dict) -> dict:
    """lambda and two thresholds from out-of-fold predictions `pred` of labels `y`."""
    truth = bands(y, th["A2_B1"], th["B1_B2"])
    floor = float(np.mean(truth == bands(pred, th["A2_B1"], th["B1_B2"]))) - MAX_ACCURACY_DROP
    mu = float(np.mean(y))
    best = None
    for lam in LAMBDAS:
        s = stretch(pred, mu, lam)
        top = (-1.0, 0.0, 0.0)
        for t1 in T1_GRID:
            for t2 in T2_GRID:
                if t2 - t1 < 0.5:
                    continue
                b = bands(s, t1, t2)
                if np.mean(truth == b) < floor:
                    continue
                a2 = b == 0
                if a2.any() and np.mean(truth[a2] == 0) < MIN_PRECISION_A2:
                    continue
                r = macro_recall(truth, b)
                if r > top[0]:
                    top = (r, float(t1), float(t2))
        if top[0] < 0:
            continue
        k = qwk(truth, bands(s, top[1], top[2]))
        if best is None or k > best["qwk"] + 1e-12:
            best = {"mu": mu, "lambda": float(lam), "A2_B1": top[1], "B1_B2": top[2], "qwk": k}
    # No threshold pair passes the guard rails: leave the model as it was.
    return best or {"mu": mu, "lambda": 1.0, **th, "qwk": qwk(truth, bands(pred, **_args(th)))}


def _args(th: dict) -> dict:
    return {"t1": th["A2_B1"], "t2": th["B1_B2"]}


def metrics(y: np.ndarray, score: np.ndarray, t1: float, t2: float, th: dict) -> dict:
    truth = bands(y, th["A2_B1"], th["B1_B2"])
    pred = bands(score, t1, t2)
    a2 = pred == 0
    return {
        "recall_a2": float(np.mean(pred[truth == 0] == 0)),
        "precision_a2": float(np.mean(truth[a2] == 0)) if a2.any() else float("nan"),
        "macro_recall": macro_recall(truth, pred),
        "qwk": qwk(truth, pred),
        "band_accuracy": float(np.mean(truth == pred)),
        "rmse": float(math.sqrt(np.mean((y - score) ** 2))),
        "predicted_a2": int(a2.sum()),
    }


def main() -> int:
    sys.path.insert(0, str(C.WORK))
    import os

    os.chdir(C.WORK)
    import features_resp as F

    base_path = MODELS / f"{BASE}.json"
    base = json.loads(base_path.read_text(encoding="utf-8"))
    order, th = base["feature_order"], base["band_thresholds"]

    keys, X19, y, names = F.build()
    names = list(names)
    j_filler = names.index("filler_ratio")
    X = X19[:, [names.index(f) for f in order]]
    y = np.asarray(y, dtype=float)
    groups = np.array([k[:12] for k in keys])
    n = y.size

    full = C.fit_like_v2(X19, y, j_filler)
    drift = float(np.max(np.abs(C.predict(full, X) - C.predict(base, X))))
    if drift > 1e-6:
        raise SystemExit(f"refit differs from {BASE} by {drift:.2e}: wrong data, stopping")

    splits = list(C.GroupKFold(n_splits=C.N_FOLDS).split(X, y, groups))
    folds, fold_of, oof = [], np.zeros(n, dtype=int), np.zeros(n)
    for k, (tr, te) in enumerate(splits):
        folds.append(C.fit_like_v2(X19[tr], y[tr], j_filler))
        fold_of[te] = k
        oof[te] = C.predict(folds[-1], X[te])

    # Nested: calibration fitted on inner out-of-fold predictions only.
    nested = np.zeros(n)
    t_of = np.zeros((n, 2))
    lams = []
    for tr, te in splits:
        inner_oof = np.zeros(tr.size)
        for itr, ite in C.GroupKFold(n_splits=C.N_FOLDS - 1).split(X[tr], y[tr], groups[tr]):
            m = C.fit_like_v2(X19[tr][itr], y[tr][itr], j_filler)
            inner_oof[ite] = C.predict(m, X[tr][ite])
        cal = fit_calibration(inner_oof, y[tr], th)
        lams.append(cal["lambda"])
        nested[te] = stretch(oof[te], cal["mu"], cal["lambda"])
        t_of[te] = (cal["A2_B1"], cal["B1_B2"])

    def nested_metrics(idx: np.ndarray) -> tuple[dict, dict]:
        before = metrics(y[idx], oof[idx], th["A2_B1"], th["B1_B2"], th)
        truth = bands(y[idx], th["A2_B1"], th["B1_B2"])
        pred = (nested[idx] >= t_of[idx, 0]).astype(int) + (nested[idx] >= t_of[idx, 1]).astype(int)
        a2 = pred == 0
        after = {
            "recall_a2": float(np.mean(pred[truth == 0] == 0)) if np.any(truth == 0) else 0.0,
            "precision_a2": float(np.mean(truth[a2] == 0)) if a2.any() else float("nan"),
            "macro_recall": macro_recall(truth, pred),
            "qwk": qwk(truth, pred),
            "band_accuracy": float(np.mean(truth == pred)),
            "rmse": float(math.sqrt(np.mean((y[idx] - nested[idx]) ** 2))),
            "predicted_a2": int(a2.sum()),
        }
        return before, after

    everyone = np.arange(n)
    before, after = nested_metrics(everyone)
    speakers = np.unique(groups)
    by_speaker = {s: np.flatnonzero(groups == s) for s in speakers}
    rng = np.random.default_rng(20261024)
    deltas = {k: [] for k in ("recall_a2", "qwk", "band_accuracy", "macro_recall")}
    for _ in range(BOOTSTRAP):
        pick = rng.choice(speakers, size=speakers.size, replace=True)
        idx = np.concatenate([by_speaker[s] for s in pick])
        b, a = nested_metrics(idx)
        for k in deltas:
            deltas[k].append(a[k] - b[k])
    ci = {
        k: [round(float(np.percentile(v, 2.5)), 4), round(float(np.percentile(v, 97.5)), 4)]
        for k, v in deltas.items()
    }

    print(f"{n} responses, {speakers.size} speakers; lambda per outer fold {lams}")
    for k in before:
        print(f"  {k:14s} {before[k]:.4f} -> {after[k]:.4f}  {ci.get(k, '')}")

    # The artifact: calibration fitted on all out-of-fold predictions.
    cal = fit_calibration(oof, y, th)
    mu, lam = cal["mu"], cal["lambda"]
    model = dict(base)
    model["model_version"] = "ridge_resp_v2_cal"
    model["calibration_version"] = CALIBRATION_VERSION
    model["coef"] = [lam * c for c in base["coef"]]
    model["intercept"] = mu + lam * (base["intercept"] - mu)
    model["band_thresholds"] = {"A2_B1": cal["A2_B1"], "B1_B2": cal["B1_B2"]}
    base_sha = hashlib.sha256(base_path.read_bytes()).hexdigest()
    model["derived_from"] = BASE
    model["derived_from_sha256"] = base_sha
    model["derivation"] = (
        f"{BASE} with every coefficient times lambda = {lam} and the intercept moved to "
        f"mu + lambda * (intercept - mu), mu = {mu:.4f}; band thresholds refitted. "
        "tools/calibrate_bands.py"
    )
    model["calibration"] = {
        "method": (
            "variance restoration y' = mu + lambda * (y_hat - mu); thresholds refitted for "
            "macro-recall under the guard rails"
        ),
        "guard_rails": {
            "min_precision_a2": MIN_PRECISION_A2,
            "max_band_accuracy_drop": MAX_ACCURACY_DROP,
        },
        "mu": round(mu, 6),
        "lambda": lam,
        "band_thresholds_before": th,
        "fitted_on": "out-of-fold predictions, GroupKFold 5 by speaker, S&I dev P3/P4",
        "nested_evaluation": {
            "before": {k: round(v, 4) for k, v in before.items()},
            "after": {k: round(v, 4) for k, v in after.items()},
            "delta_ci95_cluster_bootstrap": ci,
            "lambda_per_outer_fold": lams,
        },
        "limits": (
            "Fitted on Speak & Improve learners, not Vietnamese students; Vietnamese data only "
            "re-checks these parameters (A-02). Precision A2 must be quoted with recall A2."
        ),
    }
    model["cv_rmse"] = round(after["rmse"], 4)
    model["created_at"] = datetime.now(UTC).isoformat(timespec="seconds")
    OUT_MODEL.write_text(json.dumps(model, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    # Its CV+ intervals: the same folds, each stretched by the same lambda.
    cal_folds = [
        {**f, "coef": [lam * c for c in f["coef"]], "intercept": mu + lam * (f["intercept"] - mu)}
        for f in folds
    ]
    cal_oof = np.zeros(n)
    for k, (_, te) in enumerate(splits):
        cal_oof[te] = C.predict(cal_folds[k], X[te])
    conformal = json.loads((MODELS / "conformal_resp_v2.json").read_text(encoding="utf-8"))
    conformal.update(
        {
            "conformal_version": "cvplus_resp_v2_cal_2026-10-24",
            "model_version": model["model_version"],
            "model_sha256": hashlib.sha256(OUT_MODEL.read_bytes()).hexdigest(),
            "folds": cal_folds,
            "fold_of": [int(v) for v in fold_of],
            "residuals": [round(float(v), 6) for v in np.abs(y - cal_oof)],
            "alpha_curve": [],
            "curve_note": (
                "Fold models of ridge_resp_v2 stretched by the artifact's lambda; the alpha "
                "curve was not re-measured for the calibrated model."
            ),
            "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
        }
    )
    OUT_CONFORMAL.write_text(
        json.dumps(conformal, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"lambda {lam}, thresholds {model['band_thresholds']}; wrote {OUT_MODEL.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
