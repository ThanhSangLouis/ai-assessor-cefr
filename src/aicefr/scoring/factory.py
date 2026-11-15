"""Pick the scorer an artifact needs: `RidgeScorer` or `DebertaScorer` (fusion).

The single place that knows both adapters, so the speech worker, the
readiness check and the admin screen activate a model by name without
learning which kind it is.
"""

from __future__ import annotations

from aicefr.ports import Scorer
from aicefr.scoring.scorer import RidgeScorer, load_model


def build_scorer(name: str, alpha: float | None = None) -> Scorer:
    """The scorer for artifact `name`. Cheap: a fusion scorer loads its text model on first use."""
    from aicefr.scoring.fusion import DebertaScorer, is_fusion_artifact

    if is_fusion_artifact(load_model(name)):
        return DebertaScorer(name, alpha)
    return RidgeScorer(name, alpha)
