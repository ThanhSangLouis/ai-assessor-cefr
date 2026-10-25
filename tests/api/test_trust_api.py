from __future__ import annotations

import io
import json
from datetime import UTC, datetime
from types import SimpleNamespace

from aicefr.api.templates import render_report_content
from aicefr.audio.config import QCConfig
from aicefr.contracts import (
    CURRENT_CONSENT_VERSION,
    ActorRole,
    Assessment,
    AssessmentStatus,
    Band,
    Criterion,
    CriterionCoverage,
    Interaction,
    Provenance,
    ReasonCode,
    ResponseStatus,
    ReviewCandidate,
    ReviewState,
)
from aicefr.local.__main__ import _demo_config
from aicefr.local.app import create_runtime
from aicefr.report.service import ReportInput
from aicefr.scoring.scorer import RidgeScorer
from aicefr.trust.contracts import (
    ConformalSet,
    CriterionIndicator,
    GuardDecision,
    GuardEvidence,
    GuardKind,
    LanguageDecision,
    LanguageEvidence,
    TrustAssessment,
    TrustDisposition,
)


def _request(app, path: str, token: str | None) -> tuple[int, dict, bytes]:
    result = {}
    environ = {
        "REQUEST_METHOD": "GET",
        "PATH_INFO": path,
        "CONTENT_LENGTH": "0",
        "CONTENT_TYPE": "",
        "HTTP_AUTHORIZATION": f"Bearer {token}" if token else "",
        "wsgi.url_scheme": "http",
        "wsgi.input": io.BytesIO(),
    }

    def start_response(status, headers):
        result["status"] = status
        result["headers"] = dict(headers)

    body = b"".join(app(environ, start_response))
    return int(result["status"].split()[0]), result["headers"], body


def test_safe_report_api_filters_student_trust_and_bounds_teacher_evidence(tmp_path):
    config = _demo_config()
    pipeline = SimpleNamespace(
        _qc_config=QCConfig(**config["qc"]),
        _scorer=RidgeScorer.load(),
        enqueue=lambda _response: None,
    )
    runtime = create_runtime(tmp_path / "api-trust-data", config=config, pipeline=pipeline)
    tokens = {}
    for name, role in (
        ("owner", ActorRole.STUDENT),
        ("other", ActorRole.STUDENT),
        ("teacher", ActorRole.TEACHER),
        ("admin", ActorRole.ADMIN),
    ):
        actor = runtime.auth.bootstrap_fixture_account(f"fixture-{name}", role, "fixture-password")
        tokens[name if name != "owner" else "a"] = runtime.auth.login(
            actor.actor_id, "fixture-password"
        )
        if role is ActorRole.STUDENT:
            runtime.consents.activate(
                actor, CURRENT_CONSENT_VERSION, audio_storage_allowed=True
            )
    owner = runtime.auth.resolve(tokens["a"], allowed_roles=frozenset({ActorRole.STUDENT}))
    response = runtime.responses.submit(
        owner,
        task_id="demo-speaking",
        task_version="1",
        consent_version=CURRENT_CONSENT_VERSION,
        audio_bytes=b"synthetic fixture bytes",
    )
    trust = TrustAssessment(
        language=LanguageEvidence(
            method="fixture-independent-lid",
            version="fixture-v1",
            confidence=0.95,
            language="en",
            decision=LanguageDecision.ENGLISH,
        ),
        relevance=(
            GuardEvidence(
                kind=GuardKind.OFF_TOPIC,
                value=0.8,
                threshold_version="fixture-threshold-v1",
                decision=GuardDecision.CLEAR,
            ),
        ),
        prediction_set=ConformalSet(
            alpha=0.1,
            bands=(Band.B1,),
            calibration_id="fixture-calibration",
            checksum="a" * 64,
            low=3.0,
            high=3.3,
        ),
        criterion_indicators=tuple(
            CriterionIndicator(name=item, coverage=0.7) for item in Criterion
        ),
        reasons=(ReasonCode.SCORE_NEAR_BOUNDARY,),
        disposition=TrustDisposition.REVIEW_REQUIRED,
    )
    assessment = Assessment(
        response_id=response.response_id,
        status=AssessmentStatus.REVIEW_REQUIRED,
        overall_score=3.15,
        overall_band=Band.B1,
        criteria=tuple(CriterionCoverage(criterion=item, coverage=0.7) for item in Criterion),
        interaction=Interaction(),
        reasons=(ReasonCode.SCORE_NEAR_BOUNDARY,),
        provenance=Provenance(
            model_version="fixture-model",
            model_sha256="b" * 64,
            feature_version="fixture-feature-v1",
            band_map_version="fixture-band-v1",
            calibration_version="fixture-cal-v1",
            trained_with={},
            unit_of_inference="fixture response",
            scored_at="2026-10-15T00:00:00+00:00",
        ),
    )
    report = runtime.app._reports.build_and_store(
        ReportInput(
            response_id=response.response_id,
            audio_duration_s=1.0,
            assessment=assessment,
            trust=trust,
            provenance={
                "trust_policy": "trust-policy-v1",
                "calibration_path": "/private/calibration.json",
            },
            source_versions={"blind_metadata": "/secret/blind/key"},
        )
    )
    runtime.app._reviews.add(
        ReviewCandidate(
            response_id=response.response_id,
            response_revision=response.revision,
            assessment_status=AssessmentStatus.REVIEW_REQUIRED,
            proposed_band=Band.B1,
            reasons=report.reasons,
            source_versions=report.source_versions,
            state=ReviewState.PENDING,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
    )

    url = f"/api/v1/reports/{response.response_id}"
    code, _, body = _request(runtime.app, url, tokens["a"])
    student = json.loads(body)["report"]
    assert code == 200
    assert student["trust"]["disposition"] == "REVIEW_REQUIRED"
    assert student["trust"]["recovery"]
    assert "language" not in student["trust"]
    assert "prediction_set" not in student
    assert "provenance" not in student
    assert all(item["label"] == "chỉ báo" for item in student["criterion_indicators"])

    code, _, body = _request(runtime.app, url, tokens["teacher"])
    teacher = json.loads(body)["report"]
    assert code == 200
    assert teacher["trust"]["language"]["method"] == "fixture-independent-lid"
    assert teacher["prediction_set"]["calibration_id"] == "fixture-calibration"
    assert "calibration_path" not in teacher["provenance"]
    assert "/private" not in body.decode()
    teacher_html = render_report_content(report, teacher=True)
    assert "/private/calibration.json" not in teacher_html
    assert "/secret/blind/key" not in teacher_html

    completed_response = runtime.responses.submit(
        owner,
        task_id="demo-speaking",
        task_version="1",
        consent_version=CURRENT_CONSENT_VERSION,
        audio_bytes=b"synthetic completed fixture bytes",
    )
    runtime.responses.transition_status(
        response_id=completed_response.response_id,
        expected_revision=completed_response.revision,
        status=ResponseStatus.COMPLETED,
        actor_id="system-pipeline",
        action="pipeline_completed",
    )
    completed_trust = trust.model_copy(
        update={"disposition": TrustDisposition.CONTINUE, "reasons": ()}
    )
    completed_assessment = assessment.model_copy(
        update={
            "response_id": completed_response.response_id,
            "status": AssessmentStatus.ESTIMATED,
            "reasons": (),
        }
    )
    runtime.app._reports.build_and_store(
        ReportInput(
            response_id=completed_response.response_id,
            audio_duration_s=1.0,
            assessment=completed_assessment,
            trust=completed_trust,
        )
    )
    completed_url = f"/api/v1/reports/{completed_response.response_id}"
    assert _request(runtime.app, completed_url, tokens["teacher"])[0] == 200
    assert _request(runtime.app, completed_url, tokens["admin"])[0] == 200
    assert runtime.app._reviews.get(completed_response.response_id) is None

    code, _, _ = _request(runtime.app, url, tokens["other"])
    assert code == 404
    code, _, _ = _request(runtime.app, url, None)
    assert code == 401

    rejected_response = runtime.responses.submit(
        owner,
        task_id="demo-speaking",
        task_version="1",
        consent_version=CURRENT_CONSENT_VERSION,
        audio_bytes=b"synthetic rejected fixture bytes",
    )
    runtime.responses.transition_status(
        response_id=rejected_response.response_id,
        expected_revision=rejected_response.revision,
        status=ResponseStatus.REJECTED,
        actor_id="system-pipeline",
        action="pipeline_rejected",
        reason=ReasonCode.LANGUAGE_NOT_ENGLISH,
    )
    rejected_trust = TrustAssessment(
        language=LanguageEvidence(
            method="fixture-independent-lid",
            version="fixture-v1",
            confidence=0.97,
            language="fr",
            decision=LanguageDecision.NON_ENGLISH,
            reason_code=ReasonCode.LANGUAGE_NOT_ENGLISH,
        ),
        relevance=(),
        prediction_set=None,
        criterion_indicators=tuple(CriterionIndicator(name=item) for item in Criterion),
        reasons=(ReasonCode.LANGUAGE_NOT_ENGLISH,),
        disposition=TrustDisposition.REJECTED,
    )
    rejected_assessment = Assessment(
        response_id=rejected_response.response_id,
        status=AssessmentStatus.NOT_EVALUATED,
        overall_score=None,
        overall_band=None,
        criteria=tuple(CriterionCoverage(criterion=item, coverage=None) for item in Criterion),
        interaction=Interaction(),
        reasons=(ReasonCode.LANGUAGE_NOT_ENGLISH,),
        provenance=Provenance(
            model_version="fixture-model",
            model_sha256="b" * 64,
            feature_version="fixture-feature-v1",
            band_map_version="fixture-band-v1",
            calibration_version=None,
            trained_with={},
            unit_of_inference="fixture response",
            scored_at="2026-10-15T00:00:00+00:00",
        ),
    )
    rejected_report = runtime.app._reports.build_and_store(
        ReportInput(
            response_id=rejected_response.response_id,
            audio_duration_s=1.0,
            assessment=rejected_assessment,
            trust=rejected_trust,
        )
    )
    rejected_url = f"/api/v1/reports/{rejected_response.response_id}"
    code, _, body = _request(runtime.app, rejected_url, tokens["a"])
    rejected_student = json.loads(body)["report"]
    assert code == 200
    assert rejected_report.overall_score is None and rejected_report.overall_band is None
    assert rejected_student["trust"]["disposition"] == "REJECTED"
    assert rejected_student["overall_score"] is None and rejected_student["overall_band"] is None
    assert runtime.app._reviews.get(rejected_response.response_id) is None
    teacher_code, _, teacher_body = _request(runtime.app, rejected_url, tokens["teacher"])
    assert teacher_code == 200
    assert json.loads(teacher_body)["report"]["trust"]["disposition"] == "REJECTED"
    runtime.close()
