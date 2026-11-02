"""The language model's use, counted the way the provider counts it (D072).

Google's free quota is a number of requests a day, and its day ends at
midnight Pacific time; a request that failed, or was a retry, counts like any
other. So the global cap counts every request sent (`Calls`), in the
provider's day (`provider_day`), not upgrades made in a rolling 24 hours.

On a paid tier the cap is money instead: a day ends when what its tokens cost
at the configured prices reaches the budget. The tokens are the provider's own
counts. Which tier is in force is the administrator's call on the dashboard
(D073, `Tier`); `AICEFR_COACH_DAILY_BUDGET_USD` only sets where a deployment
starts.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

# Where Google's daily quota resets (Gemini API rate limits: "reset at
# midnight Pacific time").
PROVIDER_ZONE = ZoneInfo("America/Los_Angeles")


@dataclass
class Calls:
    """How many requests one upgrade sent the provider, retries included."""

    requests: int = 0


def provider_day(now: datetime | None = None) -> str:
    """The provider's calendar day `now` falls in, as YYYY-MM-DD."""
    return (now or datetime.now(UTC)).astimezone(PROVIDER_ZONE).date().isoformat()


def resets_at(now: datetime | None = None) -> str:
    """When the provider's current day ends, in UTC."""
    local = (now or datetime.now(UTC)).astimezone(PROVIDER_ZONE)
    midnight = datetime.combine(
        local.date() + timedelta(days=1), datetime.min.time(), PROVIDER_ZONE
    )
    return midnight.astimezone(UTC).isoformat(timespec="seconds")


def last_days(n: int, now: datetime | None = None) -> list[str]:
    """The provider's last `n` days, oldest first, today last."""
    today = datetime.fromisoformat(provider_day(now)).date()
    return [(today - timedelta(days=i)).isoformat() for i in range(n - 1, -1, -1)]


def cost_usd(settings, input_tokens: int | None, output_tokens: int | None) -> float:
    """What the tokens cost at the configured prices per million, in USD."""
    return (
        (input_tokens or 0) * settings.coach_price_input_usd
        + (output_tokens or 0) * settings.coach_price_output_usd
    ) / 1_000_000


# D073: which tier serves the requests, chosen by an administrator on the
# dashboard and kept as runtime configuration (who, when). Unset, the
# deployment's own setting decides: a budget above 0 means paid.
TIER_KEY = "coach_tier"


@dataclass(frozen=True)
class Tier:
    """Free (the provider's free quota, counted in requests) or paid (a budget in USD)."""

    paid: bool
    budget_usd: float
    changed_by: str | None = None
    changed_at: str | None = None

    @property
    def name(self) -> str:
        return "paid" if self.paid else "free"


def tier_of(settings, stored) -> Tier:
    """The tier in force: the administrator's choice (`AppConfig`), else the deployment's."""
    if stored is not None:
        value = json.loads(stored.value)
        return Tier(
            paid=value.get("tier") == "paid",
            budget_usd=float(value.get("budget_usd") or 0),
            changed_by=stored.updated_by,
            changed_at=stored.updated_at,
        )
    return Tier(paid=settings.coach_budget_usd > 0, budget_usd=settings.coach_budget_usd)


def tier_value(paid: bool, budget_usd: float) -> str:
    """The stored form of a tier, as `tier_of` reads it back."""
    return json.dumps({"tier": "paid" if paid else "free", "budget_usd": budget_usd})


def day_counts(tier: Tier, requests: int, cost: float) -> dict:
    """The counters one answer adds, on the tier that served it.

    The free quota counts the free tier's requests only, the budget the paid
    tier's cost only, so switching tiers in the middle of a day mixes neither.
    """
    if tier.paid:
        paid = {"paid_requests": requests, "paid_cost_usd": cost}
        return {"requests": requests, "cost_usd": cost, **paid}
    return {"requests": requests, "cost_usd": cost, "free_requests": requests}


def used_today(tier: Tier, day: dict) -> float:
    """How much of today's cap the tier in force has used: requests, or USD."""
    return day.get("paid_cost_usd", 0) if tier.paid else day.get("free_requests", 0)


def cap_of(settings, tier: Tier) -> float:
    return tier.budget_usd if tier.paid else settings.coach_global_daily


def global_refusal(settings, tier: Tier, day: dict) -> str | None:
    """Why no one may ask the model again today, or None."""
    if used_today(tier, day) < cap_of(settings, tier):
        return None
    if tier.paid:
        return "hôm nay hệ thống đã dùng hết ngân sách tạo bản nâng cấp, hãy thử lại vào ngày mai"
    return "hôm nay hệ thống đã dùng hết lượt tạo bản nâng cấp, hãy thử lại vào ngày mai"
