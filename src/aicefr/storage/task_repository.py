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
from aicefr.storage.db import DbRow, SqlStore, add_columns
from aicefr.storage.db import now_iso as _now

SCHEMA_TASK = """
CREATE TABLE IF NOT EXISTS task (
    task_id         TEXT PRIMARY KEY,
    title           TEXT NOT NULL,
    prompt_text     TEXT NOT NULL,
    prompt_version  TEXT NOT NULL,
    part            TEXT NOT NULL,
    -- 40-60 giay, khong phai 60-180. Mo hinh cham diem duoc huan luyen tren
    -- bai dai 26,7-60,7 giay; mot de bai moi them vao ma khong ghi ro thoi
    -- luong se lay gia tri mac dinh nay, nen gia tri mac dinh phai nam trong
    -- dai huan luyen chu khong phai ngoai no.
    min_seconds     INTEGER NOT NULL DEFAULT 40,
    max_seconds     INTEGER NOT NULL DEFAULT 60,
    active          INTEGER NOT NULL DEFAULT 1,
    created_at      TEXT NOT NULL,
    -- Tu khoa chu de TIENG ANH, cach nhau dau phay (D022). De bai viet bang
    -- tieng Viet con sinh vien noi tieng Anh, nen khong so loi noi voi de duoc;
    -- so voi danh sach nay. Rong = de mo (P5), khong kiem lac de.
    topic_keywords  TEXT NOT NULL DEFAULT '',
    -- D023. Practice tasks: criterion, band, missions, tips, read-aloud passage.
    -- Assessment tasks leave these columns empty.
    purpose         TEXT NOT NULL DEFAULT 'assessment',
    criterion       TEXT,
    band            TEXT,
    missions_json   TEXT NOT NULL DEFAULT '[]',
    tips_json       TEXT NOT NULL DEFAULT '[]',
    reference_text  TEXT
);
"""

# Columns added after the table already held data. CREATE IF NOT EXISTS does not
# add columns to an existing table, so every new column needs a line here.
_ADDED_COLUMNS = (
    ("topic_keywords", "TEXT NOT NULL DEFAULT ''"),
    ("purpose", "TEXT NOT NULL DEFAULT 'assessment'"),
    ("criterion", "TEXT"),
    ("band", "TEXT"),
    ("missions_json", "TEXT NOT NULL DEFAULT '[]'"),
    ("tips_json", "TEXT NOT NULL DEFAULT '[]'"),
    ("reference_text", "TEXT"),
)

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
    identity (`task_id`), its own table, and it is looked up by that id. Two
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


class TaskRepository(SqlStore):
    def __init__(self, db_path: str | Path = "aicefr.db") -> None:
        self.db_path = str(db_path)
        with self._conn() as c:
            c.executescript(SCHEMA_TASK)
            # Databases created before D022/D023 lack these columns.
            add_columns(c, "task", _ADDED_COLUMNS)
        self.seed_defaults()
        self.seed_practice()

    def seed_defaults(self) -> None:
        """Insert the two built-in prompts if the table is empty.

        Inserts only the prompts that are MISSING, never touching one that is
        already there. The difference matters twice over. Re-seeding everything
        on each start would overwrite whatever an administrator had edited and
        would quietly change the prompt version under reports that already
        reference it. But skipping the whole seed whenever the table is
        non-empty -- what this did before -- means a database created last month
        never learns about a prompt added this month, so P5 would exist only on
        fresh installs and the long-recording path would be unreachable on
        exactly the machines that have real data on them.
        """
        with self._conn() as c:
            c.executemany(
                "INSERT OR IGNORE INTO task(task_id,title,prompt_text,prompt_version,part,"
                "min_seconds,max_seconds,created_at) VALUES(?,?,?,?,?,?,?,?)",
                [(*t, _now()) for t in DEFAULT_TASKS],
            )
            # Chi dien vao de CHUA co tu khoa: khong de len thu admin da sua.
            c.executemany(
                "UPDATE task SET topic_keywords=? WHERE task_id=? AND topic_keywords=''",
                [(kw, tid) for tid, kw in DEFAULT_TOPIC_KEYWORDS.items() if kw],
            )

    def seed_practice(self) -> None:
        """Load the practice task bank into the `task` table. D023.

        Differs from `seed_defaults` on one point, on purpose: practice tasks are
        decided by the bank in code and nobody edits them on screen, so when the bank
        bumps a task's `prompt_version` the row in the database is updated to match.
        Rows with the same version are left alone -- earlier results keep pointing at
        the wording that produced them, because `prompt_version` is copied onto every
        submission.
        """
        rows = [
            (
                t.task_id,
                t.title,
                t.prompt_text,
                t.prompt_version,
                t.part.value,
                t.min_seconds,
                t.max_seconds,
                _now(),
                TaskPurpose.PRACTICE.value,
                t.criterion.value,
                t.band.value,
                json.dumps([m.model_dump(mode="json") for m in t.missions], ensure_ascii=False),
                json.dumps(list(t.tips), ensure_ascii=False),
                t.reference_text,
            )
            for t in PRACTICE_TASKS
        ]
        with self._conn() as c:
            c.executemany(
                """INSERT INTO task(task_id,title,prompt_text,prompt_version,part,min_seconds,
                       max_seconds,created_at,purpose,criterion,band,missions_json,tips_json,
                       reference_text)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(task_id) DO UPDATE SET
                       title=excluded.title, prompt_text=excluded.prompt_text,
                       prompt_version=excluded.prompt_version, part=excluded.part,
                       min_seconds=excluded.min_seconds, max_seconds=excluded.max_seconds,
                       purpose=excluded.purpose, criterion=excluded.criterion,
                       band=excluded.band, missions_json=excluded.missions_json,
                       tips_json=excluded.tips_json, reference_text=excluded.reference_text
                   WHERE task.prompt_version != excluded.prompt_version""",
                rows,
            )

    def list_active(self, purpose: TaskPurpose = TaskPurpose.ASSESSMENT) -> list[Task]:
        """Active tasks for one purpose. Assessment by default.

        The default deliberately matches the behaviour before D023: the submission
        screen and every older caller want assessment tasks only, and a practice task
        slipping into that list could be picked as an exam task.
        """
        with self._conn() as c:
            rows = c.execute(
                "SELECT * FROM task WHERE active=1 AND purpose=? ORDER BY task_id",
                (purpose.value,),
            ).fetchall()
        return [self._to_task(r) for r in rows]

    def get(self, task_id: str) -> Task | None:
        with self._conn() as c:
            row = c.execute("SELECT * FROM task WHERE task_id=?", (task_id,)).fetchone()
        return self._to_task(row) if row else None

    @staticmethod
    def _to_task(row: DbRow) -> Task:
        return Task(
            task_id=row["task_id"],
            title=row["title"],
            prompt_text=row["prompt_text"],
            prompt_version=row["prompt_version"],
            part=TaskPart(row["part"]),
            min_seconds=row["min_seconds"],
            max_seconds=row["max_seconds"],
            topic_keywords=tuple(
                k.strip() for k in (row["topic_keywords"] or "").split(",") if k.strip()
            ),
            purpose=TaskPurpose(row["purpose"]),
            criterion=Criterion(row["criterion"]) if row["criterion"] else None,
            band=Band(row["band"]) if row["band"] else None,
            missions=tuple(Mission.model_validate(m) for m in json.loads(row["missions_json"])),
            tips=tuple(json.loads(row["tips_json"])),
            reference_text=row["reference_text"],
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
