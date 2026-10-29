"""The feedback study in the app (D040): full feedback vs the score alone.

An administrator starts one study at a time. Every student who accepted the
terms of use (D058) at that moment is assigned to an arm at random (a seed is stored, so the
assignment can be reproduced); nobody else is enrolled. While the study runs,
a participant in the `score_only` arm gets the report of their own assessments
with the score, band and interval only -- comments, evidence, priorities, the
aspect to practise next and the indicators are held back by the server, not
hidden by the page (`gate_report`). Teachers and administrators always see the
full report, and lessons and practice attempts are never gated.

A participant can leave at any time from their progress page; from then on
they see full feedback again and their data are left out of the analysis.
Being erased has the same effect. When the
study moves to `survey`, participants answer five short questions, still
without the held-back feedback, and scores from then on no longer count as
outcomes; when it is closed, every learner gets full feedback again and the
result stays readable. The same holding back covers the advice drawn from a
report: the weakest criteria behind the practice and lesson suggestions, the
profile export, the personal export.
"""

from __future__ import annotations

import csv
import io
import secrets
from dataclasses import dataclass

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field

from aicefr.api.deps import ADMIN_ONLY, STUDENT_ONLY
from aicefr.research.study import (
    ARM_NAMES,
    MIN_PARTICIPANTS,
    STUDY_VERSION,
    SURVEY_ITEMS,
    SURVEY_KEYS,
    analyse,
    assign_arms,
)
from aicefr.services import Peers
from aicefr.storage.auth_repository import Account, Role
from aicefr.storage.study_repository import StudyRepository

router = APIRouter()

# What a `score_only` participant still receives of an assessment.
WITHHELD_FIELDS = (
    "evidence",
    "comments",
    "priorities",
    "weakest_criteria",
    "indicators",
    "windows",
    "criteria",
)


@dataclass
class Services:
    studies: StudyRepository
    repo: object  # aicefr.storage.repository.Repository: scored_assessments, write_audit
    # The other services (D043): enabled students and who accepted the terms
    # from identity, lesson attempts from learning.
    peers: Peers

    def students(self) -> set[str]:
        return {a["account_id"] for a in self.peers.identity.accounts(roles=[Role.STUDENT.value])}

    def research_allowed(self) -> set[str]:
        return set(self.peers.identity.research_allowed())


_services: Services | None = None


def configure(services: Services) -> None:
    global _services
    _services = services


def svc() -> Services:
    if _services is None:  # pragma: no cover - configured at import of main
        raise RuntimeError("study API used before configure()")
    return _services


# The phases in which the arms differ. Feedback stays held back through the
# survey too: the survey asks about the study as it was lived, and learners who
# had just been handed every comment would answer about something else.
GATED_STATUSES = ("running", "survey")


def arm_of(account_id: str) -> str | None:
    """The arm a learner is in now, or None outside a study's measured phases."""
    if _services is None:
        return None
    s = svc()
    m = s.studies.membership(account_id)
    if not m or m["withdrawn_at"] or m["status"] not in GATED_STATUSES:
        return None
    return m["arm"]


def withholds(account_id: str) -> bool:
    """Whether feedback is held back from this learner now (the `score_only` arm)."""
    return arm_of(account_id) == "score_only"


def without_advice(account_id: str, rows: list[dict], fields: tuple[str, ...]) -> list[dict]:
    """`rows` with the advice fields emptied when this learner's feedback is held back.

    The aspect to practise next is feedback too: it must not come back through
    the practice suggestion, the lesson suggestion or the profile export.
    """
    if not withholds(account_id):
        return rows
    return [{**r, **{f: [] if isinstance(r.get(f), list) else None for f in fields}} for r in rows]


def latest_assessment(account_id: str) -> dict | None:
    """The latest scored assessment, without its weakest criteria while feedback is held back.

    The basis of the practice suggestion (assessment) and of the lesson
    suggestion (learning, through the facade): naming the weakest criterion is
    naming the aspect to practise next, which the score-only arm must not see.
    """
    basis = svc().repo.latest_assessment(account_id)
    if basis is None:
        return None
    return without_advice(account_id, [basis], ("weakest_criteria",))[0]


def gate_report(account: Account, owner_id: str | None, report: dict) -> dict:
    """Hold back the feedback of an assessment from a `score_only` participant."""
    if owner_id != account.account_id or report.get("practice"):
        return report
    if account.role is not Role.STUDENT or not report.get("assessment"):
        return report
    if not withholds(account.account_id):
        return report
    a = dict(report["assessment"])
    for field in WITHHELD_FIELDS:
        a[field] = []
    return {**report, "assessment": a, "features": None, "feedback_withheld": True}


# ================================================================= admin


class StudyIn(BaseModel):
    name: str = Field(min_length=3, max_length=120)
    min_days: int = Field(default=14, ge=1, le=120)


class StatusIn(BaseModel):
    status: str = Field(pattern="^(survey|closed)$")


@router.get("/api/v1/admin/studies", tags=["admin"])
def list_studies(account: Account = ADMIN_ONLY) -> dict:
    return {"version": STUDY_VERSION, "studies": svc().studies.all()}


@router.post("/api/v1/admin/studies", tags=["admin"])
def create_study(body: StudyIn, account: Account = ADMIN_ONLY) -> dict:
    """Enrol every student who allows research use, at random, half in each arm. FR-77."""
    if svc().studies.active():
        raise HTTPException(409, "đang có một thực nghiệm chưa đóng")
    metering = getattr(svc().peers, "metering", None)
    if metering is not None and metering.is_enabled():
        # D049: people who pay per use are not study participants (BR-30).
        raise HTTPException(409, "bản triển khai tính lượt không chạy thực nghiệm nghiên cứu")
    eligible = svc().research_allowed() & svc().students()
    if len(eligible) < MIN_PARTICIPANTS:
        raise HTTPException(
            422,
            f"cần ít nhất {MIN_PARTICIPANTS} học viên đồng ý cho dùng dữ liệu nghiên cứu "
            f"(hiện có {len(eligible)})",
        )
    seed = secrets.randbelow(2**31)
    arms = assign_arms(eligible, seed)
    study_id = svc().studies.create(body.name, seed, body.min_days, account.account_id, arms)
    svc().repo.write_audit(
        account.pseudonym,
        "study.create",
        study_id,
        f"participants={len(arms)};seed={seed};min_days={body.min_days}",
    )
    return {"study_id": study_id, "participants": len(arms), "seed": seed}


def _study(study_id: str) -> dict:
    study = svc().studies.get(study_id)
    if study is None:
        raise HTTPException(404, "không có thực nghiệm này")
    return study


@router.post("/api/v1/admin/studies/{study_id}/status", tags=["admin"])
def set_study_status(study_id: str, body: StatusIn, account: Account = ADMIN_ONLY) -> dict:
    study = _study(study_id)
    order = ("running", "survey", "closed")
    if order.index(body.status) <= order.index(study["status"]):
        raise HTTPException(409, "chỉ chuyển tiếp được: đang chạy → khảo sát → đã đóng")
    svc().studies.set_status(study_id, body.status)
    svc().repo.write_audit(account.pseudonym, "study.status", study_id, f"status={body.status}")
    return {"study_id": study_id, "status": body.status}


def _inputs(study: dict) -> tuple[list[dict], dict, dict, dict]:
    """Participants still in the study, with their scores, practice and survey."""
    allowed = svc().research_allowed()
    people = [
        p for p in svc().studies.participants(study["study_id"]) if p["account_id"] in allowed
    ]
    ids = {p["account_id"] for p in people}
    # The measured phase only: from the start to the move to the survey (or to
    # closing). After it both arms see feedback, so later scores are not outcomes.
    start, end = study["created_at"], study.get("measured_until") or "9999"

    def measured(when: str) -> bool:
        return start <= when < end

    scores: dict[str, list] = {}
    for row in svc().repo.scored_assessments(accounts=sorted(ids)):
        if measured(row["created_at"]):
            scores.setdefault(row["account_id"], []).append((row["created_at"], row["overall_0_6"]))
    practice = {
        a: sum(
            1
            for t in svc().peers.learning.attempts(account_id=a)
            if measured(t.get("created_at", ""))
        )
        for a in ids
    }
    surveys = {a: s for a, s in svc().studies.surveys(study["study_id"]).items() if a in ids}
    return people, scores, practice, surveys


@router.get("/api/v1/admin/studies/{study_id}/report", tags=["admin"])
def study_report(study_id: str, account: Account = ADMIN_ONLY) -> dict:
    """The comparison of the two arms, with a bootstrap interval. FR-78."""
    study = _study(study_id)
    people, scores, practice, surveys = _inputs(study)
    result = analyse(people, scores, practice, surveys, study["min_days"], study["seed"])
    return {"study": study, **result}


@router.get("/api/v1/admin/studies/{study_id}/export.csv", tags=["admin"])
def study_csv(study_id: str, account: Account = ADMIN_ONLY) -> Response:
    """One row per participant, under a study-local code: no account id, no pseudonym."""
    study = _study(study_id)
    people, scores, practice, surveys = _inputs(study)
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(
        ["participant", "arm", "withdrawn", "n_scores", "first_score", "last_score", "practice"]
        + list(SURVEY_KEYS)
    )
    for p in sorted(people, key=lambda p: p["code"] or ""):
        if p["withdrawn_at"]:
            # Left out of the analysis, and of the export: the row says only that
            # someone of this arm withdrew.
            writer.writerow([p["code"], p["arm"], 1] + [""] * (4 + len(SURVEY_KEYS)))
            continue
        seq = sorted(scores.get(p["account_id"], []))
        answers = surveys.get(p["account_id"], {})
        writer.writerow(
            [
                p["code"],
                p["arm"],
                0,
                len(seq),
                seq[0][1] if seq else "",
                seq[-1][1] if seq else "",
                practice.get(p["account_id"], 0),
            ]
            + [answers.get(k, "") for k in SURVEY_KEYS]
        )
    return Response(
        out.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{study_id}.csv"'},
    )


# ================================================================= learners


class SurveyIn(BaseModel):
    answers: dict[str, int]


@router.get("/api/v1/me/study", tags=["student"])
def my_study(account: Account = STUDENT_ONLY) -> dict:
    """Whether this learner is in a study, which arm, and whether a survey is waiting."""
    m = svc().studies.membership(account.account_id)
    if not m:
        return {"enrolled": False}
    return {
        "enrolled": True,
        "study_id": m["study_id"],
        "name": m["name"],
        "status": m["status"],
        "arm": m["arm"],
        "arm_name": ARM_NAMES[m["arm"]],
        "withdrawn": bool(m["withdrawn_at"]),
        "survey_items": [{"key": k, "text": t} for k, t in SURVEY_ITEMS],
        "survey_done": svc().studies.has_survey(m["study_id"], account.account_id),
    }


@router.post("/api/v1/me/study/survey", tags=["student"])
def submit_survey(body: SurveyIn, account: Account = STUDENT_ONLY) -> dict:
    m = svc().studies.membership(account.account_id)
    if not m or m["withdrawn_at"] or m["status"] != "survey":
        raise HTTPException(409, "chưa đến lúc khảo sát hoặc bạn không tham gia thực nghiệm")
    if set(body.answers) != set(SURVEY_KEYS) or not all(1 <= v <= 5 for v in body.answers.values()):
        raise HTTPException(422, "cần trả lời đủ năm câu, mỗi câu từ 1 đến 5")
    svc().studies.save_survey(m["study_id"], account.account_id, body.answers)
    return {"saved": True}


@router.post("/api/v1/me/study/withdraw", tags=["student"])
def withdraw_from_study(account: Account = STUDENT_ONLY) -> dict:
    """Leave the study. Full feedback comes back at once; nothing else changes."""
    left = svc().studies.withdraw(account.account_id)
    return {"withdrawn": bool(left)}
