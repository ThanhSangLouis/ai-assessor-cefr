"""Storage of licences, orders and payment events (D033).

Four tables, none of them holding anything about a person: an order knows the
administrator account that placed it, the plan, the seats and the money; a
payment event keeps the gateway's codes and transaction number; the
organisation's name is a setting. No card number, bank account or payer name
ever reaches this file (BR-32).

Marking an order paid and installing the licence it bought happen in one
transaction, guarded by the order's status: when the browser's return and the
gateway's notification report the same payment at once, exactly one of them
installs a licence.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from aicefr.billing.payments import SETTLEABLE, OrderStatus
from aicefr.billing.plans import License, Plan
from aicefr.storage.db import Connection, DbRow, SqlStore, add_columns
from aicefr.storage.db import now_iso as _now

SCHEMA = """
CREATE TABLE IF NOT EXISTS billing_license (
    license_id    TEXT PRIMARY KEY,
    organization  TEXT NOT NULL,
    plan          TEXT NOT NULL,
    seats         INTEGER NOT NULL,
    valid_from    TEXT NOT NULL,
    valid_to      TEXT NOT NULL,
    source        TEXT NOT NULL,                  -- trial | order | key
    order_id      TEXT,
    value_vnd     INTEGER NOT NULL DEFAULT 0,
    license_key   TEXT,
    installed_by  TEXT,
    installed_at  TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS billing_order (
    order_id      TEXT PRIMARY KEY,
    plan          TEXT NOT NULL,
    seats         INTEGER NOT NULL,
    months        INTEGER NOT NULL,
    unit_price    INTEGER NOT NULL,
    list_vnd      INTEGER NOT NULL,               -- students x months x unit price
    discount_vnd  INTEGER NOT NULL DEFAULT 0,     -- a school year paid at once
    gross_vnd     INTEGER NOT NULL,               -- list minus discount: what the licence is worth
    credit_vnd    INTEGER NOT NULL DEFAULT 0,
    amount_vnd    INTEGER NOT NULL,
    kind          TEXT NOT NULL,                  -- new | renewal | upgrade | downgrade
    starts_on     TEXT NOT NULL,
    ends_on       TEXT NOT NULL,
    status        TEXT NOT NULL,                  -- pending | paid | failed | cancelled | expired
    gateway       TEXT NOT NULL,                  -- none | sandbox | vnpay | stripe | momo
    live          INTEGER NOT NULL DEFAULT 0,     -- 1: real money (D035)
    checkout_ref  TEXT,                           -- the gateway's id for the checkout, if any
    reference     TEXT,
    result_code   TEXT,
    created_by    TEXT NOT NULL,
    created_at    TEXT NOT NULL,
    expires_at    TEXT NOT NULL,
    settled_at    TEXT
);
CREATE INDEX IF NOT EXISTS idx_billing_order_created ON billing_order(created_at);
CREATE TABLE IF NOT EXISTS billing_event (
    event_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id     TEXT,
    kind         TEXT NOT NULL,
    detail_json  TEXT NOT NULL DEFAULT '{}',
    created_at   TEXT NOT NULL,
    fingerprint  TEXT,                            -- the detail without "applied" (D035)
    repeats      INTEGER NOT NULL DEFAULT 0,      -- identical messages after the first
    last_at      TEXT
);
CREATE TABLE IF NOT EXISTS billing_setting (
    key         TEXT PRIMARY KEY,
    value       TEXT NOT NULL,
    updated_by  TEXT,
    updated_at  TEXT NOT NULL
);
"""


class BillingRepository(SqlStore):
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = str(db_path)
        with self._conn() as c:
            c.executescript(SCHEMA)
            # D035 added two columns; a database from before gets them here.
            add_columns(
                c,
                "billing_order",
                (("live", "INTEGER NOT NULL DEFAULT 0"), ("checkout_ref", "TEXT")),
            )
            add_columns(
                c,
                "billing_event",
                (
                    ("fingerprint", "TEXT"),
                    ("repeats", "INTEGER NOT NULL DEFAULT 0"),
                    ("last_at", "TEXT"),
                ),
            )
            c.execute(
                "CREATE INDEX IF NOT EXISTS idx_billing_order_checkout"
                " ON billing_order(checkout_ref)"
            )
            # Events from before D035 have no fingerprint; NULLs never collide.
            c.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_billing_event_once"
                " ON billing_event(order_id, kind, fingerprint)"
            )

    # ------------------------------------------------------------ licences

    @staticmethod
    def _license(row: DbRow) -> License:
        return License(
            license_id=row["license_id"],
            organization=row["organization"],
            plan=Plan(row["plan"]),
            seats=row["seats"],
            valid_from=date.fromisoformat(row["valid_from"]),
            valid_to=date.fromisoformat(row["valid_to"]),
            source=row["source"],
            order_id=row["order_id"],
            value_vnd=row["value_vnd"],
            installed_at=row["installed_at"],
        )

    def licenses(self) -> list[License]:
        with self._conn() as c:
            rows = c.execute(
                "SELECT * FROM billing_license ORDER BY installed_at, rowid"
            ).fetchall()
        return [self._license(r) for r in rows]

    def has_license(self, license_id: str) -> bool:
        with self._conn() as c:
            return (
                c.execute(
                    "SELECT 1 FROM billing_license WHERE license_id=?", (license_id,)
                ).fetchone()
                is not None
            )

    @staticmethod
    def _insert_license(
        c: Connection, lic: License, key: str | None, by: str | None, at: str
    ) -> None:
        c.execute(
            "INSERT INTO billing_license(license_id, organization, plan, seats, valid_from,"
            " valid_to, source, order_id, value_vnd, license_key, installed_by, installed_at)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                lic.license_id,
                lic.organization,
                lic.plan.value,
                lic.seats,
                lic.valid_from.isoformat(),
                lic.valid_to.isoformat(),
                lic.source,
                lic.order_id,
                lic.value_vnd,
                key,
                by,
                at,
            ),
        )

    def add_license(self, lic: License, key: str | None = None, by: str | None = None) -> None:
        with self._conn() as c:
            self._insert_license(c, lic, key, by, lic.installed_at or _now())

    def start_trial(self, lic: License) -> bool:
        """Install the deployment's one trial; False when it was started before.

        The marker and the licence go in together, so two first requests at
        once start one trial, not two.
        """
        with self._conn() as c:
            c.execute("BEGIN IMMEDIATE")
            n = c.execute(
                "INSERT OR IGNORE INTO billing_setting(key, value, updated_at) VALUES (?,?,?)",
                ("trial_started", lic.license_id, _now()),
            ).rowcount
            if n:
                self._insert_license(c, lic, None, None, lic.installed_at or _now())
        return bool(n)

    # ------------------------------------------------------------ orders

    def create_order(self, order: dict) -> dict:
        cols = (
            "order_id plan seats months unit_price list_vnd discount_vnd gross_vnd credit_vnd"
            " amount_vnd kind"
            " starts_on ends_on status gateway live created_by created_at expires_at"
        ).split()
        with self._conn() as c:
            marks = ",".join("?" * len(cols))
            c.execute(
                f"INSERT INTO billing_order({', '.join(cols)}) VALUES ({marks})",
                [order[k] for k in cols],
            )
        return self.order(order["order_id"])

    def set_checkout_ref(self, order_id: str, reference: str) -> None:
        with self._conn() as c:
            c.execute(
                "UPDATE billing_order SET checkout_ref=? WHERE order_id=?", (reference, order_id)
            )

    def order_by_checkout(self, gateway: str, reference: str) -> dict | None:
        """The order whose checkout the gateway knows by `reference` (a Stripe session id)."""
        with self._conn() as c:
            row = c.execute(
                "SELECT * FROM billing_order WHERE gateway=? AND checkout_ref=?",
                (gateway, reference),
            ).fetchone()
        return dict(row) if row else None

    def order(self, order_id: str) -> dict | None:
        with self._conn() as c:
            row = c.execute("SELECT * FROM billing_order WHERE order_id=?", (order_id,)).fetchone()
        return dict(row) if row else None

    def orders(self, limit: int = 50) -> list[dict]:
        with self._conn() as c:
            rows = c.execute(
                "SELECT * FROM billing_order ORDER BY created_at DESC, rowid DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]

    def expire_pending(self, now: str) -> list[str]:
        """Pending orders past their time: expired. Returns their ids."""
        with self._conn() as c:
            rows = c.execute(
                "SELECT order_id FROM billing_order WHERE status=? AND expires_at <= ?",
                (OrderStatus.PENDING.value, now),
            ).fetchall()
            ids = [r["order_id"] for r in rows]
            c.executemany(
                "UPDATE billing_order SET status=? WHERE order_id=? AND status=?",
                [(OrderStatus.EXPIRED.value, i, OrderStatus.PENDING.value) for i in ids],
            )
        return ids

    def retire(self, order_id: str) -> None:
        """A pending order replaced by a newer one: expired, so a late payment still counts."""
        with self._conn() as c:
            c.execute(
                "UPDATE billing_order SET status=? WHERE order_id=? AND status=?",
                (OrderStatus.EXPIRED.value, order_id, OrderStatus.PENDING.value),
            )

    def settle(
        self,
        order_id: str,
        status: OrderStatus,
        reference: str,
        code: str,
        license: License | None = None,
        by: str | None = None,
    ) -> bool:
        """Move an order from pending or expired to `status`, installing `license` with it.

        One transaction, guarded by the status the order is in: returns False,
        and changes nothing, when another message settled the order first.
        """
        settleable = [s.value for s in SETTLEABLE]
        at = _now()
        with self._conn() as c:
            c.execute("BEGIN IMMEDIATE")
            n = c.execute(
                "UPDATE billing_order SET status=?, reference=?, result_code=?, settled_at=?"
                f" WHERE order_id=? AND status IN ({','.join('?' * len(settleable))})",
                (status.value, reference, code, at, order_id, *settleable),
            ).rowcount
            if n and license is not None:
                self._insert_license(c, license, None, by, at)
        return bool(n)

    # ------------------------------------------------------------ events and settings

    def add_event(self, order_id: str | None, kind: str, detail: dict | None = None) -> None:
        """Keep what was said about an order.

        A message identical to one already kept -- same kind, same content,
        whether or not it was applied -- is counted on that row rather than
        stored again: a signed address replayed a thousand times is one row
        that says a thousand, not a thousand rows.
        """
        detail = detail or {}
        fingerprint = json.dumps(
            {k: v for k, v in detail.items() if k != "applied"}, sort_keys=True, ensure_ascii=False
        )
        with self._conn() as c:
            c.execute(
                "INSERT INTO billing_event(order_id, kind, detail_json, created_at, fingerprint)"
                " VALUES (?,?,?,?,?)"
                " ON CONFLICT(order_id, kind, fingerprint) DO UPDATE SET"
                " repeats = billing_event.repeats + 1, last_at = excluded.created_at",
                (order_id, kind, json.dumps(detail, ensure_ascii=False), _now(), fingerprint),
            )

    def events(self, order_id: str) -> list[dict]:
        with self._conn() as c:
            rows = c.execute(
                "SELECT kind, detail_json, created_at, repeats, last_at FROM billing_event"
                " WHERE order_id=? ORDER BY event_id",
                (order_id,),
            ).fetchall()
        return [
            {
                "kind": r["kind"],
                "detail": json.loads(r["detail_json"]),
                "created_at": r["created_at"],
                "repeats": r["repeats"],
                "last_at": r["last_at"],
            }
            for r in rows
        ]

    def setting(self, key: str) -> str | None:
        with self._conn() as c:
            row = c.execute("SELECT value FROM billing_setting WHERE key=?", (key,)).fetchone()
        return row["value"] if row else None

    def set_setting(self, key: str, value: str, by: str | None = None) -> None:
        with self._conn() as c:
            c.execute(
                "INSERT INTO billing_setting(key, value, updated_by, updated_at) VALUES (?,?,?,?)"
                " ON CONFLICT(key) DO UPDATE SET value=excluded.value,"
                " updated_by=excluded.updated_by, updated_at=excluded.updated_at",
                (key, value, by, _now()),
            )

    def setting_once(self, key: str, value: str) -> str:
        """Store `value` unless the key already has one; return the value kept."""
        with self._conn() as c:
            c.execute(
                "INSERT OR IGNORE INTO billing_setting(key, value, updated_at) VALUES (?,?,?)",
                (key, value, _now()),
            )
            return c.execute("SELECT value FROM billing_setting WHERE key=?", (key,)).fetchone()[
                "value"
            ]
