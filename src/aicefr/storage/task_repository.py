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

import json
from dataclasses import dataclass
from pathlib import Path

from aicefr.contracts import Band, Criterion, Mission, TaskPart, TaskPurpose
from aicefr.practice.bank import PRACTICE_TASKS
from aicefr.storage.db import IntegrityError, MongoStore, ensure_indexes
from aicefr.storage.db import now_iso as _now

# One document per task. min_seconds/max_seconds default to 40-60, not 60-180:
# the scoring model was trained on responses of 26.7-60.7 seconds, and a task
# added without its own durations takes these, so they sit inside that range.
# topic_keywords: ENGLISH topic words, comma separated (D022) -- the prompt is in
# Vietnamese while the learner speaks English, so speech is compared with this
# list; empty means an open prompt (P5), never checked for being off topic.
# purpose, criterion, band, missions_json, tips_json, reference_text: D023,
# filled on practice tasks only.
INDEXES = {"task": [(("task_id",), True), (("purpose", "active"), False)]}

_NEW_TASK = {
    "active": 1,
    "topic_keywords": "",
    "purpose": "assessment",
    "criterion": None,
    "band": None,
    "missions_json": "[]",
    "tips_json": "[]",
    "reference_text": None,
}

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
# The two parts the scoring model was trained on. Each exam response in the
# training corpus is exactly one file for these, which is what makes the unit
# of inference line up with what a student submits here.
DEFAULT_TASKS = [
    (
        "P3",
        "Nêu quan điểm về một chủ đề",
        "Bạn nghĩ gì về việc học trực tuyến so với học trên lớp? "
        "Hãy nêu quan điểm của bạn và giải thích lý do.",
        "v1",
        "P3",
        40,
        60,
    ),
    (
        "P4",
        "Mô tả một biểu đồ hoặc quy trình",
        "Hãy mô tả một quy trình bạn quen thuộc, ví dụ cách bạn chuẩn bị cho một kỳ thi. "
        "Nói rõ từng bước theo thứ tự.",
        "v1",
        "P4",
        40,
        60,
    ),
    # De dai. Khong nam trong dai huan luyen cua mo hinh va co tinh nhu the:
    # bai nay duoc cham bang co che cat cua so trong `scoring/windows.py`, moi
    # cua so 30-60 giay nen TUNG cua so van nam trong dai mo hinh biet. Diem
    # cuoi la trung vi cac cua so, gan ReasonCode.SCORE_AGGREGATED va luon
    # chuyen giang vien cho toi khi co che gop duoc kiem dinh o tuan 10-11.
    #
    # 120 giay la san chu khong phai 61: duoi 120 giay thi viec cat chi tao ra
    # hai cua so ngan ma khong them thong tin gi so voi mot bai 60 giay, trong
    # khi van phai chiu ca sai so cua viec gop. 300 giay la tran QC san co.
    (
        "P5",
        "Thuyết trình ngắn",
        "Hãy trình bày trong 2–5 phút về một chủ đề bạn quan tâm: nêu vấn đề, "
        "đưa ít nhất hai lý lẽ có ví dụ, rồi kết luận.",
        "v1",
        "P5",
        120,
        300,
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
    "P5": "",
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
    part: TaskPart
    min_seconds: int
    max_seconds: int
    topic_keywords: tuple[str, ...] = ()
    # D023. Assessment by default; the fields below exist only on practice tasks.
    purpose: TaskPurpose = TaskPurpose.ASSESSMENT
    criterion: Criterion | None = None
    band: Band | None = None
    missions: tuple[Mission, ...] = ()
    tips: tuple[str, ...] = ()
    reference_text: str | None = None

    @property
    def is_practice(self) -> bool:
        return self.purpose is TaskPurpose.PRACTICE


class TaskRepository(MongoStore):
    def __init__(self, db_path: str | Path = "aicefr.db") -> None:
        self.db_path = str(db_path)
        ensure_indexes(self.db, INDEXES, "task")
        self.seed_defaults()
        self.seed_practice()

    def seed_defaults(self) -> None:
        """Insert the built-in prompts that are missing.

        Inserts only the prompts that are MISSING, never touching one that is
        already there. The difference matters twice over. Re-seeding everything
        on each start would overwrite whatever an administrator had edited and
        would quietly change the prompt version under reports that already
        reference it. But skipping the whole seed whenever the collection is
        non-empty -- what this did before -- means a store created last month
        never learns about a prompt added this month, so P5 would exist only on
        fresh installs and the long-recording path would be unreachable on
        exactly the machines that have real data on them.
        """
        tasks = self.col("task")
        for task_id, title, prompt, version, part, low, high in DEFAULT_TASKS:
            tasks.update_one(
                {"task_id": task_id},
                {
                    "$setOnInsert": {
                        **_NEW_TASK,
                        "title": title,
                        "prompt_text": prompt,
                        "prompt_version": version,
                        "part": part,
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

    def seed_practice(self) -> None:
        """Load the practice task bank into the `task` collection. D023.

        Differs from `seed_defaults` on one point, on purpose: practice tasks are
        decided by the bank in code and nobody edits them on screen, so when the bank
        bumps a task's `prompt_version` the document is updated to match. Documents
        with the same version are left alone -- earlier results keep pointing at the
        wording that produced them, because `prompt_version` is copied onto every
        submission.
        """
        tasks = self.col("task")
        for t in PRACTICE_TASKS:
            content = {
                "title": t.title,
                "prompt_text": t.prompt_text,
                "prompt_version": t.prompt_version,
                "part": t.part.value,
                "min_seconds": t.min_seconds,
                "max_seconds": t.max_seconds,
                "purpose": TaskPurpose.PRACTICE.value,
                "criterion": t.criterion.value,
                "band": t.band.value,
                "missions_json": json.dumps(
                    [m.model_dump(mode="json") for m in t.missions], ensure_ascii=False
                ),
                "tips_json": json.dumps(list(t.tips), ensure_ascii=False),
                "reference_text": t.reference_text,
            }
            try:
                tasks.update_one(
                    {"task_id": t.task_id, "prompt_version": {"$ne": t.prompt_version}},
                    {
                        "$set": content,
                        "$setOnInsert": {"active": 1, "topic_keywords": "", "created_at": _now()},
                    },
                    upsert=True,
                )
            except IntegrityError:
                pass  # there already, at this version: left alone

    def list_active(self, purpose: TaskPurpose = TaskPurpose.ASSESSMENT) -> list[Task]:
        """Active tasks for one purpose. Assessment by default.

        The default deliberately matches the behaviour before D023: the submission
        screen and every older caller want assessment tasks only, and a practice task
        slipping into that list could be picked as an exam task.
        """
        rows = self.col("task").find({"active": 1, "purpose": purpose.value}).sort("task_id", 1)
        return [self._to_task(r) for r in rows]

    def get(self, task_id: str) -> Task | None:
        row = self.col("task").find_one({"task_id": task_id})
        return self._to_task(row) if row else None

    @staticmethod
    def _to_task(row: dict) -> Task:
        return Task(
            task_id=row["task_id"],
            title=row["title"],
            prompt_text=row["prompt_text"],
            prompt_version=row["prompt_version"],
            part=TaskPart(row["part"]),
            min_seconds=row["min_seconds"],
            max_seconds=row["max_seconds"],
            topic_keywords=tuple(
                k.strip() for k in (row.get("topic_keywords") or "").split(",") if k.strip()
            ),
            purpose=TaskPurpose(row.get("purpose") or TaskPurpose.ASSESSMENT.value),
            criterion=Criterion(row["criterion"]) if row.get("criterion") else None,
            band=Band(row["band"]) if row.get("band") else None,
            missions=tuple(
                Mission.model_validate(m) for m in json.loads(row.get("missions_json") or "[]")
            ),
            tips=tuple(json.loads(row.get("tips_json") or "[]")),
            reference_text=row.get("reference_text"),
        )


def task_message(task: Task) -> dict:
    """A task as a message carries it to the speech worker, which has no store (D043)."""
    return {
        "task_id": task.task_id,
        "title": task.title,
        "prompt_text": task.prompt_text,
        "prompt_version": task.prompt_version,
        "part": task.part.value,
        "min_seconds": task.min_seconds,
        "max_seconds": task.max_seconds,
        "topic_keywords": list(task.topic_keywords),
        "purpose": task.purpose.value,
        "criterion": task.criterion.value if task.criterion else None,
        "band": task.band.value if task.band else None,
        "missions": [m.model_dump(mode="json") for m in task.missions],
        "tips": list(task.tips),
        "reference_text": task.reference_text,
    }


def task_from_message(data: dict) -> Task:
    return Task(
        task_id=data["task_id"],
        title=data["title"],
        prompt_text=data["prompt_text"],
        prompt_version=data["prompt_version"],
        part=TaskPart(data["part"]),
        min_seconds=data["min_seconds"],
        max_seconds=data["max_seconds"],
        topic_keywords=tuple(data["topic_keywords"]),
        purpose=TaskPurpose(data["purpose"]),
        criterion=Criterion(data["criterion"]) if data["criterion"] else None,
        band=Band(data["band"]) if data["band"] else None,
        missions=tuple(Mission.model_validate(m) for m in data["missions"]),
        tips=tuple(data["tips"]),
        reference_text=data["reference_text"],
    )
