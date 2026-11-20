"""What other services may ask the metering service (D049): may this run, and settle it.

With metering off (`AICEFR_METERING`, the default) every hold is allowed and
nothing is written: the school and research deployment never charges per use
(BR-29, BR-30). No refusal crosses the wire as an exception: `hold` returns the
sentence to show, or None for "allowed".

D101: the free runs of the month and the free lesson recordings of the day
go only to an account whose email is verified (or that has no email: one made
by an administrator). One person, many unverified sign-ups, many free runs:
that is what the rule closes.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from aicefr.metering.pricing import (
    DEFAULT_PRICES,
    UNITS_PER_RUN,
    PriceList,
    as_idpoint,
    as_runs,
    hold_for,
    lesson_units,
    passage_units,
    units_for,
    upgrade_units,
)
from aicefr.observability import count
from aicefr.platform.rpc import exposed
from aicefr.practice.streak import LOCAL_TZ
from aicefr.services.core.metering.price_book import PriceBook
from aicefr.storage.audit_repository import AuditLog
from aicefr.storage.metering_repository import (
    DailyCapReached,
    InsufficientCredits,
    LedgerState,
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
        free_ok: Callable[[str], bool] | None = None,
    ) -> None:
        self.store = store
        self.audit = audit
        self.enabled = enabled
        self.book = prices if isinstance(prices, PriceBook) else PriceBook(store, prices)
        # D101: may this account use the free runs? The identity service knows.
        self.free_ok = free_ok or (lambda _account_id: True)

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
    def free_runs_locked(self, account_id: str) -> bool:
        """True when the free runs wait for this account to verify its email (D101)."""
        return self.enabled and not self.free_ok(account_id)

    def _locked_hint(self, free: bool) -> str:
        return "" if free else ". Xác minh email ở trang Tài khoản để nhận lượt miễn phí"

    @exposed
    def hold(self, account_id: str, action: str, key: str, max_seconds: float) -> str | None:
        """Hold what a recording of at most `max_seconds` may cost; the refusal, or None."""
        if not self.enabled:
            return None
        free = self.free_ok(account_id)
        try:
            units = hold_for(self.prices, max_seconds)
            self.store.hold(account_id, MeteredAction(action), key, units, free_ok=free)
        except InsufficientCredits as e:
            return (
                f"bạn cần {as_runs(e.needed):g} lượt cho bài này nhưng chỉ còn"
                f" {as_runs(e.available):g} lượt. Mua thêm lượt ở trang Lượt của tôi để tiếp tục"
                + self._locked_hint(free)
            )
        return None

    @exposed
    def settle(
        self,
        key: str,
        action: str,
        result: bool,
        seconds: float | None = None,
    ) -> None:
        """Charge what the recording lasted when the person got a result (D057);
        release the hold otherwise. Without its length, the whole hold is charged."""
        if self.enabled:
            charge = units_for(self.prices, seconds) if seconds is not None else None
            entry = self.store.settle(key, MeteredAction(action), result, charge)
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
        free = self.free_ok(account_id)
        b = self.store.balance(account_id, free)
        return {
            "minute_runs": as_runs(units),
            "minute_idpoint": as_idpoint(prices, units),
            "free_per_day": prices.lesson_free_per_day,
            "free_left_today": (
                max(0, prices.lesson_free_per_day - done["free_used"]) if free else 0
            ),
            "free_locked": not free,
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
        free = self.free_ok(account_id)
        if not free and lesson_units(prices, max_seconds) <= 0:
            # D101 with D106: the lesson path is free, and free things wait for
            # a verified email; without this an unverified sign-up recorded free.
            count("metering_lesson_refused_total", reason="unverified")
            return {
                "status": 402,
                "message": "Bản ghi trong lộ trình miễn phí cho tài khoản đã xác minh email"
                + self._locked_hint(False),
            }
        try:
            self.store.hold_lesson(
                account_id,
                key,
                lesson_units(prices, max_seconds),
                self.today(),
                prices.lesson_free_per_day,
                prices.lesson_daily_cap,
                free_ok=free,
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
            per_day = prices.lesson_free_per_day
            spent = f"Đã hết {per_day} bản ghi miễn phí hôm nay; b" if per_day and free else "B"
            return {
                "status": 402,
                "message": f"{spent}ản ghi này cần {as_runs(e.needed):g} lượt nhưng bạn chỉ còn"
                f" {as_runs(e.available):g} lượt. Mua thêm lượt ở trang Lượt của tôi để học tiếp"
                + self._locked_hint(free),
            }
        return None

    @exposed
    def settle_lesson(
        self,
        key: str,
        result: bool,
        speaking_seconds: float | None = None,
    ) -> None:
        """Charge what was said when the recording was measured, release it otherwise.

        `result` is True only when something was measured: a recording the
        quality check refused (silence, not English, too short) gives its
        place of the day and its runs back, as a failure does.
        """
        if not self.enabled:
            return
        seconds = max(0.0, float(speaking_seconds or 0.0))
        charge = lesson_units(self.prices, seconds) if result else None
        entry = self.store.settle(key, MeteredAction.LESSON, result, charge)
        if entry is not None:
            count("metering_units_total", entry["charged"], action="lesson", state=entry["state"])

    # ------------------------------------------------------------ upgrades (D072)

    def _run_paid_for(self, response_id: str | None) -> bool:
        """D107: a run was charged when this recording was scored.

        Its AI rewrite is then part of that run: the model's bill for it is a
        small part of what the run sold for.
        """
        if not response_id:
            return False
        entry = self.store.entry(response_id, MeteredAction.ASSESSMENT)
        return (
            entry is not None
            and entry["state"] == LedgerState.CHARGED.value
            and entry["charged"] > 0
        )

    @exposed
    def upgrade_price(self, response_id: str | None = None) -> dict | None:
        """What the upgraded answer to `response_id` costs, in runs and IDPoint.

        `{"included": True}` when the recording's own run already paid for it
        (D107); None when it is free or nothing is counted.
        """
        if not self.enabled:
            return None
        if self._run_paid_for(response_id):
            return {"runs": 0, "idpoint": 0, "included": True}
        units = upgrade_units(self.prices)
        if units <= 0:
            return None
        return {"runs": as_runs(units), "idpoint": as_idpoint(self.prices, units)}

    def _passages_included(self, account_id: str | None) -> int:
        """D107: the reading passages this account's paid runs still bring, one a run."""
        if not account_id:
            return 0
        paid = self.store.runs_paid(account_id)
        return max(0, paid - self.store.included_taken(account_id, MeteredAction.DRILL_PASSAGE))

    @exposed
    def passage_price(self, account_id: str | None = None) -> dict | None:
        """What `account_id`'s next reading passage costs (D090).

        `{"included": True, "left": n}` while a scored recording's run still
        brings one (D107); None when it is free or nothing is counted.
        """
        if not self.enabled:
            return None
        left = self._passages_included(account_id)
        if left:
            return {"runs": 0, "idpoint": 0, "included": True, "left": left}
        units = passage_units(self.prices)
        if units <= 0:
            return None
        return {"runs": as_runs(units), "idpoint": as_idpoint(self.prices, units)}

    @exposed
    def hold_upgrade(
        self,
        account_id: str,
        key: str,
        action: str = "upgrade",
        response_id: str | None = None,
    ) -> str | None:
        """Hold the price of one language-model answer before the model is asked.

        `action` is "upgrade", a learner's upgraded answer (D072),
        "lesson_draft", a teacher's lesson draft (D075): one price for both; or
        "drill_passage", a reading passage around the unclear words (D090), at
        its own price. (Since D107 the lesson-draft service asks for no hold:
        a teacher's draft is free, five a day.) Free runs first, then the wallet, as for a
        recording. The refusal, or None; settled with `settle_upgrade` once the
        model answered or failed.

        D107: the upgrade of `response_id`, a recording scored for a run, and
        one reading passage for each such run take nothing: the run paid for
        them. The ledger still keeps them, marked `included`, so the learner
        sees them in the history.
        """
        what = MeteredAction(action)
        passage = what is MeteredAction.DRILL_PASSAGE
        units = passage_units(self.prices) if passage else upgrade_units(self.prices)
        if not self.enabled or units <= 0:
            return None
        included = (what is MeteredAction.UPGRADE and self._run_paid_for(response_id)) or (
            passage and self._passages_included(account_id) > 0
        )
        if included:
            self.store.hold(account_id, what, key, 0, included=True)
            return None
        free = self.free_ok(account_id)
        try:
            self.store.hold(account_id, what, key, units, free_ok=free)
        except InsufficientCredits as e:
            thing = {
                MeteredAction.LESSON_DRAFT: "bản soạn bài bằng AI",
                MeteredAction.DRILL_PASSAGE: "đoạn đọc",
            }.get(what, "bản nâng cấp")
            return (
                f"{thing} cần {as_runs(e.needed):g} lượt nhưng bạn chỉ còn"
                f" {as_runs(e.available):g} lượt. Mua thêm lượt ở trang Lượt của tôi để tiếp tục"
                + self._locked_hint(free)
            )
        return None

    @exposed
    def settle_upgrade(
        self,
        key: str,
        result: bool,
        action: str = "upgrade",
    ) -> None:
        """Charge the hold when the model answered, release it when it failed.

        The charge is today's price, never more than was held: a hold taken
        before D106 made the answer free is charged nothing.
        """
        if not self.enabled:
            return
        what = MeteredAction(action)
        passage = what is MeteredAction.DRILL_PASSAGE
        price = passage_units(self.prices) if passage else upgrade_units(self.prices)
        entry = self.store.settle(key, what, result, price)
        if entry is not None:
            count("metering_units_total", entry["charged"], action=what.value, state=entry["state"])

    @exposed
    def runs_left(self, account_id: str) -> float | None:
        """Free and bought runs together; None where nothing is counted."""
        if not self.enabled:
            return None
        b = self.store.balance(account_id, self.free_ok(account_id))
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
