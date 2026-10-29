"""What other services may ask the assessment service (D043).

A learner's latest result and series (learning suggests lessons from them),
assessments per account in a month (billing counts them), the sidebar's counts
(the web service shows them), and what the pages need to say about the limits
in force -- the QC thresholds, the upload size, the model's band thresholds.
"""

from __future__ import annotations

from aicefr.platform.rpc import exposed
from aicefr.qc import audio_qc
from aicefr.services.core.assessment import study_api
from aicefr.services.core.assessment.context import PREP_SECONDS, active_model_name, active_qc
from aicefr.storage.rating_repository import RatingRepository
from aicefr.storage.repository import Repository


class AssessmentFacade:
    def __init__(self, repo: Repository, ratings: RatingRepository) -> None:
        self.repo = repo
        self.ratings = ratings

    @exposed
    def latest_assessment(self, account_id: str) -> dict | None:
        """The latest scored assessment: the basis for suggesting practice (D040-gated)."""
        return study_api.latest_assessment(account_id)

    @exposed
    def progress_series(self, account_id: str, limit: int = 100) -> list[dict]:
        return self.repo.progress_series(account_id, limit)

    @exposed
    def assessments_by_account(self, since: str, until: str) -> dict[str, int]:
        """Assessments submitted in [since, until), per account (D033)."""
        return self.repo.assessments_by_account(since, until)

    @exposed
    def student_badges(self, account_id: str) -> dict:
        """Teacher decisions on this student's responses since they last looked (D028)."""
        seen = self.repo.seen_at(account_id, "results")
        return {
            "results": self.repo.count_reviewed_since(account_id, seen),
            "results_seen_at": seen,
        }

    @exposed
    def mark_seen(self, account_id: str, marker: str) -> str:
        return self.repo.mark_seen(account_id, marker)

    @exposed
    def staff_badges(self, account_id: str) -> dict:
        """Responses waiting for review, less those this person rates blind; their open sheets."""
        return {
            "queue": self.repo.count_waiting_review(
                exclude=self.ratings.blinded_responses(account_id)
            ),
            "ratings": self.ratings.open_count(account_id),
        }

    @exposed
    def page_limits(self) -> dict:
        """The limits the pages quote, as the machine applies them."""
        from aicefr.scoring.scorer import load_model

        thresholds, _ = active_qc()
        model = load_model(active_model_name())
        return {
            "min_duration_s": thresholds.min_duration_s,
            "max_duration_s": thresholds.max_duration_s,
            "max_size_mib": audio_qc.MAX_BYTES // (1024 * 1024),
            "sample_rate_hz": audio_qc.TARGET_SR,
            "prep_seconds": PREP_SECONDS,
            "a2_b1": model["band_thresholds"]["A2_B1"],
            "b1_b2": model["band_thresholds"]["B1_B2"],
            "model_version": model["model_version"],
        }

    @exposed
    def audit_recent(self, limit: int = 100) -> list[dict]:
        return self.repo.audit(limit)
