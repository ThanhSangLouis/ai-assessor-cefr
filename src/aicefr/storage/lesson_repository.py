"""Storage of lesson paths, published versions, step attempts and reviews (D025).

The collections follow the class diagram (D060):

* `path` -- a `LessonPath` with its `Unit`s, which live and go with it;
* `lesson` -- a lesson's draft, every version it was published as, and the
  media a teacher uploaded for it. A lesson belongs to one unit
  (`Unit ◆ Lesson`), but keeps a document of its own: it grows with every
  published version, and learners, plans and reviews find it by its id;
* `attempt` -- one `StepAttempt` per spoken take;
* `review_item` -- the spaced-repetition `ReviewItem`s;
* `achievement` -- the `Achievement`s a learner reached (D032);
* `system` -- one-off upgrades already applied, e.g. the sample path's layout.

Lessons are edited as a DRAFT; publishing appends an immutable copy to the
lesson's `versions`. Learners read only published versions, and every attempt
records the version it was made against, so a result can always be read
against the exact text the learner saw.

Step attempts live in their own collection, not in `response`. That keeps them out
of the review queue, the scoring statistics and the research export by
construction rather than by a filter someone could forget.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path

from pymongo import ASCENDING, DESCENDING

from aicefr.contracts import Band, Criterion
from aicefr.lessons.model import Lesson, PathStatus, StepResult, Topic, WordStatus, new_id
from aicefr.lessons.seed import (
    SAMPLE_LAYOUT,
    SAMPLE_PATH,
    SAMPLE_PATH_ID,
    SAMPLE_UNITS,
    sample_lessons,
)
from aicefr.storage.db import (
    IntegrityError,
    MongoStore,
    ensure_indexes,
    ensure_system,
    fields,
    get_setting,
    set_setting,
)
from aicefr.storage.db import now_iso as _now

# path.status: draft | published | archived. A unit's topic (D027): what it
# talks about. review_item.kind: word | talk | phrase; a word from a drill
# (D089) has no lesson (lesson_id and step_id empty) and points back with
# drill_id; a phrase of an upgraded answer (D070, D104) has neither, its
# `word` is the phrase's key and it never ends (`done` stays 0). A
# lesson's media kind: audio | image. achievement (D032): achievements reached,
# kept even if the attempts behind them go.
# The kind of a review item that is a phrase of the phrase book (D104).
PHRASE = "phrase"
INDEXES = {
    "path": [(("path_id",), True), (("units.unit_id",), False)],
    "lesson": [
        (("lesson_id",), True),
        (("unit_id", "position"), False),
        (("media.media_key",), False),
    ],
    "attempt": [
        (("attempt_id",), True),
        (("account_id", "lesson_id"), False),
        (("created_at",), False),
    ],
    "review_item": [
        (("item_id",), True),
        (("account_id", "kind", "lesson_id", "step_id", "word"), True),
        (("account_id", "done", "due_date"), False),
    ],
    "achievement": [(("account_id", "code"), True)],
}
SETTING = "learning."  # this part's keys in `system`

PATH_FIELDS = (
    "path_id",
    "title",
    "description",
    "band_from",
    "band_to",
    "status",
    "created_at",
)
UNIT_FIELDS = (
    "unit_id",
    "path_id",
    "title",
    "function",
    "band",
    "criterion",
    "topic",
)
ATTEMPT_FIELDS = (
    "attempt_id",
    "account_id",
    "lesson_id",
    "lesson_version",
    "review_item_id",
    "audio_key",
    "result",
    "override",
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
    "drill_id",
)
_BY_POSITION = [("position", ASCENDING), ("_id", ASCENDING)]

PATH_STATUSES = tuple(s.value for s in PathStatus)


class NotFound(LookupError):
    pass


@dataclass
class Unit:
    """One stage of a path: what it practises, at which band, and its lessons in order.

    Stored inside its path's document; `lessons` is filled when a path is read
    with its lessons (`LessonRepository.outline`), which have documents of their own.
    """

    unit_id: str
    title: str
    function: str = ""
    band: Band | None = None
    criterion: Criterion | None = None
    topic: str | None = None
    lessons: list[Lesson] = field(default_factory=list)

    @classmethod
    def from_doc(cls, doc: dict) -> Unit:
        found = {k: doc[k] for k in UNIT_FIELDS if k in doc and k != "path_id"}
        found["band"] = Band(doc["band"]) if doc.get("band") else None
        found["criterion"] = Criterion(doc["criterion"]) if doc.get("criterion") else None
        return cls(**found)

    def to_doc(self) -> dict:
        doc = asdict(self)
        doc.pop("lessons")
        doc["band"] = self.band.value if self.band else None
        doc["criterion"] = self.criterion.value if self.criterion else None
        return doc


@dataclass
class LessonPath:
    path_id: str
    title: str
    description: str = ""
    band_from: Band | None = None
    band_to: Band | None = None
    status: PathStatus = PathStatus.DRAFT
    created_at: str = ""
    units: list[Unit] = field(default_factory=list)

    @classmethod
    def from_doc(cls, doc: dict) -> LessonPath:
        found = {k: doc[k] for k in PATH_FIELDS if k in doc and k != "status"}
        for key in ("band_from", "band_to"):
            found[key] = Band(doc[key]) if doc.get(key) else None
        return cls(
            **found,
            status=PathStatus(doc["status"]),
            # D103: a unit's place is its place in the list, no `position`.
            units=[Unit.from_doc(u) for u in doc.get("units") or []],
        )

    def to_doc(self) -> dict:
        return {**self.view(), "units": [u.to_doc() for u in self.units]}

    def view(self) -> dict:
        return {
            **{k: getattr(self, k) for k in PATH_FIELDS},
            "band_from": self.band_from.value if self.band_from else None,
            "band_to": self.band_to.value if self.band_to else None,
            "status": self.status.value,
        }

    def unit(self, unit_id: str) -> Unit | None:
        return next((u for u in self.units if u.unit_id == unit_id), None)


@dataclass
class StepAttempt:
    """One spoken take of one step, against the lesson version the learner saw.

    The step, round, speaking time, rules and verdict are the result's own
    fields (D105): `result` is the machine's `StepResult`, `override` a
    teacher's correction of it. Nothing is copied out of them.
    """

    attempt_id: str
    account_id: str
    lesson_id: str
    lesson_version: int
    review_item_id: str | None
    audio_key: str | None
    result: dict  # the machine's StepResult, as a document (D104: no JSON string)
    created_at: str
    override: dict | None = None
    overridden_by: str | None = None
    overridden_at: str | None = None


@dataclass
class ReviewItem:
    """A word, a talk or a phrase to say again later: its Leitner box and the day it is due."""

    item_id: str
    account_id: str
    kind: str
    lesson_id: str
    step_id: str
    word: str
    box: int
    due_date: str
    done: int
    created_at: str
    # D089: the drill a word came from, when it came from a recording, not a lesson.
    drill_id: str | None = None

    def is_due(self, today: date) -> bool:
        return not self.done and self.due_date <= today.isoformat()


@dataclass
class Achievement:
    """One achievement of the catalogue (`AchievementRule`) one learner reached."""

    account_id: str
    code: str
    unlocked_at: str


class LessonRepository(MongoStore):
    def __init__(self, db_path: str | Path, seed: bool = True) -> None:
        self.db_path = str(db_path)
        ensure_indexes(self.db, INDEXES, "lesson")
        ensure_system(self.db)
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
        exists = self.col("path").find_one({"path_id": SAMPLE_PATH_ID}) is not None
        recorded = get_setting(self.db, SETTING + "sample_layout")
        if not exists:
            try:
                self.create_path(
                    SAMPLE_PATH["title"],
                    SAMPLE_PATH["description"],
                    SAMPLE_PATH["band_from"],
                    SAMPLE_PATH["band_to"],
                    path_id=SAMPLE_PATH_ID,
                    status="published",
                )
            except IntegrityError:
                return  # another process is laying it out
            layout = 0
        else:
            # A sample path with no record is the first layout (D025: one unit per band).
            layout = int(recorded) if recorded else 1
        if layout >= SAMPLE_LAYOUT:
            return
        self._lay_out_sample(upgrade=exists)
        set_setting(self.db, SETTING + "sample_layout", str(SAMPLE_LAYOUT))

    def _lay_out_sample(self, upgrade: bool) -> None:
        lessons = sample_lessons()
        lesson_docs = self.col("lesson")
        if upgrade:
            self.update_path(
                SAMPLE_PATH_ID,
                title=SAMPLE_PATH["title"],
                description=SAMPLE_PATH["description"],
                band_from=SAMPLE_PATH["band_from"],
                band_to=SAMPLE_PATH["band_to"],
            )
        for unit in SAMPLE_UNITS:
            uid = unit["unit_id"]
            if self._path_of_unit(uid) is None:
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
            for item in lessons[uid]:
                if lesson_docs.find_one({"lesson_id": item.lesson_id}) is None:
                    self.add_lesson(uid, item)
                    self.publish(item.lesson_id)
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
        # Sample units first, in layout order; a teacher's own units follow.
        self._order_units(SAMPLE_PATH_ID, [u["unit_id"] for u in SAMPLE_UNITS])

    # ------------------------------------------------------------ paths and units

    def create_path(
        self,
        title: str,
        description: str = "",
        band_from: Band | None = None,
        band_to: Band | None = None,
        path_id: str | None = None,
        status: str = "draft",
    ) -> str:
        now = _now()
        made = LessonPath(
            path_id=path_id or new_id("p"),
            title=title,
            description=description,
            band_from=Band(band_from) if band_from else None,
            band_to=Band(band_to) if band_to else None,
            status=PathStatus(status),
            created_at=now,
        )
        self.col("path").insert_one(made.to_doc())
        return made.path_id

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
        done = self.col("path").update_one({"path_id": path_id}, {"$set": sets})
        if not done.matched_count:
            raise NotFound(path_id)

    def paths(self, published_only: bool = False) -> list[dict]:
        query = {"status": "published"} if published_only else {"status": {"$ne": "archived"}}
        rows = self.col("path").find(query).sort([("created_at", ASCENDING), ("_id", ASCENDING)])
        return [LessonPath.from_doc(r).view() for r in rows]

    def path(self, path_id: str) -> dict:
        return self._path(path_id).view()

    def _path(self, path_id: str) -> LessonPath:
        row = self.col("path").find_one({"path_id": path_id})
        if row is None:
            raise NotFound(path_id)
        return LessonPath.from_doc(row)

    def _path_of_unit(self, unit_id: str) -> LessonPath | None:
        row = self.col("path").find_one({"units.unit_id": unit_id})
        return LessonPath.from_doc(row) if row else None

    def _set_unit(self, unit_id: str, **sets) -> bool:
        done = self.col("path").update_one(
            {"units.unit_id": unit_id}, {"$set": {f"units.$.{k}": v for k, v in sets.items()}}
        )
        return bool(done.matched_count)

    def _order_units(self, path_id: str, order: list[str]) -> None:
        """Put a path's units in `order` (unit ids); units not named keep their order, last."""
        row = self.col("path").find_one({"path_id": path_id}, {"units": 1})
        units = (row or {}).get("units") or []
        rank = {uid: n for n, uid in enumerate(order)}
        units = sorted(units, key=lambda u: rank.get(u["unit_id"], len(order)))
        self.col("path").update_one({"path_id": path_id}, {"$set": {"units": units}})

    def _next_position(self, collection: str, parent: str, parent_id: str) -> int:
        """The position after the last lesson of a unit."""
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
        self._path(path_id)  # NotFound when there is no such path
        made = Unit(
            unit_id=unit_id or new_id("u"),
            title=title,
            function=function,
            band=Band(band) if band else None,
            criterion=Criterion(criterion) if criterion else None,
            topic=Topic(topic).value if topic else None,
        )
        self.col("path").update_one({"path_id": path_id}, {"$push": {"units": made.to_doc()}})
        return made.unit_id

    def update_unit(self, unit_id: str, **changes) -> None:
        allowed = {"title", "function", "band", "criterion", "topic"}
        sets = {k: v for k, v in changes.items() if k in allowed}
        for key in ("band", "criterion", "topic"):
            if key in sets and hasattr(sets[key], "value"):
                sets[key] = sets[key].value
        if not sets:
            return
        if not self._set_unit(unit_id, **sets):
            raise NotFound(unit_id)

    def unit(self, unit_id: str) -> dict:
        owner = self._path_of_unit(unit_id)
        if owner is None:
            raise NotFound(unit_id)
        return {**owner.unit(unit_id).to_doc(), "path_id": owner.path_id}  # type: ignore[union-attr]

    def delete_unit(self, unit_id: str) -> None:
        """Only an empty unit can go: lessons carry attempts that must stay readable."""
        if self.col("lesson").find_one({"unit_id": unit_id, "archived": 0}):
            raise ValueError("chặng còn bài học, chuyển hoặc lưu trữ các bài trước")
        self.col("lesson").delete_many({"unit_id": unit_id})
        self.col("path").update_one(
            {"units.unit_id": unit_id}, {"$pull": {"units": {"unit_id": unit_id}}}
        )

    def move(self, table: str, key: str, direction: int) -> None:
        """Swap a unit or a lesson with its neighbour (direction -1 up, +1 down)."""
        if table not in ("lesson_unit", "lesson"):
            raise ValueError(table)
        if table == "lesson_unit":
            owner = self._path_of_unit(key)
            if owner is None:
                raise NotFound(key)
            units = owner.units
            i = next(n for n, u in enumerate(units) if u.unit_id == key)
            j = i + (-1 if direction < 0 else 1)
            if 0 <= j < len(units):
                order = [u.unit_id for u in units]
                order[i], order[j] = order[j], order[i]
                self._order_units(owner.path_id, order)
            return
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

    def add_lesson(self, unit_id: str, lesson: Lesson) -> str:
        if self._path_of_unit(unit_id) is None:
            raise NotFound(unit_id)
        self.col("lesson").insert_one(
            {
                "lesson_id": lesson.lesson_id,
                "unit_id": unit_id,
                "position": self._next_position("lesson", "unit_id", unit_id),
                "draft": lesson.model_dump(mode="json"),
                "published_version": 0,
                "archived": 0,
                "updated_at": _now(),
                "versions": [],
                "media": [],
            }
        )
        return lesson.lesson_id

    def draft(self, lesson_id: str) -> tuple[Lesson, dict]:
        """The working copy and its metadata (unit, published version, unpublished changes)."""
        row = self.col("lesson").find_one({"lesson_id": lesson_id})
        owner = self._path_of_unit(row["unit_id"]) if row else None
        if row is None or owner is None:
            raise NotFound(lesson_id)
        meta = {
            "unit_id": row["unit_id"],
            "path_id": owner.path_id,
            "published_version": row["published_version"],
            "draft_changed": _draft_changed(row),
            "archived": bool(row["archived"]),
            "updated_at": row["updated_at"],
        }
        return Lesson.model_validate(row["draft"]), meta

    def save_draft(self, lesson_id: str, lesson: Lesson) -> None:
        if lesson.lesson_id != lesson_id:
            raise ValueError("mã bài học không khớp")
        done = self.col("lesson").update_one(
            {"lesson_id": lesson_id},
            {"$set": {"draft": lesson.model_dump(mode="json"), "updated_at": _now()}},
        )
        if not done.matched_count:
            raise NotFound(lesson_id)

    def publish(self, lesson_id: str) -> int:
        lesson, meta = self.draft(lesson_id)
        version = meta["published_version"] + 1
        published = {
            "version": version,
            "lesson": lesson.model_dump(mode="json"),
        }
        # Guarded by the version read: of two teachers publishing at once, one
        # appends the version and moves the number, the other changes nothing.
        done = self.col("lesson").update_one(
            {"lesson_id": lesson_id, "published_version": version - 1},
            {
                "$push": {"versions": published},
                "$set": {"published_version": version},
            },
        )
        if not done.modified_count:
            raise IntegrityError(f"{lesson_id} v{version} was published a moment ago")
        return version

    def published(self, lesson_id: str, version: int | None = None) -> tuple[Lesson, int] | None:
        query: dict = {"lesson_id": lesson_id}
        if version is None:
            query["archived"] = 0
        row = self.col("lesson").find_one(query, {"versions": 1, "published_version": 1})
        if row is None:
            return None
        wanted = row["published_version"] if version is None else version
        found = next((v for v in row.get("versions") or [] if v["version"] == wanted), None)
        if found is None:
            return None
        return Lesson.model_validate(found["lesson"]), found["version"]

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
        row = self.col("path").find_one({"path_id": path_id})
        units = LessonPath.from_doc(row).units if row else []
        lessons = list(
            self.col("lesson")
            .find({"unit_id": {"$in": [u.unit_id for u in units]}, "archived": 0})
            .sort(_BY_POSITION)
        )
        published = {
            (row["lesson_id"], v["version"]): v["lesson"]
            for row in lessons
            for v in row.get("versions") or []
        }
        out = []
        for u in units:
            items = []
            for row in lessons:
                if row["unit_id"] != u.unit_id:
                    continue
                shown = published.get((row["lesson_id"], row["published_version"]))
                if published_only and not shown:
                    continue
                source = shown if published_only else row["draft"]
                items.append(
                    {
                        "lesson": Lesson.model_validate(source),
                        "published_version": row["published_version"],
                        "draft_changed": _draft_changed(row),
                    }
                )
            u.lessons = [item["lesson"] for item in items]
            out.append({**u.to_doc(), "path_id": path_id, "lessons": items})
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
        made = StepAttempt(
            attempt_id=attempt_id or new_id("a"),
            account_id=account_id,
            lesson_id=lesson_id,
            lesson_version=lesson_version,
            review_item_id=review_item_id,
            audio_key=audio_key,
            result=result.model_dump(mode="json"),
            created_at=created_at or _now(),
        )
        self.col("attempt").insert_one(asdict(made))
        return made.attempt_id

    @staticmethod
    def _attempt(row) -> dict:
        d = fields(row, ATTEMPT_FIELDS)
        machine = StepResult.model_validate(d.pop("result"))  # type: ignore[union-attr]
        override = d.pop("override") or None  # type: ignore[union-attr]
        d["result"] = apply_override(machine, override) if override else machine  # type: ignore[index]
        d["passed"] = d["result"].passed  # type: ignore[index]
        # Read from the result, never stored beside it (D105).
        d["step_id"] = machine.step_id  # type: ignore[index]
        d["round"] = machine.round  # type: ignore[index]
        d["speaking_s"] = machine.speaking_s if machine.measured else 0.0  # type: ignore[index]
        d["rules_version"] = machine.rules_version  # type: ignore[index]
        # Kept beside the corrected result, so a teacher editing a correction
        # starts from what the machine said and what was changed.
        d["machine_passed"] = machine.passed  # type: ignore[index]
        d["override"] = override  # type: ignore[index]
        return d  # type: ignore[return-value]

    def attempt(self, attempt_id: str) -> dict:
        row = self.col("attempt").find_one({"attempt_id": attempt_id})
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
        found = self.col("attempt").find(query)
        if limit:
            rows = list(found.sort([("created_at", DESCENDING), ("_id", DESCENDING)]).limit(limit))
        else:
            rows = list(found.sort([("created_at", ASCENDING), ("_id", ASCENDING)]))
        return [self._attempt(r) for r in rows]

    def set_override(self, attempt_id: str, override: dict, by: str) -> None:
        done = self.col("attempt").update_one(
            {"attempt_id": attempt_id},
            {"$set": {"override": _string_keys(override), "overridden_by": by,
                      "overridden_at": _now()}},
        )  # fmt: skip
        if not done.matched_count:
            raise NotFound(attempt_id)

    def delete_attempt(self, attempt_id: str) -> str | None:
        """Remove one attempt; returns its audio key so the caller deletes the file."""
        row = self.col("attempt").find_one_and_delete({"attempt_id": attempt_id})
        if row is None:
            raise NotFound(attempt_id)
        return row.get("audio_key")

    def erase_account(self, account_id: str) -> list[str]:
        """Erasure (FR-34/35): every attempt, review and achievement of one account.

        Returns the audio keys, so the caller deletes the recordings.
        """
        keys = [
            r["audio_key"]
            for r in self.col("attempt").find(
                {"account_id": account_id, "audio_key": {"$ne": None}}, {"audio_key": 1}
            )
        ]
        self.col("attempt").delete_many({"account_id": account_id})
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
        measured = {"result.speaking_s": {"$gt": 0}, "result.measured": {"$ne": False}}
        for r in self.col("attempt").find(measured):
            a = self._attempt(r)
            cell = stats.setdefault(a["lesson_id"], {"attempts": 0, "passed": 0, "learners": 0})
            cell["attempts"] += 1
            cell["passed"] += int(a["passed"])
            learners.setdefault(a["lesson_id"], set()).add(a["account_id"])
        for lesson_id, who in learners.items():
            stats[lesson_id]["learners"] = len(who)
        return stats

    def count_attempts(self, account_id: str) -> int:
        return self.col("attempt").count_documents({"account_id": account_id})

    # ------------------------------------------------------------ retention

    def blob_keys(self) -> set[str]:
        """Upload-folder files this store points at: recordings and teacher media."""
        keys = set(self.col("attempt").distinct("audio_key", {"audio_key": {"$ne": None}}))
        keys |= {
            m["blob_key"]
            for row in self.col("lesson").find({"media.0": {"$exists": True}}, {"media": 1})
            for m in row["media"]
        }
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
            self.col("attempt").find(
                {"created_at": {"$lt": cutoff}}, {"attempt_id": 1, "audio_key": 1, "result": 1}
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
            result = row["result"]
            changed = bool(result.get("transcript"))
            result["transcript"] = ""
            for mark in [*result.get("words", []), *result.get("gaps", [])]:
                if mark.get("said"):
                    mark["said"] = None
                    changed = True
            cleared += int(changed)
            if not dry_run and (changed or key):
                self.col("attempt").update_one(
                    {"attempt_id": row["attempt_id"]},
                    {"$set": {"result": result, "audio_key": None}},
                )  # fmt: skip
        return len(rows), audio, cleared, freed

    # ------------------------------------------------------------ achievements

    def achievements(self, account_id: str) -> dict[str, dict]:
        """What one account has reached (D032): code -> unlocked_at."""
        rows = (
            self.col("achievement")
            .find({"account_id": account_id})
            .sort([("unlocked_at", ASCENDING), ("_id", ASCENDING)])
        )
        return {r["code"]: {"unlocked_at": r["unlocked_at"]} for r in rows}

    def unlock(self, account_id: str, codes: list[str], at: str | None = None) -> list[str]:
        """Store achievements just reached; returns those this call stored.

        Two requests reaching the same achievement at once store it once, and
        only one of them reports it, so the learner is congratulated once.
        """
        when = at or _now()
        stored = []
        for code in codes:
            try:
                self.col("achievement").insert_one(asdict(Achievement(account_id, code, when)))
            except IntegrityError:
                continue
            stored.append(code)
        return stored

    # ------------------------------------------------------------ reviews

    def schedule(
        self,
        account_id: str,
        kind: str,
        lesson_id: str,
        step_id: str,
        word: str,
        due: date,
        drill_id: str | None = None,
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
            made = ReviewItem(
                **key, item_id=new_id("r"), box=1, due_date=due.isoformat(), done=0,
                created_at=now, drill_id=drill_id,
            )  # fmt: skip
            try:
                items.insert_one(asdict(made))
            except IntegrityError:
                pass  # scheduled by another request a moment ago: open, left alone
        elif row["done"]:
            items.update_one(
                {"item_id": row["item_id"]},
                {"$set": {"box": 1, "done": 0, "due_date": due.isoformat()}},
            )

    def due_reviews(self, account_id: str, today: date) -> list[dict]:
        rows = (
            self.col("review_item")
            .find({"account_id": account_id, "done": 0, "kind": {"$ne": PHRASE}})
            .sort([("due_date", ASCENDING), ("created_at", ASCENDING), ("_id", ASCENDING)])
        )
        items = (ReviewItem(**fields(r, REVIEW_FIELDS)) for r in rows)  # type: ignore[arg-type]
        return [asdict(i) for i in items if i.is_due(today)]

    def open_reviews(self, account_id: str) -> list[dict]:
        rows = (
            self.col("review_item")
            .find({"account_id": account_id, "done": 0, "kind": {"$ne": PHRASE}})
            .sort([("due_date", ASCENDING), ("_id", ASCENDING)])
        )
        return [fields(r, REVIEW_FIELDS) for r in rows]  # type: ignore[misc]

    def review(self, item_id: str) -> dict:
        row = self.col("review_item").find_one({"item_id": item_id})
        if row is None:
            raise NotFound(item_id)
        return fields(row, REVIEW_FIELDS)  # type: ignore[return-value]

    def phrase_reviews(self, account_id: str) -> dict[str, dict]:
        """Where each phrase of the phrase book is (D104): key -> box and due day."""
        rows = self.col("review_item").find({"account_id": account_id, "kind": PHRASE})
        return {r["word"]: {"box": r["box"], "due": r["due_date"]} for r in rows}

    def review_phrase(self, account_id: str, key: str, box: int, due: date) -> None:
        """Keep a phrase's box and due day after a review; its first review makes the record."""
        now = _now()
        self.col("review_item").update_one(
            {"account_id": account_id, "kind": PHRASE, "lesson_id": "", "step_id": "", "word": key},
            {
                "$set": {"box": box, "due_date": due.isoformat()},
                "$setOnInsert": {
                    "item_id": new_id("r"),
                    "done": 0,
                    "created_at": now,
                    "drill_id": None,
                },
            },  # fmt: skip
            upsert=True,
        )

    def reschedule(self, item_id: str, box: int, due: date | None) -> None:
        sets: dict = {"box": box, "done": int(due is None)}
        if due is not None:
            sets["due_date"] = due.isoformat()
        self.col("review_item").update_one({"item_id": item_id}, {"$set": sets})

    # ------------------------------------------------------------ media

    def add_media(self, lesson_id: str, kind: str, content_type: str, blob_key: str) -> str:
        """Keep a file a teacher uploaded for one of the lesson's steps; its key."""
        key = new_id("m")
        item = {
            "media_key": key,
            "kind": kind,
            "content_type": content_type,
            "blob_key": blob_key,
        }
        done = self.col("lesson").update_one({"lesson_id": lesson_id}, {"$push": {"media": item}})
        if not done.matched_count:
            raise NotFound(lesson_id)
        return key

    def media(self, key: str) -> dict:
        """A media file by its key, whichever lesson holds it: copies of a lesson share them."""
        row = self.col("lesson").find_one({"media.media_key": key}, {"media": 1})
        found = next((m for m in (row or {}).get("media") or [] if m["media_key"] == key), None)
        if found is None:
            raise NotFound(key)
        return found

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

    def import_path(self, data: dict) -> str:
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
        )
        for title, function, band, criterion, topic, lessons in planned:
            uid = self.add_unit(pid, title, function, band, criterion, topic=topic)
            for lesson in lessons:
                self.add_lesson(uid, lesson)
        return pid


def _draft_changed(row: dict) -> bool:
    """Whether the draft differs from the version learners see (D105: worked out, not kept).

    A lesson never published counts as changed: it has something to publish.
    """
    shown = row.get("published_version") or 0
    if not shown:
        return True
    version = next((v for v in row.get("versions") or [] if v["version"] == shown), None)
    if version is None:
        return True
    # Compared as lessons, not as stored documents: a version published before
    # a field was added to `Lesson` lacks its default, and is the same lesson.
    return Lesson.model_validate(row.get("draft")) != Lesson.model_validate(version.get("lesson"))


def _string_keys(value):
    """`value` with every mapping key a string, as a document needs it.

    A teacher's correction maps word positions (ints) to statuses. Kept as a
    JSON string before D104, the keys came back as strings, and
    `apply_override` reads them that way.
    """
    if isinstance(value, dict):
        return {str(k): _string_keys(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_string_keys(v) for v in value]
    return value


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
