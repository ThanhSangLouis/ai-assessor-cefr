"""SQLite-backed application service for blind ratings and learning studies."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from aicefr.research import agreement, assign, reliable_change, study, teacher_time
from aicefr.storage.sqlite import SQLiteStore


class ResearchError(ValueError):
    """Base class for safe research-service request failures."""


class ResearchNotFound(ResearchError):
    """The requested research resource is unavailable to this actor."""


class ResearchConflict(ResearchError):
    """The requested transition conflicts with the current immutable state."""


class ResearchInvalid(ResearchError):
    """The requested research payload is outside its contract."""


def actor_hash(actor_id: str) -> str:
    """Stable internal join key; the unhashed account ID never enters a rating row."""
    return hashlib.sha256(("aicefr-research-rater-v1:" + actor_id).encode()).hexdigest()


class ResearchService:
    """Transactional research operations over the W5 SQLite schema.

    The service stores only the IDs already needed for authorized joins. Public
    blind views are assembled field by field and never pass through DB rows.
    """

    def __init__(self, store: SQLiteStore, tasks) -> None:
        self.store = store
        self.tasks = tasks

    @staticmethod
    def _now() -> str:
        return datetime.now(UTC).isoformat()

    def _audit(self, connection, actor_id: str, action: str, object_id: str, reason=None) -> None:
        from aicefr.contracts import AuditEvent

        self.store.record_audit(
            connection,
            AuditEvent(
                event_id=uuid.uuid4().hex,
                actor_id=actor_id,
                action=action,
                object_id=object_id,
                recorded_at=datetime.now(UTC),
                reason=reason,
            ),
        )

    def audit_action(self, actor_id: str, action: str, object_id: str) -> None:
        with self.store.transaction() as db:
            self._audit(db, actor_id, action, object_id)

    def eligible_responses(self, *, only_new: bool = True) -> list[str]:
        rows = self.store.connection.execute(
            """SELECT r.response_id FROM responses r
               JOIN consents c ON c.participant_id=r.owner_id
               JOIN diagnostic_reports d ON d.response_id=r.response_id
               WHERE r.status='COMPLETED' AND r.audio_deleted_at IS NULL
                 AND c.state='active' AND c.research_allowed=1
                 AND (?=0 OR NOT EXISTS (
                     SELECT 1 FROM rating_assignments a
                     WHERE a.response_id=r.response_id AND a.state!='VOID'))
               ORDER BY r.response_id""",
            (int(only_new),),
        ).fetchall()
        return [row[0] for row in rows]

    def raters(self) -> list[dict[str, str]]:
        rows = self.store.connection.execute(
            "SELECT actor_id,role FROM accounts WHERE disabled=0 AND role IN ('teacher','admin') "
            "ORDER BY actor_id"
        ).fetchall()
        return [{"actor_id": row[0], "role": row[1]} for row in rows]

    def create_batch(
        self,
        actor_id: str,
        *,
        name: str,
        rater_ids: list[str],
        limit: int | None = None,
        only_new: bool = True,
        seed: int,
    ) -> dict[str, Any]:
        if len(name.strip()) < 3 or len(name) > 120:
            raise ResearchInvalid("batch name must contain 3 to 120 characters")
        raters = sorted(set(rater_ids))
        known = {row["actor_id"] for row in self.raters()}
        if len(raters) < 2 or not set(raters) <= known:
            raise ResearchInvalid("at least two active teacher/admin raters are required")
        if limit is not None and not 1 <= limit <= 2000:
            raise ResearchInvalid("limit must be between 1 and 2000")
        if not 0 <= seed <= 2**31 - 1:
            raise ResearchInvalid("seed is outside the supported range")

        pool = self.eligible_responses(only_new=only_new)
        sampled = assign.sample(pool, limit, seed)
        conn = self.store.connection
        exclusions: dict[str, set[str]] = {}
        for response_id, actor_id in conn.execute(
            "SELECT response_id,actor_id FROM machine_seen"
        ).fetchall():
            exclusions.setdefault(response_id, set()).add(actor_id)
        plan = assign.plan(sampled, raters, seed, exclude=exclusions)
        if not plan:
            raise ResearchInvalid("no response has two eligible blind raters")

        batch_id, now = uuid.uuid4().hex, self._now()
        planned_response_count = len({item.response_id for item in plan})
        with self.store.transaction() as db:
            db.execute(
                "INSERT INTO rating_batches VALUES(?,?,?,?,?,?,NULL)",
                (batch_id, "OPEN", seed, "cefr-five-v1", actor_id, now),
            )
            for ordinal, item in enumerate(plan, start=1):
                db.execute(
                    """INSERT INTO rating_assignments
                       (assignment_id,batch_id,response_id,blind_token,ordinal,
                        rater_id_hash,state,created_at) VALUES(?,?,?,?,?,?,?,?)""",
                    (
                        uuid.uuid4().hex,
                        batch_id,
                        item.response_id,
                        secrets.token_urlsafe(32),
                        ordinal,
                        actor_hash(item.rater_id),
                        "OPEN",
                        now,
                    ),
                )
            self._audit(
                db,
                actor_id,
                "rating.batch_create",
                batch_id,
                f"responses={planned_response_count}; seed={seed}; raters={len(raters)}",
            )
        included = {item.response_id for item in plan}
        return {
            "batch_id": batch_id,
            "state": "OPEN",
            "seed": seed,
            "responses": len(included),
            "assignments": len(plan),
            "skipped": len(sampled) - len(included),
        }

    def rater_assignments(self, actor_id: str) -> list[dict[str, Any]]:
        rows = self.store.connection.execute(
            """SELECT a.blind_token,a.ordinal,a.state,b.batch_id,b.state,b.created_at,
                      COUNT(*) OVER (PARTITION BY a.batch_id)
               FROM rating_assignments a JOIN rating_batches b ON b.batch_id=a.batch_id
               WHERE a.rater_id_hash=? ORDER BY b.created_at DESC,a.ordinal""",
            (actor_hash(actor_id),),
        ).fetchall()
        return [
            {
                "token": row[0],
                "position": row[1],
                "state": row[2],
                "batch_id": row[3],
                "batch_state": row[4],
                "total_assignments": row[6],
            }
            for row in rows
        ]

    def _assignment(self, actor_id: str, blind_token: str):
        row = self.store.connection.execute(
            """SELECT a.assignment_id,a.response_id,a.state,a.ordinal,b.batch_id,b.state,
                      r.owner_id,r.task_id,r.task_version,r.blob_id,r.sha256,r.size_bytes,
                      r.audio_deleted_at,t.title,t.prompt_text,t.min_seconds,t.max_seconds
               FROM rating_assignments a
               JOIN rating_batches b ON b.batch_id=a.batch_id
               JOIN responses r ON r.response_id=a.response_id
               LEFT JOIN speaking_tasks t ON t.task_id=r.task_id AND t.task_version=r.task_version
               WHERE a.blind_token=? AND a.rater_id_hash=?""",
            (blind_token, actor_hash(actor_id)),
        ).fetchone()
        if row is None:
            raise ResearchNotFound("blind assignment unavailable")
        if row[12] is not None:
            raise ResearchNotFound("recording unavailable")
        consent = self.store.connection.execute(
            "SELECT state,research_allowed FROM consents WHERE participant_id=?", (row[6],)
        ).fetchone()
        if consent is None or consent != ("active", 1):
            with self.store.transaction() as db:
                db.execute(
                    "UPDATE rating_assignments SET state='VOID' "
                    "WHERE assignment_id=? AND state='OPEN'",
                    (row[0],),
                )
            raise ResearchNotFound("blind assignment unavailable")
        return row

    def blind_sheet(self, actor_id: str, blind_token: str) -> dict[str, Any]:
        row = self._assignment(actor_id, blind_token)
        if row[2] == "VOID":
            raise ResearchNotFound("blind assignment unavailable")
        if row[5] != "OPEN":
            raise ResearchConflict("rating batch is closed")
        seen = self.store.connection.execute(
            "SELECT 1 FROM machine_seen WHERE response_id=? AND actor_id=?", (row[1], actor_id)
        ).fetchone()
        if seen:
            with self.store.transaction() as db:
                db.execute(
                    "UPDATE rating_assignments SET state='VOID' "
                    "WHERE assignment_id=? AND state='OPEN'",
                    (row[0],),
                )
            raise ResearchConflict("machine result has already been seen; sheet is void")
        self.mark_review_started(actor_id, row[1], action="rating")
        if row[2] == "SUBMITTED":
            rating = self.store.connection.execute(
                "SELECT criteria_json,band_half_step,unrateable_reason,rationale,submitted_at "
                "FROM research_ratings WHERE assignment_id=?",
                (row[0],),
            ).fetchone()
            parsed = json.loads(rating[0]) if rating else {}
            rating_view = {
                "criteria": {key: parsed.get(key) for key in agreement.CRITERIA},
                "overall": rating[1],
                "band": parsed.get("_band"),
                "unrateable_reason": rating[2],
                "rationale": rating[3],
                "submitted_at": rating[4],
            }
        else:
            rating_view = None
        return {
            "token": blind_token,
            "position": row[3],
            "adjudication": self._slot(row[0], row[1]) == 3,
            "task": {
                "title": row[13] or "Bài nói",
                "prompt_text": row[14] or "",
                "min_seconds": row[15],
                "max_seconds": row[16],
            },
            "audio_url": f"/api/v1/rating/assignments/{blind_token}/audio",
            "rating": rating_view,
        }

    def _slot(self, assignment_id: str, response_id: str) -> int:
        row = self.store.connection.execute(
            """SELECT COUNT(*) FROM rating_assignments
               WHERE batch_id=(SELECT batch_id FROM rating_assignments WHERE assignment_id=?)
                 AND response_id=? AND state!='VOID' AND ordinal <=
                   (SELECT ordinal FROM rating_assignments WHERE assignment_id=?)""",
            (assignment_id, response_id, assignment_id),
        ).fetchone()
        return int(row[0]) if row else 1

    def audio_ref(self, actor_id: str, blind_token: str):
        row = self._assignment(actor_id, blind_token)
        if row[5] != "OPEN" or row[2] == "VOID":
            raise ResearchNotFound("blind assignment unavailable")
        from aicefr.contracts import BlobRef

        return int(row[3]), BlobRef(blob_id=row[9], sha256=row[10], size_bytes=row[11])

    def submit_rating(
        self,
        actor_id: str,
        blind_token: str,
        *,
        criteria: dict[str, float],
        overall: float | None,
        band: str | None,
        rationale: str,
        unrateable_reason: str | None = None,
    ) -> dict[str, str]:
        row = self._assignment(actor_id, blind_token)
        if row[5] != "OPEN":
            raise ResearchConflict("rating batch is closed")
        if unrateable_reason is None:
            if (
                set(criteria) != set(agreement.CRITERIA)
                or overall is None
                or band not in agreement.BANDS
            ):
                raise ResearchInvalid("five criteria, overall score, and valid band are required")
            values = [overall, *criteria.values()]
            if any(
                not math.isfinite(v) or not 0 <= v <= 6 or abs(v * 2 - round(v * 2)) > 1e-9
                for v in values
            ):
                raise ResearchInvalid("scores must be finite half steps from 0 through 6")
            if not rationale.strip() or len(rationale.strip()) > 300:
                raise ResearchInvalid("a rationale of 1 to 300 characters is required")
        elif unrateable_reason not in {"broken", "inaudible", "off_task"}:
            raise ResearchInvalid("unsupported unrateable reason")
        elif overall is not None or band is not None or criteria:
            raise ResearchInvalid("unrateable submissions cannot contain scores")

        now = self._now()
        assignment_id = row[0]
        failure = None
        with self.store.transaction() as db:
            current = db.execute(
                """SELECT a.state,b.state,c.state,c.research_allowed
                   FROM rating_assignments a JOIN rating_batches b ON b.batch_id=a.batch_id
                   JOIN responses r ON r.response_id=a.response_id
                   JOIN consents c ON c.participant_id=r.owner_id
                   WHERE a.assignment_id=?""",
                (assignment_id,),
            ).fetchone()
            seen = db.execute(
                "SELECT 1 FROM machine_seen WHERE response_id=? AND actor_id=?",
                (row[1], actor_id),
            ).fetchone()
            if current is None or current[2:] != ("active", 1):
                db.execute(
                    "UPDATE rating_assignments SET state='VOID' "
                    "WHERE assignment_id=? AND state='OPEN'",
                    (assignment_id,),
                )
                failure = ResearchConflict("research consent is no longer active; sheet is void")
            elif current[0] != "OPEN" or current[1] != "OPEN":
                failure = ResearchConflict("rating sheet was already submitted or batch is closed")
            elif seen:
                db.execute(
                    "UPDATE rating_assignments SET state='VOID' WHERE assignment_id=?",
                    (assignment_id,),
                )
                failure = ResearchConflict("machine result has already been seen; sheet is void")
            else:
                changed = db.execute(
                    "UPDATE rating_assignments SET state='SUBMITTED' "
                    "WHERE assignment_id=? AND state='OPEN'",
                    (assignment_id,),
                ).rowcount
                if changed != 1:
                    failure = ResearchConflict("rating sheet was already submitted or voided")
                else:
                    payload = dict(criteria)
                    if band is not None:
                        payload["_band"] = band
                    db.execute(
                        "INSERT INTO research_ratings VALUES(?,?,?,?,?,?,?)",
                        (
                            uuid.uuid4().hex,
                            assignment_id,
                            json.dumps(payload, sort_keys=True),
                            overall,
                            unrateable_reason,
                            rationale.strip(),
                            now,
                        ),
                    )
                    self._audit(db, actor_id, "rating.submit", assignment_id)
        if failure is not None:
            raise failure
        self.mark_review_ended(actor_id, row[1], "rating")
        return {"status": "submitted"}

    def adjudication_candidates(self, batch_id: str) -> list[str]:
        rows = self.store.connection.execute(
            """SELECT a.response_id,rr.assignment_id,rr.criteria_json,rr.band_half_step,
                      rr.unrateable_reason,a.rater_id_hash,a.ordinal
               FROM rating_assignments a
               JOIN research_ratings rr ON rr.assignment_id=a.assignment_id
               WHERE a.batch_id=? ORDER BY a.response_id,a.ordinal""",
            (batch_id,),
        ).fetchall()
        grouped: dict[str, list[agreement.Rating]] = {}
        for response_id, _, criteria_json, overall, unrateable, rater_hash, _ in rows:
            data = json.loads(criteria_json)
            grouped.setdefault(response_id, []).append(
                agreement.Rating(
                    rater_id=rater_hash,
                    overall=overall,
                    band=data.get("_band"),
                    criteria={key: data.get(key) for key in agreement.CRITERIA},
                    unscorable=unrateable is not None,
                )
            )
        out = []
        for response_id, ratings in grouped.items():
            existing = self.store.connection.execute(
                """SELECT 1 FROM rating_assignments a
                   LEFT JOIN adjudications d ON d.assignment_id=a.assignment_id
                   WHERE a.batch_id=? AND a.response_id=?
                     AND d.assignment_id IS NOT NULL LIMIT 1""",
                (batch_id, response_id),
            ).fetchone()
            if len(ratings) == 2 and not existing and agreement.needs_adjudication(*ratings):
                out.append(response_id)
        return out

    def create_adjudications(
        self, actor_id: str, batch_id: str, adjudicator_id: str
    ) -> dict[str, int]:
        batch = self.store.connection.execute(
            "SELECT state,seed FROM rating_batches WHERE batch_id=?", (batch_id,)
        ).fetchone()
        if batch is None:
            raise ResearchNotFound("rating batch unavailable")
        if batch[0] != "OPEN":
            raise ResearchConflict("rating batch is closed")
        if adjudicator_id not in {row["actor_id"] for row in self.raters()}:
            raise ResearchInvalid("adjudicator must be an active teacher or admin")
        candidates = self.adjudication_candidates(batch_id)
        skipped_own = skipped_seen = 0
        rows = self.store.connection.execute(
            """SELECT response_id,rater_id_hash FROM rating_assignments WHERE batch_id=?""",
            (batch_id,),
        ).fetchall()
        own = {rid for rid, rater_hash in rows if rater_hash == actor_hash(adjudicator_id)}
        seen = {
            row[0]
            for row in self.store.connection.execute(
                "SELECT response_id FROM machine_seen WHERE actor_id=?", (adjudicator_id,)
            ).fetchall()
        }
        eligible = []
        for response_id in candidates:
            if response_id in own:
                skipped_own += 1
            elif response_id in seen:
                skipped_seen += 1
            else:
                eligible.append(response_id)
        plan = assign.adjudication(eligible, adjudicator_id, batch[1] + 1)
        now = self._now()
        with self.store.transaction() as db:
            next_ordinal = int(
                db.execute(
                    "SELECT COALESCE(MAX(ordinal),0)+1 FROM rating_assignments WHERE batch_id=?",
                    (batch_id,),
                ).fetchone()[0]
            )
            for offset, item in enumerate(plan):
                db.execute(
                    """INSERT INTO rating_assignments
                       (assignment_id,batch_id,response_id,blind_token,ordinal,
                        rater_id_hash,state,created_at) VALUES(?,?,?,?,?,?,?,?)""",
                    (
                        uuid.uuid4().hex,
                        batch_id,
                        item.response_id,
                        secrets.token_urlsafe(32),
                        next_ordinal + offset,
                        actor_hash(item.rater_id),
                        "OPEN",
                        now,
                    ),
                )
            self._audit(db, actor_id, "rating.adjudicate", batch_id, f"created={len(plan)}")
        return {"created": len(plan), "skipped_own": skipped_own, "skipped_seen": skipped_seen}

    def submit_adjudication(
        self,
        actor_id: str,
        blind_token: str,
        *,
        criteria: dict[str, float],
        overall: float | None,
        band: str | None,
        reason: str,
    ) -> dict[str, str]:
        row = self._assignment(actor_id, blind_token)
        if self._slot(row[0], row[1]) != 3:
            raise ResearchNotFound("adjudication assignment unavailable")
        if row[5] != "OPEN":
            raise ResearchConflict("rating batch is closed")
        if (
            set(criteria) != set(agreement.CRITERIA)
            or overall is None
            or band not in agreement.BANDS
        ):
            raise ResearchInvalid("five criteria, overall score, and valid band are required")
        values = [overall, *criteria.values()]
        if any(
            not math.isfinite(v) or not 0 <= v <= 6 or abs(v * 2 - round(v * 2)) > 1e-9
            for v in values
        ):
            raise ResearchInvalid("scores must be finite half steps from 0 through 6")
        if not reason.strip() or len(reason.strip()) > 300:
            raise ResearchInvalid("a rationale of 1 to 300 characters is required")
        now = self._now()
        failure = None
        with self.store.transaction() as db:
            current = db.execute(
                """SELECT a.state,b.state,c.state,c.research_allowed
                   FROM rating_assignments a JOIN rating_batches b ON b.batch_id=a.batch_id
                   JOIN responses r ON r.response_id=a.response_id
                   JOIN consents c ON c.participant_id=r.owner_id
                   WHERE a.assignment_id=?""",
                (row[0],),
            ).fetchone()
            seen = db.execute(
                "SELECT 1 FROM machine_seen WHERE response_id=? AND actor_id=?",
                (row[1], actor_id),
            ).fetchone()
            if current is None or current[2:] != ("active", 1):
                db.execute(
                    "UPDATE rating_assignments SET state='VOID' "
                    "WHERE assignment_id=? AND state='OPEN'",
                    (row[0],),
                )
                failure = ResearchConflict("research consent is no longer active; sheet is void")
            elif current[0] != "OPEN" or current[1] != "OPEN":
                failure = ResearchConflict(
                    "adjudication sheet was already submitted or batch is closed"
                )
            elif seen:
                db.execute(
                    "UPDATE rating_assignments SET state='VOID' WHERE assignment_id=?",
                    (row[0],),
                )
                failure = ResearchConflict("machine result has already been seen; sheet is void")
            else:
                changed = db.execute(
                    "UPDATE rating_assignments SET state='SUBMITTED' "
                    "WHERE assignment_id=? AND state='OPEN'",
                    (row[0],),
                ).rowcount
                if changed != 1:
                    failure = ResearchConflict("adjudication sheet was already submitted or voided")
                else:
                    db.execute(
                        "INSERT INTO adjudications VALUES(?,?,?,?,?,?,?)",
                        (
                            uuid.uuid4().hex,
                            row[0],
                            actor_id,
                            json.dumps({**criteria, "_band": band}, sort_keys=True),
                            overall,
                            reason.strip(),
                            now,
                        ),
                    )
                    self._audit(db, actor_id, "rating.adjudication_submit", row[0])
        if failure is not None:
            raise failure
        self.mark_review_ended(actor_id, row[1], "rating")
        return {"status": "submitted"}

    def list_batches(self) -> list[dict[str, Any]]:
        rows = self.store.connection.execute(
            "SELECT batch_id,state,seed,criteria_version,created_by,created_at,closed_at "
            "FROM rating_batches ORDER BY created_at DESC"
        ).fetchall()
        out = []
        for row in rows:
            counts = self.store.connection.execute(
                "SELECT COUNT(*),SUM(state='SUBMITTED'),SUM(state='VOID') "
                "FROM rating_assignments WHERE batch_id=?",
                (row[0],),
            ).fetchone()
            out.append(
                {
                    "batch_id": row[0],
                    "state": row[1],
                    "seed": row[2],
                    "criteria_version": row[3],
                    "created_by": row[4],
                    "created_at": row[5],
                    "closed_at": row[6],
                    "assignments": counts[0],
                    "submitted": counts[1] or 0,
                    "void": counts[2] or 0,
                    "needs_adjudication": len(self.adjudication_candidates(row[0])),
                }
            )
        return out

    def mark_machine_seen(self, actor_id: str, response_id: str, source: str) -> None:
        now = self._now()
        with self.store.transaction() as db:
            inserted = db.execute(
                "INSERT INTO machine_seen(response_id,actor_id,seen_at,source) VALUES(?,?,?,?) "
                "ON CONFLICT(response_id,actor_id) DO NOTHING",
                (response_id, actor_id, now, source[:80]),
            ).rowcount
            if inserted:
                self._audit(db, actor_id, "machine.result_seen", response_id, source[:80])

    def may_view_machine(self, actor_id: str, response_id: str) -> bool:
        row = self.store.connection.execute(
            """SELECT 1 FROM rating_assignments a JOIN rating_batches b ON b.batch_id=a.batch_id
               WHERE a.response_id=? AND a.rater_id_hash=? AND a.state='OPEN' AND b.state='OPEN'
               LIMIT 1""",
            (response_id, actor_hash(actor_id)),
        ).fetchone()
        return row is None

    def blinded_response_ids(self, actor_id: str) -> set[str]:
        rows = self.store.connection.execute(
            """SELECT DISTINCT a.response_id FROM rating_assignments a
               JOIN rating_batches b ON b.batch_id=a.batch_id
               WHERE a.rater_id_hash=? AND a.state='OPEN' AND b.state='OPEN'""",
            (actor_hash(actor_id),),
        ).fetchall()
        return {row[0] for row in rows}

    def batch_response_ids(self, batch_id: str) -> set[str]:
        rows = self.store.connection.execute(
            "SELECT DISTINCT response_id FROM rating_assignments WHERE batch_id=?", (batch_id,)
        ).fetchall()
        return {row[0] for row in rows}

    def replace_void(self, actor_id: str, batch_id: str, rater_id: str) -> dict[str, int]:
        batch = self.store.connection.execute(
            "SELECT state,seed FROM rating_batches WHERE batch_id=?", (batch_id,)
        ).fetchone()
        if batch is None:
            raise ResearchNotFound("rating batch unavailable")
        if batch[0] != "OPEN":
            raise ResearchConflict("rating batch is closed")
        if rater_id not in {row["actor_id"] for row in self.raters()}:
            raise ResearchInvalid("replacement rater must be an active teacher or admin")
        voided = self.store.connection.execute(
            """SELECT response_id,ordinal FROM rating_assignments
               WHERE batch_id=? AND state='VOID' ORDER BY ordinal""",
            (batch_id,),
        ).fetchall()
        skipped_own = skipped_seen = 0
        slots = []
        for response_id, ordinal in voided:
            already = self.store.connection.execute(
                """SELECT 1 FROM rating_assignments WHERE batch_id=? AND response_id=?
                   AND rater_id_hash=? AND state!='VOID' LIMIT 1""",
                (batch_id, response_id, actor_hash(rater_id)),
            ).fetchone()
            seen = self.store.connection.execute(
                "SELECT 1 FROM machine_seen WHERE response_id=? AND actor_id=?",
                (response_id, rater_id),
            ).fetchone()
            if already:
                skipped_own += 1
                continue
            if seen:
                skipped_seen += 1
                continue
            slots.append((response_id, ordinal))
        plan = assign.reassignment(slots, rater_id, batch[1] + 2)
        now = self._now()
        with self.store.transaction() as db:
            next_ordinal = int(
                db.execute(
                    "SELECT COALESCE(MAX(ordinal),0)+1 FROM rating_assignments WHERE batch_id=?",
                    (batch_id,),
                ).fetchone()[0]
            )
            for offset, item in enumerate(plan):
                db.execute(
                    """INSERT INTO rating_assignments
                       (assignment_id,batch_id,response_id,blind_token,ordinal,
                        rater_id_hash,state,created_at) VALUES(?,?,?,?,?,?,?,?)""",
                    (
                        uuid.uuid4().hex,
                        batch_id,
                        item.response_id,
                        secrets.token_urlsafe(32),
                        next_ordinal + offset,
                        actor_hash(item.rater_id),
                        "OPEN",
                        now,
                    ),
                )
            self._audit(db, actor_id, "rating.replace", batch_id, f"created={len(plan)}")
        return {"created": len(plan), "skipped_own": skipped_own, "skipped_seen": skipped_seen}

    def close_batch(self, actor_id: str, batch_id: str, *, reopen: bool = False) -> dict[str, str]:
        row = self.store.connection.execute(
            "SELECT state FROM rating_batches WHERE batch_id=?", (batch_id,)
        ).fetchone()
        if row is None:
            raise ResearchNotFound("rating batch unavailable")
        target = "OPEN" if reopen else "CLOSED"
        with self.store.transaction() as db:
            db.execute(
                "UPDATE rating_batches SET state=?,closed_at=? WHERE batch_id=?",
                (target, None if reopen else self._now(), batch_id),
            )
            self._audit(db, actor_id, f"rating.batch_{target.lower()}", batch_id)
        return {"batch_id": batch_id, "state": target}

    def rating_report(self, batch_id: str) -> dict[str, Any]:
        batch = self.store.connection.execute(
            "SELECT seed,state,criteria_version FROM rating_batches WHERE batch_id=?",
            (batch_id,),
        ).fetchone()
        if batch is None:
            raise ResearchNotFound("rating batch unavailable")
        rows = self.store.connection.execute(
            """SELECT a.response_id,r.owner_id,r.status,d.report_json,a.ordinal,a.rater_id_hash,
                      rr.criteria_json,rr.band_half_step,rr.unrateable_reason,rr.rationale,
                      ad.criteria_json,ad.band_half_step,ad.reason,ad.adjudicator_id
               FROM rating_assignments a JOIN responses r ON r.response_id=a.response_id
               JOIN consents c ON c.participant_id=r.owner_id
               LEFT JOIN diagnostic_reports d ON d.response_id=r.response_id
               LEFT JOIN research_ratings rr ON rr.assignment_id=a.assignment_id
               LEFT JOIN adjudications ad ON ad.assignment_id=a.assignment_id
               WHERE a.batch_id=? AND a.state!='VOID'
                 AND c.state='active' AND c.research_allowed=1
               ORDER BY a.response_id,a.ordinal""",
            (batch_id,),
        ).fetchall()
        by_response: dict[str, dict[str, Any]] = {}
        owners: set[str] = set()
        for row in rows:
            rid, owner = row[0], row[1]
            owners.add(owner)
            entry = by_response.setdefault(
                rid,
                {"owner": owner, "status": row[2], "report": row[3], "ratings": []},
            )
            if row[6] is not None:
                data = json.loads(row[6])
                entry["ratings"].append(
                    agreement.Rating(
                        rater_id=row[5],
                        overall=row[7],
                        band=data.get("_band"),
                        criteria={key: data.get(key) for key in agreement.CRITERIA},
                        unscorable=row[8] is not None,
                        adjudication=len(entry["ratings"]) >= 2,
                    )
                )
            if row[10] is not None:
                data = json.loads(row[10])
                entry["adjudication"] = agreement.Rating(
                    rater_id=actor_hash(row[13]),
                    overall=row[11],
                    band=data.get("_band"),
                    criteria={key: data.get(key) for key in agreement.CRITERIA},
                    unscorable=False,
                    adjudication=True,
                )
        owner_codes = {owner: f"P{index:03d}" for index, owner in enumerate(sorted(owners), 1)}
        items = []
        for index, (_response_id, row) in enumerate(sorted(by_response.items()), 1):
            ratings = row["ratings"][:2]
            if "adjudication" in row:
                ratings = [*ratings, row["adjudication"]]
            report = json.loads(row["report"]) if row["report"] else {}
            overall = report.get("overall_score")
            band = report.get("overall_band")
            if isinstance(band, dict):
                band = band.get("value")
            items.append(
                agreement.RatedResponse(
                    response_id=f"R{index:03d}",
                    speaker_id=owner_codes[row["owner"]],
                    ratings=tuple(ratings),
                    ai_overall=overall,
                    ai_band=band if band in agreement.BANDS else None,
                    flagged=row["status"] == "REVIEW_REQUIRED",
                )
            )
        return {
            "batch_id": batch_id,
            "state": batch[1],
            "seed": batch[0],
            "config_version": batch[2],
            "report": agreement.agreement_report(items, seed=batch[0]),
            "sample_count": len(items),
            "source": "SQLite research ratings and active research consent",
        }

    def rating_csv(self, batch_id: str) -> str:
        out = io.StringIO(newline="")
        writer = csv.writer(out)
        writer.writerow(
            [
                "speaker_id",
                "response_id",
                "slot",
                "rater_id_hash",
                "overall",
                "band",
                *agreement.CRITERIA,
                "unrateable_reason",
            ]
        )
        rows = self.store.connection.execute(
            """SELECT a.response_id,r.owner_id,
                      ROW_NUMBER() OVER (PARTITION BY a.response_id ORDER BY a.ordinal),
                      a.rater_id_hash,rr.criteria_json,rr.band_half_step,rr.unrateable_reason,
                      ad.criteria_json,ad.band_half_step,ad.reason,ad.adjudicator_id
               FROM rating_assignments a JOIN responses r ON r.response_id=a.response_id
               JOIN consents c ON c.participant_id=r.owner_id
               LEFT JOIN research_ratings rr ON rr.assignment_id=a.assignment_id
               LEFT JOIN adjudications ad ON ad.assignment_id=a.assignment_id
               WHERE a.batch_id=? AND a.state!='VOID'
                 AND c.state='active' AND c.research_allowed=1
               ORDER BY r.owner_id,a.response_id,a.ordinal""",
            (batch_id,),
        ).fetchall()
        owner_ids = sorted({row[1] for row in rows})
        pseudonyms = {owner_id: f"P{index:03d}" for index, owner_id in enumerate(owner_ids, 1)}
        response_codes = {
            rid: f"R{index:03d}" for index, rid in enumerate(sorted({row[0] for row in rows}), 1)
        }
        for row in rows:
            rating_json = row[4] or row[7]
            data = json.loads(rating_json) if rating_json else {}
            rater_hash = row[3] if row[4] else actor_hash(row[10]) if row[7] else ""
            writer.writerow(
                [
                    pseudonyms.get(row[1], ""),
                    response_codes[row[0]],
                    row[2],
                    rater_hash[:12],
                    row[5] if row[4] else row[8],
                    data.get("_band", ""),
                    *(data.get(key, "") for key in agreement.CRITERIA),
                    row[6] or row[9] or "",
                ]
            )
        return "\ufeff" + out.getvalue()

    def mark_review_started(
        self, actor_id: str, response_id: str, *, action: str = "decision"
    ) -> None:
        if action not in {"decision", "rating"}:
            raise ResearchInvalid("unsupported review session type")
        with self.store.transaction() as db:
            opened = db.execute(
                "SELECT 1 FROM review_sessions "
                "WHERE response_id=? AND reviewer_id=? AND state='OPEN' LIMIT 1",
                (response_id, actor_id),
            ).fetchone()
            if opened:
                return
            db.execute(
                "INSERT INTO review_sessions"
                "(session_id,response_id,reviewer_id,started_at,ended_at,action,state) "
                "VALUES(?,?,?, ?,NULL,?,'OPEN')",
                (uuid.uuid4().hex, response_id, actor_id, self._now(), action),
            )

    def mark_review_ended(self, actor_id: str, response_id: str, action: str) -> None:
        with self.store.transaction() as db:
            db.execute(
                """UPDATE review_sessions SET ended_at=?,action=?,state='CLOSED'
                   WHERE session_id=(SELECT session_id FROM review_sessions
                     WHERE response_id=? AND reviewer_id=? AND state='OPEN'
                     ORDER BY started_at DESC LIMIT 1)""",
                (self._now(), action[:40], response_id, actor_id),
            )

    def teacher_time_report(self) -> dict[str, Any]:
        now = datetime.now(UTC)
        cutoff = (now - timedelta(minutes=teacher_time.IDLE_CAP_MINUTES)).isoformat()
        with self.store.transaction() as db:
            expired = db.execute(
                "SELECT session_id,response_id,reviewer_id,action FROM review_sessions "
                "WHERE state='OPEN' AND started_at<=?",
                (cutoff,),
            ).fetchall()
            for session_id, response_id, reviewer_id, action in expired:
                if action not in {"rating", "decision"}:
                    active_rating = db.execute(
                        """SELECT 1 FROM rating_assignments WHERE response_id=?
                           AND rater_id_hash=? AND state='OPEN' LIMIT 1""",
                        (response_id, actor_hash(reviewer_id)),
                    ).fetchone()
                    action = "rating" if active_rating else "decision"
                db.execute(
                    "UPDATE review_sessions SET ended_at=?,action=?,state='CLOSED' "
                    "WHERE session_id=? AND state='OPEN'",
                    (now.isoformat(), action, session_id),
                )
        review_rows = self.store.connection.execute(
            """SELECT s.started_at,s.ended_at,s.action FROM review_sessions s
               JOIN responses r ON r.response_id=s.response_id
               JOIN consents c ON c.participant_id=r.owner_id
               WHERE s.state='CLOSED' AND s.action='decision'
                 AND c.state='active' AND c.research_allowed=1"""
        ).fetchall()
        rating_rows = self.store.connection.execute(
            """SELECT s.started_at,s.ended_at,s.action FROM review_sessions s
               JOIN responses r ON r.response_id=s.response_id
               JOIN consents c ON c.participant_id=r.owner_id
               WHERE s.state='CLOSED' AND s.action='rating'
                 AND c.state='active' AND c.research_allowed=1"""
        ).fetchall()
        assisted, idle_assisted = teacher_time.session_minutes(
            [{"opened_at": row[0], "decided_at": row[1], "action": row[2]} for row in review_rows]
        )
        manual, idle_manual = teacher_time.capped(
            [teacher_time._minutes(row[0], row[1]) for row in rating_rows]
        )
        counts = self.store.connection.execute(
            """SELECT COUNT(*),SUM(CASE WHEN r.status='COMPLETED' THEN 1 ELSE 0 END)
               FROM responses r JOIN consents c ON c.participant_id=r.owner_id
               WHERE r.status IN ('COMPLETED','REVIEW_REQUIRED')
                 AND c.state='active' AND c.research_allowed=1"""
        ).fetchone()
        n = int(counts[0] or 0)
        alone = int(counts[1] or 0)
        kept = self.store.connection.execute(
            """SELECT COUNT(DISTINCT d.response_id) FROM review_decisions d
               JOIN responses r ON r.response_id=d.response_id
               JOIN consents c ON c.participant_id=r.owner_id
               WHERE d.final_band IS NOT NULL AND c.state='active' AND c.research_allowed=1"""
        ).fetchone()[0]
        decisions = self.store.connection.execute(
            """SELECT COUNT(DISTINCT d.response_id) FROM review_decisions d
               JOIN responses r ON r.response_id=d.response_id
               JOIN consents c ON c.participant_id=r.owner_id
               WHERE d.action IN ('approve','correct','reject')
                 AND c.state='active' AND c.research_allowed=1"""
        ).fetchone()[0]
        result = teacher_time.kpi(
            assisted, idle_assisted, manual, alone, n, int(kept or 0), int(decisions or 0)
        )
        result["source"] = "research-consented review sessions and assessment responses"
        for key in ("review_with_machine", "rating_without_machine"):
            result[key]["status"] = (
                "available" if result[key]["median_minutes"] is not None else "insufficient_data"
            )
        return result

    def create_study(self, actor_id: str, title: str, seed: int, min_days: int) -> dict[str, Any]:
        if not title.strip() or len(title) > 120 or not 0 <= seed <= 2**31 - 1:
            raise ResearchInvalid("invalid study title or seed")
        if not 1 <= min_days <= 365:
            raise ResearchInvalid("min_days must be from 1 through 365")
        active = self.store.connection.execute(
            "SELECT 1 FROM feedback_studies WHERE state IN ('RUNNING','SURVEY') LIMIT 1"
        ).fetchone()
        if active:
            raise ResearchConflict("another feedback study is active")
        study_id, now = uuid.uuid4().hex, self._now()
        with self.store.transaction() as db:
            db.execute(
                "INSERT INTO feedback_studies VALUES(?,?,?,?,?,?,?,NULL)",
                (
                    study_id,
                    title.strip(),
                    "DRAFT",
                    seed,
                    json.dumps({"min_days": min_days}),
                    actor_id,
                    now,
                ),
            )
            self._audit(db, actor_id, "study.create", study_id)
        return {"study_id": study_id, "state": "DRAFT", "seed": seed, "min_days": min_days}

    def start_study(self, actor_id: str, study_id: str) -> dict[str, Any]:
        row = self.store.connection.execute(
            "SELECT state,seed FROM feedback_studies WHERE study_id=?", (study_id,)
        ).fetchone()
        if row is None:
            raise ResearchNotFound("study unavailable")
        if row[0] != "DRAFT":
            raise ResearchConflict("only a draft study can start")
        participants = self.store.connection.execute(
            """SELECT a.actor_id FROM accounts a JOIN consents c ON c.participant_id=a.actor_id
               WHERE a.role='student' AND a.disabled=0 AND c.state='active'
                 AND c.research_allowed=1 ORDER BY a.actor_id"""
        ).fetchall()
        ids = [item[0] for item in participants]
        if len(ids) < study.MIN_PARTICIPANTS:
            raise ResearchInvalid("at least four consenting active students are required")
        arms = study.assign_arms(ids, row[1])
        now = self._now()
        with self.store.transaction() as db:
            db.execute(
                "UPDATE feedback_studies SET state='RUNNING' WHERE study_id=? AND state='DRAFT'",
                (study_id,),
            )
            for number, participant_id in enumerate(sorted(ids), 1):
                db.execute(
                    "INSERT INTO study_enrollments VALUES(?,?,?,?,?,?,NULL)",
                    (
                        uuid.uuid4().hex,
                        study_id,
                        participant_id,
                        f"P{number:03d}",
                        arms[participant_id],
                        now,
                    ),
                )
            self._audit(
                db, actor_id, "study.start", study_id, f"participants={len(ids)}; seed={row[1]}"
            )
        return {"study_id": study_id, "state": "RUNNING", "participants": len(ids), "seed": row[1]}

    def study_for_participant(self, actor_id: str) -> dict[str, Any] | None:
        row = self.store.connection.execute(
            """SELECT s.study_id,s.state,e.arm,e.enrolled_at,e.pseudonym,
                      e.withdrawn_at,s.config_json
               FROM study_enrollments e JOIN feedback_studies s ON s.study_id=e.study_id
               JOIN consents c ON c.participant_id=e.participant_id
               WHERE e.participant_id=? AND e.withdrawn_at IS NULL
                 AND c.state='active' AND c.research_allowed=1
                 AND s.state IN ('RUNNING','SURVEY') ORDER BY s.created_at DESC LIMIT 1""",
            (actor_id,),
        ).fetchone()
        if row is None:
            return None
        return {
            "study_id": row[0],
            "state": row[1],
            "arm": row[2],
            "enrolled_at": row[3],
            "pseudonym": row[4],
            "config": json.loads(row[6]),
        }

    def feedback_withheld(self, actor_id: str) -> bool:
        enrollment = self.study_for_participant(actor_id)
        return bool(enrollment and enrollment["arm"] == "score_only")

    def submit_survey(self, actor_id: str, phase: str, answers: dict[str, int]) -> dict[str, str]:
        enrollment = self.store.connection.execute(
            """SELECT e.enrollment_id,s.state FROM study_enrollments e
               JOIN feedback_studies s ON s.study_id=e.study_id
               JOIN consents c ON c.participant_id=e.participant_id
               WHERE e.participant_id=? AND e.withdrawn_at IS NULL
                 AND c.state='active' AND c.research_allowed=1
                 AND s.state IN ('RUNNING','SURVEY') ORDER BY s.created_at DESC LIMIT 1""",
            (actor_id,),
        ).fetchone()
        if enrollment is None:
            raise ResearchNotFound("active study participation unavailable")
        if phase not in {"pre", "post"} or set(answers) != set(study.SURVEY_KEYS):
            raise ResearchInvalid("survey phase and five answer keys are required")
        if any(type(value) is not int or not 1 <= value <= 5 for value in answers.values()):
            raise ResearchInvalid("survey answers must be integers from 1 through 5")
        try:
            with self.store.transaction() as db:
                db.execute(
                    "INSERT INTO study_surveys VALUES(?,?,?,?,?)",
                    (
                        uuid.uuid4().hex,
                        enrollment[0],
                        phase,
                        json.dumps(answers, sort_keys=True),
                        self._now(),
                    ),
                )
                self._audit(db, actor_id, "study.survey", enrollment[0], phase)
        except Exception as error:
            if "UNIQUE constraint failed" in str(error):
                raise ResearchConflict("survey phase already submitted") from error
            raise
        return {"status": "submitted"}

    def set_study_state(self, actor_id: str, study_id: str, state: str) -> dict[str, str]:
        if state not in {"SURVEY", "CLOSED"}:
            raise ResearchInvalid("study state transition is unsupported")
        row = self.store.connection.execute(
            "SELECT state FROM feedback_studies WHERE study_id=?", (study_id,)
        ).fetchone()
        if row is None:
            raise ResearchNotFound("study unavailable")
        allowed = {"RUNNING": {"SURVEY", "CLOSED"}, "SURVEY": {"CLOSED"}}
        if state not in allowed.get(row[0], set()):
            raise ResearchConflict("study state transition is not allowed")
        with self.store.transaction() as db:
            db.execute(
                "UPDATE feedback_studies SET state=?,closed_at=? WHERE study_id=?",
                (state, self._now() if state == "CLOSED" else None, study_id),
            )
            self._audit(db, actor_id, "study.state", study_id, state)
        return {"study_id": study_id, "state": state}

    def study_report(self, study_id: str) -> dict[str, Any]:
        row = self.store.connection.execute(
            "SELECT state,seed,config_json FROM feedback_studies WHERE study_id=?", (study_id,)
        ).fetchone()
        if row is None:
            raise ResearchNotFound("study unavailable")
        members = self.store.connection.execute(
            """SELECT e.participant_id,e.pseudonym,e.arm,e.enrolled_at,e.withdrawn_at
               FROM study_enrollments e JOIN consents c ON c.participant_id=e.participant_id
               WHERE e.study_id=? AND e.withdrawn_at IS NULL
                 AND c.state='active' AND c.research_allowed=1 ORDER BY e.pseudonym""",
            (study_id,),
        ).fetchall()
        participants = []
        scores: dict[str, list[tuple[str, float]]] = {}
        surveys: dict[str, dict[str, int]] = {}
        for member in members:
            account_id = member[0]
            participants.append(
                {
                    "account_id": account_id,
                    "arm": member[2],
                    "enrolled_at": member[3],
                    "withdrawn_at": None,
                }
            )
            score_rows = self.store.connection.execute(
                """SELECT r.created_at,d.report_json FROM responses r JOIN diagnostic_reports d
                   ON d.response_id=r.response_id WHERE r.owner_id=? AND r.status='COMPLETED'
                   ORDER BY r.created_at""",
                (account_id,),
            ).fetchall()
            values = []
            for created_at, report_json in score_rows:
                value = json.loads(report_json).get("overall_score")
                if isinstance(value, (int, float)):
                    values.append((created_at, float(value)))
            scores[account_id] = values
            survey_row = self.store.connection.execute(
                """SELECT v.answers_json FROM study_surveys v JOIN study_enrollments e
                   ON e.enrollment_id=v.enrollment_id WHERE e.study_id=? AND e.participant_id=?
                   AND v.phase='post'""",
                (study_id, account_id),
            ).fetchone()
            if survey_row:
                surveys[account_id] = json.loads(survey_row[0])
        config = json.loads(row[2])
        analysis = study.analyse(
            participants,
            scores,
            {},
            surveys,
            int(config.get("min_days", 7)),
            int(row[1]),
        )
        analysis.update(
            status=row[0],
            n=len(members),
            source="completed diagnostic reports and active research consent",
            config_version=study.STUDY_VERSION,
            reason_code=None
            if len(members) >= study.MIN_PARTICIPANTS
            else "insufficient_participants",
        )
        for arm in analysis["arms"].values():
            arm["reason_code"] = (
                None if arm["with_pre_post"] >= 2 else "insufficient_pre_post_sample"
            )
        analysis["difference"]["reason_code"] = (
            None if analysis["difference"]["ci95"] is not None else "insufficient_arm_sample"
        )
        return analysis

    def study_csv(self, study_id: str) -> str:
        rows = self.store.connection.execute(
            """SELECT e.participant_id,e.pseudonym,e.arm,e.enrolled_at
               FROM study_enrollments e JOIN consents c ON c.participant_id=e.participant_id
               WHERE e.study_id=? AND e.withdrawn_at IS NULL
                 AND c.state='active' AND c.research_allowed=1 ORDER BY e.pseudonym""",
            (study_id,),
        ).fetchall()
        out = io.StringIO(newline="")
        writer = csv.writer(out)
        writer.writerow(
            ["participant_code", "arm", "enrolled_at", "pre_score", "post_score", "gain"]
        )
        config_row = self.store.connection.execute(
            "SELECT config_json FROM feedback_studies WHERE study_id=?", (study_id,)
        ).fetchone()
        min_days = int(json.loads(config_row[0]).get("min_days", 7)) if config_row else 7
        for account_id, pseudonym, arm, enrolled_at in rows:
            scored = []
            for created_at, report_json in self.store.connection.execute(
                """SELECT r.created_at,d.report_json FROM responses r JOIN diagnostic_reports d
                   ON d.response_id=r.response_id WHERE r.owner_id=? AND r.status='COMPLETED'
                   ORDER BY r.created_at""",
                (account_id,),
            ).fetchall():
                value = json.loads(report_json).get("overall_score")
                if isinstance(value, (int, float)):
                    scored.append((created_at, float(value)))
            pair = study.pre_post(scored, enrolled_at, min_days)
            writer.writerow(
                [
                    pseudonym,
                    arm,
                    enrolled_at,
                    pair[0] if pair else "",
                    pair[1] if pair else "",
                    pair[1] - pair[0] if pair else "",
                ]
            )
        return "\ufeff" + out.getvalue()

    def manual_sem(
        self, actor_id: str, value: float, source: str, sample_count: int
    ) -> dict[str, Any]:
        if (
            not math.isfinite(value)
            or value <= 0
            or not source.strip()
            or len(source) > 240
            or "rmse" in source.lower()
        ):
            raise ResearchInvalid("positive SEM and a bounded source are required")
        if sample_count < 0:
            raise ResearchInvalid("sample_count cannot be negative")
        now = self._now()
        config_id = uuid.uuid4().hex
        with self.store.transaction() as db:
            db.execute(
                "INSERT INTO sem_configs VALUES(?,?,?,?,?,?,?)",
                (config_id, value, "manual", source.strip(), sample_count, actor_id, now),
            )
            self._audit(
                db, actor_id, "measurement.sem_manual", config_id, f"sample_count={sample_count}"
            )
        return {
            "config_id": config_id,
            "value": value,
            "method": "manual",
            "source": source,
            "sample_count": sample_count,
            "created_at": now,
        }

    def reliable_change_for(self, actor_id: str) -> dict[str, Any]:
        rows = self.store.connection.execute(
            """SELECT r.task_id,r.created_at,d.report_json FROM responses r
               JOIN diagnostic_reports d ON d.response_id=r.response_id
               WHERE r.owner_id=? AND r.status='COMPLETED' ORDER BY r.created_at""",
            (actor_id,),
        ).fetchall()
        score_rows = []
        for _task_id, created_at, report_json in rows:
            value = json.loads(report_json).get("overall_score")
            if isinstance(value, (int, float)):
                score_rows.append((created_at, float(value)))
        sem_row = self.store.connection.execute(
            "SELECT value,method,source,sample_count,created_at FROM sem_configs "
            "ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
        if sem_row:
            sem = float(sem_row[0])
            sem_source, sem_method, sem_count = sem_row[2], sem_row[1], sem_row[3]
        else:
            sem_input = []
            for owner_id, task_id, created_at, report_json in self.store.connection.execute(
                """SELECT r.owner_id,r.task_id,r.created_at,d.report_json FROM responses r
                   JOIN diagnostic_reports d ON d.response_id=r.response_id
                   JOIN accounts a ON a.actor_id=r.owner_id AND a.role='student'
                   JOIN consents c ON c.participant_id=r.owner_id
                   WHERE r.status='COMPLETED' AND c.state='active' AND c.research_allowed=1
                   ORDER BY r.owner_id,r.task_id,r.created_at"""
            ).fetchall():
                report = json.loads(report_json)
                score = report.get("overall_score")
                versions = report.get("source_versions") or {}
                model = versions.get("model_version") or versions.get("assessment") or "unknown"
                if isinstance(score, (int, float)):
                    sem_input.append(
                        {
                            "account_id": owner_id,
                            "task_id": task_id,
                            "created_at": created_at,
                            "overall_0_6": score,
                            "model_version": model,
                        }
                    )
            pairs = reliable_change.retest_pairs(sem_input)
            sem = reliable_change.sem_from_pairs(pairs)
            sem_source = (
                "same-owner/task completed-report retest pairs within 48h"
                if sem
                else "not_measured"
            )
            sem_method, sem_count = (
                ("retest", len(pairs)) if sem is not None else (None, len(pairs))
            )
        result = reliable_change.reliable_change([score for _, score in score_rows], sem)
        result.update(
            n=len(score_rows),
            source=sem_source,
            sem_method=sem_method,
            sem_sample_count=sem_count,
            config_version=reliable_change.RELIABLE_CHANGE_VERSION,
            reason_code="insufficient_scores" if len(score_rows) < 2 else None,
        )
        return result
