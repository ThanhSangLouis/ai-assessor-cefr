"""Storage of lesson paths, published versions, step attempts and reviews (D025).

Lessons are edited as a DRAFT; publishing copies the draft into an immutable
`lesson_version` document. Learners read only published versions, and every attempt
records the version it was made against, so a result can always be read
against the exact text the learner saw.

Step attempts live in their own collection, not in `response`. That keeps them out
of the review queue, the scoring statistics and the research export by
construction rather than by a filter someone could forget.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from pymongo import ASCENDING, DESCENDING

from aicefr.contracts import Band, Criterion
from aicefr.lessons.model import Lesson, StepResult, Topic, WordStatus, new_id
from aicefr.lessons.seed import (
    SAMPLE_LAYOUT,
    SAMPLE_PATH,
    SAMPLE_PATH_ID,
    SAMPLE_UNITS,
    sample_lessons,
)
from aicefr.storage.db import IntegrityError, MongoStore, ensure_indexes, fields
from aicefr.storage.db import now_iso as _now

# lesson_path.status: draft | published | archived. lesson_unit.topic (D027):
# what the unit talks about. review_item.kind: word | talk. lesson_meta: one-off
# upgrades already applied, e.g. the layout of the sample path. lesson_media.kind:
# audio | image. achievement (D032): achievements reached, kept even if the
# attempts behind them go; seen_at None until the learner has seen it.
INDEXES = {
    "lesson_path": [(("path_id",), True)],
    "lesson_unit": [(("unit_id",), True), (("path_id", "position"), False)],
    "lesson": [(("lesson_id",), True), (("unit_id", "position"), False)],
    "lesson_version": [(("lesson_id", "version"), True)],
    "step_attempt": [
        (("attempt_id",), True),
        (("account_id", "lesson_id"), False),
        (("lesson_id", "step_id"), False),
        (("created_at",), False),
    ],
    "review_item": [
        (("item_id",), True),
        (("account_id", "kind", "lesson_id", "step_id", "word"), True),
        (("account_id", "done", "due_date"), False),
    ],
    "lesson_meta": [(("key",), True)],
    "lesson_media": [(("media_key",), True)],
    "achievement": [(("account_id", "code"), True)],
}

PATH_FIELDS = (
    "path_id",
    "title",
    "description",
    "band_from",
    "band_to",
    "status",
    "sample",
    "created_by",
    "created_at",
    "updated_at",
)
UNIT_FIELDS = (
    "unit_id",
    "path_id",
    "title",
    "function",
    "band",
    "criterion",
    "topic",
    "position",
    "created_at",
)
ATTEMPT_FIELDS = (
    "attempt_id",
    "account_id",
    "lesson_id",
    "lesson_version",
    "step_id",
    "round",
    "review_item_id",
    "audio_key",
    "result_json",
    "passed",
    "speaking_s",
    "rules_version",
    "override_json",
    "overridden_by",
    "overridden_at",
    "created_at",
)
REVIEW_FIELDS = (
    "item_id",
    "account_id",
    "kind",
    "lesson_id",
    "step_id",
    "word",
    "box",
    "due_date",
    "done",
    "created_at",
    "updated_at",
)
_BY_POSITION = [("position", ASCENDING), ("_id", ASCENDING)]

PATH_STATUSES = ("draft", "published", "archived")


class NotFound(LookupError):
    pass


class LessonRepository(MongoStore):
    def __init__(self, db_path: str | Path, seed: bool = True) -> None:
        self.db_path = str(db_path)
        ensure_indexes(self.db, INDEXES, "lesson")
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
        exists = self.col("lesson_path").find_one({"path_id": SAMPLE_PATH_ID}) is not None
        row = self.col("lesson_meta").find_one({"key": "sample_layout"})
        if not exists:
            try:
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
            except IntegrityError:
                return  # another process is laying it out
            layout = 0
        else:
            # A sample path with no record is the first layout (D025: one unit per band).
            layout = int(row["value"]) if row else 1
        if layout >= SAMPLE_LAYOUT:
            return
        self._lay_out_sample(upgrade=exists)
        self.col("lesson_meta").update_one(
            {"key": "sample_layout"}, {"$set": {"value": str(SAMPLE_LAYOUT)}}, upsert=True
        )

    def _lay_out_sample(self, upgrade: bool) -> None:
        lessons = sample_lessons()
        units, lesson_docs = self.col("lesson_unit"), self.col("lesson")
        if upgrade:
            self.update_path(
                SAMPLE_PATH_ID,
                title=SAMPLE_PATH["title"],
                description=SAMPLE_PATH["description"],
                band_from=SAMPLE_PATH["band_from"],
                band_to=SAMPLE_PATH["band_to"],
            )
        for position, unit in enumerate(SAMPLE_UNITS, 1):
            uid = unit["unit_id"]
            if units.find_one({"unit_id": uid}) is None:
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
            units.update_one({"unit_id": uid}, {"$set": {"position": position}})
            for item in lessons[uid]:
                if lesson_docs.find_one({"lesson_id": item.lesson_id}) is None:
                    self.add_lesson(uid, item, by="system")
                    self.publish(item.lesson_id, by="system")
            ids = [item.lesson_id for item in lessons[uid]]
            # Sample lessons first, in layout order; anything a teacher added
            # to this unit follows in its own order.
            others = [
                r["lesson_id"]
                for r in lesson_docs.find({"unit_id": uid}).sort(_BY_POSITION)
                if r["lesson_id"] not in ids
            ]
            for pos, lid in enumerate([*ids, *others], 1):
                lesson_docs.update_one(
                    {"lesson_id": lid}, {"$set": {"unit_id": uid, "position": pos}}
                )
        sample_ids = [u["unit_id"] for u in SAMPLE_UNITS]
        rest = [
            r["unit_id"]
            for r in units.find({"path_id": SAMPLE_PATH_ID}).sort(_BY_POSITION)
            if r["unit_id"] not in sample_ids
        ]
        for pos, uid in enumerate(rest, len(sample_ids) + 1):
            units.update_one({"unit_id": uid}, {"$set": {"position": pos}})

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
        self.col("lesson_path").insert_one(
            {
                "path_id": pid,
                "title": title,
                "description": description,
                "band_from": band_from.value if band_from else None,
                "band_to": band_to.value if band_to else None,
                "status": status,
                "sample": int(sample),
                "created_by": by,
                "created_at": now,
                "updated_at": now,
            }
        )
        return pid

    def update_path(self, path_id: str, **changes) -> None:
        allowed = {"title", "description", "band_from", "band_to", "status"}
        sets = {k: v for k, v in changes.items() if k in allowed and v is not None}
        if "status" in sets and sets["status"] not in PATH_STATUSES:
            raise ValueError("trạng thái lộ trình không hợp lệ")
        for key in ("band_from", "band_to"):
            if isinstance(sets.get(key), Band):
                sets[key] = sets[key].value
        if not sets:
            return
        sets["updated_at"] = _now()
        done = self.col("lesson_path").update_one({"path_id": path_id}, {"$set": sets})
        if not done.matched_count:
            raise NotFound(path_id)

    def paths(self, published_only: bool = False) -> list[dict]:
        query = {"status": "published"} if published_only else {"status": {"$ne": "archived"}}
        rows = (
            self.col("lesson_path")
            .find(query)
            .sort([("sample", ASCENDING), ("created_at", ASCENDING), ("_id", ASCENDING)])
        )
        return [fields(r, PATH_FIELDS) for r in rows]  # type: ignore[misc]

    def path(self, path_id: str) -> dict:
        row = self.col("lesson_path").find_one({"path_id": path_id})
        if row is None:
            raise NotFound(path_id)
        return fields(row, PATH_FIELDS)  # type: ignore[return-value]

    def _next_position(self, collection: str, parent: str, parent_id: str) -> int:
        last = self.col(collection).find_one({parent: parent_id}, sort=[("position", DESCENDING)])
        return (int(last["position"]) if last else 0) + 1

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
        if self.col("lesson_path").find_one({"path_id": path_id}) is None:
            raise NotFound(path_id)
        self.col("lesson_unit").insert_one(
            {
                "unit_id": uid,
                "path_id": path_id,
                "title": title,
                "function": function,
                "band": band.value if band else None,
                "criterion": criterion.value if criterion else None,
                "topic": topic.value if topic else None,
                "position": self._next_position("lesson_unit", "path_id", path_id),
                "created_at": _now(),
            }
        )
        return uid

    def update_unit(self, unit_id: str, **changes) -> None:
        allowed = {"title", "function", "band", "criterion", "topic"}
        sets = {k: v for k, v in changes.items() if k in allowed}
        for key in ("band", "criterion", "topic"):
            if key in sets and hasattr(sets[key], "value"):
                sets[key] = sets[key].value
        if not sets:
            return
        done = self.col("lesson_unit").update_one({"unit_id": unit_id}, {"$set": sets})
        if not done.matched_count:
            raise NotFound(unit_id)

    def unit(self, unit_id: str) -> dict:
        row = self.col("lesson_unit").find_one({"unit_id": unit_id})
        if row is None:
            raise NotFound(unit_id)
        return fields(row, UNIT_FIELDS)  # type: ignore[return-value]

    def delete_unit(self, unit_id: str) -> None:
        """Only an empty unit can go: lessons carry attempts that must stay readable."""
        if self.col("lesson").find_one({"unit_id": unit_id, "archived": 0}):
            raise ValueError("chặng còn bài học, chuyển hoặc lưu trữ các bài trước")
        self.col("lesson").delete_many({"unit_id": unit_id})
        self.col("lesson_unit").delete_one({"unit_id": unit_id})

    def move(self, table: str, key: str, direction: int) -> None:
        """Swap a unit or a lesson with its neighbour (direction -1 up, +1 down)."""
        if table not in ("lesson_unit", "lesson"):
            raise ValueError(table)
        id_field = "unit_id" if table == "lesson_unit" else "lesson_id"
        parent = "path_id" if table == "lesson_unit" else "unit_id"
        items = self.col(table)
        row = items.find_one({id_field: key})
        if row is None:
            raise NotFound(key)
        query: dict = {
            parent: row[parent],
            "position": {"$lt" if direction < 0 else "$gt": row["position"]},
        }
        if table == "lesson":
            query["archived"] = 0
        other = items.find_one(
            query, sort=[("position", DESCENDING if direction < 0 else ASCENDING)]
        )
        if other is None:
            return
        items.update_one({id_field: key}, {"$set": {"position": other["position"]}})
        items.update_one({id_field: other[id_field]}, {"$set": {"position": row["position"]}})

    # ------------------------------------------------------------ lessons

    def add_lesson(self, unit_id: str, lesson: Lesson, by: str | None = None) -> str:
        if self.col("lesson_unit").find_one({"unit_id": unit_id}) is None:
            raise NotFound(unit_id)
        self.col("lesson").insert_one(
            {
                "lesson_id": lesson.lesson_id,
                "unit_id": unit_id,
                "position": self._next_position("lesson", "unit_id", unit_id),
                "draft_json": lesson.model_dump_json(),
                "published_version": 0,
                "draft_changed": 1,
                "archived": 0,
                "updated_by": by,
                "updated_at": _now(),
            }
        )
        return lesson.lesson_id

    def draft(self, lesson_id: str) -> tuple[Lesson, dict]:
        """The working copy and its metadata (unit, published version, unpublished changes)."""
        row = self.col("lesson").find_one({"lesson_id": lesson_id})
        unit = self.col("lesson_unit").find_one({"unit_id": row["unit_id"]}) if row else None
        if row is None or unit is None:
            raise NotFound(lesson_id)
        meta = {
            "unit_id": row["unit_id"],
            "path_id": unit["path_id"],
            "published_version": row["published_version"],
            "draft_changed": bool(row["draft_changed"]),
            "archived": bool(row["archived"]),
            "updated_by": row.get("updated_by"),
            "updated_at": row["updated_at"],
        }
        return Lesson.model_validate_json(row["draft_json"]), meta

    def save_draft(self, lesson_id: str, lesson: Lesson, by: str | None = None) -> None:
        if lesson.lesson_id != lesson_id:
            raise ValueError("mã bài học không khớp")
        done = self.col("lesson").update_one(
            {"lesson_id": lesson_id},
            {"$set": {"draft_json": lesson.model_dump_json(), "draft_changed": 1,
                      "updated_by": by, "updated_at": _now()}},
        )  # fmt: skip
        if not done.matched_count:
            raise NotFound(lesson_id)

    def publish(self, lesson_id: str, by: str | None = None) -> int:
        lesson, meta = self.draft(lesson_id)
        version = meta["published_version"] + 1
        # The version first: a unique index refuses a second publish of the
        # same number, so two teachers publishing at once cannot both win.
        self.col("lesson_version").insert_one(
            {
                "lesson_id": lesson_id,
                "version": version,
                "lesson_json": lesson.model_dump_json(),
                "published_by": by,
                "published_at": _now(),
            }
        )
        self.col("lesson").update_one(
            {"lesson_id": lesson_id}, {"$set": {"published_version": version, "draft_changed": 0}}
        )
        return version

    def published(self, lesson_id: str, version: int | None = None) -> tuple[Lesson, int] | None:
        if version is None:
            row = self.col("lesson").find_one({"lesson_id": lesson_id, "archived": 0})
            if row is None:
                return None
            version = row["published_version"]
        found = self.col("lesson_version").find_one({"lesson_id": lesson_id, "version": version})
        if found is None:
            return None
        return Lesson.model_validate_json(found["lesson_json"]), found["version"]

    def archive_lesson(self, lesson_id: str) -> None:
        """Hide a lesson from its path. Never-published drafts are deleted outright."""
        _, meta = self.draft(lesson_id)
        if meta["published_version"] == 0:
            self.col("lesson").delete_one({"lesson_id": lesson_id})
        else:
            self.col("lesson").update_one({"lesson_id": lesson_id}, {"$set": {"archived": 1}})

    def outline(self, path_id: str, published_only: bool = True) -> list[dict]:
        """Units of a path in order, each with its lessons in order.

        For learners (`published_only`) a lesson appears only once published, and
        its content is the published version; for teachers it is the draft.
        """
        units = list(self.col("lesson_unit").find({"path_id": path_id}).sort(_BY_POSITION))
        lessons = list(
            self.col("lesson")
            .find({"unit_id": {"$in": [u["unit_id"] for u in units]}, "archived": 0})
            .sort(_BY_POSITION)
        )
        published = {
            (v["lesson_id"], v["version"]): v["lesson_json"]
            for v in self.col("lesson_version").find(
                {"lesson_id": {"$in": [row["lesson_id"] for row in lessons]}}
            )
        }
        out = []
        for u in units:
            items = []
            for row in lessons:
                if row["unit_id"] != u["unit_id"]:
                    continue
                published_json = published.get((row["lesson_id"], row["published_version"]))
                if published_only and not published_json:
                    continue
                source = published_json if published_only else row["draft_json"]
                items.append(
                    {
                        "lesson": Lesson.model_validate_json(source),
                        "published_version": row["published_version"],
                        "draft_changed": bool(row["draft_changed"]),
                    }
                )
            out.append({**fields(u, UNIT_FIELDS), "lessons": items})  # type: ignore[dict-item]
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
        self.col("step_attempt").insert_one(
            {
                "attempt_id": aid,
                "account_id": account_id,
                "lesson_id": lesson_id,
                "lesson_version": lesson_version,
                "step_id": result.step_id,
                "round": result.round,
                "review_item_id": review_item_id,
                "audio_key": audio_key,
                "result_json": result.model_dump_json(),
                "passed": int(result.passed),
                "speaking_s": result.speaking_s if result.measured else 0.0,
                "rules_version": result.rules_version,
                "override_json": None,
                "overridden_by": None,
                "overridden_at": None,
                "created_at": created_at or _now(),
            }
        )
        return aid

    @staticmethod
    def _attempt(row) -> dict:
        d = fields(row, ATTEMPT_FIELDS)
        machine = StepResult.model_validate_json(d.pop("result_json"))  # type: ignore[union-attr]
        override = json.loads(d.pop("override_json") or "null")  # type: ignore[union-attr]
        d["result"] = apply_override(machine, override) if override else machine  # type: ignore[index]
        d["passed"] = d["result"].passed  # type: ignore[index]
        # Kept beside the corrected result, so a teacher editing a correction
        # starts from what the machine said and what was changed.
        d["machine_passed"] = machine.passed  # type: ignore[index]
        d["override"] = override  # type: ignore[index]
        return d  # type: ignore[return-value]

    def attempt(self, attempt_id: str) -> dict:
        row = self.col("step_attempt").find_one({"attempt_id": attempt_id})
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
        query: dict = {}
        if account_id is not None:
            query["account_id"] = account_id
        if lesson_id is not None:
            query["lesson_id"] = lesson_id
        if lesson_ids is not None:
            if not lesson_ids:
                return []
            query.setdefault("$and", []).append({"lesson_id": {"$in": list(lesson_ids)}})
        # Oldest first, ties broken by insertion order; with a limit, the newest.
        found = self.col("step_attempt").find(query)
        if limit:
            rows = list(found.sort([("created_at", DESCENDING), ("_id", DESCENDING)]).limit(limit))
        else:
            rows = list(found.sort([("created_at", ASCENDING), ("_id", ASCENDING)]))
        return [self._attempt(r) for r in rows]

    def set_override(self, attempt_id: str, override: dict, by: str) -> None:
        attempts = self.col("step_attempt")
        row = attempts.find_one({"attempt_id": attempt_id}, {"result_json": 1})
        if row is None:
            raise NotFound(attempt_id)
        passed = (
            int(bool(override.get("passed")))
            if "passed" in override
            else int(StepResult.model_validate_json(row["result_json"]).passed)
        )
        attempts.update_one(
            {"attempt_id": attempt_id},
            {"$set": {"override_json": json.dumps(override, ensure_ascii=False),
                      "overridden_by": by, "overridden_at": _now(), "passed": passed}},
        )  # fmt: skip

    def delete_attempt(self, attempt_id: str) -> str | None:
        """Remove one attempt; returns its audio key so the caller deletes the file."""
        row = self.col("step_attempt").find_one_and_delete({"attempt_id": attempt_id})
        if row is None:
            raise NotFound(attempt_id)
        return row.get("audio_key")

    def erase_account(self, account_id: str) -> list[str]:
        """Erasure (FR-34/35): every attempt, review and achievement of one account.

        Returns the audio keys, so the caller deletes the recordings.
        """
        keys = [
            r["audio_key"]
            for r in self.col("step_attempt").find(
                {"account_id": account_id, "audio_key": {"$ne": None}}, {"audio_key": 1}
            )
        ]
        self.col("step_attempt").delete_many({"account_id": account_id})
        self.col("review_item").delete_many({"account_id": account_id})
        self.col("achievement").delete_many({"account_id": account_id})
        return keys

    def lesson_stats(self) -> dict[str, dict]:
        """Per lesson: step attempts, how many passed, how many learners (D046).

        Measured attempts only (`speaking_s > 0`): a silent or rejected clip
        says nothing about how hard the lesson is.
        """
        stats: dict[str, dict] = {}
        learners: dict[str, set] = {}
        for r in self.col("step_attempt").find(
            {"speaking_s": {"$gt": 0}}, {"lesson_id": 1, "passed": 1, "account_id": 1}
        ):
            cell = stats.setdefault(r["lesson_id"], {"attempts": 0, "passed": 0, "learners": 0})
            cell["attempts"] += 1
            cell["passed"] += int(r.get("passed") or 0)
            learners.setdefault(r["lesson_id"], set()).add(r["account_id"])
        for lesson_id, who in learners.items():
            stats[lesson_id]["learners"] = len(who)
        return stats

    def count_attempts(self, account_id: str) -> int:
        return self.col("step_attempt").count_documents({"account_id": account_id})

    # ------------------------------------------------------------ retention

    def blob_keys(self) -> set[str]:
        """Upload-folder files this store points at: recordings and teacher media."""
        keys = set(self.col("step_attempt").distinct("audio_key", {"audio_key": {"$ne": None}}))
        keys |= set(self.col("lesson_media").distinct("blob_key"))
        return keys

    def forget_older_than(self, cutoff: str, blobs, dry_run: bool) -> tuple[int, int, int, int]:
        """Storage limitation for attempts older than `cutoff` (see `aicefr.retention`).

        Recordings are in `blobs`, the learning service's blob store (D051).

        Same split as for responses: the recording and what was heard go, the
        result stays. What the learner said lives in `transcript` and in the
        `said` of each word and gap; the words of the text itself are the
        teacher's, and the statuses are the record of the practice, so both are
        kept. Returns (attempts considered, recordings, transcripts, bytes).
        """
        rows = list(
            self.col("step_attempt").find(
                {"created_at": {"$lt": cutoff}}, {"attempt_id": 1, "audio_key": 1, "result_json": 1}
            )
        )
        audio = cleared = freed = 0
        for row in rows:
            key = row.get("audio_key")
            size = blobs.size(key) if key else None
            if size is not None:
                freed += size
                audio += 1
                if not dry_run:
                    blobs.delete(key)
            result = json.loads(row["result_json"])
            changed = bool(result.get("transcript"))
            result["transcript"] = ""
            for mark in [*result.get("words", []), *result.get("gaps", [])]:
                if mark.get("said"):
                    mark["said"] = None
                    changed = True
            cleared += int(changed)
            if not dry_run and (changed or key):
                self.col("step_attempt").update_one(
                    {"attempt_id": row["attempt_id"]},
                    {"$set": {"result_json": json.dumps(result, ensure_ascii=False),
                              "audio_key": None}},
                )  # fmt: skip
        return len(rows), audio, cleared, freed

    # ------------------------------------------------------------ achievements

    def achievements(self, account_id: str) -> dict[str, dict]:
        """What one account has reached (D032): code -> unlocked_at, seen_at."""
        rows = (
            self.col("achievement")
            .find({"account_id": account_id})
            .sort([("unlocked_at", ASCENDING), ("_id", ASCENDING)])
        )
        return {
            r["code"]: {"unlocked_at": r["unlocked_at"], "seen_at": r.get("seen_at")} for r in rows
        }

    def unlock(self, account_id: str, codes: list[str], at: str | None = None) -> list[str]:
        """Store achievements just reached; returns those this call stored.

        Two requests reaching the same achievement at once store it once, and
        only one of them reports it, so the learner is congratulated once.
        """
        when = at or _now()
        stored = []
        for code in codes:
            try:
                self.col("achievement").insert_one(
                    {"account_id": account_id, "code": code, "unlocked_at": when, "seen_at": None}
                )
            except IntegrityError:
                continue
            stored.append(code)
        return stored

    def mark_seen(self, account_id: str, codes: list[str] | None = None) -> int:
        """Mark achievements as seen: those named, or every one not seen yet."""
        query: dict = {"account_id": account_id, "seen_at": None}
        if codes is not None:
            if not codes:
                return 0
            query["code"] = {"$in": list(codes)}
        return (
            self.col("achievement").update_many(query, {"$set": {"seen_at": _now()}}).modified_count
        )

    # ------------------------------------------------------------ reviews

    def schedule(
        self, account_id: str, kind: str, lesson_id: str, step_id: str, word: str, due: date
    ) -> None:
        """Add a review item, or bring a finished one back to box 1. An open item is left alone."""
        now = _now()
        items = self.col("review_item")
        key = {
            "account_id": account_id,
            "kind": kind,
            "lesson_id": lesson_id,
            "step_id": step_id,
            "word": word,
        }
        row = items.find_one(key)
        if row is None:
            try:
                items.insert_one(
                    {**key, "item_id": new_id("r"), "box": 1, "due_date": due.isoformat(),
                     "done": 0, "created_at": now, "updated_at": now}
                )  # fmt: skip
            except IntegrityError:
                pass  # scheduled by another request a moment ago: open, left alone
        elif row["done"]:
            items.update_one(
                {"item_id": row["item_id"]},
                {"$set": {"box": 1, "done": 0, "due_date": due.isoformat(), "updated_at": now}},
            )

    def due_reviews(self, account_id: str, today: date) -> list[dict]:
        rows = (
            self.col("review_item")
            .find({"account_id": account_id, "done": 0, "due_date": {"$lte": today.isoformat()}})
            .sort([("due_date", ASCENDING), ("created_at", ASCENDING), ("_id", ASCENDING)])
        )
        return [fields(r, REVIEW_FIELDS) for r in rows]  # type: ignore[misc]

    def open_reviews(self, account_id: str) -> list[dict]:
        rows = (
            self.col("review_item")
            .find({"account_id": account_id, "done": 0})
            .sort([("due_date", ASCENDING), ("_id", ASCENDING)])
        )
        return [fields(r, REVIEW_FIELDS) for r in rows]  # type: ignore[misc]

    def review(self, item_id: str) -> dict:
        row = self.col("review_item").find_one({"item_id": item_id})
        if row is None:
            raise NotFound(item_id)
        return fields(row, REVIEW_FIELDS)  # type: ignore[return-value]

    def reschedule(self, item_id: str, box: int, due: date | None) -> None:
        sets: dict = {"box": box, "done": int(due is None), "updated_at": _now()}
        if due is not None:
            sets["due_date"] = due.isoformat()
        self.col("review_item").update_one({"item_id": item_id}, {"$set": sets})

    # ------------------------------------------------------------ media

    def add_media(self, kind: str, content_type: str, blob_key: str, by: str | None) -> str:
        key = new_id("m")
        self.col("lesson_media").insert_one(
            {
                "media_key": key,
                "kind": kind,
                "content_type": content_type,
                "blob_key": blob_key,
                "created_by": by,
                "created_at": _now(),
            }
        )
        return key

    def media(self, key: str) -> dict:
        row = self.col("lesson_media").find_one({"media_key": key})
        if row is None:
            raise NotFound(key)
        return fields(
            row, ("media_key", "kind", "content_type", "blob_key", "created_by", "created_at")
        )  # type: ignore[return-value]

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
