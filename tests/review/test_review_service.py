import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime

import pytest

from aicefr.auth.service import AuthorizationError
from aicefr.contracts import (
    Actor,
    ActorRole,
    Assessment,
    AssessmentStatus,
    Band,
    Criterion,
    CriterionCoverage,
    Interaction,
    Provenance,
    ReasonCode,
    ReviewAction,
    ReviewState,
)
from aicefr.report.service import (
    MemoryReportRepository,
    ReportInput,
    ReportService,
    UnverifiedReviewDecision,
)
from aicefr.review.routing import NoReviewNeeded, review_candidate_from_assessment, routed_reasons
from aicefr.review.service import (
    MemoryReviewRepository,
    ReviewActionRequest,
    ReviewService,
    StaleReview,
)
from aicefr.review.sqlite import SQLiteReviewRepository


class Clock:
    def __init__(self) -> None:
        self.now = datetime(2026, 9, 28, tzinfo=UTC)

    def __call__(self) -> datetime:
        return self.now


class InMemoryMetadata:
    """SQLiteStore-shaped fixture without filesystem or user data."""

    def __init__(self) -> None:
        self.connection = sqlite3.connect(":memory:", isolation_level=None)
        self.connection.execute("PRAGMA foreign_keys=ON")
        self.connection.executescript(
            """
            CREATE TABLE accounts (actor_id TEXT PRIMARY KEY);
            CREATE TABLE responses (
                response_id TEXT PRIMARY KEY,
                owner_id TEXT NOT NULL REFERENCES accounts(actor_id),
                revision INTEGER NOT NULL
            );
            CREATE TABLE audit (
                event_id TEXT PRIMARY KEY, actor_id TEXT NOT NULL, action TEXT NOT NULL,
                object_id TEXT NOT NULL, recorded_at TEXT NOT NULL, reason TEXT
            );
            CREATE TABLE review_candidates (
                response_id TEXT PRIMARY KEY REFERENCES responses(response_id),
                response_revision INTEGER NOT NULL,
                assessment_status TEXT NOT NULL,
                proposed_band TEXT,
                reasons_json TEXT NOT NULL,
                source_versions_json TEXT NOT NULL,
                state TEXT NOT NULL,
                revision INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL, claimed_by TEXT
            );
            CREATE TABLE review_decisions (
                decision_id TEXT PRIMARY KEY,
                response_id TEXT NOT NULL REFERENCES review_candidates(response_id),
                teacher_id TEXT NOT NULL REFERENCES accounts(actor_id),
                action TEXT NOT NULL,
                old_state TEXT NOT NULL,
                new_state TEXT NOT NULL,
                candidate_revision INTEGER NOT NULL,
                proposed_band TEXT,
                final_band TEXT,
                reason TEXT,
                audit_id TEXT UNIQUE NOT NULL REFERENCES audit(event_id),
                recorded_at TEXT NOT NULL
            );
            """
        )
        self.connection.execute("INSERT INTO accounts VALUES (?)", ("fixture-student",))
        self.connection.execute("INSERT INTO accounts VALUES (?)", ("fixture-teacher",))
        self.connection.execute(
            "INSERT INTO responses VALUES (?, ?, ?)", ("f" * 32, "fixture-student", 1)
        )

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        self.connection.execute("BEGIN IMMEDIATE")
        try:
            yield self.connection
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise

    @staticmethod
    def record_audit(connection: sqlite3.Connection, event) -> None:
        connection.execute(
            "INSERT INTO audit VALUES (?, ?, ?, ?, ?, ?)",
            (
                event.event_id,
                event.actor_id,
                event.action,
                event.object_id,
                event.recorded_at.isoformat(),
                event.reason,
            ),
        )


def _assessment(
    *,
    status=AssessmentStatus.REVIEW_REQUIRED,
    reasons=(ReasonCode.SCORE_NEAR_BOUNDARY,),
    band=Band.B1,
) -> Assessment:
    return Assessment(
        response_id="fixture-response",
        status=status,
        overall_score=3.4 if band is not None else None,
        overall_band=band,
        criteria=tuple(CriterionCoverage(criterion=criterion) for criterion in Criterion),
        interaction=Interaction(),
        reasons=reasons,
        provenance=Provenance(
            model_version="ridge-v2",
            model_sha256="0" * 64,
            feature_version="features-v3",
            band_map_version="bands-v1",
            calibration_version=None,
            unit_of_inference="một bài nói",
            scored_at="2026-09-28T00:00:00+00:00",
        ),
    )


def _candidate(clock: Clock):
    return review_candidate_from_assessment(_assessment(), response_revision=1, clock=clock)


def _sqlite_candidate(clock: Clock):
    return review_candidate_from_assessment(
        _assessment().model_copy(update={"response_id": "f" * 32}),
        response_revision=1,
        clock=clock,
    )


def test_m07_test_001_reason_map_routes_uncertain_results_but_not_hard_upload_rejects():
    assert routed_reasons(_assessment()) == (ReasonCode.SCORE_NEAR_BOUNDARY,)
    assert routed_reasons(
        _assessment(
            status=AssessmentStatus.NOT_EVALUATED,
            reasons=(ReasonCode.OUT_OF_DISTRIBUTION, ReasonCode.QC_EMPTY_AUDIO),
            band=None,
        )
    ) == (ReasonCode.OUT_OF_DISTRIBUTION,)
    trust_reasons = (
        ReasonCode.LANGUAGE_UNCERTAIN,
        ReasonCode.OFF_TOPIC_SUSPECTED,
        ReasonCode.PROMPT_READING_SUSPECTED,
        ReasonCode.CALIBRATION_MISSING,
    )
    assert (
        routed_reasons(_assessment(status=AssessmentStatus.REVIEW_REQUIRED, reasons=trust_reasons))
        == trust_reasons
    )
    with pytest.raises(NoReviewNeeded):
        review_candidate_from_assessment(
            _assessment(
                status=AssessmentStatus.NOT_EVALUATED,
                reasons=(ReasonCode.QC_EMPTY_AUDIO,),
                band=None,
            ),
            response_revision=1,
        )


def test_m07_test_002_candidate_appears_in_teacher_queue_with_versioned_reason():
    clock = Clock()
    repository = MemoryReviewRepository()
    service = ReviewService(repository, clock=clock)
    teacher = Actor(actor_id="fixture-teacher", role=ActorRole.TEACHER)
    candidate = service.add_candidate(_candidate(clock))

    queue = service.queue(teacher)

    assert queue == (candidate,)
    assert queue[0].reasons == (ReasonCode.SCORE_NEAR_BOUNDARY,)
    assert queue[0].source_versions["model"] == "ridge-v2"


def test_m07_test_003_second_teacher_with_stale_revision_is_blocked_without_losing_audit():
    clock = Clock()
    repository = MemoryReviewRepository()
    service = ReviewService(repository, clock=clock)
    first = Actor(actor_id="fixture-teacher-a", role=ActorRole.TEACHER)
    second = Actor(actor_id="fixture-teacher-b", role=ActorRole.TEACHER)
    candidate = service.add_candidate(_candidate(clock))

    outcome = service.decide(
        first,
        candidate.response_id,
        ReviewActionRequest(action=ReviewAction.APPROVE, expected_revision=candidate.revision),
    )
    with pytest.raises(StaleReview):
        service.decide(
            second,
            candidate.response_id,
            ReviewActionRequest(action=ReviewAction.APPROVE, expected_revision=candidate.revision),
        )

    assert outcome.candidate.state is ReviewState.APPROVED
    assert len(repository.list_audit()) == 1
    assert repository.list_audit()[0].actor_id == first.actor_id


def test_m07_test_003_sqlite_repository_persists_decision_and_rejects_stale_write():
    clock = Clock()
    metadata = InMemoryMetadata()
    repository = SQLiteReviewRepository(metadata)  # type: ignore[arg-type]
    service = ReviewService(repository, clock=clock)
    teacher = Actor(actor_id="fixture-teacher", role=ActorRole.TEACHER)
    candidate = service.add_candidate(_sqlite_candidate(clock))

    outcome = service.decide(
        teacher,
        candidate.response_id,
        ReviewActionRequest(action=ReviewAction.APPROVE, expected_revision=candidate.revision),
    )
    reloaded = SQLiteReviewRepository(metadata)  # type: ignore[arg-type]

    assert reloaded.get(candidate.response_id) == outcome.candidate
    assert reloaded.verify_decision(outcome.decision) is True
    assert reloaded.list_queue() == ()
    with pytest.raises(StaleReview):
        service.decide(
            teacher,
            candidate.response_id,
            ReviewActionRequest(action=ReviewAction.APPROVE, expected_revision=candidate.revision),
        )


def test_m07_test_004_student_cannot_claim_or_decide():
    clock = Clock()
    service = ReviewService(MemoryReviewRepository(), clock=clock)
    candidate = service.add_candidate(_candidate(clock))
    student = Actor(actor_id="fixture-student", role=ActorRole.STUDENT)

    with pytest.raises(AuthorizationError):
        service.claim(student, candidate.response_id, candidate.revision)
    with pytest.raises(AuthorizationError):
        service.decide(
            student,
            candidate.response_id,
            ReviewActionRequest(action=ReviewAction.APPROVE, expected_revision=candidate.revision),
        )


def test_m07_test_005_teacher_action_updates_report_with_final_audit_reference():
    clock = Clock()
    repository = MemoryReviewRepository()
    reports = ReportService(MemoryReportRepository(), decision_verifier=repository)
    reports.build_and_store(
        ReportInput(response_id="fixture-response", audio_duration_s=1.0, assessment=_assessment())
    )
    service = ReviewService(repository, clock=clock, report_sink=reports)
    candidate = service.add_candidate(_candidate(clock))
    teacher = Actor(actor_id="fixture-teacher", role=ActorRole.TEACHER)

    outcome = service.decide(
        teacher,
        candidate.response_id,
        ReviewActionRequest(
            action=ReviewAction.OVERRIDE,
            expected_revision=candidate.revision,
            final_band=Band.B2,
            reason="Teacher verified fixture evidence",
        ),
    )
    report = reports.get(candidate.response_id)

    assert outcome.decision.old_state is ReviewState.PENDING
    assert outcome.decision.new_state is ReviewState.OVERRIDDEN
    assert outcome.audit.event_id == outcome.decision.audit_id
    assert report is not None
    assert report.teacher_verified is True
    assert report.teacher_final is not None
    assert report.teacher_final.overall_band is Band.B2
    assert report.teacher_final.audit_id == outcome.audit.event_id


def test_m06_task_003_does_not_accept_an_unbound_review_decision():
    clock = Clock()
    review = ReviewService(MemoryReviewRepository(), clock=clock)
    candidate = review.add_candidate(_candidate(clock))
    teacher = Actor(actor_id="fixture-teacher", role=ActorRole.TEACHER)
    outcome = review.decide(
        teacher,
        candidate.response_id,
        ReviewActionRequest(action=ReviewAction.APPROVE, expected_revision=candidate.revision),
    )
    reports = ReportService(MemoryReportRepository())
    reports.build_and_store(
        ReportInput(response_id="fixture-response", audio_duration_s=1.0, assessment=_assessment())
    )

    with pytest.raises(UnverifiedReviewDecision):
        reports.apply_review(outcome.decision)

    report = reports.get(candidate.response_id)
    assert report is not None
    assert report.teacher_verified is False
