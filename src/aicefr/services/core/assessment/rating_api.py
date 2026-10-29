"""Blind double rating in the app (D030): raters score without seeing the machine.

Part of the assessment service (D043): the ratings sit beside the responses
they rate. Raters' names and research consent come from the identity service;
the rating pages are drawn by the web service.

The field study needs human scores that nothing has anchored
(KE_HOACH_KHAO_SAT.md §6, HUONG_PHAT_TRIEN_TIEP.md §2.1). The review flow cannot
give them: it shows the machine's score on the same screen. So rating has its
own path, and it is blind by construction:

* **A rater's sheet carries the task and the recording, nothing else.** No
  pseudonym, no response id (the audio is served under the assignment), no
  machine score, no other rater's score. A test checks the payload for every
  one of those.
* **The way round is closed too.** While a rater still has a response to rate
  blind, the report of that response answers 403 to them and the review queue
  leaves it out.
* **Ratings are final once submitted** and never touch `response` or
  `review_action`.

An administrator creates batches (two raters per response, a random order per
rater, one seed recorded), sends disagreements to a third rater, and reads the
agreement report -- human-human agreement first, machine-human after -- or
downloads every rating as CSV for the analysis. Only responses whose owner
consents to research use are rated, reported or exported.
"""

from __future__ import annotations

import csv
import io
import secrets
import statistics
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field

from aicefr.api.deps import (
    ADMIN_ONLY,
    STAFF_ONLY,
    require_plan,
)
from aicefr.billing.plans import PlanFeature
from aicefr.research.agreement import (
    CRITERIA,
    RatedResponse,
    Rating,
    agreement_report,
)
from aicefr.services import Peers
from aicefr.storage.auth_repository import Account, Role
from aicefr.storage.rating_repository import (
    AlreadyRated,
    RatingRepository,
    SeenMachine,
    rated_responses,
)

router = APIRouter()


# Targets the survey plan sets for the agreement between the two raters
# (KE_HOACH_KHAO_SAT.md §6.3). Shown next to the measured values as the plan's
# reference, not as a verdict: the metrics are not signed yet (G1).
PLAN_TARGETS = {"qwk_band": 0.70, "icc_overall": 0.75}


@dataclass
class Services:
    ratings: RatingRepository
    repo: object  # aicefr.storage.repository.Repository: write_audit
    task_lookup: object  # TaskRepository.get
    # The other services (D043): who the raters are and who allows research use
    # (identity); whether the plan in force allows a new batch (billing) -- a
    # batch already started always finishes. No billing: no plans.
    peers: Peers

    def research_allowed(self) -> set[str]:
        return set(self.peers.identity.research_allowed())

    def pseudonyms(self) -> dict[str, str]:
        return {
            a["account_id"]: a["pseudonym"]
            for a in self.peers.identity.accounts(enabled_only=False)
        }


_services: Services | None = None


def configure(services: Services) -> None:
    global _services
    _services = services


def svc() -> Services:
    if _services is None:  # pragma: no cover - configured at import of main
        raise RuntimeError("rating API used before configure()")
    return _services


# ================================================================= raters


def _mine(assignment_id: str, account: Account) -> dict:
    """The assignment if it is this rater's, else 404 (never 403: that would confirm it)."""
    view = svc().ratings.rater_view(assignment_id)
    if view is None or view["rater_id"] != account.account_id:
        raise HTTPException(404, "không có phiếu chấm này")
    return view


def _sheet(view: dict) -> dict:
    """What the rater sees. Built field by field: nothing is passed through."""
    task = svc().task_lookup(view["task_id"])
    rating = view["rating"]
    return {
        "assignment_id": view["assignment_id"],
        "batch": {"name": view["name"], "open": view["status"] == "open"},
        "position": view["position"],
        "total": view["total"],
        "adjudication": view["slot"] == 3,
        "task": (
            {
                "title": task.title,
                "prompt_text": task.prompt_text,
                "min_seconds": task.min_seconds,
                "max_seconds": task.max_seconds,
            }
            if task
            else None
        ),
        "audio_url": f"/api/v1/rate/assignments/{view['assignment_id']}/audio",
        # The rater opened the machine's result for this response before rating
        # it: the sheet is no longer blind and takes no rating (D030).
        "seen_machine": bool(view["seen"]) and rating is None,
        "rating": (
            {
                "unscorable": bool(rating["unscorable"]),
                "unscorable_reason": rating["unscorable_reason"],
                "overall": rating["score_overall"],
                "band": rating["band"],
                "criteria": {k: rating[f"score_{k}"] for k in CRITERIA},
                "reason": rating["reason"],
                "submitted_at": rating["submitted_at"],
            }
            if rating
            else None
        ),
        "next_assignment_id": view["next_assignment_id"],
    }


@router.get("/api/v1/rate/assignments", tags=["teacher"])
def my_assignments(account: Account = STAFF_ONLY) -> dict:
    rows = svc().ratings.rater_list(account.account_id)
    batches: dict[str, dict] = {}
    for r in rows:
        b = batches.setdefault(
            r["batch_id"],
            {
                "batch_id": r["batch_id"],
                "name": r["name"],
                "open": r["status"] == "open",
                "total": 0,
                "done": 0,
                "voided": 0,
                "next_assignment_id": None,
                "items": [],
            },
        )
        if r["submitted_at"]:
            state = "done"
        elif r["seen"]:
            state = "seen"  # no longer blind: it will not be rated
        else:
            state = "opened" if r["opened_at"] else "new"
        b["total"] += 1
        b["done"] += state == "done"
        b["voided"] += state == "seen"
        if state in ("new", "opened") and b["next_assignment_id"] is None:
            b["next_assignment_id"] = r["assignment_id"]
        b["items"].append(
            {
                "assignment_id": r["assignment_id"],
                "position": r["position"],
                "state": state,
                "adjudication": r["slot"] == 3,
            }
        )
    return {"batches": list(batches.values())}


@router.get("/api/v1/rate/assignments/{assignment_id}", tags=["teacher"])
def my_sheet(assignment_id: str, account: Account = STAFF_ONLY) -> dict:
    view = _mine(assignment_id, account)
    if view["rating"] is None:
        svc().ratings.mark_opened(assignment_id)
    return _sheet(view)


@router.get("/api/v1/rate/assignments/{assignment_id}/audio", tags=["teacher"])
def sheet_audio(assignment_id: str, account: Account = STAFF_ONLY) -> FileResponse:
    """The recording, under the assignment and with a neutral file name."""
    view = _mine(assignment_id, account)
    path = view["audio_path"]
    if not path or not Path(path).is_file():
        raise HTTPException(404, "không còn tệp ghi âm của bài này")
    svc().repo.write_audit(account.account_id, "AUDIO_ACCESS", view["response_id"], "blind_rating")
    return FileResponse(path, media_type="audio/wav", filename=f"bai-{view['position']}.wav")


class RatingIn(BaseModel):
    """One completed rating sheet (KE_HOACH_KHAO_SAT.md appendix B)."""

    unscorable: bool = False
    unscorable_reason: Literal["broken", "inaudible", "off_task"] | None = None
    overall: float | None = Field(None, ge=0, le=6)
    band: Literal["A2", "B1", "B2"] | None = None
    criteria: dict[str, float] = Field(default_factory=dict)
    reason: str | None = Field(None, max_length=300)


def _half_point(value: float) -> bool:
    return abs(value * 2 - round(value * 2)) < 1e-9


def _to_rating(body: RatingIn, rater_id: str, adjudication: bool) -> Rating:
    if body.unscorable:
        if not body.unscorable_reason:
            raise HTTPException(422, "cần chọn lý do không chấm được")
        if body.overall is not None or body.band is not None or body.criteria:
            raise HTTPException(422, "bài không chấm được thì không ghi điểm hay band")
        return Rating(rater_id, None, None, {}, unscorable=True, adjudication=adjudication)
    if body.overall is None or body.band is None:
        raise HTTPException(422, "cần điểm tổng và band")
    missing = sorted(set(CRITERIA) - set(body.criteria))
    extra = sorted(set(body.criteria) - set(CRITERIA))
    if missing or extra:
        raise HTTPException(422, "cần đủ năm tiêu chí: " + ", ".join(CRITERIA))
    values = [body.overall, *body.criteria.values()]
    if any(not 0 <= v <= 6 or not _half_point(v) for v in values):
        raise HTTPException(422, "điểm theo thang 0–6, bước nửa điểm")
    if not body.reason or len(body.reason.strip()) < 3:
        raise HTTPException(422, "cần một dòng lý do")
    return Rating(
        rater_id,
        body.overall,
        body.band,
        dict(body.criteria),
        adjudication=adjudication,
    )


@router.post("/api/v1/rate/assignments/{assignment_id}", tags=["teacher"])
def submit_sheet(assignment_id: str, body: RatingIn, account: Account = STAFF_ONLY) -> dict:
    """Record the rating. Final: a sheet is submitted once, and only while its batch is open."""
    view = _mine(assignment_id, account)
    if view["status"] != "open":
        raise HTTPException(409, "đợt chấm đã đóng")
    rating = _to_rating(body, account.account_id, view["slot"] == 3)
    reason = body.reason.strip() if body.reason else None
    try:
        svc().ratings.submit(assignment_id, rating, reason, body.unscorable_reason)
    except AlreadyRated as e:
        raise HTTPException(409, "phiếu này đã nộp; điểm đã nộp không sửa được") from e
    except SeenMachine as e:
        raise HTTPException(
            409,
            "bạn đã mở kết quả của máy cho bài này nên phiếu không còn mù; phiếu này không nhận"
            " điểm nữa",
        ) from e
    # No score in the audit line: who rated what, and when, is enough.
    svc().repo.write_audit(account.account_id, "rating.submit", assignment_id, None)
    return {"status": "ok", "next_assignment_id": view["next_assignment_id"]}


# ================================================================= administrator


class BatchIn(BaseModel):
    name: str = Field(min_length=3, max_length=120)
    rater_ids: list[str] = Field(min_length=2, max_length=20)
    limit: int | None = Field(None, ge=1, le=2000)
    only_new: bool = True
    seed: int | None = Field(None, ge=0, le=2**31 - 1)


class AdjudicationIn(BaseModel):
    adjudicator_id: str = Field(min_length=1, max_length=64)


def _raters() -> list[dict]:
    """Enabled teachers and administrators: who can be asked to rate."""
    return [
        {"account_id": a["account_id"], "pseudonym": a["pseudonym"], "role": a["role"]}
        for a in svc().peers.identity.accounts(roles=[Role.TEACHER.value, Role.ADMIN.value])
    ]


def _batch_or_404(batch_id: str):
    batch = svc().ratings.batch(batch_id)
    if batch is None:
        raise HTTPException(404, "không có đợt chấm này")
    return batch


@router.get("/api/v1/admin/ratings/setup", tags=["admin"])
def rating_setup(
    account: Account = ADMIN_ONLY,
) -> dict:
    """What a new batch can draw on: eligible responses and possible raters."""
    allowed = svc().research_allowed()
    return {
        "eligible_new": len(svc().ratings.eligible(allowed, only_new=True)),
        "eligible_all": len(svc().ratings.eligible(allowed, only_new=False)),
        "raters": _raters(),
    }


@router.post("/api/v1/admin/ratings/batches", tags=["admin"])
def create_batch(
    body: BatchIn,
    account: Account = ADMIN_ONLY,
) -> dict:
    """Two raters per response drawn from the chosen ones; one seed decides sample and orders."""
    require_plan(svc().peers.billing, PlanFeature.BLIND_RATING)
    known = {r["account_id"] for r in _raters()}
    chosen = sorted(set(body.rater_ids))
    if len(chosen) < 2 or not set(chosen) <= known:
        raise HTTPException(422, "cần ít nhất hai giám khảo là giảng viên hoặc quản trị viên")
    allowed = svc().research_allowed()
    seed = body.seed if body.seed is not None else secrets.randbelow(2**31)
    from aicefr.research.assign import sample

    responses = sample(svc().ratings.eligible(allowed, body.only_new), body.limit, seed)
    if not responses:
        raise HTTPException(422, "không có bài nào đủ điều kiện để chấm")
    try:
        made = svc().ratings.create_batch(
            body.name.strip(), account.account_id, responses, chosen, seed
        )
    except ValueError as e:
        raise HTTPException(
            422,
            "không bài nào còn hai giám khảo chưa xem kết quả của máy: chọn thêm giám khảo",
        ) from e
    svc().repo.write_audit(
        account.pseudonym,
        "rating.batch_create",
        made["batch_id"],
        f"responses={made['responses']} skipped_seen={made['skipped_seen']}"
        f" raters={len(chosen)} seed={seed}",
    )
    return {**made, "raters": len(chosen), "seed": seed}


@router.get("/api/v1/admin/ratings/batches", tags=["admin"])
def list_batches(account: Account = ADMIN_ONLY):
    names = svc().pseudonyms()
    out = []
    for b in svc().ratings.batches():
        b["raters"] = [
            {"account_id": rid, "pseudonym": names.get(rid, rid), **progress}
            for rid, progress in sorted(b["raters"].items(), key=lambda kv: names.get(kv[0], kv[0]))
        ]
        out.append(b)
    return out


@router.post("/api/v1/admin/ratings/batches/{batch_id}/adjudicate", tags=["admin"])
def adjudicate(
    batch_id: str,
    body: AdjudicationIn,
    account: Account = ADMIN_ONLY,
) -> dict:
    """Send every response the two raters disagree on to a third rater."""
    batch = _batch_or_404(batch_id)
    if body.adjudicator_id not in {r["account_id"] for r in _raters()}:
        raise HTTPException(422, "người phân xử phải là giảng viên hoặc quản trị viên")
    result = svc().ratings.add_adjudication(batch_id, body.adjudicator_id, batch["seed"] + 1)
    svc().repo.write_audit(
        account.pseudonym,
        "rating.adjudicate",
        batch_id,
        f"created={result['created']} skipped_own={result['skipped_own']}"
        f" skipped_seen={result['skipped_seen']}",
    )
    return result


class ReplaceIn(BaseModel):
    rater_id: str = Field(min_length=1, max_length=64)


# Declared before the close/reopen route below: its `{action}` would otherwise
# take "replace" and refuse it as an unknown action.
@router.post("/api/v1/admin/ratings/batches/{batch_id}/replace", tags=["admin"])
def replace_void_sheets(
    batch_id: str,
    body: ReplaceIn,
    account: Account = ADMIN_ONLY,
) -> dict:
    """Give every sheet that went void (its rater saw the machine's result) to another rater."""
    batch = _batch_or_404(batch_id)
    if body.rater_id not in {r["account_id"] for r in _raters()}:
        raise HTTPException(422, "giám khảo mới phải là giảng viên hoặc quản trị viên")
    result = svc().ratings.replace_void(batch_id, body.rater_id, batch["seed"] + 2)
    svc().repo.write_audit(
        account.pseudonym,
        "rating.replace",
        batch_id,
        f"created={result['created']} skipped_own={result['skipped_own']}"
        f" skipped_seen={result['skipped_seen']}",
    )
    return result


@router.post("/api/v1/admin/ratings/batches/{batch_id}/{action}", tags=["admin"])
def set_batch_status(
    batch_id: str, action: Literal["close", "reopen"], account: Account = ADMIN_ONLY
) -> dict:
    _batch_or_404(batch_id)
    status = "closed" if action == "close" else "open"
    svc().ratings.set_status(batch_id, status)
    svc().repo.write_audit(account.pseudonym, f"rating.batch_{action}", batch_id, None)
    return {"batch_id": batch_id, "status": status}


def _items(batch_id: str, allowed: set[str]) -> list[RatedResponse]:
    return rated_responses(svc().ratings.analysis_rows(batch_id, allowed))


def _not_while_owed(batch_id: str, account: Account) -> None:
    """An administrator who is also a rater in this batch reads its machine scores last.

    The report and the export put the machine's score next to every response;
    an administrator still owing a blind sheet on one of them waits (D030).
    """
    owed = svc().ratings.blinded_responses(account.account_id) & svc().ratings.batch_responses(
        batch_id
    )
    if owed:
        raise HTTPException(
            409,
            f"bạn còn {len(owed)} phiếu chấm mù chưa nộp trong đợt này: nộp xong ở trang Chấm mù"
            " rồi mới xem điểm của máy",
        )


@router.get("/api/v1/admin/ratings/batches/{batch_id}/report", tags=["admin"])
def batch_report(batch_id: str, account: Account = ADMIN_ONLY) -> dict:
    """The agreement report of one batch: humans first, then the machine (agreement.py)."""
    batch = _batch_or_404(batch_id)
    _not_while_owed(batch_id, account)
    allowed = svc().research_allowed()
    everyone = svc().ratings.analysis_rows(batch_id, allowed=None)
    items = _items(batch_id, allowed)
    times = svc().ratings.times_to_rate(batch_id)
    svc().repo.write_audit(account.pseudonym, "rating.report", batch_id, None)
    return {
        "batch": {
            "batch_id": batch["batch_id"],
            "name": batch["name"],
            "status": batch["status"],
            "seed": batch["seed"],
            "created_at": batch["created_at"],
        },
        "withdrawn": len(everyone) - len(items),
        "time_to_rate": {
            "n": len(times),
            "median_s": round(statistics.median(times), 1) if times else None,
        },
        "plan_targets": PLAN_TARGETS,
        "report": agreement_report(items),
    }


EXPORT_COLUMNS = [
    "batch_id",
    "response_id",
    "speaker_id",
    "task_id",
    "rater_id",
    "slot",
    *(f"score_{k}" for k in CRITERIA),
    "score_overall",
    "band",
    "unscorable",
    "unscorable_reason",
    "reason",
    "opened_at",
    "submitted_at",
    "ai_overall",
    "ai_band",
    "flagged",
]


@router.get("/api/v1/admin/ratings/batches/{batch_id}/export.csv", tags=["admin"])
def batch_export(
    batch_id: str,
    account: Account = ADMIN_ONLY,
) -> Response:
    """Every submitted rating of the batch, one row each, for the analysis outside the app.

    Raters appear under their pseudonyms; the machine's score is its own
    output, from before any teacher decision. Owners who withdrew consent are
    left out.
    """
    _batch_or_404(batch_id)
    _not_while_owed(batch_id, account)
    allowed = svc().research_allowed()
    names = svc().pseudonyms()
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=EXPORT_COLUMNS, extrasaction="ignore")
    writer.writeheader()
    count = 0
    for item in svc().ratings.analysis_rows(batch_id, allowed):
        for row in item["rows"]:
            writer.writerow(
                {
                    **row,
                    "batch_id": batch_id,
                    "speaker_id": item["speaker_id"],
                    "rater_id": names.get(row["rater_id"], row["rater_id"]),
                    "ai_overall": item["ai_overall"],
                    "ai_band": item["ai_band"],
                    "flagged": int(item["flagged"]),
                }
            )
            count += 1
    svc().repo.write_audit(account.pseudonym, "export.ratings", batch_id, f"rows={count}")
    return Response(
        "﻿" + out.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="cham-mu-{batch_id}.csv"'},
    )
