"""Versioned speaking prompts and a durable submission gate."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime

from aicefr.api.student import SubmissionError
from aicefr.contracts import Actor, ActorRole, AuditEvent, ReasonCode
from aicefr.portal.contracts import TaskRecord
from aicefr.storage.sqlite import ConcurrentResponseUpdate, SQLiteStore


class TaskRepository:
    def __init__(self, store: SQLiteStore) -> None:
        self.store = store

    def _from_row(self, row: tuple) -> TaskRecord:
        keywords = self.store.connection.execute(
            "SELECT payload FROM runtime_settings WHERE key=?",
            (self._keyword_key(row[0], row[1]),),
        ).fetchone()
        topic_keywords = tuple(json.loads(keywords[0])) if keywords else ()
        return TaskRecord(
            task_id=row[0],
            task_version=row[1],
            title=row[2],
            prompt_text=row[3],
            topic_keywords=topic_keywords,
            min_seconds=row[4],
            max_seconds=row[5],
            active=bool(row[6]),
            revision=row[7],
        )

    @staticmethod
    def _keyword_key(task_id: str, task_version: str) -> str:
        return f"task_topic_keywords:{task_id}:{task_version}"

    @classmethod
    def _store_keywords(cls, connection, task: TaskRecord, actor_id: str, *, insert_only=False):
        query = (
            "INSERT OR IGNORE INTO runtime_settings "
            "(key,payload,revision,version,updated_by,updated_at) VALUES (?,?,?,?,?,?)"
            if insert_only
            else "INSERT INTO runtime_settings "
            "(key,payload,revision,version,updated_by,updated_at) "
            "VALUES (?,?,?,?,?,?) ON CONFLICT(key) DO UPDATE SET "
            "payload=excluded.payload,revision=runtime_settings.revision+1,"
            "version=excluded.version,updated_by=excluded.updated_by,updated_at=excluded.updated_at"
        )
        connection.execute(
            query,
            (
                cls._keyword_key(task.task_id, task.task_version),
                json.dumps(task.topic_keywords, ensure_ascii=False),
                1,
                "task-topic-keywords-v1",
                actor_id,
                datetime.now(UTC).isoformat(),
            ),
        )

    def list(self, *, active_only: bool = False) -> tuple[TaskRecord, ...]:
        where = " WHERE active=1" if active_only else ""
        rows = self.store.connection.execute(
            "SELECT * FROM speaking_tasks" + where + " ORDER BY task_id, task_version"
        ).fetchall()
        return tuple(self._from_row(row) for row in rows)

    def get(self, task_id: str, task_version: str) -> TaskRecord | None:
        row = self.store.connection.execute(
            "SELECT * FROM speaking_tasks WHERE task_id=? AND task_version=?",
            (task_id, task_version),
        ).fetchone()
        return self._from_row(row) if row else None

    def seed(self, task: TaskRecord) -> None:
        with self.store.transaction() as connection:
            inserted = connection.execute(
                "INSERT OR IGNORE INTO speaking_tasks VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    task.task_id,
                    task.task_version,
                    task.title,
                    task.prompt_text,
                    task.min_seconds,
                    task.max_seconds,
                    int(task.active),
                    1,
                    datetime.now(UTC).isoformat(),
                ),
            )
            # Seed metadata belongs only to the task row inserted by this seed.
            # A later configuration load must never rewrite a teacher-managed or
            # already-used version whose keyword metadata predates this field.
            if inserted.rowcount == 1:
                self._store_keywords(connection, task, "system-seed", insert_only=True)

    def seed_demo_task(self, task: TaskRecord) -> None:
        """Upgrade the untouched W3 demo placeholder without rewriting used prompts."""
        current = self.get(task.task_id, task.task_version)
        if (
            task.task_id != "demo-speaking"
            or task.task_version != "1"
            or current is None
            or not current.active
            or current.title != task.task_id
            or current.prompt_text
        ):
            self.seed(task)
            return

        used = self.store.connection.execute(
            "SELECT 1 FROM responses WHERE task_id=? AND task_version=? LIMIT 1",
            (task.task_id, task.task_version),
        ).fetchone()
        system_actor = Actor(actor_id="system-demo-seed", role=ActorRole.ADMIN)
        if used:
            self.save(
                system_actor,
                current.model_copy(update={"active": False}),
                current.revision,
            )
            self.seed(task.model_copy(update={"task_version": "2"}))
            return
        self.save(system_actor, task, current.revision)

    def save(self, actor: Actor, task: TaskRecord, expected_revision: int) -> TaskRecord:
        with self.store.transaction() as connection:
            current = self.get(task.task_id, task.task_version)
            if current is None:
                if expected_revision != 0:
                    raise ConcurrentResponseUpdate("task revision is stale")
                connection.execute(
                    "INSERT INTO speaking_tasks VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        task.task_id,
                        task.task_version,
                        task.title,
                        task.prompt_text,
                        task.min_seconds,
                        task.max_seconds,
                        int(task.active),
                        1,
                        datetime.now(UTC).isoformat(),
                    ),
                )
            else:
                if current.revision != expected_revision:
                    raise ConcurrentResponseUpdate("task revision is stale")
                used = connection.execute(
                    "SELECT 1 FROM responses WHERE task_id=? AND task_version=? LIMIT 1",
                    (task.task_id, task.task_version),
                ).fetchone()
                if used and (
                    current.title,
                    current.prompt_text,
                    current.topic_keywords,
                    current.min_seconds,
                    current.max_seconds,
                ) != (
                    task.title,
                    task.prompt_text,
                    task.topic_keywords,
                    task.min_seconds,
                    task.max_seconds,
                ):
                    raise ConcurrentResponseUpdate("create a new task version for revised wording")
                connection.execute(
                    "UPDATE speaking_tasks SET title=?, prompt_text=?, min_seconds=?, "
                    "max_seconds=?, active=?, revision=revision+1 "
                    "WHERE task_id=? AND task_version=? AND revision=?",
                    (
                        task.title,
                        task.prompt_text,
                        task.min_seconds,
                        task.max_seconds,
                        int(task.active),
                        task.task_id,
                        task.task_version,
                        expected_revision,
                    ),
                )
            self._store_keywords(connection, task, actor.actor_id, insert_only=current is None)
            self.store.record_audit(
                connection,
                AuditEvent(
                    event_id=uuid.uuid4().hex,
                    actor_id=actor.actor_id,
                    action="task_saved",
                    object_id=f"{task.task_id}:{task.task_version}",
                    recorded_at=datetime.now(UTC),
                ),
            )
            result = self.get(task.task_id, task.task_version)
            assert result is not None
            return result

    def require_open(self, task_id: str, task_version: str) -> None:
        task = self.get(task_id, task_version)
        if task is None or not task.active:
            raise SubmissionError(ReasonCode.TASK_NOT_OPEN, "Task is not open for submission")
