#!/usr/bin/env python3
"""Hieu chinh lop tin cay (Trust Layer) cho mo hinh ridge_resp_v2 bang CV+.

    .venv/bin/python tools/calibrate_conformal.py [duong-dan-sandi-work]

Dau ra: `src/aicefr/scoring/models/conformal_resp_v2.json`.

VI SAO CV+ CHU KHONG PHAI SPLIT CONFORMAL. Split conformal can mot tap hieu
chinh ma mo hinh CHUA THAY. Mo hinh dang chay da hoc tren ca 876 bai, nen moi
phan du tinh tren 876 bai do la phan du trong mau -- qua nho, khoang qua hep,
bao dam mat. CV+ (Barber, Candes, Ramdas, Tibshirani 2021, "Predictive
inference with the jackknife+") dung dung nam mo hinh theo fold da co san:

  * moi bai i co phan du R_i = |y_i - f_{-k(i)}(x_i)| do mo hinh KHONG thay no;
  * voi bai moi x: can duoi la phan vi floor(alpha (n+1)) cua
    {f_{-k(i)}(x) - R_i}, can tren la phan vi ceil((1-alpha)(n+1)) cua
    {f_{-k(i)}(x) + R_i}.

Bao dam ly thuyet: do phu >= 1 - 2*alpha - sqrt(2/n) (Barber 2021, Dinh ly 4);
thuc nghiem thuong sat 1 - alpha. Muc phu thuc nghiem duoi day duoc DO, khong
gia dinh.

DANH GIA KHONG LAC QUAN. Duong alpha -> do phu -> tai giang vien duoc do bang CV
LONG NHAU: voi moi fold ngoai k, CV+ duoc dung lai CHI tu bon fold con lai (bon
mo hinh trong + phan du trong), roi ap len bai cua fold k. Dung thang nam mo
hinh ngoai thi bon trong nam mo hinh da hoc chinh bai dang danh gia.

GIAY PHEP. Tep dau ra la thong ke dan xuat tu Speak & Improve Corpus 2025. Giay
phep cam cong bo khi chua duoc CUP&A cho phep: tep chi duoc nam trong repo
RIENG TU nay, khong chep sang repo cong khai.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
from scipy.stats import pearsonr
from sklearn.linear_model import RidgeCV
from sklearn.model_selection import GroupKFold
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parent.parent
MODELS = ROOT / "src/aicefr/scoring/models"
MODEL_NAME = "ridge_resp_v2"
OUT = MODELS / "conformal_resp_v2.json"
WORK = Path(sys.argv[1] if len(sys.argv) > 1 else ROOT.parent / "sandi-work").resolve()

ALPHAS = np.logspace(-2, 4, 40)  # giong tools/train_scorer.py
N_FOLDS = 5
ALPHA_GRID = (0.05, 0.10, 0.15, 0.20, 0.25, 0.30)
ALPHA_DEFAULT = 0.10
SCORE_MIN, SCORE_MAX = 1.0, 6.0


def fit(X: np.ndarray, y: np.ndarray) -> dict:
    """Mot mo hinh fold, luu duoi dang so de doc lai khong can sklearn."""
    sc = StandardScaler().fit(X)
    m = RidgeCV(alphas=ALPHAS).fit(sc.transform(X), y)
    return {
        "mean": [float(v) for v in sc.mean_],
        "scale": [float(v) for v in sc.scale_],
        "coef": [float(v) for v in m.coef_],
        "intercept": float(m.intercept_),
    }


def fit_like_v2(X19: np.ndarray, y: np.ndarray, j_filler: int) -> dict:
    """Hoc nhu v1 (19 dac trung) roi bo `filler_ratio` dung nhu `derive_model_v2.py`.

    Hoc thang tren 18 dac trung KHONG cho ra mo hinh dang chay: `filler_ratio`
    khac 0 o 5/876 bai huan luyen (toi da 0,123), nen bo cot do truoc khi hoc
    lam RidgeCV chon alpha khac (11,9 thay vi 70,2) va du doan lech toi 0,24
    diem. Phan du cua mot mo hinh khac khong hieu chinh duoc mo hinh nay.
    """
    m = fit(X19, y)
    shift = m["coef"][j_filler] * ((0.0 - m["mean"][j_filler]) / m["scale"][j_filler])
    out = {k: [v for i, v in enumerate(m[k]) if i != j_filler] for k in ("mean", "scale", "coef")}
    out["intercept"] = m["intercept"] + shift
    return out


def predict(model: dict, X: np.ndarray) -> np.ndarray:
    z = (X - np.array(model["mean"])) / np.array(model["scale"])
    raw = z @ np.array(model["coef"]) + model["intercept"]
    return np.clip(raw, SCORE_MIN, SCORE_MAX)


def cv_plus(
    preds_by_fold: np.ndarray, residuals: np.ndarray, fold_of: np.ndarray, alpha: float
) -> tuple[np.ndarray, np.ndarray]:
    """Khoang CV+ cho nhieu bai cung luc.

    `preds_by_fold[k, j]`: du doan cua mo hinh fold k cho bai moi j.
    """
    n = residuals.size
    centers = preds_by_fold[fold_of]  # (n, m): f_{-k(i)}(x_j)
    lows = np.sort(centers - residuals[:, None], axis=0)
    highs = np.sort(centers + residuals[:, None], axis=0)
    lo_rank = math.floor(alpha * (n + 1))
    hi_rank = math.ceil((1 - alpha) * (n + 1))
    lo = lows[lo_rank - 1] if lo_rank >= 1 else np.full(lows.shape[1], SCORE_MIN)
    hi = highs[hi_rank - 1] if hi_rank <= n else np.full(highs.shape[1], SCORE_MAX)
    return np.clip(lo, SCORE_MIN, SCORE_MAX), np.clip(hi, SCORE_MIN, SCORE_MAX)


def band_index(score: np.ndarray, thresholds: dict) -> np.ndarray:
    return (score >= thresholds["A2_B1"]).astype(int) + (score >= thresholds["B1_B2"]).astype(int)


def main() -> int:
    sys.path.insert(0, str(WORK))
    os.chdir(WORK)
    import features_resp as F

    artifact_path = MODELS / f"{MODEL_NAME}.json"
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    order = artifact["feature_order"]
    th = artifact["band_thresholds"]

    keys, X19, y, names = F.build()
    names = list(names)
    j_filler = names.index("filler_ratio")
    # Hoc tren 19 cot nhu v1 (filler that); du doan tren 18 cot cua v2, tuc
    # filler = 0 -- dung dau vao luc chay, vi Whisper khong ghi tu dem.
    X = X19[:, [names.index(f) for f in order]]
    y = np.asarray(y, dtype=float)
    groups = np.array([k[:12] for k in keys])
    n = y.size
    print(f"{n} bai noi tu {len(set(groups))} nguoi noi, {len(order)} dac trung")

    # Kiem tai lap: mo hinh toan bo hoc lai phai cho cung du doan voi artifact.
    full = fit_like_v2(X19, y, j_filler)
    drift = float(np.max(np.abs(predict(full, X) - predict(artifact, X))))
    print(f"lech du doan giua mo hinh hoc lai va artifact: {drift:.2e}")
    if drift > 1e-6:
        raise SystemExit("du lieu hoac quy trinh khac luc huan luyen artifact -- dung lai")

    splits = list(GroupKFold(n_splits=N_FOLDS).split(X, y, groups))
    folds, fold_of, oof = [], np.zeros(n, dtype=int), np.zeros(n)
    for k, (tr, te) in enumerate(splits):
        folds.append(fit_like_v2(X19[tr], y[tr], j_filler))
        fold_of[te] = k
        oof[te] = predict(folds[-1], X[te])
    residuals = np.abs(y - oof)
    print(f"OOF RMSE {math.sqrt(np.mean((y - oof) ** 2)):.4f}")

    # Duong alpha bang CV long nhau.
    curve = []
    for alpha in ALPHA_GRID:
        cover, width, single, wrong_single = [], [], [], []
        for tr, te in splits:
            inner = list(GroupKFold(n_splits=N_FOLDS - 1).split(X[tr], y[tr], groups[tr]))
            inner_models, inner_fold, inner_oof = (
                [],
                np.zeros(tr.size, dtype=int),
                np.zeros(tr.size),
            )
            for j, (itr, ite) in enumerate(inner):
                inner_models.append(fit_like_v2(X19[tr][itr], y[tr][itr], j_filler))
                inner_fold[ite] = j
                inner_oof[ite] = predict(inner_models[-1], X[tr][ite])
            preds = np.stack([predict(mdl, X[te]) for mdl in inner_models])
            lo, hi = cv_plus(preds, np.abs(y[tr] - inner_oof), inner_fold, alpha)
            b_lo, b_hi = band_index(lo, th), band_index(hi, th)
            one = b_lo == b_hi
            cover += list((y[te] >= lo) & (y[te] <= hi))
            width += list(hi - lo)
            single += list(one)
            wrong_single += list(one & (band_index(y[te], th) != b_lo))
        n_single = int(np.sum(single))
        curve.append(
            {
                "alpha": alpha,
                "coverage": round(float(np.mean(cover)), 4),
                "mean_width": round(float(np.mean(width)), 4),
                "auto_band_rate": round(n_single / n, 4),
                "teacher_load": round(1 - n_single / n, 4),
                "gross_error_rate_in_auto": (
                    round(float(np.sum(wrong_single)) / n_single, 4) if n_single else None
                ),
            }
        )
        c = curve[-1]
        print(
            f"alpha {alpha:.2f}: phu {c['coverage']:.3f}, rong {c['mean_width']:.2f}, "
            f"tu phat band {c['auto_band_rate']:.1%}, sai band trong nhom tu phat "
            f"{c['gross_error_rate_in_auto']}"
        )

    # Phan bo tham chieu cho chi bao theo tieu chi.
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

    out = {
        "conformal_version": "cvplus_resp_v2_2026-10-03",
        "model_version": MODEL_NAME,
        "model_sha256": hashlib.sha256(artifact_path.read_bytes()).hexdigest(),
        "method": "cv+",
        "method_ref": "Barber, Candes, Ramdas, Tibshirani (2021), Annals of Statistics 49(1)",
        "alpha_default": ALPHA_DEFAULT,
        "n": n,
        "n_folds": N_FOLDS,
        "fold_scheme": "GroupKFold theo nguoi noi, cung cach chia voi tools/train_scorer.py",
        "feature_order": order,
        "folds": folds,
        "fold_of": [int(v) for v in fold_of],
        "residuals": [round(float(v), 6) for v in residuals],
        "alpha_curve": curve,
        "curve_note": (
            "Do bang CV long nhau tren S&I dev P3/P4; khong phai so do tren nguoi hoc Viet."
        ),
        "indicator_reference": reference,
        "data": artifact["train_set"],
        "license_note": (
            "Thong ke dan xuat tu Speak & Improve Corpus 2025. Chi luu trong repo rieng tu; "
            "khong cong bo khi chua co phep cua CUP&A."
        ),
        "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"da ghi {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
