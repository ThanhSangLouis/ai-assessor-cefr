"""Speaking tasks: the prompts students record against. Implements FR-01, UC-21.

Separate from `Repository` because tasks are reference data with a different
lifecycle: an administrator edits them, they are versioned, and a report has to
record which version of the prompt the student actually saw.

That last point is why `prompt_version` is stored on the task and copied onto
the request rather than looked up later. Reword a prompt after a cohort has
already answered it and every earlier report would silently start claiming the
student answered the new wording.
"""

from __future__ import annotations

import re
import secrets
from dataclasses import dataclass
from pathlib import Path

from aicefr.contracts import Band
from aicefr.practice.assessment_bank import (
    ASSESSMENT_PROMPTS,
    MAX_SECONDS,
    MIN_SECONDS,
    title_of,
)
from aicefr.storage.db import MongoStore, ensure_indexes
from aicefr.storage.db import now_iso as _now

# One document per task. min_seconds/max_seconds default to 40-60, not 60-180:
# the scoring model was trained on responses of 26.7-60.7 seconds, and a task
# added without its own durations takes these, so they sit inside that range.
# topic_keywords: ENGLISH topic words, comma separated (D022) -- the prompt is in
# Vietnamese while the learner speaks English, so speech is compared with this
# list; empty means an open prompt, never checked for being off topic.
# Every task is an assessment prompt with a band (D076); the practice tasks of
# D023 and their fields are gone (D083, migration 14).
INDEXES = {"task": [(("task_id",), True), (("active",), False)]}

_NEW_TASK = {"active": 1, "topic_keywords": "", "band": None}

# Recommended durations come from the SCORING MODEL's training distribution,
# not from the SRS. The SRS suggests 60-180 seconds and the quality check passes
# anything from 30 to 300, but `ridge_resp_v1` was fitted on responses of
# 26.7-60.7 seconds. A student who follows a "60-180 seconds" card and speaks for
# 95 seconds passes QC and is then refused by the scorer with
# OUT_OF_DISTRIBUTION -- a report with no score at all.
#
# So the card says 40-60 seconds: comfortably inside the model's range, and
# above the 30-second floor where QC stops flagging the recording as short.
# tests/test_tasks_and_admin.py keeps this honest by checking the advertised
# window against the artifact's own percentiles.
#
# The two prompts the system started with: an opinion and a process, the kinds
# of answer the scoring model was trained on. Their ids are only keys now
# (D078): reports point at them, nobody reads them.
DEFAULT_TASKS = [
    (
        "P3",
        "Bạn nghĩ gì về việc học trực tuyến so với học trên lớp? "
        "Hãy nêu quan điểm của bạn và giải thích lý do.",
        "v1",
        40,
        60,
    ),
    (
        "P4",
        "Hãy mô tả một quy trình bạn quen thuộc, ví dụ cách bạn chuẩn bị cho một kỳ thi. "
        "Nói rõ từng bước theo thứ tự.",
        "v1",
        40,
        60,
    ),
]


# Tu khoa chu de mac dinh (D022). Rong rai co chu dich: mot cau tra loi dung de
# chi can cham MOT tu la khong bi gan co, nen danh sach rong thi it bao nham.
# Nhung KHONG duoc chung chung: "night", "morning" tung nam o day va mot bai ve
# bong da ("saturday night") lot qua vi cham dung tu do.
DEFAULT_TOPIC_KEYWORDS = {
    "P3": (
        "online, internet, computer, laptop, zoom, video, classroom, class, school, "
        "university, teacher, lecturer, student, classmate, study, learn, lesson, "
        "course, home, face, offline, distance, interact, discuss"
    ),
    "P4": (
        "exam, test, prepare, preparation, study, review, revise, note, practice, "
        "practise, schedule, plan, step, first, next, finally, textbook, material, "
        "subject, question, revision, homework, memorize, memorise"
    ),
}


@dataclass(frozen=True)
class Task:
    """One speaking prompt.

    An ENTITY, not a value object as this docstring used to say: it has its own
    identity (`task_id`), its own document, and it is looked up by that id. Two
    prompts with identical wording are still two different prompts. The class
    diagram marks it «entity»; this line used to contradict it.
    """

    task_id: str
    title: str
    prompt_text: str
    prompt_version: str
    min_seconds: int
    max_seconds: int
    topic_keywords: tuple[str, ...] = ()
    band: Band | None = None


class TaskRepository(MongoStore):
    def __init__(self, db_path: str | Path = "aicefr.db") -> None:
        self.db_path = str(db_path)
        ensure_indexes(self.db, INDEXES, "task")
        self.seed_defaults()

    def seed_defaults(self) -> None:
        """Insert the built-in prompts that are missing.

        Inserts only the prompts that are MISSING, never touching one that is
        already there. The difference matters twice over. Re-seeding everything
        on each start would overwrite whatever an administrator had edited and
        would quietly change the prompt version under reports that already
        reference it. But skipping the whole seed whenever the collection is
        non-empty -- what this did before -- means a store created last month
        never learns about a prompt added this month.
        """
        tasks = self.col("task")
        for task_id, prompt, version, low, high in DEFAULT_TASKS:
            tasks.update_one(
                {"task_id": task_id},
                {
                    "$setOnInsert": {
                        **_NEW_TASK,
                        "title": title_of(Band.B1),
                        "prompt_text": prompt,
                        "prompt_version": version,
                        "band": Band.B1.value,
                        "min_seconds": low,
                        "max_seconds": high,
                        "created_at": _now(),
                    }
                },
                upsert=True,
            )
        # Chi dien vao de CHUA co tu khoa: khong de len thu admin da sua.
        for task_id, keywords in DEFAULT_TOPIC_KEYWORDS.items():
            if keywords:
                tasks.update_one(
                    {"task_id": task_id, "topic_keywords": ""},
                    {"$set": {"topic_keywords": keywords}},
                )
        # D076: the two first prompts are the bank's B1 ones; the long talk P5,
        # outside what the model was trained on, is retired once -- kept for the
        # reports that point at it, offered to nobody. A teacher may bring it back.
        tasks.update_many(
            {"task_id": {"$in": ["P3", "P4"]}, "band": None}, {"$set": {"band": Band.B1.value}}
        )
        tasks.update_one(
            {"task_id": "P5", "retired": {"$exists": False}},
            {"$set": {"active": 0, "retired": "D076"}},
        )
        for p in ASSESSMENT_PROMPTS:
            tasks.update_one(
                {"task_id": p.task_id},
                {
                    "$setOnInsert": {
                        **_NEW_TASK,
                        "title": p.title,
                        "prompt_text": p.prompt_text,
                        "prompt_version": "v1",
                        "band": p.band.value,
                        "min_seconds": MIN_SECONDS,
                        "max_seconds": MAX_SECONDS,
                        "topic_keywords": p.topic_keywords,
                        "created_at": _now(),
                    }
                },
                upsert=True,
            )

    # ------------------------------------------------------------ teachers' prompts (D076)

    def assessment_rows(self) -> list[dict]:
        """Every assessment prompt, retired ones too, for the teachers' screen."""
        rows = self.col("task").find()
        out = []
        for r in rows:
            t = self._to_task(r)
            out.append({**task_message(t), "active": bool(r.get("active", 1))})
        order = {b.value: i for i, b in enumerate(Band)}
        return sorted(out, key=lambda t: (order.get(t["band"] or "", 9), t["task_id"]))

    def add_assessment(self, band: Band, prompt_text: str, topic_keywords: str, by: str) -> str:
        """A teacher's new prompt, 40-60 seconds like every assessment prompt."""
        task_id = f"{band.value}-{secrets.token_hex(3).upper()}"
        self.col("task").insert_one(
            {
                **_NEW_TASK,
                "task_id": task_id,
                "title": title_of(band),
                "prompt_text": prompt_text,
                "prompt_version": "v1",
                "band": band.value,
                "min_seconds": MIN_SECONDS,
                "max_seconds": MAX_SECONDS,
                "topic_keywords": topic_keywords,
                "created_by": by,
                "created_at": _now(),
            }
        )
        return task_id

    def edit_assessment(self, task_id: str, changes: dict) -> bool:
        """Change a prompt. A new wording is a new version: earlier reports keep the old one."""
        row = self.col("task").find_one({"task_id": task_id})
        if row is None:
            return False
        sets = dict(changes)
        if "band" in sets:
            sets["title"] = title_of(sets["band"])
        if "prompt_text" in sets and sets["prompt_text"] != row["prompt_text"]:
            n = re.match(r"v(\d+)$", row.get("prompt_version") or "")
            sets["prompt_version"] = f"v{int(n.group(1)) + 1 if n else 2}"
        if "active" in sets:
            sets["active"] = int(bool(sets["active"]))
        self.col("task").update_one({"task_id": task_id}, {"$set": sets})
        return True

    def list_active(self) -> list[Task]:
        """The prompts a learner may be given."""
        rows = self.col("task").find({"active": 1}).sort("task_id", 1)
        return [self._to_task(r) for r in rows]

    def get(self, task_id: str) -> Task | None:
        row = self.col("task").find_one({"task_id": task_id})
        return self._to_task(row) if row else None

    @staticmethod
    def _to_task(row: dict) -> Task:
        # D078: a prompt is called by its band; a title stored before (an exam
        # part's name) is not read.
        title = title_of(row["band"]) if row.get("band") else row["title"]
        return Task(
            task_id=row["task_id"],
            title=title,
            prompt_text=row["prompt_text"],
            prompt_version=row["prompt_version"],
            min_seconds=row["min_seconds"],
            max_seconds=row["max_seconds"],
            topic_keywords=tuple(
                k.strip() for k in (row.get("topic_keywords") or "").split(",") if k.strip()
            ),
            band=Band(row["band"]) if row.get("band") else None,
        )


def task_message(task: Task) -> dict:
    """A task as a message carries it to the speech worker, which has no store (D043)."""
    return {
        "task_id": task.task_id,
        "title": task.title,
        "prompt_text": task.prompt_text,
        "prompt_version": task.prompt_version,
        "min_seconds": task.min_seconds,
        "max_seconds": task.max_seconds,
        "topic_keywords": list(task.topic_keywords),
        "band": task.band.value if task.band else None,
    }


def task_from_message(data: dict) -> Task:
    return Task(
        task_id=data["task_id"],
        title=data["title"],
        prompt_text=data["prompt_text"],
        prompt_version=data["prompt_version"],
        min_seconds=data["min_seconds"],
        max_seconds=data["max_seconds"],
        topic_keywords=tuple(data["topic_keywords"]),
        band=Band(data["band"]) if data.get("band") else None,
    )
