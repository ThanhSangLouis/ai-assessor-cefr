"""What other services may ask the metering service (D049): may this run, and settle it.

With metering off (`AICEFR_METERING`, the default) every hold is allowed and
nothing is written: the school and research deployment never charges per use
(BR-29, BR-30). No refusal crosses the wire as an exception: `hold` returns the
sentence to show, or None for "allowed".
"""

from __future__ import annotations

from datetime import datetime

from aicefr.metering.pricing import (
    DEFAULT_PRICES,
    UNITS_PER_RUN,
    PriceList,
    TokenUsage,
    as_idpoint,
    as_runs,
    hold_for,
    lesson_units,
    passage_units,
    units_for,
    upgrade_units,
    usage_of,
)
from aicefr.observability import count
from aicefr.platform.rpc import exposed
from aicefr.practice.streak import LOCAL_TZ
from aicefr.services.core.metering.price_book import PriceBook
from aicefr.storage.audit_repository import AuditLog
from aicefr.storage.metering_repository import (
    DailyCapReached,
    InsufficientCredits,
    MeteredAction,
    MeteringRepository,
)


class MeteringFacade:
    def __init__(
        self,
        store: MeteringRepository,
        audit: AuditLog,
        enabled: bool,
        prices: PriceList | PriceBook = DEFAULT_PRICES,
    ) -> None:
        self.store = store
        self.audit = audit
        self.enabled = enabled
        self.book = prices if isinstance(prices, PriceBook) else PriceBook(store, prices)

    @property
    def prices(self) -> PriceList:
        """The prices in force now (D078): an administrator may change them any time."""
        return self.book.current()

    @exposed
    def run_packs(self) -> list[list[int]]:
        """The run packs on sale, `[[runs, price_vnd], ...]` (D078: set on the dashboard)."""
        return [list(p) for p in self.book.packs()]

    @exposed
    def is_enabled(self) -> bool:
        return self.enabled

    @exposed
    def hold(self, account_id: str, action: str, key: str, max_seconds: float) -> str | None:
        """Hold what a recording of at most `max_seconds` may cost; the refusal, or None."""
        if not self.enabled:
            return None
        try:
            units = hold_for(self.prices, max_seconds)
            self.store.hold(account_id, MeteredAction(action), key, units, self.prices.version)
        except InsufficientCredits as e:
            return (
                f"bạn cần {as_runs(e.needed):g} lượt cho bài này nhưng chỉ còn"
                f" {as_runs(e.available):g} lượt. Nạp thêm IDPoint để tiếp tục"
            )
        return None

    @exposed
    def settle(
        self,
        key: str,
        action: str,
        result: bool,
        seconds: float | None = None,
        output_tokens: int | None = None,
        words: int | None = None,
    ) -> None:
        """Charge what the recording lasted when the person got a result, and keep
        the tokens it used (D057); release the hold otherwise. Without its length,
        the whole hold is charged."""
        if self.enabled:
            usage = usage_of(seconds, output_tokens, words) if seconds is not None else None
            charge = units_for(self.prices, seconds) if usage else None
            entry = self.store.settle(key, MeteredAction(action), result, charge, usage)
            if entry is not None:
                count("metering_units_total", entry["charged"], action=action, state=entry["state"])

    # ------------------------------------------------------------ lesson recordings (D094)

    @staticmethod
    def today() -> str:
        """The Vietnam day a lesson recording counts in, as the streak's days are."""
        return datetime.now(LOCAL_TZ).date().isoformat()

    @exposed
    def lesson_quote(self, account_id: str) -> dict | None:
        """What a lesson recording costs this learner now; None when nothing is counted."""
        if not self.enabled:
            return None
        prices = self.prices
        done = self.store.lesson_today(account_id, self.today())
        units = lesson_units(prices, 60.0)
        b = self.store.balance(account_id)
        return {
            "minute_runs": as_runs(units),
            "minute_idpoint": as_idpoint(prices, units),
            "free_per_day": prices.lesson_free_per_day,
            "free_left_today": max(0, prices.lesson_free_per_day - done["free_used"]),
            "daily_cap": prices.lesson_daily_cap,
            "left_today": max(0, prices.lesson_daily_cap - done["used"]),
            "runs_left": as_runs(b["free_left"] + b["wallet"]),
        }

    @exposed
    def hold_lesson(self, account_id: str, key: str, max_seconds: float) -> dict | None:
        """Hold one recording on the lesson path before it is measured (D094).

        A place among the day's recordings, then -- past the free ones -- what
        `max_seconds` of speech would cost. The refusal as data, `{"status",
        "message"}`: 429 when the day is full, 402 when the runs fall short; or
        None for "go on". Settled with `settle_lesson` once measured.
        """
        if not self.enabled:
            return None
        prices = self.prices
        try:
            self.store.hold_lesson(
                account_id,
                key,
                lesson_units(prices, max_seconds),
                self.today(),
                prices.lesson_free_per_day,
                prices.lesson_daily_cap,
                prices.version,
            )
        except DailyCapReached as e:
            count("metering_lesson_refused_total", reason="cap")
            return {
                "status": 429,
                "message": f"Hôm nay bạn đã nói đủ {e.cap} bản ghi trong lộ trình."
                " Nghỉ một chút, mai học tiếp nhé",
            }
        except InsufficientCredits as e:
            count("metering_lesson_refused_total", reason="credits")
            free = prices.lesson_free_per_day
            spent = f"Đã hết {free} bản ghi miễn phí hôm nay; b" if free else "B"
            return {
                "status": 402,
                "message": f"{spent}ản ghi này cần {as_runs(e.needed):g} lượt nhưng bạn chỉ còn"
                f" {as_runs(e.available):g} lượt. Nạp thêm IDPoint để học tiếp",
            }
        return None

    @exposed
    def settle_lesson(
        self,
        key: str,
        result: bool,
        speaking_seconds: float | None = None,
        words: int | None = None,
    ) -> None:
        """Charge what was said when the recording was measured, release it otherwise.

        `result` is True only when something was measured: a recording the
        quality check refused (silence, not English, too short) gives its
        place of the day and its runs back, as a failure does.
        """
        if not self.enabled:
            return
        seconds = max(0.0, float(speaking_seconds or 0.0))
        usage = usage_of(seconds, None, words) if result else None
        charge = lesson_units(self.prices, seconds) if result else None
        entry = self.store.settle(key, MeteredAction.LESSON, result, charge, usage)
        if entry is not None:
            count("metering_units_total", entry["charged"], action="lesson", state=entry["state"])

    # ------------------------------------------------------------ upgrades (D072)

    @exposed
    def upgrade_price(self) -> dict | None:
        """What one upgraded answer costs, in runs and IDPoint; None when nothing is counted."""
        if not self.enabled:
            return None
        units = upgrade_units(self.prices)
        return {"runs": as_runs(units), "idpoint": as_idpoint(self.prices, units)}

    @exposed
    def passage_price(self) -> dict | None:
        """What one reading passage costs (D090); None when nothing is counted."""
        if not self.enabled:
            return None
        units = passage_units(self.prices)
        return {"runs": as_runs(units), "idpoint": as_idpoint(self.prices, units)}

    @exposed
    def hold_upgrade(self, account_id: str, key: str, action: str = "upgrade") -> str | None:
        """Hold the price of one language-model answer before the model is asked.

        `action` is "upgrade", a learner's upgraded answer (D072),
        "lesson_draft", a teacher's lesson draft (D075): one price for both; or
        "drill_passage", a reading passage around the unclear words (D090), at
        its own lower price. Free runs first, then the wallet, as for a
        recording. The refusal, or None; settled with `settle_upgrade` once the
        model answered or failed.
        """
        what = MeteredAction(action)
        passage = what is MeteredAction.DRILL_PASSAGE
        units = passage_units(self.prices) if passage else upgrade_units(self.prices)
        if not self.enabled or units <= 0:
            return None
        try:
            self.store.hold(account_id, what, key, units, self.prices.version)
        except InsufficientCredits as e:
            thing = {
                MeteredAction.LESSON_DRAFT: "bản soạn bài bằng AI",
                MeteredAction.DRILL_PASSAGE: "đoạn đọc",
            }.get(what, "bản nâng cấp")
            return (
                f"{thing} cần {as_runs(e.needed):g} lượt nhưng bạn chỉ còn"
                f" {as_runs(e.available):g} lượt. Nạp thêm IDPoint để tiếp tục"
            )
        return None

    @exposed
    def settle_upgrade(
        self,
        key: str,
        result: bool,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
        action: str = "upgrade",
    ) -> None:
        """Charge the hold when the model answered, release it when it failed.

        The language model's own token counts are kept with the entry, for the
        cost per request and the reconciliation, as Whisper's are for a recording.
        """
        if not self.enabled:
            return
        usage = (
            TokenUsage(int(input_tokens or 0), int(output_tokens or 0),
                       estimated=input_tokens is None or output_tokens is None)
            if result else None
        )  # fmt: skip
        what = MeteredAction(action)
        entry = self.store.settle(key, what, result, None, usage)
        if entry is not None:
            count("metering_units_total", entry["charged"], action=what.value, state=entry["state"])

    @exposed
    def runs_left(self, account_id: str) -> float | None:
        """Free and bought runs together; None where nothing is counted."""
        if not self.enabled:
            return None
        b = self.store.balance(account_id)
        return as_runs(b["free_left"] + b["wallet"])

    @exposed
    def credit(self, account_id: str, runs: int, order_id: str) -> bool:
        """Put a paid run pack in the buyer's wallet, once per order (D053).

        True when the runs are in the wallet, now or from an earlier call: the
        grant is unique on (source, reference), so a retry never credits twice.
        """
        if not self.enabled:
            return False
        if self.store.grant(account_id, runs * UNITS_PER_RUN, "order", order_id, None):
            self.audit.write(
                "billing", "metering.credit_order", account_id, f"runs={runs} order={order_id}"
            )
            count("metering_credited_runs_total", runs)
        return True

    @exposed
    def audit_recent(self, limit: int = 100) -> list[dict]:
        return self.audit.recent(limit)
