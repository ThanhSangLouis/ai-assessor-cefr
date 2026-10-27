"""Guided listening with random control moments (D056)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from aicefr.contracts import (
    Assessment,
    Band,
    Criterion,
    Evidence,
    EvidenceKind,
    Response,
    Status,
    Transcript,
    Word,
)
from aicefr.report.replay import CHOICES, CONTROL, MACHINE, WINDOW_S, analyse, moments

ROOT = Path(__file__).resolve().parent.parent


def report(response_id: str = "r-1", flagged: tuple[float, ...] = (5.0, 30.0)) -> Response:
    words = [Word(text=f"w{i}", start_s=i * 0.5, end_s=i * 0.5 + 0.4) for i in range(120)]
    evidence = [
        Evidence(
            evidence_id=f"ev-{i}",
            criterion=Criterion.FLUENCY,
            kind=EvidenceKind.PAUSE,
            start_s=t,
            end_s=t + 1.5,
            note="ngừng dài",
        )
        for i, t in enumerate(flagged)
    ]
    return Response(
        response_id=response_id,
        status=Status.REVIEW_REQUIRED,
        asr=Transcript(text="…", words=words, engine="fake", model_version="fake"),
        assessment=Assessment(
            overall_0_6=3.0, overall_band=Band.B1, model_version="m", evidence=evidence
        ),
        config_version="c",
    )


@pytest.mark.unit
def test_the_machines_moments_and_a_control_are_shuffled_and_fixed():
    first, again = moments(report()), moments(report())
    assert first == again  # the same moments each time the report is opened
    assert sorted(m.source for m in first) == [CONTROL, MACHINE, MACHINE]
    assert all(m.end_s - m.start_s == pytest.approx(WINDOW_S) for m in first)
    assert [m.moment_id for m in first] == ["m1", "m2", "m3"]


@pytest.mark.unit
def test_a_control_moment_avoids_everything_flagged():
    for rid in ("a", "b", "c", "d", "e"):
        found = moments(report(rid))
        control = [m for m in found if m.source == CONTROL]
        assert control
        for m in control:
            assert not any(m.start_s - 1.0 <= t <= m.end_s + 1.0 for t in (5.0, 30.0))


@pytest.mark.unit
def test_more_machine_moments_bring_two_controls():
    found = moments(report(flagged=(5.0, 15.0, 30.0, 45.0)))
    assert [m.source for m in found].count(CONTROL) == 2


@pytest.mark.unit
def test_nothing_flagged_means_nothing_to_listen_to():
    assert moments(report(flagged=())) == []


@pytest.mark.unit
def test_the_learner_is_never_told_which_moment_is_which():
    assert set(moments(report())[0].public()) == {"moment_id", "start_s", "end_s"}


@pytest.mark.unit
def test_the_gap_and_its_interval_resample_learners():
    labels = []
    for k in range(20):
        labels += [
            {"account_id": f"a{k}", "source": MACHINE, "choice": "hard"},
            {"account_id": f"a{k}", "source": MACHINE, "choice": "hesitant"},
            {"account_id": f"a{k}", "source": CONTROL, "choice": "smooth"},
            {"account_id": f"a{k}", "source": CONTROL, "choice": "unsure"},
        ]
    out = analyse(labels)
    assert out["gap"] == 1.0 and out["headline_met"] is True
    assert out["control"] == {"confirmed": 0, "answered": 1 * 20}


@pytest.mark.unit
def test_a_picker_no_better_than_chance_does_not_pass():
    labels = []
    for k in range(20):
        for source in (MACHINE, CONTROL):
            labels += [
                {"account_id": f"a{k}", "source": source, "choice": "hard"},
                {"account_id": f"a{k}", "source": source, "choice": "smooth"},
            ]
    out = analyse(labels)
    assert out["gap"] == 0.0 and out["headline_met"] is False


@pytest.mark.unit
def test_no_wording_calls_a_moment_a_pronunciation_error():
    """HUONG_PHAT_TRIEN_TIEP 3.4: an unclear word is what the machine heard, not an error."""
    banned = re.compile(r"lỗi phát âm|phát âm sai|sai phát âm|mispronunc", re.IGNORECASE)
    texts = [
        *CHOICES.values(),
        (ROOT / "src/aicefr/api/static/replay.js").read_text(encoding="utf-8"),
        (ROOT / "src/aicefr/services/core/assessment/replay_api.py").read_text(encoding="utf-8"),
    ]
    assert not [t for t in texts if banned.search(t)]


# ================================================================= the application


@pytest.fixture
def m(tmp_path, monkeypatch):
    from test_billing import boot

    return boot(tmp_path, monkeypatch, AICEFR_GUIDED_REPLAY="on")


def _with_moments(m, rid: str) -> None:
    """Give a stored response a transcript and evidence the fake recogniser does not make."""
    from aicefr.services.core.assessment import context

    repo = context.svc().repo
    stored = repo.get(rid)
    rich = report(rid)
    stored.asr, stored.assessment.evidence = rich.asr, rich.assessment.evidence
    repo.col("response").update_one(
        {"response_id": rid}, {"$set": {"report_json": stored.model_dump_json()}}
    )


@pytest.mark.integration
def test_a_learner_answers_and_reads_it_back(m):
    from test_lessons_integration import login_as, submit_assessment

    student = login_as(m, "SV-001")
    rid = submit_assessment(student)
    _with_moments(m, rid)
    got = student.get(f"/api/v1/responses/{rid}/replay").json()
    assert len(got["moments"]) == 3 and set(got["choices"]) == set(CHOICES)
    assert "source" not in got["moments"][0]
    first = got["moments"][0]["moment_id"]
    url = f"/api/v1/responses/{rid}/replay/{first}"
    assert student.post(url, json={"choice": "đại"}).status_code == 422
    assert (
        student.post(url, json={"choice": "hard", "intended": "I wanted to say"}).status_code == 200
    )
    again = student.get(f"/api/v1/responses/{rid}/replay").json()["moments"][0]
    assert (again["choice"], again["intended"]) == ("hard", "I wanted to say")
    notes = student.get("/api/v1/me/replay-labels").json()
    assert notes[0]["intended"] == "I wanted to say" and "source" not in notes[0]
    assert student.get("/api/v1/me/export.json").json()["replay_labels"] == notes


@pytest.mark.integration
def test_only_the_owner_listens_and_the_analysis_counts_consented_learners(m):
    from test_lessons_integration import login_as, submit_assessment

    owner, other = login_as(m, "SV-001"), login_as(m, "SV-002")
    admin = login_as(m, "QT-01", "admin", consent=False)
    rid = submit_assessment(owner)
    _with_moments(m, rid)
    assert other.get(f"/api/v1/responses/{rid}/replay").status_code == 404
    first = owner.get(f"/api/v1/responses/{rid}/replay").json()["moments"][0]["moment_id"]
    owner.post(f"/api/v1/responses/{rid}/replay/{first}", json={"choice": "hard"})
    assert admin.get("/api/v1/admin/replay/report").json()["labels"] == 1
    owner.post(
        "/api/v1/me/consent",
        data={"audio_storage_allowed": "true", "research_use_allowed": "false"},
    )
    assert admin.get("/api/v1/admin/replay/report").json()["labels"] == 0


@pytest.mark.integration
def test_off_by_default(tmp_path, monkeypatch):
    from test_billing import boot
    from test_lessons_integration import login_as, submit_assessment

    m = boot(tmp_path, monkeypatch)
    student = login_as(m, "SV-001")
    rid = submit_assessment(student)
    assert student.get(f"/api/v1/responses/{rid}/replay").status_code == 404
