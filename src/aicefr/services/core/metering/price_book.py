"""The prices in force (D078): the administrator's latest version, else the settings'.

An administrator sets them on the dashboard -- what a recording and an
upgraded answer cost, what a run is in IDPoint, the free runs
each month and the run packs on sale -- and every change is a new version
(`price-admin-N`). A charge keeps the version it was held under, so changing
the prices never rewrites what was already paid. Until the first change the
settings (`AICEFR_PRICE_*`, `AICEFR_CREDIT_PACKS`) stand.
"""

from __future__ import annotations

from aicefr.metering.pricing import UNITS_PER_RUN, PriceList
from aicefr.storage.metering_repository import MeteringRepository

FIELDS = ("first_minute_runs", "extra_minute_runs", "upgrade_runs")


class PriceBook:
    def __init__(
        self,
        store: MeteringRepository,
        defaults: PriceList,
        packs: tuple[tuple[int, int], ...] = (),
    ) -> None:
        self.store = store
        self.defaults = defaults
        self.default_packs = tuple(packs)

    def current(self) -> PriceList:
        doc = self.store.price_list()
        if not doc:
            return self.defaults
        return PriceList(
            **{f: float(doc[f]) for f in FIELDS},
            idpoint_per_run=int(doc["idpoint_per_run"]),
            version=doc["version"],
        )

    def packs(self) -> tuple[tuple[int, int], ...]:
        doc = self.store.price_list()
        if not doc:
            return self.default_packs
        return tuple((int(p["runs"]), int(p["price_vnd"])) for p in doc.get("packs", []))

    def view(self) -> dict:
        doc = self.store.price_list() or {}
        return {
            **self.current().as_dict(),
            "free_runs": self.store.free_units / UNITS_PER_RUN,
            "packs": [{"runs": r, "price_vnd": p} for r, p in self.packs()],
            "from_settings": not doc,
            "changed_by": doc.get("changed_by"),
            "changed_at": doc.get("changed_at"),
            "history": [
                {k: h.get(k) for k in ("version", "changed_by", "changed_at")}
                for h in self.store.price_history()
            ],
        }

    def set(self, values: dict, by: str) -> dict:
        """Save a new version; ValueError when a price is impossible."""
        PriceList(
            **{f: float(values[f]) for f in FIELDS}, idpoint_per_run=int(values["idpoint_per_run"])
        )
        packs = sorted({int(p["runs"]): int(p["price_vnd"]) for p in values["packs"]}.items())
        if any(r <= 0 or v <= 0 for r, v in packs):
            raise ValueError("gói lượt phải có số lượt và giá lớn hơn 0")
        if float(values["free_runs"]) < 0:
            raise ValueError("lượt miễn phí không được âm")
        return self.store.set_price_list(
            {
                **{f: float(values[f]) for f in FIELDS},
                "idpoint_per_run": int(values["idpoint_per_run"]),
                "free_runs": float(values["free_runs"]),
                "packs": [{"runs": r, "price_vnd": v} for r, v in packs],
            },
            by,
        )
