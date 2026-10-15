"""Role- and owner-gated history, statistics, export and administration."""

from __future__ import annotations

import hashlib
import json
import secrets
import uuid
from collections import Counter
from dataclasses import asdict
from datetime import UTC, datetime
from typing import Any

from aicefr.auth.service import AuthorizationError, AuthService, ResourceNotFound
from aicefr.contracts import Actor, ActorRole, AuditEvent, ConsentState, ResponseStatus
from aicefr.portal.contracts import AccountChange, AccountCreate, PageQuery, TaskRecord
from aicefr.portal.tasks import TaskRepository
from aicefr.report.contracts import DiagnosticReport
from aicefr.storage.sqlite import ConcurrentResponseUpdate, SQLiteStore

STAFF = frozenset({ActorRole.TEACHER, ActorRole.ADMIN})


class PortalService:
    def __init__(
        self,
        auth: AuthService,
        store: SQLiteStore,
        tasks: TaskRepository,
        accounts: Any | None = None,
    ) -> None:
        self.auth, self.store, self.tasks = auth, store, tasks
        if accounts is None and auth.identity_repository is not None:
            from aicefr.auth.accounts import AccountService

            accounts = AccountService(auth, auth.identity_repository)
        self.identity_accounts = accounts

    def actor(self, token: str, roles: frozenset[ActorRole] | None = None) -> Actor:
        return self.auth.resolve(token, allowed_roles=roles)

    def audit(
        self, actor: Actor, action: str, object_id: str, *, reason: str | None = None
    ) -> None:
        with self.store.transaction() as connection:
            self.store.record_audit(
                connection,
                AuditEvent(
                    event_id=uuid.uuid4().hex,
                    actor_id=actor.actor_id,
                    action=action,
                    object_id=object_id,
                    recorded_at=datetime.now(UTC),
                    reason=reason,
                ),
            )

    @staticmethod
    def _where(owner_id: str | None, query: PageQuery) -> tuple[str, list[Any]]:
        clauses, values = [], []
        if owner_id is not None:
            clauses.append("r.owner_id=?")
            values.append(owner_id)
        for column, value in (("task_id", query.task_id), ("status", query.status)):
            if value is not None:
                if column == "status":
                    ResponseStatus(value)
                clauses.append(f"r.{column}=?")
                values.append(value)
        for operator, value in ((">=", query.since), ("<=", query.until)):
            if value is not None:
                clauses.append(f"julianday(r.created_at){operator}julianday(?)")
                values.append(value.isoformat())
        return (" WHERE " + " AND ".join(clauses) if clauses else ""), values

    def _rows(self, owner_id: str | None, query: PageQuery, *, page: bool = True) -> list[tuple]:
        where, values = self._where(owner_id, query)
        statement = (
            "SELECT r.*, d.report_json FROM responses r "
            "LEFT JOIN diagnostic_reports d ON d.response_id=r.response_id"
            + where
            + " ORDER BY julianday(r.created_at) DESC, r.response_id"
        )
        if page:
            statement += " LIMIT ? OFFSET ?"
            values.extend((query.limit, query.offset))
        return self.store.connection.execute(statement, values).fetchall()

    def _item(self, row: tuple) -> dict[str, Any]:
        response = self.store._response_from_row(row)
        report = DiagnosticReport.model_validate_json(row[12]) if row[12] else None
        return {
            "response_id": response.response_id,
            "owner_id": response.owner_id,
            "task_id": response.task_id,
            "task_version": response.task_version,
            "created_at": response.created_at.isoformat(),
            "status": response.status.value,
            "revision": response.revision,
            "audio_available": response.audio_available,
            "reason": response.status_reason.value if response.status_reason else None,
            "report_available": report is not None,
            "assessment_status": report.assessment_status.value if report else None,
            "overall_score": report.overall_score if report else None,
            "overall_band": report.overall_band.value if report and report.overall_band else None,
            "teacher_verified": report.teacher_verified if report else False,
            "teacher_final_band": (
                report.teacher_final.overall_band.value
                if report and report.teacher_final and report.teacher_final.overall_band
                else None
            ),
            "teacher_action": report.teacher_final.action.value
            if report and report.teacher_final
            else None,
            "source_versions": report.source_versions if report else {},
        }

    def responses(self, token: str, query: PageQuery, *, mine: bool = True) -> dict[str, Any]:
        actor = self.actor(token, frozenset({ActorRole.STUDENT}) if mine else STAFF)
        owner = actor.actor_id if mine else None
        where, values = self._where(owner, query)
        total = self.store.connection.execute(
            "SELECT COUNT(*) FROM responses r" + where, values
        ).fetchone()[0]
        return {
            "items": [self._item(row) for row in self._rows(owner, query)],
            "total": total,
            "limit": query.limit,
            "offset": query.offset,
        }

    def statistics(self, token: str, query: PageQuery, *, mine: bool = False) -> dict[str, Any]:
        actor = self.actor(token, frozenset({ActorRole.STUDENT}) if mine else STAFF)
        items = [
            self._item(row)
            for row in self._rows(actor.actor_id if mine else None, query, page=False)
        ]
        ai = Counter(item["overall_band"] for item in items if item["overall_band"] is not None)
        final = Counter(
            item["teacher_final_band"]
            for item in items
            if item["teacher_verified"] and item["teacher_final_band"] is not None
        )
        by_model: dict[str, list[float]] = {}
        for item in items:
            if item["overall_score"] is not None:
                model = item["source_versions"].get("assessment", "unknown")
                by_model.setdefault(model, []).append(item["overall_score"])
        return {
            "total": len(items),
            "statuses": dict(Counter(item["status"] for item in items)),
            "ai_bands": dict(ai),
            "teacher_final_bands": dict(final),
            "estimated_count": sum(ai.values()),
            "not_evaluated_count": sum(item["overall_score"] is None for item in items),
            "teacher_verified_count": sum(item["teacher_verified"] for item in items),
            "mean_overall_by_model": {
                model: sum(scores) / len(scores) for model, scores in by_model.items()
            },
            "items": list(reversed(items)) if mine else [],
            "note": "AI là ước lượng; band giảng viên được thống kê riêng. "
            "Không có năm điểm tiêu chí hoặc nhãn CEFR ground truth.",
        }

    def response(self, token: str, response_id: str, *, staff: bool = False):
        actor = self.actor(token, STAFF if staff else frozenset({ActorRole.STUDENT}))
        response = self.store.get_response(response_id)
        if response is None or (not staff and response.owner_id != actor.actor_id):
            raise ResourceNotFound("resource unavailable")
        return actor, response

    def history(self, token: str, response_id: str) -> list[dict[str, Any]]:
        self.response(token, response_id, staff=True)
        rows = self.store.connection.execute(
            "SELECT a.event_id,a.actor_id,a.action,a.object_id,a.recorded_at,a.reason,"
            "d.proposed_band,d.final_band,d.old_state,d.new_state FROM audit a "
            "LEFT JOIN review_decisions d ON d.audit_id=a.event_id "
            "WHERE a.object_id=? ORDER BY a.rowid",
            (response_id,),
        ).fetchall()
        entries = [
            dict(
                zip(
                    (
                        "event_id",
                        "actor_id",
                        "action",
                        "object_id",
                        "recorded_at",
                        "reason",
                        "before_band",
                        "after_band",
                        "before_state",
                        "after_state",
                    ),
                    row,
                    strict=True,
                )
            )
            for row in rows
        ]
        previous_seen, previous_band = False, None
        for entry in entries:
            if entry["after_state"] is not None:
                if previous_seen:
                    entry["before_band"] = previous_band
                previous_seen, previous_band = True, entry["after_band"]
        return entries

    def request_review(self, token: str, response_id: str, expected_revision: int, repository):
        from aicefr.contracts import AssessmentStatus, ReasonCode, ReviewCandidate

        actor, response = self.response(token, response_id, staff=True)
        with self.store.transaction():
            if response.revision != expected_revision or response.status in {
                ResponseStatus.RUNNING,
                ResponseStatus.QUEUED,
            }:
                raise ConcurrentResponseUpdate("response revision is stale or processing")
            existing = repository.get(response_id)
            if existing is not None:
                raise ConcurrentResponseUpdate("review candidate already exists")
            row = self.store.connection.execute(
                "SELECT report_json FROM diagnostic_reports WHERE response_id=?", (response_id,)
            ).fetchone()
            if row is None:
                raise ResourceNotFound("report unavailable")
            report = DiagnosticReport.model_validate_json(row[0])
            now = datetime.now(UTC)
            candidate = repository.add(
                ReviewCandidate(
                    response_id=response_id,
                    response_revision=response.revision,
                    assessment_status=AssessmentStatus.REVIEW_REQUIRED,
                    proposed_band=report.overall_band,
                    reasons=(ReasonCode.MANUAL_REVIEW_REQUESTED,),
                    source_versions=report.source_versions,
                    created_at=now,
                    updated_at=now,
                )
            )
            self.audit(actor, "manual_review_requested", response_id)
            return candidate

    def reopen_review(self, token: str, response_id: str, request, repository):
        from aicefr.contracts import ReviewState

        actor, response = self.response(token, response_id, staff=True)
        if not request.reason.strip():
            raise ValueError("reopening a review needs a reason")
        with self.store.transaction() as connection:
            current = repository.get(response_id)
            if current is None:
                raise ResourceNotFound("review unavailable")
            if (
                current.revision != request.expected_revision
                or current.response_revision != response.revision
            ):
                raise ConcurrentResponseUpdate("review revision is stale")
            if current.state not in {
                ReviewState.APPROVED,
                ReviewState.OVERRIDDEN,
                ReviewState.REJECTED,
            }:
                raise ConcurrentResponseUpdate("only final reviews may be reopened")
            connection.execute(
                "UPDATE review_candidates SET state=?, claimed_by=NULL, "
                "revision=revision+1, updated_at=? WHERE response_id=? AND revision=?",
                (ReviewState.PENDING, datetime.now(UTC).isoformat(), response_id, current.revision),
            )
            self.audit(actor, "review_reopened", response_id, reason=request.reason)
            return repository.get(response_id)

    def export_own(self, token: str) -> dict[str, Any]:
        actor = self.actor(token, frozenset({ActorRole.STUDENT}))
        rows = self._rows(actor.actor_id, PageQuery(), page=False)
        items = []
        for row in rows:
            item = self._item(row)
            # Personal export is an explicit public projection. It retains the
            # familiar response/report shape while excluding transcript, audio,
            # evidence text, credential material and provider identifiers.
            raw_report = json.loads(row[12]) if row[12] else None
            item["report"] = self._safe_export_report(raw_report)
            items.append(item)
        consent = self.store.get_consent(actor.actor_id)
        self.audit(actor, "data_exported", actor.actor_id)
        profile = self.identity_accounts.get_profile(token) if self.identity_accounts else None
        connection = self.store.connection
        learning = {}
        for table, columns in (
            (
                "practice_attempts",
                "attempt_id,mission_id,prompt_version,purpose,attempt_state,rules_version,"
                "mission_snapshot,result_json,reasons_json,status,measurements,evidence,revision,"
                "created_at,updated_at",
            ),
            (
                "step_attempts",
                "attempt_id,lesson_id,lesson_version,step_id,rules_version,attempt_state,"
                "round_index,result_json,reasons_json,status,measurements,evidence,revision,"
                "created_at,updated_at",
            ),
            (
                "review_items",
                "review_id,source_attempt,content_key,box,due_at,state,revision,updated_at",
            ),
            (
                "learning_audio_artifacts",
                "artifact_id,attempt_kind,practice_attempt_id,step_attempt_id,content_type,sha256,size_bytes,created_at",
            ),
            (
                "teacher_override_events",
                "event_id,attempt_id,actor_id,old_value,new_value,reason,recorded_at",
            ),
            (
                "step_review_items",
                "review_id,source_step_attempt,content_key,box,due_at,state,revision,updated_at",
            ),
            ("achievements", "code,unlocked_at,seen_at"),
            ("streak_days", "local_date,effort_count"),
        ):
            rows_for_table = connection.execute(
                f"SELECT {columns} FROM {table} WHERE owner_id=? ORDER BY 1", (actor.actor_id,)
            ).fetchall()
            learning[table] = []
            for record in rows_for_table:
                item = dict(zip(columns.split(","), record, strict=True))
                if table in {"practice_attempts", "step_attempts"}:
                    item["measurements"] = self._safe_measurements(item["measurements"])
                    item["evidence"] = self._safe_learning_evidence(item["evidence"])
                    item["result"] = self._safe_learning_payload(item.pop("result_json"))
                    item.pop("result_json", None)
                    if table == "practice_attempts":
                        item["mission_snapshot"] = self._safe_learning_payload(
                            item["mission_snapshot"]
                        )
                    item["reasons"] = self._safe_learning_payload(item.pop("reasons_json"))
                learning[table].append(item)
        study = connection.execute(
            "SELECT s.study_id,e.arm,e.enrolled_at,e.withdrawn_at,v.phase,"
            "v.answers_json,v.submitted_at "
            "FROM study_enrollments e JOIN feedback_studies s ON s.study_id=e.study_id "
            "LEFT JOIN study_surveys v ON v.enrollment_id=e.enrollment_id "
            "WHERE e.participant_id=? ORDER BY s.study_id,v.phase",
            (actor.actor_id,),
        ).fetchall()
        study_data = [
            {
                "study_id": row[0],
                "arm": row[1],
                "enrolled_at": row[2],
                "withdrawn_at": row[3],
                "phase": row[4],
                "answers": self._safe_likert_answers(row[5]) if row[5] else None,
                "submitted_at": row[6],
            }
            for row in study
        ]
        receipts = connection.execute(
            "SELECT r.receipt_id,r.issued_at,o.amount_minor,o.currency,o.state "
            "FROM billing_receipts r JOIN billing_orders o ON o.order_id=r.order_id "
            "WHERE r.account_id=? ORDER BY r.issued_at",
            (actor.actor_id,),
        ).fetchall()
        sessions = connection.execute(
            "SELECT m.device,m.method,m.expires_at,m.revoked_at FROM session_metadata m "
            "JOIN sessions s ON s.token_digest=m.token_digest WHERE s.actor_id=? "
            "ORDER BY m.expires_at",
            (actor.actor_id,),
        ).fetchall()
        consent_events = connection.execute(
            "SELECT consent_version,state,research_allowed,recorded_at,source "
            "FROM consent_events WHERE account_id=? ORDER BY recorded_at,event_id",
            (actor.actor_id,),
        ).fetchall()
        return {
            "actor_id": actor.actor_id,
            "exported_at": datetime.now(UTC).isoformat(),
            "profile": asdict(profile) if profile else None,
            "consent": consent.model_dump(mode="json") if consent else None,
            "consent_history": [
                {
                    "consent_version": row[0],
                    "state": row[1],
                    "research_allowed": bool(row[2]),
                    "recorded_at": row[3],
                    "source": row[4] if row[4] in {"self_service", "admin"} else "other",
                }
                for row in consent_events
            ],
            "sessions": [
                {
                    "device": row[0][:32],
                    "method": row[1] if row[1] in {"password", "google"} else "other",
                    "expires_at": row[2],
                    "revoked_at": row[3],
                }
                for row in sessions
            ],
            "row_count": len(items),
            "responses": items,
            "learning": learning,
            "study_participation": study_data,
            "receipts": [
                {
                    "receipt_id": r[0],
                    "issued_at": r[1],
                    "amount_minor": r[2],
                    "currency": r[3],
                    "state": r[4],
                }
                for r in receipts
            ],
        }

    @staticmethod
    def _safe_measurements(raw: str) -> dict[str, int | float | bool | None]:
        try:
            values = json.loads(raw)
        except (TypeError, json.JSONDecodeError):
            return {}
        if not isinstance(values, dict):
            return {}
        return {
            key: value
            for key, value in values.items()
            if isinstance(key, str)
            and len(key) <= 48
            and not any(
                word in key.lower() for word in ("secret", "token", "transcript", "path", "id")
            )
            and (value is None or type(value) in {int, float, bool})
        }

    @staticmethod
    def _safe_learning_evidence(raw: str) -> dict[str, Any]:
        try:
            evidence = json.loads(raw)
        except (TypeError, json.JSONDecodeError):
            return {}
        if not isinstance(evidence, dict):
            return {}
        safe: dict[str, Any] = {}
        for key, value in evidence.items():
            if (
                not isinstance(key, str)
                or len(key) > 48
                or any(
                    word in key.lower()
                    for word in ("secret", "token", "transcript", "provider", "path", "nonce")
                )
            ):
                continue
            if type(value) in {int, float, bool} or value is None:
                safe[key] = value
            elif key in {"pattern", "error_code", "status", "reason_code", "kind"} and isinstance(
                value, str
            ):
                safe[key] = value[:64]
            elif key == "examples" and isinstance(value, list):
                safe[key] = [
                    {
                        nested_key: nested_value[:64]
                        for nested_key, nested_value in example.items()
                        if nested_key in {"expected", "heard", "pattern"}
                        and isinstance(nested_value, str)
                    }
                    for example in value[:5]
                    if isinstance(example, dict)
                ]
        return safe

    @classmethod
    def _safe_learning_payload(cls, raw: str | None) -> Any:
        """Keep typed learning facts while excluding transcript/audio and secret fields."""
        if raw is None:
            return None
        try:
            value = json.loads(raw)
        except (TypeError, json.JSONDecodeError):
            return None

        def project(item: Any) -> Any:
            if isinstance(item, dict):
                projected = {}
                for key, child in item.items():
                    if not isinstance(key, str) or len(key) > 64:
                        continue
                    lowered = key.lower()
                    if any(
                        word in lowered
                        for word in (
                            "secret",
                            "token",
                            "transcript",
                            "provider",
                            "path",
                            "nonce",
                            "audio",
                            "blob",
                            "heard_text",
                            "heard_token",
                        )
                    ):
                        continue
                    projected[key] = project(child)
                return projected
            if isinstance(item, list):
                return [project(child) for child in item[:512]]
            if isinstance(item, str):
                return item[:2_048]
            if item is None or type(item) in {bool, int, float}:
                return item
            return None

        return project(value)

    @staticmethod
    def _safe_likert_answers(raw: str) -> dict[str, int]:
        try:
            answers = json.loads(raw)
        except (TypeError, json.JSONDecodeError):
            return {}
        if not isinstance(answers, dict):
            return {}
        return {
            key: value
            for key, value in answers.items()
            if key in {"q1", "q2", "q3", "q4", "q5"} and type(value) is int and 1 <= value <= 5
        }

    @staticmethod
    def _safe_export_report(report: dict[str, Any] | None) -> dict[str, Any] | None:
        if report is None:
            return None
        keys = {
            "response_id",
            "assessment_status",
            "overall_score",
            "overall_band",
            "teacher_verified",
            "teacher_final",
            "source_versions",
            "limitations",
            "criteria",
            "interaction",
            "generated_at",
            "rubric_version",
        }
        result = {key: value for key, value in report.items() if key in keys}
        # Evidence may contain transcript fragments or media references. Keep only
        # the criterion-level score/coverage and summary labels.
        criteria = result.get("criteria")
        if isinstance(criteria, list):
            result["criteria"] = [
                {
                    k: v
                    for k, v in item.items()
                    if k in {"criterion", "score", "band", "coverage", "status"}
                }
                for item in criteria
                if isinstance(item, dict)
            ]
        return result

    def profile(self, token: str) -> dict[str, Any]:
        actor = self.actor(token, frozenset({ActorRole.STUDENT}))
        rows = self._rows(actor.actor_id, PageQuery(), page=False)
        latest = next((row for row in rows if row[12]), None)
        report = DiagnosticReport.model_validate_json(latest[12]) if latest else None
        return {
            "actor_id": actor.actor_id,
            "latest_response_id": report.response_id if report else None,
            "overall_score": report.overall_score if report else None,
            "overall_band": report.overall_band.value if report and report.overall_band else None,
            "coverage": [row.model_dump(mode="json") for row in report.criteria] if report else [],
            "interaction": {"value": None, "reason": "insufficient_evidence"},
            "teacher_verified": report.teacher_verified if report else False,
        }

    def research_export(self, token: str, consent_version: str) -> dict[str, Any]:
        actor = self.actor(token, frozenset({ActorRole.ADMIN}))
        allowed = {
            row[0]
            for row in self.store.connection.execute(
                "SELECT participant_id FROM consents WHERE state=? AND research_allowed=1 "
                "AND consent_version=?",
                (ConsentState.ACTIVE, consent_version),
            )
        }
        salt = secrets.token_bytes(32)
        items = []
        for row in self._rows(None, PageQuery(), page=False):
            item = self._item(row)
            if item["owner_id"] not in allowed:
                continue
            participant = hashlib.sha256(salt + item["owner_id"].encode()).hexdigest()[:24]
            items.append(
                {
                    "participant_id": participant,
                    "task_id": item["task_id"],
                    "task_version": item["task_version"],
                    "assessment_status": item["assessment_status"],
                    "overall_score": item["overall_score"],
                    "overall_band": item["overall_band"],
                    "teacher_final_band": item["teacher_final_band"],
                    "teacher_verified": item["teacher_verified"],
                    "source_versions": item["source_versions"],
                }
            )
        self.audit(actor, "research_exported", "research-export", reason=f"rows={len(items)}")
        return {
            "exported_at": datetime.now(UTC).isoformat(),
            "consent_version": consent_version,
            "accounts_allowing_research": len(allowed),
            "row_count": len(items),
            "rows": items,
            "note": "Không gồm audio, transcript, credential hoặc owner ID. "
            "Mã participant chỉ liên kết trong một lần export; chưa phải validation CEFR.",
        }

    def accounts(self, token: str) -> list[dict[str, Any]]:
        self.actor(token, frozenset({ActorRole.ADMIN}))
        rows = self.store.connection.execute(
            "SELECT actor_id,role,disabled,failed_attempts,locked_until FROM accounts "
            "ORDER BY actor_id"
        ).fetchall()
        return [
            {
                "actor_id": row[0],
                "role": row[1],
                "disabled": bool(row[2]),
                "failed_attempts": row[3],
                "locked_until": row[4],
            }
            for row in rows
        ]

    def create_account(self, token: str, request: AccountCreate) -> dict[str, Any]:
        if self.identity_accounts is None:
            raise AuthorizationError("identity account service unavailable")
        created = self.identity_accounts.create_legacy_account(
            token,
            request.actor_id,
            request.role,
            request.password.get_secret_value(),
        )
        return {
            "actor_id": created.actor_id,
            "role": created.role.value,
            "temporary_password_required": created.temporary_password_required,
        }

    def change_account(self, token: str, actor_id: str, request: AccountChange) -> dict[str, Any]:
        if self.identity_accounts is None:
            raise AuthorizationError("identity account service unavailable")
        change = getattr(self.identity_accounts, "change_legacy_account", None)
        if change is None:
            raise AuthorizationError("identity account service unavailable")
        return change(token, actor_id, request.disabled, request.unlock)

    def task_list(self, token: str, *, admin: bool = False) -> list[dict[str, Any]]:
        self.actor(token, frozenset({ActorRole.ADMIN}) if admin else None)
        return [task.model_dump(mode="json") for task in self.tasks.list(active_only=not admin)]

    def save_task(self, token: str, task: TaskRecord, expected_revision: int) -> dict[str, Any]:
        actor = self.actor(token, frozenset({ActorRole.ADMIN}))
        return self.tasks.save(actor, task, expected_revision).model_dump(mode="json")

    def audit_entries(self, token: str, query: PageQuery) -> dict[str, Any]:
        self.actor(token, frozenset({ActorRole.ADMIN}))
        rows = self.store.connection.execute(
            "SELECT * FROM audit ORDER BY rowid DESC LIMIT ? OFFSET ?",
            (query.limit, query.offset),
        ).fetchall()
        return {
            "items": [
                dict(
                    zip(
                        ("event_id", "actor_id", "action", "object_id", "recorded_at", "reason"),
                        row,
                        strict=True,
                    )
                )
                for row in rows
            ],
            "total": self.store.connection.execute("SELECT COUNT(*) FROM audit").fetchone()[0],
        }
