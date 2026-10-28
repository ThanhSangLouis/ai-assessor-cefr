"""What other services may ask the metering service (D049): may this run, and settle it.

With metering off (`AICEFR_METERING`, the default) every hold is allowed and
nothing is written: the school and research deployment never charges per use
(BR-29, BR-30). No refusal crosses the wire as an exception: `hold` returns the
sentence to show, or None for "allowed".
"""

from __future__ import annotations

from aicefr.metering.pricing import (
    DEFAULT_PRICES,
    UNITS_PER_RUN,
    Action,
    PriceList,
    as_runs,
    hold_for,
    units_for,
    usage_of,
)
from aicefr.observability import count
from aicefr.platform.rpc import exposed
from aicefr.storage.audit_repository import AuditLog
from aicefr.storage.metering_repository import InsufficientCredits, MeteringRepository


class MeteringFacade:
    def __init__(
        self,
        store: MeteringRepository,
        audit: AuditLog,
        enabled: bool,
        prices: PriceList = DEFAULT_PRICES,
    ) -> None:
        self.store = store
        self.audit = audit
        self.enabled = enabled
        self.prices = prices

    @exposed
    def is_enabled(self) -> bool:
        return self.enabled

    @exposed
    def hold(self, account_id: str, action: str, key: str, max_seconds: float) -> str | None:
        """Hold what a recording of at most `max_seconds` may cost; the refusal, or None."""
        if not self.enabled:
            return None
        try:
            units = hold_for(self.prices, Action(action), max_seconds)
            self.store.hold(account_id, Action(action), key, units, self.prices.version)
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
            charge = units_for(self.prices, Action(action), seconds) if usage else None
            entry = self.store.settle(key, Action(action), result, charge, usage)
            if entry is not None:
                count("metering_units_total", entry["charged"], action=action, state=entry["state"])

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
