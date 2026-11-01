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

D072: what it costs. A cap for everyone together keeps the system under the
provider's free daily quota: every request sent, retries and failures
included, in the provider's day (`coach/usage.py`); on a paid tier a daily
budget in USD replaces it. `GET /api/v1/admin/coach` gives the administrator
those counters for the last days; D073: `PUT /api/v1/admin/coach/tier` is the
administrator's switch between the two, with the paid tier's own key. On the
metered channel an upgrade costs `AICEFR_PRICE_UPGRADE_RUNS` runs: held
before the model is asked, charged when the upgrade is made, released when the
model fails. The provider's own token
counts go to the ledger entry and the day's counters, not into the upgrade.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from aicefr.api.deps import ADMIN_ONLY, require_login
from aicefr.coach import phrasebook, usage
from aicefr.coach.providers import OPENAI_COMPATIBLE, PAID_KEY_ENV, provider_from
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
        and _provider(_tier()) is not None
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
    tier = _tier()
    provider = _provider(tier)
    if provider is None:
        raise HTTPException(503, "máy chủ chưa bật tính năng bản nâng cấp")
    day = usage.provider_day()
    since = (datetime.now(UTC) - timedelta(days=1)).isoformat(timespec="seconds")
    if s.repo.upgrades_since(account.account_id, since) >= s.settings.coach_daily:
        s.repo.record_coach(day, refused_user=1)
        raise HTTPException(
            429, f"mỗi ngày tạo được tối đa {s.settings.coach_daily} bản nâng cấp, hãy thử lại sau"
        )
    refusal = usage.global_refusal(s.settings, tier, s.repo.coach_days([day])[0])
    if refusal:
        s.repo.record_coach(day, refused_global=1)
        count("coach_upgrade_global_cap_total")
        raise HTTPException(429, refusal)
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
    calls = usage.Calls()
    used: dict = {}
    try:
        with_usage = getattr(provider, "complete_with_usage", None)
        if with_usage:
            raw, used = with_usage(message, calls)
        else:
            calls.requests += 1
            raw = provider.complete(message)
        made = parse(raw, transcript)
    except UpgradeError as e:
        s.repo.record_coach(
            day,
            account_id=account.account_id,
            error=str(e),
            failed=1,
            **_counts(s.settings, tier, calls, used),
        )
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
    }
    s.repo.save_upgrade(response_id, kept)
    s.repo.record_coach(
        day,
        account_id=account.account_id,
        upgrades=1,
        **_counts(s.settings, tier, calls, used),
    )
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


def _tier() -> usage.Tier:
    return usage.tier_of(svc().settings, svc().repo.get_config(usage.TIER_KEY))


def _provider(tier: usage.Tier):
    """The provider serving `tier`: the paid tier asks with the paid key (D073)."""
    return provider_from(svc().settings, paid=tier.paid)


def _counts(settings, tier: usage.Tier, calls: usage.Calls, used: dict) -> dict:
    """The day's counters for one answer of the provider, on the tier that served it."""
    i, o = used.get("input_tokens") or 0, used.get("output_tokens") or 0
    cost = usage.cost_usd(settings, i, o)
    return {"input_tokens": i, "output_tokens": o, **usage.day_counts(tier, calls.requests, cost)}


# ================================================================= the dashboard (D072)

DASHBOARD_DAYS = 14


@router.get("/api/v1/admin/coach", tags=["admin"], dependencies=[ADMIN_ONLY])
def coach_dashboard() -> dict:
    """The language model's use: today against the cap, and the last 14 days."""
    st = svc().settings
    tier = _tier()
    provider = _provider(tier)
    free = provider_from(st)
    name = st.coach_provider
    preset = OPENAI_COMPATIBLE.get(name)
    days = svc().repo.coach_days(usage.last_days(DASHBOARD_DAYS))
    model = st.coach_model or (preset.model if preset else "")
    return {
        "provider": name,
        "model": provider.model if provider else model,
        "enabled": provider is not None,
        "missing_key": (
            (PAID_KEY_ENV if tier.paid else preset.key_env)
            if preset and provider is None and name != "off"
            else None
        ),
        "tier": tier.name,
        "tier_changed_by": tier.changed_by,
        "tier_changed_at": tier.changed_at,
        "free_ready": free is not None,
        "paid_ready": provider_from(st, paid=True) is not None,
        "paid_key_env": PAID_KEY_ENV,
        "daily_requests": st.coach_global_daily,
        "budget_usd": tier.budget_usd or st.coach_budget_usd,
        "used_today": usage.used_today(tier, days[-1]),
        "cap_today": usage.cap_of(st, tier),
        "free_used_up": days[-1]["free_requests"] >= st.coach_global_daily,
        "per_student_daily": st.coach_daily,
        "price_input_usd": st.coach_price_input_usd,
        "price_output_usd": st.coach_price_output_usd,
        "today": days[-1],
        "resets_at": usage.resets_at(),
        "days": days,
    }


class TierIn(BaseModel):
    tier: Literal["free", "paid"]
    # A ceiling against a runaway day, not a forecast: well above any real use.
    budget_usd: float | None = Field(default=None, gt=0, le=500)


@router.put("/api/v1/admin/coach/tier", tags=["admin"])
def set_coach_tier(body: TierIn, account: Account = ADMIN_ONLY) -> dict:
    """Switch the language model between the free quota and a paid daily budget (D073).

    The administrator's call, made on the dashboard: who and when are kept
    with the setting and in the audit log.
    """
    s = svc()
    paid = body.tier == "paid"
    if paid and body.budget_usd is None:
        raise HTTPException(422, "hãy đặt ngân sách mỗi ngày cho gói trả phí")
    if paid and provider_from(s.settings, paid=True) is None:
        raise HTTPException(
            409, f"máy chủ chưa có khoá trả phí: thêm {PAID_KEY_ENV} vào .env rồi khởi động lại"
        )
    budget = body.budget_usd if paid else (_tier().budget_usd or 0.0)
    value = usage.tier_value(paid, budget)
    s.repo.set_config(usage.TIER_KEY, value, body.tier, account.pseudonym)
    detail = f"tier={body.tier} budget_usd={budget}" if paid else "tier=free"
    s.repo.write_audit(account.pseudonym, "coach.tier", None, detail)
    return coach_dashboard()


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
