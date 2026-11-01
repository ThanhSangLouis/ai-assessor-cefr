"""The language model's use, counted the way the provider counts it (D072).

Google's free quota is a number of requests a day, and its day ends at
midnight Pacific time; a request that failed, or was a retry, counts like any
other. So the global cap counts every request sent (`Calls`), in the
provider's day (`provider_day`), not upgrades made in a rolling 24 hours.

On a paid tier the cap is money instead: with `AICEFR_COACH_DAILY_BUDGET_USD`
set, a day ends when what its tokens cost at the configured prices reaches the
budget. The tokens are the provider's own counts, kept with every upgrade.
"""

from __future__ import annotations

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


def budget_mode(settings) -> bool:
    """Whether the day is capped by money (paid tier) rather than requests (free tier)."""
    return settings.coach_budget_usd > 0


def global_refusal(settings, day: dict) -> str | None:
    """Why no one may ask the model again today, or None."""
    if budget_mode(settings):
        if day.get("cost_usd", 0) >= settings.coach_budget_usd:
            return (
                "hôm nay hệ thống đã dùng hết ngân sách tạo bản nâng cấp, hãy thử lại vào ngày mai"
            )
        return None
    if day.get("requests", 0) >= settings.coach_global_daily:
        return "hôm nay hệ thống đã dùng hết lượt tạo bản nâng cấp, hãy thử lại vào ngày mai"
    return None
