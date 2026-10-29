#!/usr/bin/env python3
"""Huan luyen bo cham diem o MUC MOT BAI NOI va luu artifact.

Don vi suy luan: mot file audio, mot diem. Dung phan P3 va P4 cua Speak &
Improve vi hai phan nay moi bai thi dung mot file, khop voi cach de tai su
dung: sinh vien thu am mot bai, he thong cham bai do.

Chia du lieu theo NGUOI NOI (GroupKFold) vi P3 va P4 cua cung mot nguoi deu
co mat; chia ngau nhien se lam ro ri va ket qua bi lac quan.

Chay:  python tools/train_scorer.py [duong-dan-sandi-work] [--out FILE] [--group-alpha]

Tai lap: mac dinh script sinh lai DUNG artifact ridge_resp_v1 dang chay (cung
metadata `boundary_margin`, `trained_with`, `band_map_version`,
`calibration_version`) va in SHA-256 cua ma tran dac trung va nhan de lan
sau biet hai lan chay co cung dau vao hay khong. ridge_resp_v2 duoc suy ra
tu v1 bang tools/derive_model_v2.py.

Alpha: artifact dang chay chon alpha bang LOO cua RidgeCV (khong chia theo
nguoi noi). `--group-alpha` chon alpha bang GroupKFold theo nguoi noi, dung
cho lan huan luyen sau; ket qua khac artifact dang chay nen phai doi ten
model_version truoc khi dung.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

import numpy as np
from scipy.stats import pearsonr, spearmanr
from sklearn.linear_model import RidgeCV
from sklearn.model_selection import GroupKFold
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "src/aicefr/scoring/models/ridge_resp_v1.json"

ALPHAS = np.logspace(-2, 4, 40)
OOD_PCT = (1.0, 99.0)  # nguong coi la ngoai phan bo huan luyen

# Metadata ma artifact dang chay mang theo. Giu o day de lan huan luyen lai
# khong lam lech so voi file dang trien khai (truoc day script ghi
# boundary_margin 0,25 va bo qua trained_with).
ARTIFACT_META = {
    "feature_version": "v3",
    "band_map_version": "band-v1",
    "calibration_version": "chua-hieu-chuan",
    "trained_with": {
        "asr_model": "whisper-small",
        "asr_source": "corpus pre-norm CTM (README.txt dong 57)",
        "vad_name": "silero",
        "vad_threshold": 0.5,
        "vad_min_silence_ms": 150,
        "note": "Dac trung huan luyen lay tu ban chep cua Whisper small. Chay that bang"
        " mot he nhan dang khac se lam lech asr_conf_mean, dac trung co he so lon"
        " nhat cua mo hinh.",
    },
    "band_thresholds": {"A2_B1": 2.75, "B1_B2": 3.75},
    "boundary_margin": 0.5,
    "ood_tolerance": 0.5,  # cho phep lech 50% ngoai khoang truoc khi tu choi
}


def _sha256(a: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(a, dtype=np.float64).tobytes()).hexdigest()


def _group_alpha(X: np.ndarray, y: np.ndarray, groups: np.ndarray) -> float:
    """Chon alpha bang GroupKFold theo nguoi noi thay cho LOO."""
    from sklearn.linear_model import Ridge

    best, best_err = ALPHAS[0], np.inf
    for a in ALPHAS:
        err = 0.0
        for tr, te in GroupKFold(n_splits=5).split(X, y, groups):
            sc = StandardScaler().fit(X[tr])
            pred = Ridge(alpha=a).fit(sc.transform(X[tr]), y[tr]).predict(sc.transform(X[te]))
            err += float(np.sum((pred - y[te]) ** 2))
        if err < best_err:
            best, best_err = a, err
    return float(best)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("work", nargs="?", default=str(ROOT.parent / "sandi-work"))
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--group-alpha", action="store_true")
    args = ap.parse_args()
    out = Path(args.out).resolve()
    work = Path(args.work).resolve()
    sys.path.insert(0, str(work))
    os.chdir(work)

    import features_resp as F

    keys, X, y, names = F.build()
    groups = np.array([k[:12] for k in keys])
    print(f"{len(keys)} bai noi tu {len(set(groups))} nguoi noi")

    oof = np.zeros(len(y))
    for tr, te in GroupKFold(n_splits=5).split(X, y, groups):
        sc = StandardScaler().fit(X[tr])
        oof[te] = (
            RidgeCV(alphas=ALPHAS).fit(sc.transform(X[tr]), y[tr]).predict(sc.transform(X[te]))
        )
    rmse = float(np.sqrt(np.mean((oof - y) ** 2)))
    pcc, src = float(pearsonr(y, oof)[0]), float(spearmanr(y, oof)[0])
    print(f"GroupKFold theo nguoi noi: RMSE {rmse:.3f} · PCC {pcc:.3f} · SRC {src:.3f}")

    scaler = StandardScaler().fit(X)
    if args.group_alpha:
        from sklearn.linear_model import Ridge

        model = Ridge(alpha=_group_alpha(X, y, groups)).fit(scaler.transform(X), y)
        model.alpha_ = model.alpha
        alpha_scheme = "GroupKFold 5 theo nguoi noi"
    else:
        model = RidgeCV(alphas=ALPHAS).fit(scaler.transform(X), y)
        alpha_scheme = "LOO cua RidgeCV (khong chia theo nguoi noi)"
    art = {
        "model_version": "ridge_resp_v1",
        **{k: ARTIFACT_META[k] for k in ("feature_version", "band_map_version")},
        **{k: ARTIFACT_META[k] for k in ("calibration_version", "trained_with")},
        "unit_of_inference": "mot bai noi (mot file audio), khong phai ca bai thi",
        "feature_order": list(names),
        "mean": scaler.mean_.tolist(),
        "scale": scaler.scale_.tolist(),
        "coef": model.coef_.tolist(),
        "intercept": float(model.intercept_),
        "alpha": float(model.alpha_),
        "train_n": int(len(y)),
        "train_set": "Speak & Improve 2025 dev, phan P3 va P4 (chi luu he so, khong luu du lieu)",
        "cv_scheme": "GroupKFold 5 theo nguoi noi",
        "cv_rmse": round(rmse, 4),
        "cv_pcc": round(pcc, 4),
        "cv_src": round(src, 4),
        "band_thresholds": ARTIFACT_META["band_thresholds"],
        "boundary_margin": ARTIFACT_META["boundary_margin"],
        # Khoang hop le de phat hien dau vao ngoai phan bo huan luyen.
        "feature_lo": np.percentile(X, OOD_PCT[0], axis=0).tolist(),
        "feature_hi": np.percentile(X, OOD_PCT[1], axis=0).tolist(),
        "ood_tolerance": ARTIFACT_META["ood_tolerance"],
    }
    # Ma bam in ra man hinh chu khong ghi vao artifact, de file sinh lai
    # trung tung byte voi file dang chay khi dau vao khong doi.
    print(f"alpha {model.alpha_:.4g} ({alpha_scheme})")
    print(f"sha256 X {_sha256(X)[:16]} · y {_sha256(y)[:16]}")
    out.write_text(json.dumps(art, indent=2), encoding="utf-8")
    print(f"da luu {out} ({out.stat().st_size} byte)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
