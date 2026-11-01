"""The assessment prompts teachers keep (D076): add, reword, retire.

The bank (`practice/assessment_bank.py`) starts every deployment with prompts
for each band; teachers and administrators add their own here. Every prompt is
known by its band (D078), runs 40-60 seconds -- the length the scoring model
knows -- and carries English topic words for the off-topic check (D022).
Rewording a prompt makes a new version: the reports already written keep the
wording their learner saw.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from aicefr.api.deps import STAFF_ONLY
from aicefr.contracts import Band
from aicefr.services.core.assessment.context import svc
from aicefr.storage.auth_repository import Account

router = APIRouter()


def _keywords(raw: str) -> str:
    words = [w.strip().lower() for w in raw.split(",") if w.strip()]
    return ", ".join(dict.fromkeys(words))


class PromptIn(BaseModel):
    band: Band
    prompt_text: str = Field(min_length=10, max_length=600)
    topic_keywords: str = Field(default="", max_length=600)


class PromptPatch(BaseModel):
    band: Band | None = None
    prompt_text: str | None = Field(default=None, min_length=10, max_length=600)
    topic_keywords: str | None = Field(default=None, max_length=600)
    active: bool | None = None


@router.get("/api/v1/teach/tasks", tags=["teacher"])
def assessment_prompts(account: Account = STAFF_ONLY) -> list[dict]:
    """Every assessment prompt by band, retired ones too."""
    return svc().tasks.assessment_rows()


@router.post("/api/v1/teach/tasks", tags=["teacher"])
def add_prompt(body: PromptIn, account: Account = STAFF_ONLY) -> dict:
    s = svc()
    task_id = s.tasks.add_assessment(
        body.band,
        " ".join(body.prompt_text.split()),
        _keywords(body.topic_keywords),
        account.account_id,
    )
    s.repo.write_audit(account.pseudonym, "task.create", task_id, body.band.value)
    return {"task_id": task_id}


@router.patch("/api/v1/teach/tasks/{task_id}", tags=["teacher"])
def edit_prompt(task_id: str, body: PromptPatch, account: Account = STAFF_ONLY) -> dict:
    s = svc()
    changes = body.model_dump(exclude_none=True, mode="json")
    if "prompt_text" in changes:
        changes["prompt_text"] = " ".join(changes["prompt_text"].split())
    if "topic_keywords" in changes:
        changes["topic_keywords"] = _keywords(changes["topic_keywords"])
    if not changes:
        raise HTTPException(422, "không có gì để đổi")
    if not s.tasks.edit_assessment(task_id, changes):
        raise HTTPException(404, "không tìm thấy đề đánh giá này")
    s.repo.write_audit(account.pseudonym, "task.edit", task_id, ",".join(sorted(changes)))
    return {"task_id": task_id, "changed": sorted(changes)}
