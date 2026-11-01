"""What other services may ask the assessment service (D043).

A learner's latest result and series (learning suggests lessons from them),
assessments per account in a month (billing counts them), the sidebar's counts
(the web service shows them), and what the pages need to say about the limits
in force -- the QC thresholds, the upload size, the model's band thresholds.
"""

from __future__ import annotations

from aicefr.platform.rpc import exposed
from aicefr.qc import audio_qc
from aicefr.scoring.band_map import thresholds_of
from aicefr.services.core.assessment import study_api
from aicefr.services.core.assessment.context import PREP_SECONDS, active_model_name, active_qc
from aicefr.storage.rating_repository import RatingRepository
from aicefr.storage.repository import Repository


class AssessmentFacade:
    def __init__(self, repo: Repository, ratings: RatingRepository) -> None:
        self.repo = repo
        self.ratings = ratings

    @exposed
    def teaches(self, teacher_id: str, student_id: str) -> bool:
        """Whether the student is in a class the teacher teaches (D071)."""
        from aicefr.services.core.assessment.context import svc

        rooms = svc().classrooms
        return rooms is not None and rooms.teaches(teacher_id, student_id)

    @exposed
    def students_of(self, teacher_id: str) -> list[str]:
        """Every member of every class the teacher teaches (D071)."""
        from aicefr.services.core.assessment.context import svc

        rooms = svc().classrooms
        return sorted(rooms.students_of(teacher_id)) if rooms is not None else []

    @exposed
    def latest_assessment(self, account_id: str) -> dict | None:
        """The latest scored assessment: the basis for suggesting practice (D040-gated)."""
        return study_api.latest_assessment(account_id)

    @exposed
    def retell_source(self, account_id: str, response_id: str) -> dict | None:
        """The task of one of this learner's own scored assessments, to say it again (D069).

        None for someone else's response or one without a result: the caller
        answers 404 either way. The upgraded answer comes along when one was made.
        """
        from aicefr.contracts import ResponseStatus
        from aicefr.services.core.assessment.context import svc

        if self.repo.owner_of(response_id) != account_id:
            return None
        status = self.repo.status_of(response_id) or {}
        if status.get("status") not in (
            ResponseStatus.COMPLETED.value,
            ResponseStatus.REVIEW_REQUIRED.value,
        ):
            return None
        task = svc().tasks.get(status.get("task_id") or "")
        if task is None:
            return None
        upgrade = self.repo.upgrade_of(response_id)
        return {
            "response_id": response_id,
            "task_id": task.task_id,
            "title": task.title,
            "prompt": task.prompt_text,
            "min_seconds": task.min_seconds,
            "max_seconds": task.max_seconds,
            "band": status.get("overall_band"),
            "upgraded": upgrade["upgraded"] if upgrade else None,
        }

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
        from aicefr.services.core.assessment.context import svc

        seen = svc().peers.identity.seen_at(account_id=account_id, marker="results")
        return {
            "results": self.repo.count_reviewed_since(account_id, seen),
            "results_seen_at": seen,
        }

    @exposed
    def practice_daily(self, account_id: str) -> dict:
        """Today's practice against the daily goal, and the streak (D023), for reminders."""
        from aicefr.services.core.assessment.responses_api import _daily_view, _practice_state

        _bank, attempts, _progress = _practice_state(account_id)
        return _daily_view(attempts)

    @exposed
    def staff_badges(self, account_id: str, role: str = "teacher") -> dict:
        """Responses waiting for review, less those this person rates blind; their open sheets.

        D071: a teacher counts the work of their classes' students; an administrator, all.
        """
        from aicefr.services.core.assessment.context import svc

        owners = None
        if role != "admin":
            rooms = svc().classrooms
            owners = rooms.students_of(account_id) if rooms is not None else set()
        return {
            "queue": self.repo.count_waiting_review(
                exclude=self.ratings.blinded_responses(account_id), owners=owners
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
            "band_thresholds": thresholds_of(model["band_thresholds"]),
            "model_version": model["model_version"],
        }

    @exposed
    def audit_recent(self, limit: int = 100) -> list[dict]:
        return self.repo.audit(limit)
