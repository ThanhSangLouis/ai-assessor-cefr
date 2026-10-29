"""Trust Layer: khoang diem co bao dam thong ke (CV+) va chi bao theo tieu chi. D022.

Tai sao co module nay. Truoc day mot bai bi chuyen giang vien vi "diem nam
trong +-0,5 quanh nguong band" -- 0,5 la con so dat tay. Thay vao do, CV+
(Barber, Candes, Ramdas, Tibshirani 2021) cho moi bai mot khoang [low, high]
voi muc phu danh nghia 1 - alpha. Khoang cham hon mot band thi may khong du
can cu de phat band: chuyen giang vien voi `SCORE_NEAR_BOUNDARY`.

Cach tinh, cho mot bai moi x (xem `tools/calibrate_conformal.py`):

    can duoi = phan vi thu floor(alpha (n+1)) cua { f_{-k(i)}(x) - R_i }
    can tren = phan vi thu ceil((1-alpha)(n+1)) cua { f_{-k(i)}(x) + R_i }

voi f_{-k} la nam mo hinh theo fold va R_i la phan du out-of-fold cua bai
hieu chinh i. Bao dam ly thuyet >= 1 - 2*alpha; muc phu DO DUOC tren S&I nam
trong `alpha_curve` cua artifact (alpha 0,10 -> 0,899).

Artifact gan voi DUNG MOT mo hinh qua SHA-256: hieu chinh cua mot mo hinh
khong dung duoc cho mo hinh khac, va dung nham thi khoang van tron tria ma sai.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

from aicefr.contracts import Band, Criterion, CriterionIndicator, FeatureSet, ScoreInterval

MODEL_DIR = Path(__file__).parent / "models"
SCORE_MIN, SCORE_MAX = 1.0, 6.0


class CalibrationMismatchError(ValueError):
    """Artifact hieu chinh khong thuoc mo hinh dang nap."""


def bands_between(low: float, high: float, thresholds: dict[str, float]) -> list[Band]:
    """Moi band co mot phan nam trong [low, high], theo thu tu A2 -> B2."""
    edges = [
        (Band.A2, -math.inf, thresholds["A2_B1"]),
        (Band.B1, thresholds["A2_B1"], thresholds["B1_B2"]),
        (Band.B2, thresholds["B1_B2"], math.inf),
    ]
    return [b for b, lo, hi in edges if low < hi and high >= lo]


class ConformalCalibrator:
    """Doc artifact CV+ va tinh khoang, tap band, chi bao cho mot FeatureSet."""

    def __init__(self, artifact: dict, model_path: Path, alpha: float | None = None) -> None:
        digest = hashlib.sha256(model_path.read_bytes()).hexdigest()
        if artifact.get("model_sha256") != digest:
            raise CalibrationMismatchError(
                f"hieu chinh {artifact.get('conformal_version')!r} thuoc mo hinh co SHA-256 "
                f"{artifact.get('model_sha256')}, khong phai {model_path.name} ({digest})"
            )
        self.version: str = artifact["conformal_version"]
        self.method: str = artifact["method"]
        self.alpha: float = alpha if alpha is not None else artifact["alpha_default"]
        if not 0.0 < self.alpha < 0.5:
            raise ValueError("alpha phai nam trong (0; 0,5)")
        self._order: list[str] = artifact["feature_order"]
        self._folds: list[dict] = artifact["folds"]
        self._fold_of: list[int] = artifact["fold_of"]
        self._residuals: list[float] = artifact["residuals"]
        self._reference: dict = artifact.get("indicator_reference", {})
        self.alpha_curve: list[dict] = artifact.get("alpha_curve", [])

    @classmethod
    def for_model(cls, model_name: str, alpha: float | None = None) -> ConformalCalibrator | None:
        """Artifact `conformal_<ten bo tien to ridge_>.json` neu co, khong thi None.

        Khong co artifact thi he thong van chay -- voi luat bien cu, va noi ro
        dieu do qua `ScoreInterval` rong. Khong nap duoc vi SHA lech thi BAO
        LOI: im lang dung luat cu se che mat mot artifact hong.
        """
        name = model_name.removeprefix("ridge_")
        path = MODEL_DIR / f"conformal_{name}.json"
        if not path.exists():
            return None
        artifact = json.loads(path.read_text(encoding="utf-8"))
        return cls(artifact, MODEL_DIR / f"{model_name}.json", alpha)

    # ------------------------------------------------------------------ khoang

    def _fold_predictions(self, features: FeatureSet) -> list[float] | None:
        x = [features.value_of(n) for n in self._order]
        if any(v is None for v in x):
            return None
        out = []
        for f in self._folds:
            raw = f["intercept"] + sum(
                c * ((v - m) / (s if s else 1.0))
                for v, m, s, c in zip(x, f["mean"], f["scale"], f["coef"], strict=True)
            )
            out.append(min(max(raw, SCORE_MIN), SCORE_MAX))
        return out

    def interval(self, features: FeatureSet, thresholds: dict[str, float]) -> ScoreInterval | None:
        preds = self._fold_predictions(features)
        if preds is None:
            return None
        n = len(self._residuals)
        lows = sorted(preds[k] - r for k, r in zip(self._fold_of, self._residuals, strict=True))
        highs = sorted(preds[k] + r for k, r in zip(self._fold_of, self._residuals, strict=True))
        lo_rank = math.floor(self.alpha * (n + 1))
        hi_rank = math.ceil((1 - self.alpha) * (n + 1))
        low = lows[lo_rank - 1] if lo_rank >= 1 else SCORE_MIN
        high = highs[hi_rank - 1] if hi_rank <= n else SCORE_MAX
        # Lam tron TRUOC khi suy tap band: nguoi doc thay "2,75" thi tap band
        # phai la tap cua 2,75, khong phai cua 2,7499.
        low, high = round(max(low, SCORE_MIN), 2), round(min(high, SCORE_MAX), 2)
        return ScoreInterval(
            low=low,
            high=high,
            band_set=bands_between(low, high, thresholds),
            coverage=round(1 - self.alpha, 4),
            method=self.method,
            calibration_version=self.version,
        )

    # ------------------------------------------------------------- chi bao

    def indicators(
        self, features: FeatureSet, criterion_features: dict[Criterion, tuple[str, ...]]
    ) -> list[CriterionIndicator]:
        """Phan vi cua tung phep do trong phan bo huan luyen, theo tieu chi.

        Phan vi noi suy tuyen tinh giua cac thap phan vi da luu. Phep do khong
        co gia tri thi KHONG co chi bao -- vang mat khong duoc doc thanh trung
        binh.
        """
        out: list[CriterionIndicator] = []
        for crit, names in criterion_features.items():
            for name in names:
                ref = self._reference.get(name)
                value = features.value_of(name)
                if ref is None or value is None:
                    continue
                out.append(
                    CriterionIndicator(
                        criterion=crit,
                        feature=name,
                        value=round(float(value), 4),
                        percentile=round(_percentile(float(value), ref["deciles"]), 3),
                        higher_is_better=bool(ref["higher_is_better"]),
                    )
                )
        return out


def weakest(indicators: list[CriterionIndicator]) -> list[Criterion]:
    """Tieu chi co trung binh `standing` thap nhat; hoa thi tra ca hai.

    So voi PHAN BO BAI NOI THAM CHIEU, khong so voi band cua chinh nguoi hoc --
    "yeu nhat" o day nghia la "xa nhat ve phia duoi so voi bai noi trung binh".
    """
    by_crit: dict[Criterion, list[float]] = {}
    for ind in indicators:
        by_crit.setdefault(ind.criterion, []).append(ind.standing)
    if not by_crit:
        return []
    means = {c: sum(v) / len(v) for c, v in by_crit.items()}
    low = min(means.values())
    return [c for c in Criterion if c in means and abs(means[c] - low) < 1e-9]


def _percentile(value: float, deciles: list[float]) -> float:
    if value <= deciles[0]:
        return 0.0
    if value >= deciles[-1]:
        return 1.0
    for i in range(len(deciles) - 1):
        lo, hi = deciles[i], deciles[i + 1]
        if lo <= value <= hi:
            frac = 0.0 if hi == lo else (value - lo) / (hi - lo)
            return (i + frac) / (len(deciles) - 1)
    return 1.0
