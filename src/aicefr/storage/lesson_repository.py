"""Storage of lesson paths, published versions, step attempts and reviews (D025).

Lessons are edited as a DRAFT; publishing copies the draft into an immutable
`lesson_version` row. Learners read only published versions, and every attempt
records the version it was made against, so a result can always be read
against the exact text the learner saw.

Step attempts live in their own table, not in `response`. That keeps them out
of the review queue, the scoring statistics and the research export by
construction rather than by a filter someone could forget.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from aicefr.contracts import Band, Criterion
from aicefr.lessons.model import Lesson, StepResult, Topic, WordStatus, new_id
from aicefr.lessons.seed import (
    SAMPLE_LAYOUT,
    SAMPLE_PATH,
    SAMPLE_PATH_ID,
    SAMPLE_UNITS,
    sample_lessons,
)
from aicefr.storage.db import Connection, DbRow, SqlStore, add_columns
from aicefr.storage.db import now_iso as _now

SCHEMA = """
CREATE TABLE IF NOT EXISTS lesson_path (
    path_id      TEXT PRIMARY KEY,
    title        TEXT NOT NULL,
    description  TEXT NOT NULL DEFAULT '',
    band_from    TEXT,
    band_to      TEXT,
    status       TEXT NOT NULL DEFAULT 'draft',   -- draft | published | archived
    sample       INTEGER NOT NULL DEFAULT 0,
    created_by   TEXT,
    created_at   TEXT NOT NULL,
    updated_at   TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS lesson_unit (
    unit_id      TEXT PRIMARY KEY,
    path_id      TEXT NOT NULL REFERENCES lesson_path(path_id) ON DELETE CASCADE,
    title        TEXT NOT NULL,
    function     TEXT NOT NULL DEFAULT '',
    band         TEXT,
    criterion    TEXT,
    topic        TEXT,                            -- D027: what the unit talks about
    position     INTEGER NOT NULL,
    created_at   TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS lesson (
    lesson_id          TEXT PRIMARY KEY,
    unit_id            TEXT NOT NULL REFERENCES lesson_unit(unit_id) ON DELETE CASCADE,
    position           INTEGER NOT NULL,
    draft_json         TEXT NOT NULL,
    published_version  INTEGER NOT NULL DEFAULT 0,
    draft_changed      INTEGER NOT NULL DEFAULT 1,
    archived           INTEGER NOT NULL DEFAULT 0,
    updated_by         TEXT,
    updated_at         TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS lesson_version (
    lesson_id     TEXT NOT NULL,
    version       INTEGER NOT NULL,
    lesson_json   TEXT NOT NULL,
    published_by  TEXT,
    published_at  TEXT NOT NULL,
    PRIMARY KEY (lesson_id, version)
);
CREATE TABLE IF NOT EXISTS step_attempt (
    attempt_id      TEXT PRIMARY KEY,
    account_id      TEXT NOT NULL,
    lesson_id       TEXT NOT NULL,
    lesson_version  INTEGER NOT NULL,
    step_id         TEXT NOT NULL,
    round           INTEGER,
    review_item_id  TEXT,
    audio_key       TEXT,
    result_json     TEXT NOT NULL,
    passed          INTEGER NOT NULL,
    speaking_s      REAL NOT NULL DEFAULT 0,
    rules_version   TEXT NOT NULL,
    override_json   TEXT,
    overridden_by   TEXT,
    overridden_at   TEXT,
    created_at      TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_step_attempt_account ON step_attempt(account_id, lesson_id);
CREATE INDEX IF NOT EXISTS idx_step_attempt_lesson ON step_attempt(lesson_id, step_id);
CREATE TABLE IF NOT EXISTS review_item (
    item_id     TEXT PRIMARY KEY,
    account_id  TEXT NOT NULL,
    kind        TEXT NOT NULL,                    -- word | talk
    lesson_id   TEXT NOT NULL,
    step_id     TEXT NOT NULL,
    word        TEXT NOT NULL DEFAULT '',
    box         INTEGER NOT NULL DEFAULT 1,
    due_date    TEXT NOT NULL,
    done        INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL,
    UNIQUE (account_id, kind, lesson_id, step_id, word)
);
-- One-off upgrades already applied, e.g. the layout of the sample path.
CREATE TABLE IF NOT EXISTS lesson_meta (
    key    TEXT PRIMARY KEY,
    value  TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS lesson_media (
    media_key     TEXT PRIMARY KEY,
    kind          TEXT NOT NULL,                  -- audio | image
    content_type  TEXT NOT NULL,
    blob_key      TEXT NOT NULL,
    created_by    TEXT,
    created_at    TEXT NOT NULL
);
-- D032: achievements reached, kept even if the attempts behind them go.
CREATE TABLE IF NOT EXISTS achievement (
    account_id   TEXT NOT NULL,
    code         TEXT NOT NULL,
    unlocked_at  TEXT NOT NULL,
    seen_at      TEXT,                            -- NULL until the learner has seen it
    PRIMARY KEY (account_id, code)
);
"""

PATH_STATUSES = ("draft", "published", "archived")


class NotFound(LookupError):
    pass


class LessonRepository(SqlStore):
    def __init__(self, db_path: str | Path, seed: bool = True) -> None:
        self.db_path = str(db_path)
        with self._conn() as c:
            c.executescript(SCHEMA)
            add_columns(c, "lesson_unit", (("topic", "TEXT"),))  # a database from before D027
        if seed:
            self.seed_sample()

    # ------------------------------------------------------------ seeding

    def seed_sample(self) -> None:
        """Create the sample path, or bring one made by an older version up to date.

        The upgrade runs once (recorded in `lesson_meta`), so a teacher who later
        moves or renames sample content keeps their change. It adds what is
        missing, gives the sample units their title, topic and order, and puts
        each sample lesson in its unit; lesson drafts and attempts are untouched.
        """
        with self._conn() as c:
            exists = c.execute(
                "SELECT 1 FROM lesson_path WHERE path_id=?", (SAMPLE_PATH_ID,)
            ).fetchone()
            row = c.execute("SELECT value FROM lesson_meta WHERE key='sample_layout'").fetchone()
        if not exists:
            self.create_path(
                SAMPLE_PATH["title"],
                SAMPLE_PATH["description"],
                SAMPLE_PATH["band_from"],
                SAMPLE_PATH["band_to"],
                by="system",
                path_id=SAMPLE_PATH_ID,
                sample=True,
                status="published",
            )
            layout = 0
        else:
            # A sample path with no record is the first layout (D025: one unit per band).
            layout = int(row["value"]) if row else 1
        if layout >= SAMPLE_LAYOUT:
            return
        self._lay_out_sample(upgrade=bool(exists))
        with self._conn() as c:
            c.execute(
                "INSERT INTO lesson_meta(key, value) VALUES ('sample_layout', ?)"
                " ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (str(SAMPLE_LAYOUT),),
            )

    def _lay_out_sample(self, upgrade: bool) -> None:
        lessons = sample_lessons()
        if upgrade:
            self.update_path(
                SAMPLE_PATH_ID,
                title=SAMPLE_PATH["title"],
                description=SAMPLE_PATH["description"],
            )
        for position, unit in enumerate(SAMPLE_UNITS, 1):
            uid = unit["unit_id"]
            with self._conn() as c:
                known = c.execute("SELECT 1 FROM lesson_unit WHERE unit_id=?", (uid,)).fetchone()
            if known is None:
                self.add_unit(
                    SAMPLE_PATH_ID,
                    unit["title"],
                    unit["function"],
                    unit["band"],
                    None,
                    unit_id=uid,
                    topic=unit["topic"],
                )
            else:
                self.update_unit(
                    uid,
                    title=unit["title"],
                    function=unit["function"],
                    band=unit["band"],
                    topic=unit["topic"],
                )
            with self._conn() as c:
                c.execute("UPDATE lesson_unit SET position=? WHERE unit_id=?", (position, uid))
            for item in lessons[uid]:
                with self._conn() as c:
                    there = c.execute(
                        "SELECT 1 FROM lesson WHERE lesson_id=?", (item.lesson_id,)
                    ).fetchone()
                if there is None:
                    self.add_lesson(uid, item, by="system")
                    self.publish(item.lesson_id, by="system")
            with self._conn() as c:
                ids = [item.lesson_id for item in lessons[uid]]
                # Sample lessons first, in layout order; anything a teacher added
                # to this unit follows in its own order.
                others = [
                    r["lesson_id"]
                    for r in c.execute(
                        "SELECT lesson_id FROM lesson WHERE unit_id=? ORDER BY position",
                        (uid,),
                    )
                    if r["lesson_id"] not in ids
                ]
                for pos, lid in enumerate([*ids, *others], 1):
                    c.execute(
                        "UPDATE lesson SET unit_id=?, position=? WHERE lesson_id=?",
                        (uid, pos, lid),
                    )
        with self._conn() as c:
            sample_ids = [u["unit_id"] for u in SAMPLE_UNITS]
            rest = [
                r["unit_id"]
                for r in c.execute(
                    "SELECT unit_id FROM lesson_unit WHERE path_id=? ORDER BY position",
                    (SAMPLE_PATH_ID,),
                )
                if r["unit_id"] not in sample_ids
            ]
            for pos, uid in enumerate(rest, len(sample_ids) + 1):
                c.execute("UPDATE lesson_unit SET position=? WHERE unit_id=?", (pos, uid))

    # ------------------------------------------------------------ paths and units

    def create_path(
        self,
        title: str,
        description: str = "",
        band_from: Band | None = None,
        band_to: Band | None = None,
        by: str | None = None,
        path_id: str | None = None,
        sample: bool = False,
        status: str = "draft",
    ) -> str:
        pid = path_id or new_id("p")
        now = _now()
        with self._conn() as c:
            c.execute(
                "INSERT INTO lesson_path(path_id, title, description, band_from, band_to, status,"
                " sample, created_by, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (
                    pid,
                    title,
                    description,
                    band_from.value if band_from else None,
                    band_to.value if band_to else None,
                    status,
                    int(sample),
                    by,
                    now,
                    now,
                ),
            )
        return pid

    def update_path(self, path_id: str, **fields) -> None:
        allowed = {"title", "description", "band_from", "band_to", "status"}
        sets = {k: v for k, v in fields.items() if k in allowed and v is not None}
        if "status" in sets and sets["status"] not in PATH_STATUSES:
            raise ValueError("trạng thái lộ trình không hợp lệ")
        for key in ("band_from", "band_to"):
            if isinstance(sets.get(key), Band):
                sets[key] = sets[key].value
        if not sets:
            return
        sets["updated_at"] = _now()
        cols = ", ".join(f"{k}=?" for k in sets)
        with self._conn() as c:
            n = c.execute(
                f"UPDATE lesson_path SET {cols} WHERE path_id=?", (*sets.values(), path_id)
            ).rowcount
        if not n:
            raise NotFound(path_id)

    def paths(self, published_only: bool = False) -> list[dict]:
        sql = "SELECT * FROM lesson_path WHERE status != 'archived'"
        if published_only:
            sql = "SELECT * FROM lesson_path WHERE status = 'published'"
        with self._conn() as c:
            rows = c.execute(sql + " ORDER BY sample ASC, created_at ASC").fetchall()
        return [dict(r) for r in rows]

    def path(self, path_id: str) -> dict:
        with self._conn() as c:
            row = c.execute("SELECT * FROM lesson_path WHERE path_id=?", (path_id,)).fetchone()
        if row is None:
            raise NotFound(path_id)
        return dict(row)

    def add_unit(
        self,
        path_id: str,
        title: str,
        function: str = "",
        band: Band | None = None,
        criterion: Criterion | None = None,
        unit_id: str | None = None,
        topic: Topic | None = None,
    ) -> str:
        uid = unit_id or new_id("u")
        with self._conn() as c:
            if (
                c.execute("SELECT 1 FROM lesson_path WHERE path_id=?", (path_id,)).fetchone()
                is None
            ):
                raise NotFound(path_id)
            pos = c.execute(
                "SELECT COALESCE(MAX(position), 0) + 1 FROM lesson_unit WHERE path_id=?", (path_id,)
            ).fetchone()[0]
            c.execute(
                "INSERT INTO lesson_unit(unit_id, path_id, title, function, band, criterion,"
                " topic, position, created_at) VALUES (?,?,?,?,?,?,?,?,?)",
                (
                    uid,
                    path_id,
                    title,
                    function,
                    band.value if band else None,
                    criterion.value if criterion else None,
                    topic.value if topic else None,
                    pos,
                    _now(),
                ),
            )
        return uid

    def update_unit(self, unit_id: str, **fields) -> None:
        allowed = {"title", "function", "band", "criterion", "topic"}
        sets = {k: v for k, v in fields.items() if k in allowed}
        for key in ("band", "criterion", "topic"):
            if key in sets and hasattr(sets[key], "value"):
                sets[key] = sets[key].value
        if not sets:
            return
        cols = ", ".join(f"{k}=?" for k in sets)
        with self._conn() as c:
            n = c.execute(
                f"UPDATE lesson_unit SET {cols} WHERE unit_id=?", (*sets.values(), unit_id)
            ).rowcount
        if not n:
            raise NotFound(unit_id)

    def unit(self, unit_id: str) -> dict:
        with self._conn() as c:
            row = c.execute("SELECT * FROM lesson_unit WHERE unit_id=?", (unit_id,)).fetchone()
        if row is None:
            raise NotFound(unit_id)
        return dict(row)

    def delete_unit(self, unit_id: str) -> None:
        """Only an empty unit can go: lessons carry attempts that must stay readable."""
        with self._conn() as c:
            busy = c.execute(
                "SELECT 1 FROM lesson WHERE unit_id=? AND archived=0", (unit_id,)
            ).fetchone()
            if busy:
                raise ValueError("chặng còn bài học, chuyển hoặc lưu trữ các bài trước")
            c.execute("DELETE FROM lesson WHERE unit_id=?", (unit_id,))
            c.execute("DELETE FROM lesson_unit WHERE unit_id=?", (unit_id,))

    def move(self, table: str, key: str, direction: int) -> None:
        """Swap a unit or a lesson with its neighbour (direction -1 up, +1 down)."""
        if table not in ("lesson_unit", "lesson"):
            raise ValueError(table)
        id_col = "unit_id" if table == "lesson_unit" else "lesson_id"
        parent = "path_id" if table == "lesson_unit" else "unit_id"
        with self._conn() as c:
            row = c.execute(
                f"SELECT {parent} AS parent, position FROM {table} WHERE {id_col}=?", (key,)
            ).fetchone()
            if row is None:
                raise NotFound(key)
            cmp, order = ("<", "DESC") if direction < 0 else (">", "ASC")
            extra = " AND archived=0" if table == "lesson" else ""
            other = c.execute(
                f"SELECT {id_col} AS id, position FROM {table} WHERE {parent}=?"
                f" AND position {cmp} ?{extra} ORDER BY position {order} LIMIT 1",
                (row["parent"], row["position"]),
            ).fetchone()
            if other is None:
                return
            c.execute(f"UPDATE {table} SET position=? WHERE {id_col}=?", (other["position"], key))
            c.execute(
                f"UPDATE {table} SET position=? WHERE {id_col}=?", (row["position"], other["id"])
            )

    # ------------------------------------------------------------ lessons

    def add_lesson(self, unit_id: str, lesson: Lesson, by: str | None = None) -> str:
        with self._conn() as c:
            if (
                c.execute("SELECT 1 FROM lesson_unit WHERE unit_id=?", (unit_id,)).fetchone()
                is None
            ):
                raise NotFound(unit_id)
            pos = c.execute(
                "SELECT COALESCE(MAX(position), 0) + 1 FROM lesson WHERE unit_id=?", (unit_id,)
            ).fetchone()[0]
            c.execute(
                "INSERT INTO lesson(lesson_id, unit_id, position, draft_json, updated_by,"
                " updated_at) VALUES (?,?,?,?,?,?)",
                (lesson.lesson_id, unit_id, pos, lesson.model_dump_json(), by, _now()),
            )
        return lesson.lesson_id

    def draft(self, lesson_id: str) -> tuple[Lesson, dict]:
        """The working copy and its metadata (unit, published version, unpublished changes)."""
        with self._conn() as c:
            row = c.execute(
                "SELECT l.*, u.path_id FROM lesson l JOIN lesson_unit u ON u.unit_id = l.unit_id"
                " WHERE l.lesson_id=?",
                (lesson_id,),
            ).fetchone()
        if row is None:
            raise NotFound(lesson_id)
        meta = {
            "unit_id": row["unit_id"],
            "path_id": row["path_id"],
            "published_version": row["published_version"],
            "draft_changed": bool(row["draft_changed"]),
            "archived": bool(row["archived"]),
            "updated_by": row["updated_by"],
            "updated_at": row["updated_at"],
        }
        return Lesson.model_validate_json(row["draft_json"]), meta

    def save_draft(self, lesson_id: str, lesson: Lesson, by: str | None = None) -> None:
        if lesson.lesson_id != lesson_id:
            raise ValueError("mã bài học không khớp")
        with self._conn() as c:
            n = c.execute(
                "UPDATE lesson SET draft_json=?, draft_changed=1, updated_by=?, updated_at=?"
                " WHERE lesson_id=?",
                (lesson.model_dump_json(), by, _now(), lesson_id),
            ).rowcount
        if not n:
            raise NotFound(lesson_id)

    def publish(self, lesson_id: str, by: str | None = None) -> int:
        lesson, meta = self.draft(lesson_id)
        version = meta["published_version"] + 1
        with self._conn() as c:
            c.execute(
                "INSERT INTO lesson_version(lesson_id, version, lesson_json, published_by,"
                " published_at) VALUES (?,?,?,?,?)",
                (lesson_id, version, lesson.model_dump_json(), by, _now()),
            )
            c.execute(
                "UPDATE lesson SET published_version=?, draft_changed=0 WHERE lesson_id=?",
                (version, lesson_id),
            )
        return version

    def published(self, lesson_id: str, version: int | None = None) -> tuple[Lesson, int] | None:
        with self._conn() as c:
            if version is None:
                row = c.execute(
                    "SELECT v.lesson_json, v.version FROM lesson l JOIN lesson_version v"
                    " ON v.lesson_id = l.lesson_id AND v.version = l.published_version"
                    " WHERE l.lesson_id=? AND l.archived=0",
                    (lesson_id,),
                ).fetchone()
            else:
                row = c.execute(
                    "SELECT lesson_json, version FROM lesson_version"
                    " WHERE lesson_id=? AND version=?",
                    (lesson_id, version),
                ).fetchone()
        if row is None:
            return None
        return Lesson.model_validate_json(row["lesson_json"]), row["version"]

    def archive_lesson(self, lesson_id: str) -> None:
        """Hide a lesson from its path. Never-published drafts are deleted outright."""
        _, meta = self.draft(lesson_id)
        with self._conn() as c:
            if meta["published_version"] == 0:
                c.execute("DELETE FROM lesson WHERE lesson_id=?", (lesson_id,))
            else:
                c.execute("UPDATE lesson SET archived=1 WHERE lesson_id=?", (lesson_id,))

    def outline(self, path_id: str, published_only: bool = True) -> list[dict]:
        """Units of a path in order, each with its lessons in order.

        For learners (`published_only`) a lesson appears only once published, and
        its content is the published version; for teachers it is the draft.
        """
        with self._conn() as c:
            units = c.execute(
                "SELECT * FROM lesson_unit WHERE path_id=? ORDER BY position", (path_id,)
            ).fetchall()
            lessons = c.execute(
                "SELECT l.*, v.lesson_json AS published_json FROM lesson l"
                " JOIN lesson_unit u ON u.unit_id = l.unit_id"
                " LEFT JOIN lesson_version v ON v.lesson_id = l.lesson_id"
                " AND v.version = l.published_version"
                " WHERE u.path_id=? AND l.archived=0 ORDER BY l.position",
                (path_id,),
            ).fetchall()
        out = []
        for u in units:
            items = []
            for row in lessons:
                if row["unit_id"] != u["unit_id"]:
                    continue
                if published_only and not row["published_json"]:
                    continue
                source = row["published_json"] if published_only else row["draft_json"]
                items.append(
                    {
                        "lesson": Lesson.model_validate_json(source),
                        "published_version": row["published_version"],
                        "draft_changed": bool(row["draft_changed"]),
                    }
                )
            out.append({**dict(u), "lessons": items})
        return out

    # ------------------------------------------------------------ attempts

    def add_attempt(
        self,
        account_id: str,
        lesson_id: str,
        lesson_version: int,
        result: StepResult,
        audio_key: str | None = None,
        review_item_id: str | None = None,
        attempt_id: str | None = None,
        created_at: str | None = None,
    ) -> str:
        aid = attempt_id or new_id("a")
        with self._conn() as c:
            c.execute(
                "INSERT INTO step_attempt(attempt_id, account_id, lesson_id, lesson_version,"
                " step_id, round, review_item_id, audio_key, result_json, passed, speaking_s,"
                " rules_version, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    aid,
                    account_id,
                    lesson_id,
                    lesson_version,
                    result.step_id,
                    result.round,
                    review_item_id,
                    audio_key,
                    result.model_dump_json(),
                    int(result.passed),
                    result.speaking_s if result.measured else 0.0,
                    result.rules_version,
                    created_at or _now(),
                ),
            )
        return aid

    @staticmethod
    def _attempt(row: DbRow) -> dict:
        d = dict(row)
        machine = StepResult.model_validate_json(d.pop("result_json"))
        override = json.loads(d.pop("override_json") or "null")
        d["result"] = apply_override(machine, override) if override else machine
        d["passed"] = d["result"].passed
        # Kept beside the corrected result, so a teacher editing a correction
        # starts from what the machine said and what was changed.
        d["machine_passed"] = machine.passed
        d["override"] = override
        return d

    def attempt(self, attempt_id: str) -> dict:
        with self._conn() as c:
            row = c.execute(
                "SELECT * FROM step_attempt WHERE attempt_id=?", (attempt_id,)
            ).fetchone()
        if row is None:
            raise NotFound(attempt_id)
        return self._attempt(row)

    def attempts(
        self,
        account_id: str | None = None,
        lesson_id: str | None = None,
        lesson_ids: list[str] | None = None,
        limit: int | None = None,
    ) -> list[dict]:
        where, args = [], []
        if account_id is not None:
            where.append("account_id=?")
            args.append(account_id)
        if lesson_id is not None:
            where.append("lesson_id=?")
            args.append(lesson_id)
        if lesson_ids is not None:
            if not lesson_ids:
                return []
            where.append(f"lesson_id IN ({','.join('?' * len(lesson_ids))})")
            args += lesson_ids
        sql = "SELECT * FROM step_attempt"
        if where:
            sql += " WHERE " + " AND ".join(where)
        # Oldest first, ties broken by insertion order; with a limit, the newest.
        if limit:
            sql += " ORDER BY created_at DESC, rowid DESC LIMIT ?"
            args.append(limit)
        else:
            sql += " ORDER BY created_at, rowid"
        with self._conn() as c:
            rows = c.execute(sql, args).fetchall()
        return [self._attempt(r) for r in rows]

    def set_override(self, attempt_id: str, override: dict, by: str) -> None:
        with self._conn() as c:
            n = c.execute(
                "UPDATE step_attempt SET override_json=?, overridden_by=?, overridden_at=?,"
                " passed=? WHERE attempt_id=?",
                (
                    json.dumps(override, ensure_ascii=False),
                    by,
                    _now(),
                    int(bool(override.get("passed")))
                    if "passed" in override
                    else self._stored_passed(c, attempt_id),
                    attempt_id,
                ),
            ).rowcount
        if not n:
            raise NotFound(attempt_id)

    @staticmethod
    def _stored_passed(c: Connection, attempt_id: str) -> int:
        row = c.execute(
            "SELECT result_json FROM step_attempt WHERE attempt_id=?", (attempt_id,)
        ).fetchone()
        if row is None:
            return 0
        return int(StepResult.model_validate_json(row["result_json"]).passed)

    def delete_attempt(self, attempt_id: str) -> str | None:
        """Remove one attempt; returns its audio key so the caller deletes the file."""
        with self._conn() as c:
            row = c.execute(
                "SELECT audio_key FROM step_attempt WHERE attempt_id=?", (attempt_id,)
            ).fetchone()
            if row is None:
                raise NotFound(attempt_id)
            c.execute("DELETE FROM step_attempt WHERE attempt_id=?", (attempt_id,))
        return row["audio_key"]

    def erase_account(self, account_id: str) -> list[str]:
        """Erasure (FR-34/35): every attempt, review and achievement of one account.

        Returns the audio keys, so the caller deletes the recordings.
        """
        with self._conn() as c:
            keys = [
                r["audio_key"]
                for r in c.execute(
                    "SELECT audio_key FROM step_attempt"
                    " WHERE account_id=? AND audio_key IS NOT NULL",
                    (account_id,),
                ).fetchall()
            ]
            c.execute("DELETE FROM step_attempt WHERE account_id=?", (account_id,))
            c.execute("DELETE FROM review_item WHERE account_id=?", (account_id,))
            c.execute("DELETE FROM achievement WHERE account_id=?", (account_id,))
        return keys

    def count_attempts(self, account_id: str) -> int:
        with self._conn() as c:
            return c.execute(
                "SELECT COUNT(*) FROM step_attempt WHERE account_id=?", (account_id,)
            ).fetchone()[0]

    # ------------------------------------------------------------ retention

    def blob_keys(self) -> set[str]:
        """Upload-folder files this store points at: recordings and teacher media."""
        with self._conn() as c:
            keys = {r[0] for r in c.execute(
                "SELECT audio_key FROM step_attempt WHERE audio_key IS NOT NULL"
            )}  # fmt: skip
            keys |= {r[0] for r in c.execute("SELECT blob_key FROM lesson_media")}
        return keys

    def forget_older_than(
        self, cutoff: str, upload_dir: Path, dry_run: bool
    ) -> tuple[int, int, int, int]:
        """Storage limitation for attempts older than `cutoff` (see `aicefr.retention`).

        Same split as for responses: the recording and what was heard go, the
        result stays. What the learner said lives in `transcript` and in the
        `said` of each word and gap; the words of the text itself are the
        teacher's, and the statuses are the record of the practice, so both are
        kept. Returns (attempts considered, recordings, transcripts, bytes).
        """
        with self._conn() as c:
            rows = c.execute(
                "SELECT attempt_id, audio_key, result_json FROM step_attempt WHERE created_at < ?",
                (cutoff,),
            ).fetchall()
        audio = cleared = freed = 0
        for row in rows:
            path = upload_dir / row["audio_key"] if row["audio_key"] else None
            if path and path.is_file():
                freed += path.stat().st_size
                audio += 1
                if not dry_run:
                    path.unlink(missing_ok=True)
            result = json.loads(row["result_json"])
            changed = bool(result.get("transcript"))
            result["transcript"] = ""
            for mark in [*result.get("words", []), *result.get("gaps", [])]:
                if mark.get("said"):
                    mark["said"] = None
                    changed = True
            cleared += int(changed)
            if not dry_run and (changed or row["audio_key"]):
                with self._conn() as c:
                    c.execute(
                        "UPDATE step_attempt SET result_json=?, audio_key=NULL WHERE attempt_id=?",
                        (json.dumps(result, ensure_ascii=False), row["attempt_id"]),
                    )
        return len(rows), audio, cleared, freed

    # ------------------------------------------------------------ achievements

    def achievements(self, account_id: str) -> dict[str, dict]:
        """What one account has reached (D032): code -> unlocked_at, seen_at."""
        with self._conn() as c:
            rows = c.execute(
                "SELECT code, unlocked_at, seen_at FROM achievement WHERE account_id=?"
                " ORDER BY unlocked_at, rowid",
                (account_id,),
            ).fetchall()
        return {r["code"]: {"unlocked_at": r["unlocked_at"], "seen_at": r["seen_at"]} for r in rows}

    def unlock(self, account_id: str, codes: list[str], at: str | None = None) -> list[str]:
        """Store achievements just reached; returns those this call stored.

        Two requests reaching the same achievement at once store it once, and
        only one of them reports it, so the learner is congratulated once.
        """
        when = at or _now()
        stored = []
        with self._conn() as c:
            for code in codes:
                n = c.execute(
                    "INSERT OR IGNORE INTO achievement(account_id, code, unlocked_at)"
                    " VALUES (?,?,?)",
                    (account_id, code, when),
                ).rowcount
                if n:
                    stored.append(code)
        return stored

    def mark_seen(self, account_id: str, codes: list[str] | None = None) -> int:
        """Mark achievements as seen: those named, or every one not seen yet."""
        sql = "UPDATE achievement SET seen_at=? WHERE account_id=? AND seen_at IS NULL"
        args: list = [_now(), account_id]
        if codes is not None:
            if not codes:
                return 0
            sql += f" AND code IN ({','.join('?' * len(codes))})"
            args += codes
        with self._conn() as c:
            return c.execute(sql, args).rowcount

    # ------------------------------------------------------------ reviews

    def schedule(
        self, account_id: str, kind: str, lesson_id: str, step_id: str, word: str, due: date
    ) -> None:
        """Add a review item, or bring a finished one back to box 1. An open item is left alone."""
        now = _now()
        with self._conn() as c:
            row = c.execute(
                "SELECT item_id, done FROM review_item WHERE account_id=? AND kind=? AND"
                " lesson_id=? AND step_id=? AND word=?",
                (account_id, kind, lesson_id, step_id, word),
            ).fetchone()
            if row is None:
                c.execute(
                    "INSERT INTO review_item(item_id, account_id, kind, lesson_id, step_id, word,"
                    " box, due_date, created_at, updated_at) VALUES (?,?,?,?,?,?,1,?,?,?)",
                    (
                        new_id("r"),
                        account_id,
                        kind,
                        lesson_id,
                        step_id,
                        word,
                        due.isoformat(),
                        now,
                        now,
                    ),
                )
            elif row["done"]:
                c.execute(
                    "UPDATE review_item SET box=1, done=0, due_date=?, updated_at=?"
                    " WHERE item_id=?",
                    (due.isoformat(), now, row["item_id"]),
                )

    def due_reviews(self, account_id: str, today: date) -> list[dict]:
        with self._conn() as c:
            rows = c.execute(
                "SELECT * FROM review_item WHERE account_id=? AND done=0 AND due_date<=?"
                " ORDER BY due_date, created_at",
                (account_id, today.isoformat()),
            ).fetchall()
        return [dict(r) for r in rows]

    def open_reviews(self, account_id: str) -> list[dict]:
        with self._conn() as c:
            rows = c.execute(
                "SELECT * FROM review_item WHERE account_id=? AND done=0 ORDER BY due_date",
                (account_id,),
            ).fetchall()
        return [dict(r) for r in rows]

    def review(self, item_id: str) -> dict:
        with self._conn() as c:
            row = c.execute("SELECT * FROM review_item WHERE item_id=?", (item_id,)).fetchone()
        if row is None:
            raise NotFound(item_id)
        return dict(row)

    def reschedule(self, item_id: str, box: int, due: date | None) -> None:
        with self._conn() as c:
            c.execute(
                "UPDATE review_item SET box=?, due_date=COALESCE(?, due_date), done=?,"
                " updated_at=? WHERE item_id=?",
                (box, due.isoformat() if due else None, int(due is None), _now(), item_id),
            )

    # ------------------------------------------------------------ media

    def add_media(self, kind: str, content_type: str, blob_key: str, by: str | None) -> str:
        key = new_id("m")
        with self._conn() as c:
            c.execute(
                "INSERT INTO lesson_media(media_key, kind, content_type, blob_key, created_by,"
                " created_at) VALUES (?,?,?,?,?,?)",
                (key, kind, content_type, blob_key, by, _now()),
            )
        return key

    def media(self, key: str) -> dict:
        with self._conn() as c:
            row = c.execute("SELECT * FROM lesson_media WHERE media_key=?", (key,)).fetchone()
        if row is None:
            raise NotFound(key)
        return dict(row)

    # ------------------------------------------------------------ export and import

    def export_path(self, path_id: str) -> dict:
        """A path as JSON a teacher can share: structure and lesson drafts, no media."""
        p = self.path(path_id)
        units = []
        for u in self.outline(path_id, published_only=False):
            units.append(
                {
                    "title": u["title"],
                    "function": u["function"],
                    "band": u["band"],
                    "criterion": u["criterion"],
                    "topic": u["topic"],
                    "lessons": [
                        item["lesson"].model_dump(mode="json", exclude={"lesson_id"})
                        for item in u["lessons"]
                    ],
                }
            )
        for unit in units:
            for lesson in unit["lessons"]:
                for step in lesson["steps"]:
                    step.pop("step_id", None)
                    step["model_audio"] = None
                    step["image"] = None
        return {
            "format": "aicefr-lesson-path",
            "version": 1,
            "title": p["title"],
            "description": p["description"],
            "band_from": p["band_from"],
            "band_to": p["band_to"],
            "units": units,
        }

    def import_path(self, data: dict, by: str | None = None) -> str:
        """Create a draft path from an exported file.

        The whole file is checked before anything is written, so a file with one
        bad unit creates nothing rather than half a path. Lessons get new ids,
        and media keys are dropped: media only ever come from an upload on this
        installation.
        """
        if not isinstance(data, dict) or data.get("format") != "aicefr-lesson-path":
            raise ValueError("không phải tệp lộ trình của hệ thống")
        units = data.get("units", [])
        if not isinstance(units, list):
            raise ValueError("danh sách chặng không hợp lệ")
        band_from = Band(data["band_from"]) if data.get("band_from") else None
        band_to = Band(data["band_to"]) if data.get("band_to") else None
        planned = []
        for unit in units:
            if not isinstance(unit, dict) or not isinstance(unit.get("lessons", []), list):
                raise ValueError("mỗi chặng phải có tên và danh sách bài học")
            lessons = []
            for item in unit.get("lessons", []):
                lesson = Lesson.model_validate(item)
                lesson.lesson_id = new_id("l")
                for step in lesson.steps:
                    step.model_audio = None
                    step.image = None
                lessons.append(lesson)
            planned.append(
                (
                    str(unit.get("title") or "Chặng")[:160],
                    str(unit.get("function") or "")[:300],
                    Band(unit["band"]) if unit.get("band") else None,
                    Criterion(unit["criterion"]) if unit.get("criterion") else None,
                    Topic(unit["topic"]) if unit.get("topic") else None,
                    lessons,
                )
            )
        pid = self.create_path(
            str(data.get("title") or "Lộ trình nhập")[:160],
            str(data.get("description") or "")[:1000],
            band_from,
            band_to,
            by=by,
        )
        for title, function, band, criterion, topic, lessons in planned:
            uid = self.add_unit(pid, title, function, band, criterion, topic=topic)
            for lesson in lessons:
                self.add_lesson(uid, lesson, by=by)
        return pid


def apply_override(result: StepResult, override: dict) -> StepResult:
    """A teacher's corrections on top of the machine's result."""
    # Stored as JSON, so the statuses come back as plain strings; model_copy does
    # not validate, so they are turned back into WordStatus here.
    words = {int(k): WordStatus(v) for k, v in (override.get("words") or {}).items()}
    marks = []
    for m in result.words:
        if m.index in words:
            m = m.model_copy(update={"teacher": words[m.index]})
        marks.append(m)
    update = {
        "words": marks,
        "teacher_reviewed": True,
        "teacher_note": str(override.get("note") or ""),
    }
    if "passed" in override:
        update["passed"] = bool(override["passed"])
    return result.model_copy(update=update)
