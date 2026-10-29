"""Derive `ridge_resp_v2` from `ridge_resp_v1` by dropping `filler_ratio`.

Why this is a derivation and not a retrain
------------------------------------------

`filler_ratio` is **constant in the training data**. The artifact says so in
its own numbers: `feature_lo = feature_hi = 0.0`, `mean = 0.0002`. Whisper in
its standard configuration deletes hesitation markers -- "um", "uh" -- before
they ever reach the transcript, so 876 training responses produced essentially
876 zeros.

A coefficient fitted on a constant column is **not identified**: the data
contains no information about what that coefficient should be. Ridge shrinks it
toward zero and lands on 0.0088, but that number describes the regulariser, not
the speakers. Today it costs nothing, because the running recogniser also
produces zeros. The day the project switches to a verbatim model -- which is a
written plan, not a hypothetical -- a realistic `filler_ratio` of 0.02 becomes
z = 4.5 and starts moving scores by about 0.04 points for a reason no data ever
supported.

So this script removes the term rather than re-estimating it. Removing an
unidentified coefficient is not the same act as changing a fitted one: on every
input the current recogniser can produce, v2 and v1 give **identical** scores,
and `tests/test_scorer.py` asserts exactly that.

A real retrain -- on features re-extracted with the recogniser actually in use,
against ratings from Vietnamese students -- is a separate piece of work, planned
in `docs/plan/KE_HOACH_KHAO_SAT.md` for weeks 10-11. This script does not
pretend to be that.

Usage:
    python tools/derive_model_v2.py
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

MODEL_DIR = Path(__file__).resolve().parents[1] / "src" / "aicefr" / "scoring" / "models"
SOURCE = MODEL_DIR / "ridge_resp_v1.json"
TARGET = MODEL_DIR / "ridge_resp_v2.json"
DROP = "filler_ratio"

# Per-feature arrays that must stay aligned with `feature_order`.
ALIGNED = ("mean", "scale", "coef", "feature_lo", "feature_hi")


def main() -> int:
    model = json.loads(SOURCE.read_text(encoding="utf-8"))
    order = model["feature_order"]
    if DROP not in order:
        print(f"{DROP} không có trong {SOURCE.name}, không phải làm gì")
        return 0

    index = order.index(DROP)
    lo, hi = model["feature_lo"][index], model["feature_hi"][index]
    if lo != hi:
        # The whole argument rests on the column being constant. If a future
        # training set has real variation, the feature carries information and
        # must be refitted, not deleted.
        print(f"DỪNG: {DROP} không còn là hằng số trong tập huấn luyện (lo={lo}, hi={hi}).")
        print("Đặc trưng này giờ mang thông tin — phải huấn luyện lại, không được bỏ.")
        return 1

    # Fold the dropped term into the intercept instead of deleting it outright.
    #
    # The term is `coef * (x - mean) / scale`. With x = 0 -- what the running
    # recogniser produces for every response -- it is a constant, and dropping a
    # constant shifts every prediction by that amount. Small (about 0.0005
    # points) but enough to move a score across a rounding boundary, which is
    # exactly the kind of "tiny" change that makes two artifacts disagree about
    # a band and nobody can say why.
    #
    # Absorbed into the intercept, v2 reproduces v1 EXACTLY on `filler_ratio = 0`.
    shift = model["coef"][index] * ((0.0 - model["mean"][index]) / model["scale"][index])

    out = dict(model)
    out["feature_order"] = [n for n in order if n != DROP]
    for key in ALIGNED:
        out[key] = [v for i, v in enumerate(model[key]) if i != index]
    out["intercept"] = model["intercept"] + shift

    out["model_version"] = "ridge_resp_v2"
    out["derived_from"] = "ridge_resp_v1"
    out["derivation"] = (
        f"Bỏ đặc trưng {DROP}: nó là hằng số 0 trong toàn bộ tập huấn luyện"
        " (feature_lo = feature_hi = 0) nên hệ số của nó không xác định được."
        " Số hạng cũ được cộng vào intercept nên điểm TRÙNG KHỚP TUYỆT ĐỐI với"
        " ridge_resp_v1 ở mọi đầu vào có filler_ratio = 0."
    )
    out["derived_at"] = datetime.now(UTC).isoformat(timespec="seconds")
    out["cv_note"] = (
        "PCC và RMSE giữ nguyên của ridge_resp_v1 vì không huấn luyện lại;"
        " đây là cùng một mô hình đã bỏ một số hạng bằng không."
    )

    TARGET.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Đã ghi {TARGET.name}: {len(out['feature_order'])} đặc trưng (bỏ {DROP}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
