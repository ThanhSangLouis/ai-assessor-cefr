"""Typed, bounded persistence ports for the W5 domain table groups."""

from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import dataclass
from typing import Any

from aicefr.storage.sqlite import SQLiteStore


@dataclass(frozen=True, slots=True)
class ProfileRecord:
    account_id: str
    goal: int | None = None
    icon: str | None = None
    color: str | None = None
    updated_at: str = "1970-01-01T00:00:00+00:00"


@dataclass(frozen=True, slots=True)
class LearningPathRecord:
    path_id: str
    title: str
    description: str = ""
    state: str = "draft"
    revision: int = 0
    created_at: str = "1970-01-01T00:00:00+00:00"
    updated_at: str = "1970-01-01T00:00:00+00:00"


@dataclass(frozen=True, slots=True)
class PracticeAttemptRecord:
    attempt_id: str
    owner_id: str
    mission_id: str
    prompt_version: str
    status: str
    measurements: dict[str, Any]
    evidence: dict[str, Any]
    created_at: str
    updated_at: str


@dataclass(frozen=True, slots=True)
class ResearchRatingRecord:
    rating_id: str
    assignment_id: str
    criteria: dict[str, Any]
    band_half_step: float | None
    unrateable_reason: str | None
    rationale: str
    submitted_at: str


@dataclass(frozen=True, slots=True)
class StudyRecord:
    study_id: str
    title: str
    state: str
    seed: int
    config: dict[str, Any]
    created_by: str
    created_at: str


@dataclass(frozen=True, slots=True)
class QuoteRecord:
    quote_id: str
    account_id: str
    plan_code: str
    inputs: dict[str, Any]
    subtotal_minor: int
    discount_minor: int
    credit_minor: int
    total_minor: int
    currency: str
    expires_at: str
    created_at: str


@dataclass(frozen=True, slots=True)
class CleanupIntent:
    resource_kind: str
    resource_id: str
    available_at: float
    owner_id: str | None = None
    intent_id: str = ""
    state: str = "pending"
    attempt: int = 0
    created_at: float = 0.0
    updated_at: float = 0.0
    last_reason: str | None = None


class _Repository:
    def __init__(self, store: SQLiteStore) -> None:
        self._store = store

    @property
    def _db(self) -> sqlite3.Connection:
        return self._store.connection


class ProfileRepository(_Repository):
    def save(self, profile: ProfileRecord) -> ProfileRecord:
        """Insert or update only the caller-selected profile fields."""
        with self._store.transaction() as db:
            db.execute(
                """INSERT INTO account_profiles(account_id,goal,icon,color,updated_at)
                   VALUES(?,?,?,?,?) ON CONFLICT(account_id) DO UPDATE SET
                   goal=excluded.goal,icon=excluded.icon,
                   color=excluded.color,revision=account_profiles.revision+1,
                   updated_at=excluded.updated_at""",
                (profile.account_id, profile.goal, profile.icon, profile.color, profile.updated_at),
            )
        return self.get(profile.account_id)  # type: ignore[return-value]

    def get(self, account_id: str) -> ProfileRecord | None:
        row = self._db.execute(
            "SELECT account_id,goal,icon,color,updated_at FROM account_profiles WHERE account_id=?",
            (account_id,),
        ).fetchone()
        return ProfileRecord(*row) if row else None


class LearningRepository(_Repository):
    def save_path(self, path: LearningPathRecord) -> LearningPathRecord:
        with self._store.transaction() as db:
            db.execute(
                """INSERT INTO learning_paths(
                   path_id,title,description,state,revision,created_at,updated_at)
                   VALUES(?,?,?,?,?,?,?) ON CONFLICT(path_id) DO UPDATE SET title=excluded.title,
                   description=excluded.description,state=excluded.state,
                   revision=learning_paths.revision+1,updated_at=excluded.updated_at""",
                (
                    path.path_id,
                    path.title,
                    path.description,
                    path.state,
                    path.revision,
                    path.created_at,
                    path.updated_at,
                ),
            )
        return self.get_path(path.path_id)  # type: ignore[return-value]

    def get_path(self, path_id: str) -> LearningPathRecord | None:
        row = self._db.execute(
            "SELECT path_id,title,description,state,revision,created_at,updated_at "
            "FROM learning_paths WHERE path_id=?",
            (path_id,),
        ).fetchone()
        return LearningPathRecord(*row) if row else None

    def save_practice_attempt(self, attempt: PracticeAttemptRecord) -> None:
        with self._store.transaction() as db:
            db.execute(
                """INSERT INTO practice_attempts(
                   attempt_id,owner_id,mission_id,prompt_version,status,
                   measurements,evidence,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)""",
                (
                    attempt.attempt_id,
                    attempt.owner_id,
                    attempt.mission_id,
                    attempt.prompt_version,
                    attempt.status,
                    json.dumps(attempt.measurements, sort_keys=True),
                    json.dumps(attempt.evidence, sort_keys=True),
                    attempt.created_at,
                    attempt.updated_at,
                ),
            )

    def get_practice_attempt(self, attempt_id: str) -> PracticeAttemptRecord | None:
        row = self._db.execute(
            "SELECT attempt_id,owner_id,mission_id,prompt_version,status,measurements,evidence,"
            "created_at,updated_at FROM practice_attempts WHERE attempt_id=?",
            (attempt_id,),
        ).fetchone()
        if not row:
            return None
        return PracticeAttemptRecord(*row[:5], json.loads(row[5]), json.loads(row[6]), *row[7:])


class RatingRepository(_Repository):
    def save_rating(self, rating: ResearchRatingRecord) -> None:
        with self._store.transaction() as db:
            db.execute(
                "INSERT INTO research_ratings(rating_id,assignment_id,criteria_json,"
                "band_half_step,unrateable_reason,rationale,submitted_at) VALUES(?,?,?,?,?,?,?)",
                (
                    rating.rating_id,
                    rating.assignment_id,
                    json.dumps(rating.criteria, sort_keys=True),
                    rating.band_half_step,
                    rating.unrateable_reason,
                    rating.rationale,
                    rating.submitted_at,
                ),
            )

    def get_rating(self, assignment_id: str) -> ResearchRatingRecord | None:
        row = self._db.execute(
            "SELECT rating_id,assignment_id,criteria_json,band_half_step,unrateable_reason,"
            "rationale,submitted_at FROM research_ratings WHERE assignment_id=?",
            (assignment_id,),
        ).fetchone()
        return ResearchRatingRecord(*row[:2], json.loads(row[2]), *row[3:]) if row else None


class ResearchRepository(_Repository):
    def save_study(self, study: StudyRecord) -> None:
        with self._store.transaction() as db:
            db.execute(
                "INSERT INTO feedback_studies(study_id,title,state,seed,config_json,created_by,"
                "created_at) VALUES(?,?,?,?,?,?,?)",
                (
                    study.study_id,
                    study.title,
                    study.state,
                    study.seed,
                    json.dumps(study.config, sort_keys=True),
                    study.created_by,
                    study.created_at,
                ),
            )

    def get_study(self, study_id: str) -> StudyRecord | None:
        row = self._db.execute(
            "SELECT study_id,title,state,seed,config_json,created_by,created_at "
            "FROM feedback_studies WHERE study_id=?",
            (study_id,),
        ).fetchone()
        return StudyRecord(*row[:4], json.loads(row[4]), *row[5:]) if row else None


class BillingRepository(_Repository):
    def save_quote(self, quote: QuoteRecord) -> None:
        with self._store.transaction() as db:
            db.execute(
                "INSERT INTO billing_quotes(quote_id,account_id,plan_code,inputs_json,"
                "subtotal_minor,discount_minor,credit_minor,total_minor,currency,expires_at,"
                "created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (
                    quote.quote_id,
                    quote.account_id,
                    quote.plan_code,
                    json.dumps(quote.inputs, sort_keys=True),
                    quote.subtotal_minor,
                    quote.discount_minor,
                    quote.credit_minor,
                    quote.total_minor,
                    quote.currency,
                    quote.expires_at,
                    quote.created_at,
                ),
            )

    def get_quote(self, quote_id: str) -> QuoteRecord | None:
        row = self._db.execute(
            "SELECT quote_id,account_id,plan_code,inputs_json,subtotal_minor,discount_minor,"
            "credit_minor,total_minor,currency,expires_at,created_at FROM billing_quotes "
            "WHERE quote_id=?",
            (quote_id,),
        ).fetchone()
        return QuoteRecord(*row[:3], json.loads(row[3]), *row[4:]) if row else None


class CleanupRepository(_Repository):
    def enqueue(self, intent: CleanupIntent) -> CleanupIntent:
        intent_id = intent.intent_id or uuid.uuid4().hex
        created = intent.created_at or intent.available_at
        updated = intent.updated_at or created
        with self._store.transaction() as db:
            db.execute(
                """INSERT INTO cleanup_intents(
                   intent_id,owner_id,resource_kind,resource_id,state,attempt,
                   available_at,created_at,updated_at,last_reason) VALUES(?,?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(resource_kind,resource_id) DO NOTHING""",
                (
                    intent_id,
                    intent.owner_id,
                    intent.resource_kind,
                    intent.resource_id,
                    intent.state,
                    intent.attempt,
                    intent.available_at,
                    created,
                    updated,
                    intent.last_reason,
                ),
            )
        row = self._db.execute(
            "SELECT intent_id,owner_id,resource_kind,resource_id,state,attempt,available_at,"
            "created_at,updated_at,last_reason FROM cleanup_intents "
            "WHERE resource_kind=? AND resource_id=?",
            (intent.resource_kind, intent.resource_id),
        ).fetchone()
        return CleanupIntent(
            resource_kind=row[2],
            resource_id=row[3],
            available_at=row[6],
            owner_id=row[1],
            intent_id=row[0],
            state=row[4],
            attempt=row[5],
            created_at=row[7],
            updated_at=row[8],
            last_reason=row[9],
        )

    def pending(self, *, now: float, limit: int = 100) -> tuple[CleanupIntent, ...]:
        if not 1 <= limit <= 500:
            raise ValueError("limit must be between 1 and 500")
        rows = self._db.execute(
            "SELECT intent_id,owner_id,resource_kind,resource_id,state,attempt,available_at,"
            "created_at,updated_at,last_reason FROM cleanup_intents "
            "WHERE state IN ('pending','failed') AND available_at<=? "
            "ORDER BY available_at,created_at LIMIT ?",
            (now, limit),
        ).fetchall()
        return tuple(
            CleanupIntent(
                resource_kind=r[2],
                resource_id=r[3],
                available_at=r[6],
                owner_id=r[1],
                intent_id=r[0],
                state=r[4],
                attempt=r[5],
                created_at=r[7],
                updated_at=r[8],
                last_reason=r[9],
            )
            for r in rows
        )


@dataclass(frozen=True, slots=True)
class RepositoryProviders:
    profiles: ProfileRepository
    learning: LearningRepository
    rating: RatingRepository
    research: ResearchRepository
    billing: BillingRepository
    cleanup: CleanupRepository


def build_providers(store: SQLiteStore) -> RepositoryProviders:
    """Build request-scoped repositories over an injected SQLite store."""
    return RepositoryProviders(
        profiles=ProfileRepository(store),
        learning=LearningRepository(store),
        rating=RatingRepository(store),
        research=ResearchRepository(store),
        billing=BillingRepository(store),
        cleanup=CleanupRepository(store),
    )
