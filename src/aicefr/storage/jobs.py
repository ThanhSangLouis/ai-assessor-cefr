"""SQLite-backed durable jobs with owner, revision, and lease fencing."""

from __future__ import annotations

import sqlite3
import time
import uuid
from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol

from aicefr.contracts import ReasonCode, ResponseStatus


class JobStore(Protocol):
    connection: sqlite3.Connection

    def transaction(self) -> AbstractContextManager[sqlite3.Connection]: ...


@dataclass(frozen=True, slots=True)
class Job:
    job_id: str
    response_id: str
    kind: str
    state: str
    attempt: int
    max_attempts: int
    lease_owner: str | None
    lease_until: float | None
    idempotency_key: str
    schema_version: int
    created_at: float
    updated_at: float
    available_at: float
    last_reason: str | None
    revision: int


class SQLiteJobRepository:
    """Repository for the shared ``durable_jobs`` SQLite contract."""

    def __init__(
        self,
        store: JobStore,
        *,
        clock: Callable[[], float] | None = None,
        random_id: Callable[[], str] | None = None,
    ) -> None:
        self.store = store
        self.connection = store.connection
        self.clock = clock or time.time
        self._random_id = random_id or (lambda: uuid.uuid4().hex)

    def enqueue(
        self,
        response_id: str,
        *,
        kind: str = "assessment",
        max_attempts: int = 3,
        capacity: int | None = None,
    ) -> Job:
        if max_attempts < 1:
            raise ValueError("max_attempts must be positive")
        now = self.clock()
        key = f"{kind}:{response_id}"
        with self.store.transaction() as connection:
            existing = connection.execute(
                "SELECT * FROM durable_jobs WHERE response_id=?", (response_id,)
            ).fetchone()
            if existing is not None:
                return self._from_row(existing)
            if capacity is not None:
                pending = connection.execute(
                    "SELECT COUNT(*) FROM durable_jobs WHERE state IN ('queued','running')"
                ).fetchone()[0]
                if pending >= capacity:
                    raise ValueError("pipeline queue is full")
            connection.execute(
                """INSERT OR IGNORE INTO durable_jobs
                (job_id,response_id,kind,state,attempt,max_attempts,idempotency_key,
                 schema_version,created_at,updated_at,available_at,revision)
                VALUES (?,?,?,'queued',0,?,?,1,?,?,?,0)""",
                (self._random_id(), response_id, kind, max_attempts, key, now, now, now),
            )
            row = connection.execute(
                "SELECT * FROM durable_jobs WHERE response_id=?", (response_id,)
            ).fetchone()
            if row is None:
                raise RuntimeError("job insert did not produce a durable job")
            return self._from_row(row)

    def claim(self, owner: str, *, lease_seconds: float = 30.0) -> Job | None:
        if not owner or lease_seconds <= 0:
            raise ValueError("owner and positive lease_seconds are required")
        now = self.clock()
        with self.store.transaction() as connection:
            row = connection.execute(
                """SELECT * FROM durable_jobs WHERE state='queued' AND available_at<=?
                ORDER BY available_at,created_at,job_id LIMIT 1""",
                (now,),
            ).fetchone()
            if row is None:
                return None
            job = self._from_row(row)
            cursor = connection.execute(
                """UPDATE durable_jobs SET state='running',attempt=attempt+1,
                lease_owner=?,lease_until=?,updated_at=?,revision=revision+1
                WHERE job_id=? AND state='queued' AND revision=? AND available_at<=?""",
                (owner, now + lease_seconds, now, job.job_id, job.revision, now),
            )
            if cursor.rowcount != 1:
                return None
            return self.get(job.job_id, connection=connection)

    def heartbeat(self, job_id: str, owner: str, revision: int, *, lease_seconds: float) -> bool:
        now = self.clock()
        with self.store.transaction() as connection:
            cursor = connection.execute(
                """UPDATE durable_jobs SET lease_until=?,updated_at=?
                WHERE job_id=? AND state='running' AND lease_owner=? AND revision=?
                AND lease_until>?""",
                (now + lease_seconds, now, job_id, owner, revision, now),
            )
            return cursor.rowcount == 1

    def assert_owned(
        self, job_id: str, owner: str, revision: int, response_id: str, response_revision: int
    ) -> None:
        """Raise ``LeaseLost`` unless this live lease owns this RUNNING response revision."""
        now = self.clock()
        row = self.connection.execute(
            """SELECT j.job_id FROM durable_jobs j JOIN responses r
            ON r.response_id=j.response_id
            WHERE j.job_id=? AND j.response_id=? AND j.state='running'
            AND j.lease_owner=? AND j.revision=? AND j.lease_until>?
            AND r.status IN (?,?) AND r.revision=?""",
            (
                job_id,
                response_id,
                owner,
                revision,
                now,
                ResponseStatus.RUNNING,
                ResponseStatus.QUEUED,
                response_revision,
            ),
        ).fetchone()
        if row is None:
            raise LeaseLost("durable job lease or response revision is stale")

    def complete(self, job_id: str, owner: str, revision: int) -> bool:
        now = self.clock()
        with self.store.transaction() as connection:
            cursor = connection.execute(
                """UPDATE durable_jobs SET state='succeeded',lease_owner=NULL,lease_until=NULL,
                updated_at=?,revision=revision+1,last_reason=NULL
                WHERE job_id=? AND state='running' AND lease_owner=? AND revision=?
                AND lease_until>? AND EXISTS (
                    SELECT 1 FROM responses r WHERE r.response_id=durable_jobs.response_id
                    AND r.status IN (?,?,?)
                )""",
                (
                    now,
                    job_id,
                    owner,
                    revision,
                    now,
                    ResponseStatus.COMPLETED,
                    ResponseStatus.REJECTED,
                    ResponseStatus.REVIEW_REQUIRED,
                ),
            )
            return cursor.rowcount == 1

    def fail(
        self,
        job_id: str,
        owner: str,
        revision: int,
        reason: str,
        *,
        retry_delay: float = 0.0,
    ) -> bool:
        now = self.clock()
        with self.store.transaction() as connection:
            job_row = connection.execute(
                """SELECT * FROM durable_jobs WHERE job_id=? AND state='running'
                AND lease_owner=? AND revision=? AND lease_until>?""",
                (job_id, owner, revision, now),
            ).fetchone()
            if job_row is None:
                return False
            job = self._from_row(job_row)
            response = connection.execute(
                "SELECT status,revision FROM responses WHERE response_id=?", (job.response_id,)
            ).fetchone()
            if response is not None and response[0] in (
                ResponseStatus.COMPLETED,
                ResponseStatus.REJECTED,
                ResponseStatus.REVIEW_REQUIRED,
            ):
                connection.execute(
                    """UPDATE durable_jobs SET state='succeeded',lease_owner=NULL,lease_until=NULL,
                    updated_at=?,revision=revision+1,last_reason=NULL
                    WHERE job_id=? AND revision=?""",
                    (now, job_id, revision),
                )
                return True
            if job.attempt < job.max_attempts:
                if response is not None and response[0] == ResponseStatus.RUNNING:
                    connection.execute(
                        """UPDATE responses SET status=?,status_reason=NULL,revision=revision+1
                        WHERE response_id=? AND status=? AND revision=?""",
                        (
                            ResponseStatus.QUEUED,
                            job.response_id,
                            ResponseStatus.RUNNING,
                            response[1],
                        ),
                    )
                connection.execute(
                    """UPDATE durable_jobs SET state='queued',lease_owner=NULL,lease_until=NULL,
                    available_at=?,updated_at=?,revision=revision+1,last_reason=?
                    WHERE job_id=? AND state='running' AND lease_owner=? AND revision=?""",
                    (now + max(0.0, retry_delay), now, reason[:500], job_id, owner, revision),
                )
                return True
            connection.execute(
                """UPDATE durable_jobs SET state='failed',lease_owner=NULL,lease_until=NULL,
                updated_at=?,revision=revision+1,last_reason=?
                WHERE job_id=? AND state='running' AND lease_owner=? AND revision=?""",
                (now, reason[:500], job_id, owner, revision),
            )
            if response is not None and response[0] in (
                ResponseStatus.RUNNING,
                ResponseStatus.QUEUED,
            ):
                cursor = connection.execute(
                    """UPDATE responses SET status='FAILED',status_reason=?,revision=revision+1
                    WHERE response_id=? AND status=? AND revision=?""",
                    (
                        ReasonCode.PIPELINE_ENQUEUE_FAILED,
                        job.response_id,
                        response[0],
                        response[1],
                    ),
                )
                if cursor.rowcount == 1:
                    connection.execute(
                        """INSERT INTO audit(event_id,actor_id,action,object_id,recorded_at,reason)
                        VALUES (?,?,?,?,?,?)""",
                        (
                            self._random_id(),
                            "system-pipeline",
                            "pipeline_failed",
                            job.response_id,
                            datetime.now(UTC).astimezone().isoformat(),
                            ReasonCode.PIPELINE_ENQUEUE_FAILED,
                        ),
                    )
            return True

    def recover_expired(self) -> int:
        """Recover expired leases; active leases and their RUNNING responses are untouched."""
        now = self.clock()
        recovered = 0
        with self.store.transaction() as connection:
            rows = connection.execute(
                """SELECT j.*,r.status AS response_status,r.revision AS response_revision
                FROM durable_jobs j JOIN responses r ON r.response_id=j.response_id
                WHERE j.state='running' AND j.lease_until<=?""",
                (now,),
            ).fetchall()
            for row in rows:
                job = self._from_row(row)
                response_status = row[15]
                if response_status in (
                    ResponseStatus.COMPLETED,
                    ResponseStatus.REJECTED,
                    ResponseStatus.REVIEW_REQUIRED,
                ):
                    connection.execute(
                        """UPDATE durable_jobs SET state='succeeded',lease_owner=NULL,
                        lease_until=NULL,updated_at=?,revision=revision+1
                        WHERE job_id=? AND state='running' AND revision=? AND lease_until<=?""",
                        (now, job.job_id, job.revision, now),
                    )
                elif response_status in (ResponseStatus.RUNNING, ResponseStatus.QUEUED):
                    if job.attempt < job.max_attempts:
                        if response_status == ResponseStatus.RUNNING:
                            connection.execute(
                                """UPDATE responses SET status=?,status_reason=NULL,
                                revision=revision+1 WHERE response_id=? AND status=?
                                AND revision=?""",
                                (
                                    ResponseStatus.QUEUED,
                                    job.response_id,
                                    ResponseStatus.RUNNING,
                                    row[16],
                                ),
                            )
                        connection.execute(
                            """UPDATE durable_jobs SET state='queued',lease_owner=NULL,
                            lease_until=NULL,available_at=?,updated_at=?,revision=revision+1,
                            last_reason='worker_lease_expired'
                            WHERE job_id=? AND state='running' AND revision=? AND lease_until<=?""",
                            (now, now, job.job_id, job.revision, now),
                        )
                    else:
                        connection.execute(
                            """UPDATE responses SET status='FAILED',status_reason=?,
                            revision=revision+1 WHERE response_id=? AND status=? AND revision=?""",
                            (
                                ReasonCode.PIPELINE_ENQUEUE_FAILED,
                                job.response_id,
                                response_status,
                                row[16],
                            ),
                        )
                        connection.execute(
                            """INSERT INTO audit(event_id,actor_id,action,object_id,
                            recorded_at,reason)
                            VALUES (?,?,?,?,?,?)""",
                            (
                                self._random_id(),
                                "system-pipeline",
                                "pipeline_failed",
                                job.response_id,
                                datetime.now(UTC).astimezone().isoformat(),
                                ReasonCode.PIPELINE_ENQUEUE_FAILED,
                            ),
                        )
                        connection.execute(
                            """UPDATE durable_jobs SET state='failed',lease_owner=NULL,
                            lease_until=NULL,updated_at=?,revision=revision+1,
                            last_reason='max_attempts_exceeded'
                            WHERE job_id=? AND state='running' AND revision=? AND lease_until<=?""",
                            (now, job.job_id, job.revision, now),
                        )
                else:
                    # A response may have been erased under its retention workflow.
                    connection.execute(
                        """UPDATE durable_jobs SET state='failed',lease_owner=NULL,lease_until=NULL,
                        updated_at=?,revision=revision+1,last_reason='response_unavailable'
                        WHERE job_id=? AND state='running' AND revision=? AND lease_until<=?""",
                        (now, job.job_id, job.revision, now),
                    )
                recovered += 1
        return recovered

    def discover_queued_responses(self, *, max_attempts: int = 3) -> int:
        now = self.clock()
        with self.store.transaction() as connection:
            rows = connection.execute(
                """SELECT r.response_id FROM responses r LEFT JOIN durable_jobs j
                ON j.response_id=r.response_id WHERE r.status=? AND j.job_id IS NULL""",
                (ResponseStatus.QUEUED,),
            ).fetchall()
            for row in rows:
                response_id = row[0]
                connection.execute(
                    """INSERT OR IGNORE INTO durable_jobs
                    (job_id,response_id,kind,state,attempt,max_attempts,idempotency_key,
                     schema_version,created_at,updated_at,available_at,revision)
                    VALUES (?,?,?,'queued',0,?,?,1,?,?,?,0)""",
                    (
                        self._random_id(),
                        response_id,
                        "assessment",
                        max_attempts,
                        f"assessment:{response_id}",
                        now,
                        now,
                        now,
                    ),
                )
            return len(rows)

    def count_pending(self) -> int:
        return self.connection.execute(
            "SELECT COUNT(*) FROM durable_jobs WHERE state IN ('queued','running')"
        ).fetchone()[0]

    def get(self, job_id: str, *, connection: sqlite3.Connection | None = None) -> Job:
        row = (
            (connection or self.connection)
            .execute("SELECT * FROM durable_jobs WHERE job_id=?", (job_id,))
            .fetchone()
        )
        if row is None:
            raise KeyError(job_id)
        return self._from_row(row)

    @staticmethod
    def _from_row(row: sqlite3.Row | tuple) -> Job:
        # SQLiteStore configures tuple rows; preserve compatibility with mappings too.
        if isinstance(row, sqlite3.Row):
            value = row.__getitem__
        else:
            names = (
                "job_id",
                "response_id",
                "kind",
                "state",
                "attempt",
                "max_attempts",
                "lease_owner",
                "lease_until",
                "idempotency_key",
                "schema_version",
                "created_at",
                "updated_at",
                "available_at",
                "last_reason",
                "revision",
            )
            mapping = dict(zip(names, row[: len(names)], strict=True))
            value = mapping.__getitem__
        return Job(
            *(
                value(name)
                for name in (
                    "job_id",
                    "response_id",
                    "kind",
                    "state",
                    "attempt",
                    "max_attempts",
                    "lease_owner",
                    "lease_until",
                    "idempotency_key",
                    "schema_version",
                    "created_at",
                    "updated_at",
                    "available_at",
                    "last_reason",
                    "revision",
                )
            )
        )


class LeaseLost(RuntimeError):
    """The worker no longer owns a live lease for this response."""
