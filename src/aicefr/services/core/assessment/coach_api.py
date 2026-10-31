"""From a result to the next band: targets in numbers and the upgraded answer (D069).

Two things a report adds for its owner:

* `GET  /api/v1/responses/{id}/coach` -- the next band and up to three targets
  read off the scoring model (`report/next_band.py`), whether an upgraded
  answer can be made, and the one already made;
* `POST /api/v1/responses/{id}/upgrade` -- the owner's answer rewritten one
  band higher by the configured language model (`coach/`), made once and kept
  with the response: a second request returns the same text and costs nothing.

And the phrase book built from those upgrades (D070, `coach/phrasebook.py`):
`GET /api/v1/me/phrases` lists the cards and the few due today, `POST
/api/v1/me/phrases/review` records one self-judged review.

Only the owner, only a scored assessment with a transcript, never while the
feedback study holds this learner's feedback back (D040), and a daily cap per
student so a free tier stays inside its limits.

D072: what it costs. A cap for everyone together in 24 hours
(`AICEFR_COACH_GLOBAL_DAILY`) keeps the system under the provider's free daily
quota. On the metered channel an upgrade costs `AICEFR_PRICE_UPGRADE_RUNS`
runs: held before the model is asked, charged when the upgrade is made,
released when the model fails. The provider's own token counts are kept with
the upgrade and its ledger entry.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from aicefr.api.deps import require_login
from aicefr.coach import phrasebook
from aicefr.coach.providers import provider_from
from aicefr.coach.upgrade import PROMPT_VERSION, UpgradeError, parse, user_message
from aicefr.contracts import ResponseStatus
from aicefr.observability import count
from aicefr.report.next_band import next_band_plan
from aicefr.services.core.assessment import study_api
from aicefr.services.core.assessment.context import can_view, svc
from aicefr.storage.auth_repository import Account, Role

router = APIRouter()

SCORED = (ResponseStatus.COMPLETED, ResponseStatus.REVIEW_REQUIRED)
NEXT = {"A1": "A2", "A2": "B1", "B1": "B2", "B2": "C1", "C1": "C2"}


def _scored(response_id: str, account: Account, owner_only: bool):
    """The response and its owner, or 404: someone else's is not confirmed to exist."""
    s = svc()
    report = s.repo.get(response_id)
    owner = s.repo.owner_of(response_id)
    allowed = owner == account.account_id if owner_only else can_view(account, owner)
    if report is None or not allowed:
        raise HTTPException(404, "không tìm thấy bài này")
    return report, owner


def _plan(report) -> dict | None:
    a = report.assessment
    if a is None or a.overall_0_6 is None or report.features is None or not a.model_version:
        return None
    from aicefr.scoring.scorer import load_model

    try:
        model = load_model(a.model_version)
    except Exception:  # noqa: BLE001 - an artifact no longer installed: no targets, not an error
        return None
    return next_band_plan(model, report.features, a.overall_0_6)


@router.get("/api/v1/responses/{response_id}/coach", tags=["student"])
def coach(response_id: str, account: Account = Depends(require_login)) -> dict:
    report, owner = _scored(response_id, account, owner_only=False)
    withheld = account.role is Role.STUDENT and study_api.withholds(account.account_id)
    if withheld or report.status not in SCORED:
        return {"next_band": None, "upgrade": None, "can_upgrade": False}
    upgrade = svc().repo.upgrade_of(response_id)
    can = (
        owner == account.account_id
        and provider_from(svc().settings) is not None
        and bool(report.asr and report.asr.text.strip())
        and report.assessment is not None
        and report.assessment.overall_band is not None
        and report.assessment.overall_band.value in NEXT
    )
    metering = getattr(svc().peers, "metering", None)
    price = metering.upgrade_price() if metering is not None and can else None
    return {"next_band": _plan(report), "upgrade": upgrade, "can_upgrade": can, "price": price}


@router.post("/api/v1/responses/{response_id}/upgrade", tags=["student"])
def upgrade(response_id: str, account: Account = Depends(require_login)) -> dict:
    s = svc()
    report, _ = _scored(response_id, account, owner_only=True)
    kept = s.repo.upgrade_of(response_id)
    if kept:
        return kept
    if study_api.withholds(account.account_id):
        raise HTTPException(403, "trong thực nghiệm phản hồi, bản nâng cấp tạm thời chưa mở")
    a = report.assessment
    if (
        report.status not in SCORED
        or a is None
        or a.overall_band is None
        or not (report.asr and report.asr.text.strip())
    ):
        raise HTTPException(409, "bài này chưa có kết quả và bản chép lời để nâng cấp")
    band = a.overall_band.value
    if band not in NEXT:
        raise HTTPException(409, "bài đã ở band cao nhất")
    provider = provider_from(s.settings)
    if provider is None:
        raise HTTPException(503, "máy chủ chưa bật tính năng bản nâng cấp")
    since = (datetime.now(UTC) - timedelta(days=1)).isoformat(timespec="seconds")
    if s.repo.upgrades_since(account.account_id, since) >= s.settings.coach_daily:
        raise HTTPException(
            429, f"mỗi ngày tạo được tối đa {s.settings.coach_daily} bản nâng cấp, hãy thử lại sau"
        )
    if s.repo.upgrades_since_all(since) >= s.settings.coach_global_daily:
        count("coach_upgrade_global_cap_total")
        raise HTTPException(
            429, "hôm nay hệ thống đã dùng hết lượt tạo bản nâng cấp, hãy thử lại vào ngày mai"
        )
    metering = getattr(s.peers, "metering", None)
    key = f"upgrade-{response_id}"
    if metering is not None:
        refusal = metering.hold_upgrade(account_id=account.account_id, key=key)
        if refusal:
            raise HTTPException(402, refusal)
    status = s.repo.status_of(response_id) or {}
    task = s.tasks.get(status.get("task_id") or "")
    transcript = report.asr.text.strip()
    message = user_message(task.prompt_text if task else "", transcript, band, NEXT[band])
    try:
        with_usage = getattr(provider, "complete_with_usage", None)
        raw, used = with_usage(message) if with_usage else (provider.complete(message), {})
        made = parse(raw, transcript)
    except UpgradeError as e:
        if metering is not None:
            metering.settle_upgrade(key=key, result=False)
        count("coach_upgrade_failed_total")
        raise HTTPException(502, str(e)) from e
    kept = {
        "from_band": band,
        "to_band": NEXT[band],
        "upgraded": made.upgraded,
        "changes": made.changes,
        "phrases": made.phrases,
        "provider": provider.name,
        "model": provider.model,
        "prompt_version": PROMPT_VERSION,
        "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "input_tokens": used.get("input_tokens"),
        "output_tokens": used.get("output_tokens"),
    }
    s.repo.save_upgrade(response_id, kept)
    if metering is not None:
        metering.settle_upgrade(
            key=key,
            result=True,
            input_tokens=used.get("input_tokens"),
            output_tokens=used.get("output_tokens"),
        )
    s.repo.write_audit(account.pseudonym, "coach.upgrade", response_id, provider.name)
    count("coach_upgrade_total")
    return kept


# ================================================================= phrase book (D070)


class PhraseReview(BaseModel):
    key: str = Field(min_length=1, max_length=200)
    remembered: bool


def _phrase_cards(account_id: str) -> tuple[list[dict], list[dict]]:
    upgrades = svc().repo.upgrades_of_account(account_id)
    return upgrades, phrasebook.cards(upgrades, phrasebook.now_utc())


@router.get("/api/v1/me/phrases", tags=["student"])
def my_phrases(account: Account = Depends(require_login)) -> dict:
    now = phrasebook.now_utc()
    _, cards = _phrase_cards(account.account_id)
    return {
        **phrasebook.summary(cards, now),
        "due": phrasebook.due_today(cards, now),
        "cards": sorted(cards, key=lambda c: (c["box"], c["key"])),
    }


@router.post("/api/v1/me/phrases/review", tags=["student"])
def review_phrase(body: PhraseReview, account: Account = Depends(require_login)) -> dict:
    now = phrasebook.now_utc()
    key = phrasebook.key_of(body.key)
    upgrades, cards = _phrase_cards(account.account_id)
    card = next((c for c in cards if c["key"] == key), None)
    if card is None:
        raise HTTPException(404, "không có cụm từ này trong sổ của bạn")
    state = phrasebook.reviewed(card, body.remembered, now)
    # Every upgrade that suggested the phrase carries the same state, so the
    # card stays one card whichever of them is erased later.
    for u in upgrades:
        phrases = u.get("phrases") or []
        if any(phrasebook.key_of(p.get("phrase") or "") == key for p in phrases):
            svc().repo.save_upgrade_phrases(u["response_id"], phrasebook.apply(phrases, key, state))
    return {**card, **state}
