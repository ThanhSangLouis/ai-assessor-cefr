"""Fixture data controls with committed cleanup intents and append-only audit."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import sqlite3
import time
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

from aicefr.auth.service import AuthorizationError, ResourceNotFound
from aicefr.contracts import ActorRole, AuditEvent, BlobRef, ResponseStatus
from aicefr.portal.contracts import DeleteRequest
from aicefr.portal.service import PortalService
from aicefr.storage.blob import BlobStore
from aicefr.storage.sqlite import ConcurrentResponseUpdate


class DataControl:
    def __init__(self, portal: PortalService, blobs: BlobStore) -> None:
        self.portal, self.blobs = portal, blobs

    def _queue_blob(self, response) -> None:
        self._queue_blob_ref(response.blob)

    def _queue_blob_ref(self, blob: BlobRef) -> None:
        connection = self.portal.store.connection
        now = datetime.now(UTC)
        connection.execute(
            "INSERT OR IGNORE INTO blob_deletions VALUES (?,?)",
            (blob.blob_id, now.isoformat()),
        )
        if connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='cleanup_intents'"
        ).fetchone():
            stamp = now.timestamp()
            connection.execute(
                "INSERT INTO cleanup_intents "
                "(intent_id,owner_id,resource_kind,resource_id,state,attempt,available_at,"
                "created_at,updated_at,last_reason) "
                "VALUES (?,?,?,?,?,?,?,?,?,NULL) ON CONFLICT(resource_kind,resource_id) "
                "DO UPDATE SET state='pending',attempt=0,available_at=excluded.available_at,"
                "updated_at=excluded.updated_at,last_reason=NULL",
                (
                    uuid.uuid4().hex,
                    None,
                    "blob",
                    blob.blob_id,
                    "pending",
                    0,
                    stamp,
                    stamp,
                    stamp,
                ),
            )

    def cleanup_pending(self) -> dict:
        """A crash leaves a durable intent; retry never removes a referenced live blob."""
        removed, pending = 0, 0
        store = self.portal.store
        queued = {
            row[0]
            for row in store.connection.execute("SELECT blob_id FROM blob_deletions").fetchall()
        }
        if store.connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='cleanup_intents'"
        ).fetchone():
            queued.update(
                row[0]
                for row in store.connection.execute(
                    "SELECT resource_id FROM cleanup_intents WHERE resource_kind='blob' "
                    "AND state IN ('pending','failed') AND available_at<=?",
                    (datetime.now(UTC).timestamp(),),
                )
            )
        for blob_id in sorted(queued):
            try:
                with store.transaction() as connection:
                    live = connection.execute(
                        "SELECT 1 FROM responses WHERE blob_id=? AND audio_deleted_at IS NULL",
                        (blob_id,),
                    ).fetchone()
                    if (
                        not live
                        and connection.execute(
                            "SELECT 1 FROM sqlite_master WHERE type='table' "
                            "AND name='learning_media'"
                        ).fetchone()
                    ):
                        live = connection.execute(
                            "SELECT 1 FROM learning_media WHERE blob_id=? LIMIT 1", (blob_id,)
                        ).fetchone()
                    if (
                        not live
                        and connection.execute(
                            "SELECT 1 FROM sqlite_master WHERE type='table' "
                            "AND name='learning_audio_artifacts'"
                        ).fetchone()
                    ):
                        live = connection.execute(
                            "SELECT 1 FROM learning_audio_artifacts WHERE blob_id=? LIMIT 1",
                            (blob_id,),
                        ).fetchone()
                    if live:
                        connection.execute("DELETE FROM blob_deletions WHERE blob_id=?", (blob_id,))
                        connection.execute(
                            "UPDATE cleanup_intents SET state='complete',updated_at=?,"
                            "last_reason=NULL WHERE resource_kind='blob' AND resource_id=?",
                            (datetime.now(UTC).timestamp(), blob_id),
                        )
                        continue
                    # Keep the SQLite write lock while unlinking: a learning-media
                    # reference cannot be attached between the reference check and unlink.
                    self.blobs._path(blob_id).unlink(missing_ok=True)
                    connection.execute("DELETE FROM blob_deletions WHERE blob_id=?", (blob_id,))
                    connection.execute(
                        "DELETE FROM cleanup_intents WHERE resource_kind='blob' AND resource_id=?",
                        (blob_id,),
                    )
                removed += 1
            except (OSError, ValueError) as error:
                pending += 1
                with store.transaction() as connection:
                    stamp = datetime.now(UTC).timestamp()
                    connection.execute(
                        "INSERT OR IGNORE INTO cleanup_intents "
                        "(intent_id,owner_id,resource_kind,resource_id,state,attempt,available_at,"
                        "created_at,updated_at,last_reason) VALUES(?,NULL,'blob',?,'pending',"
                        "0,?,?,?,NULL)",
                        (uuid.uuid4().hex, blob_id, stamp, stamp, stamp),
                    )
                    connection.execute(
                        "UPDATE cleanup_intents SET attempt=attempt+1,state=CASE WHEN attempt>=7 "
                        "THEN 'failed' ELSE 'pending' END,available_at=?,updated_at=?,"
                        "last_reason=? WHERE resource_kind='blob' AND resource_id=?",
                        (
                            stamp + 3600,
                            datetime.now(UTC).timestamp(),
                            type(error).__name__,
                            blob_id,
                        ),
                    )
        return {"removed": removed, "pending": pending}

    def delete_response(self, token: str, response_id: str, request: DeleteRequest) -> dict:
        actor, response = self.portal.response(token, response_id)
        if request.confirm_id != response_id:
            raise ValueError("confirmation must match response ID")
        with self.portal.store.transaction():
            current = self.portal.store.get_response(response_id)
            if current is None or current.revision != request.expected_revision:
                raise ConcurrentResponseUpdate("response revision is stale")
            self._delete(current)
            self.portal.audit(actor, "response_deleted", response_id)
        return {"deleted": response_id, "blob_cleanup": self.cleanup_pending()}

    def _delete(self, response) -> None:
        if response.status in {ResponseStatus.QUEUED, ResponseStatus.RUNNING}:
            raise ConcurrentResponseUpdate("cannot delete a response while processing")
        connection = self.portal.store.connection
        self._queue_blob(response)
        for table in ("review_decisions", "review_candidates", "diagnostic_reports", "responses"):
            connection.execute(f"DELETE FROM {table} WHERE response_id=?", (response.response_id,))

    def erasure_preview(self, token: str, actor_id: str) -> dict:
        self.portal.actor(token, frozenset({ActorRole.ADMIN}))
        account = self.portal.store.get_account(actor_id)
        if account is None:
            raise ResourceNotFound("account unavailable")
        if account.actor.role is not ActorRole.STUDENT:
            raise AuthorizationError("only fixture student erasure is supported")
        connection = self.portal.store.connection
        snapshot: dict[str, list] = {}
        specs = {
            "accounts": ("actor_id=?", (actor_id,)),
            "sessions": ("actor_id=?", (actor_id,)),
            "account_profiles": ("account_id=?", (actor_id,)),
            "temporary_passwords": ("account_id=?", (actor_id,)),
            "account_identities": ("account_id=?", (actor_id,)),
            "consents": ("participant_id=?", (actor_id,)),
            "responses": ("owner_id=?", (actor_id,)),
            "practice_attempts": ("owner_id=?", (actor_id,)),
            "step_attempts": ("owner_id=?", (actor_id,)),
            "learning_audio_artifacts": ("owner_id=?", (actor_id,)),
            "teacher_override_events": ("owner_id=?", (actor_id,)),
            "review_items": ("owner_id=?", (actor_id,)),
            "step_review_items": ("owner_id=?", (actor_id,)),
            "achievements": ("owner_id=?", (actor_id,)),
            "streak_days": ("owner_id=?", (actor_id,)),
            "study_enrollments": ("participant_id=?", (actor_id,)),
            "billing_quotes": ("account_id=?", (actor_id,)),
            "billing_orders": ("account_id=?", (actor_id,)),
            "billing_receipts": ("account_id=?", (actor_id,)),
            "licenses": ("account_id=?", (actor_id,)),
            "cleanup_intents": ("owner_id=?", (actor_id,)),
            "entitlements": ("account_id=?", (actor_id,)),
            "consent_events": ("account_id=?", (actor_id,)),
            "activity_events": ("account_id=?", (actor_id,)),
            "machine_seen": ("actor_id=?", (actor_id,)),
            "review_sessions": ("reviewer_id=?", (actor_id,)),
        }
        for table, (where, params) in specs.items():
            if connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
            ).fetchone():
                snapshot[table] = [
                    list(row)
                    for row in connection.execute(
                        f'SELECT * FROM "{table}" WHERE {where} ORDER BY rowid', params
                    )
                ]
        if connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='session_metadata'"
        ).fetchone():
            snapshot["session_metadata"] = [
                list(row)
                for row in connection.execute(
                    "SELECT m.* FROM session_metadata m JOIN sessions s "
                    "ON s.token_digest=m.token_digest WHERE s.actor_id=? ORDER BY m.token_digest",
                    (actor_id,),
                )
            ]
        response_ids = [row[0] for row in snapshot.get("responses", [])]
        if response_ids:
            marks = ",".join("?" for _ in response_ids)
            snapshot["durable_jobs"] = [
                list(row)
                for row in connection.execute(
                    f"SELECT * FROM durable_jobs WHERE response_id IN ({marks}) ORDER BY job_id",
                    response_ids,
                )
            ]
            response_columns = [
                row[1] for row in connection.execute("PRAGMA table_info(responses)")
            ]
            blob_index = response_columns.index("blob_id")
            response_blob_ids = sorted(
                {str(row[blob_index]) for row in snapshot["responses"] if row[blob_index]}
            )
            if response_blob_ids:
                blob_marks = ",".join("?" for _ in response_blob_ids)
                snapshot["blob_deletions"] = [
                    list(row)
                    for row in connection.execute(
                        f"SELECT * FROM blob_deletions WHERE blob_id IN ({blob_marks}) "
                        "ORDER BY blob_id",
                        response_blob_ids,
                    )
                ]
                snapshot["response_cleanup_intents"] = [
                    list(row)
                    for row in connection.execute(
                        f"SELECT * FROM cleanup_intents WHERE resource_kind='blob' "
                        f"AND resource_id IN ({blob_marks}) ORDER BY intent_id",
                        response_blob_ids,
                    )
                ]
            for table, where in (
                ("rating_assignments", f"response_id IN ({marks})"),
                ("review_candidates", f"response_id IN ({marks})"),
                ("review_decisions", f"response_id IN ({marks})"),
                ("review_sessions", f"response_id IN ({marks})"),
            ):
                if connection.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
                ).fetchone():
                    snapshot[table] = [
                        list(row)
                        for row in connection.execute(
                            f'SELECT * FROM "{table}" WHERE {where} ORDER BY rowid', response_ids
                        )
                    ]
            assignment_ids = [row[0] for row in snapshot.get("rating_assignments", [])]
            if assignment_ids:
                marks = ",".join("?" for _ in assignment_ids)
                for table in ("research_ratings", "adjudications"):
                    snapshot[table] = [
                        list(row)
                        for row in connection.execute(
                            f'SELECT * FROM "{table}" WHERE assignment_id IN ({marks}) '
                            "ORDER BY rowid",
                            assignment_ids,
                        )
                    ]
        enrollment_ids = [row[0] for row in snapshot.get("study_enrollments", [])]
        if enrollment_ids:
            marks = ",".join("?" for _ in enrollment_ids)
            snapshot["study_surveys"] = [
                list(row)
                for row in connection.execute(
                    f"SELECT * FROM study_surveys WHERE enrollment_id IN ({marks}) ORDER BY rowid",
                    enrollment_ids,
                )
            ]
        snapshot["audit_object"] = [
            list(row)
            for row in connection.execute(
                "SELECT * FROM audit WHERE object_id IN (SELECT response_id FROM responses "
                "WHERE owner_id=?) "
                "ORDER BY event_id",
                (actor_id,),
            )
        ]
        snapshot["audit_actor"] = [
            list(row)
            for row in connection.execute(
                "SELECT * FROM audit WHERE actor_id=? ORDER BY event_id", (actor_id,)
            )
        ]
        owned_resource_ids = set(response_ids)
        for table, id_column in (
            ("practice_attempts", "attempt_id"),
            ("step_attempts", "attempt_id"),
            ("learning_audio_artifacts", "artifact_id"),
            ("teacher_override_events", "event_id"),
            ("review_items", "review_id"),
            ("step_review_items", "review_id"),
            ("study_enrollments", "enrollment_id"),
            ("billing_quotes", "quote_id"),
            ("billing_orders", "order_id"),
            ("billing_receipts", "receipt_id"),
            ("licenses", "license_id"),
        ):
            columns = [row[1] for row in connection.execute(f'PRAGMA table_info("{table}")')]
            if id_column in columns:
                id_index = columns.index(id_column)
                owned_resource_ids.update(
                    str(row[id_index]) for row in snapshot.get(table, []) if row[id_index]
                )
        for table, id_column in (
            ("rating_assignments", "assignment_id"),
            ("review_candidates", "candidate_id"),
            ("review_decisions", "decision_id"),
            ("review_sessions", "session_id"),
            ("research_ratings", "rating_id"),
            ("adjudications", "adjudication_id"),
        ):
            columns = [row[1] for row in connection.execute(f'PRAGMA table_info("{table}")')]
            if id_column in columns:
                id_index = columns.index(id_column)
                owned_resource_ids.update(
                    str(row[id_index]) for row in snapshot.get(table, []) if row[id_index]
                )
        if owned_resource_ids:
            marks = ",".join("?" for _ in owned_resource_ids)
            snapshot["audit_owned_objects"] = [
                list(row)
                for row in connection.execute(
                    f"SELECT * FROM audit WHERE object_id IN ({marks}) ORDER BY event_id",
                    sorted(owned_resource_ids),
                )
            ]
        snapshot["responses_report"] = [
            list(row)
            for row in connection.execute(
                "SELECT d.response_id,d.report_json FROM diagnostic_reports d JOIN responses r "
                "ON r.response_id=d.response_id WHERE r.owner_id=? ORDER BY d.response_id",
                (actor_id,),
            )
        ]
        fingerprint = hashlib.sha256(
            json.dumps(snapshot, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        response_rows = snapshot.get("responses", [])
        response_columns = [row[1] for row in connection.execute("PRAGMA table_info(responses)")]
        positions = {column: response_columns.index(column) for column in response_columns}
        return {
            "actor_id": actor_id,
            "row_count": len(response_rows),
            "audio_bytes": sum(int(row[positions["size_bytes"]]) for row in response_rows),
            "fingerprint": fingerprint,
            "responses": [
                {
                    "response_id": row[positions["response_id"]],
                    "revision": row[positions["revision"]],
                    "status": row[positions["status"]],
                }
                for row in response_rows
            ],
            "owned_counts": {table: len(rows) for table, rows in snapshot.items()},
            "note": "Thao tác xóa sẽ gỡ thông tin cá nhân, dữ liệu đăng nhập, hồ sơ, bài nộp, "
            "ý kiến khảo sát và lịch sử đồng ý. Nhật ký chỉ giữ lại hành động và thời điểm "
            "với mã tham chiếu không thể truy ngược danh tính. Bản sao lưu không bị thay đổi.",
        }

    def erase(self, token: str, actor_id: str, confirm_id: str, fingerprint: str) -> dict:
        actor = self.portal.actor(token, frozenset({ActorRole.ADMIN}))
        if confirm_id != actor_id:
            raise ValueError("confirmation must match participant ID")
        with self.portal.store.transaction() as connection:
            actor = self.portal.actor(token, frozenset({ActorRole.ADMIN}))
            preview = self.erasure_preview(token, actor_id)
            if fingerprint != preview["fingerprint"]:
                raise ConcurrentResponseUpdate("erasure preview is stale")
            tombstone = (
                "erased-" + hashlib.sha256((actor_id + uuid.uuid4().hex).encode()).hexdigest()[:24]
            )
            intent_id = uuid.uuid4().hex
            stamp = datetime.now(UTC).timestamp()
            resource_id = "privacy-" + intent_id
            connection.execute(
                "INSERT INTO cleanup_intents "
                "(intent_id,owner_id,resource_kind,resource_id,state,attempt,available_at,"
                "created_at,updated_at,last_reason) "
                "VALUES (?,?,?,?,?,?,?,?,?,NULL)",
                (
                    intent_id,
                    actor_id,
                    "privacy_erasure",
                    resource_id,
                    "running",
                    0,
                    stamp,
                    stamp,
                    stamp,
                ),
            )
            if connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='learning_audio_artifacts'"
            ).fetchone():
                for artifact in connection.execute(
                    "SELECT blob_id,sha256,size_bytes FROM learning_audio_artifacts "
                    "WHERE owner_id=?",
                    (actor_id,),
                ).fetchall():
                    self._queue_blob_ref(
                        BlobRef(blob_id=artifact[0], sha256=artifact[1], size_bytes=artifact[2])
                    )
            link_ids: set[tuple[str, str]] = set()
            # Capture only primary IDs of rows directly owned by this actor.
            # Shared lesson/task/unit IDs must not select unrelated audit rows.
            owned_tables = {
                "responses": ("owner_id", "response_id"),
                "practice_attempts": ("owner_id", "attempt_id"),
                "step_attempts": ("owner_id", "attempt_id"),
                "review_items": ("owner_id", "review_id"),
                "study_enrollments": ("participant_id", "enrollment_id"),
                "billing_quotes": ("account_id", "quote_id"),
                "billing_orders": ("account_id", "order_id"),
                "billing_receipts": ("account_id", "receipt_id"),
                "licenses": ("account_id", "license_id"),
            }
            for table, (owner_column, id_column) in owned_tables.items():
                if not connection.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
                ).fetchone():
                    continue
                rows = connection.execute(
                    f'SELECT * FROM "{table}" WHERE "{owner_column}"=?', (actor_id,)
                ).fetchall()
                id_index = [
                    row[1] for row in connection.execute(f'PRAGMA table_info("{table}")')
                ].index(id_column)
                for row in rows:
                    value = row[id_index]
                    if isinstance(value, str):
                        link_ids.add((table, value))
            for response in preview["responses"]:
                response_id = response["response_id"]
                assignment_ids = [
                    row[0]
                    for row in connection.execute(
                        "SELECT assignment_id FROM rating_assignments WHERE response_id=?",
                        (response_id,),
                    )
                ]
                link_ids.update(("rating_assignments", value) for value in assignment_ids)
                if assignment_ids:
                    marks = ",".join("?" for _ in assignment_ids)
                    for table, id_column in (
                        ("research_ratings", "rating_id"),
                        ("adjudications", "adjudication_id"),
                    ):
                        for (value,) in connection.execute(
                            f'SELECT "{id_column}" FROM "{table}" WHERE assignment_id IN ({marks})',
                            assignment_ids,
                        ):
                            link_ids.add((table, value))
                for (value,) in connection.execute(
                    "SELECT session_id FROM review_sessions WHERE response_id=?", (response_id,)
                ):
                    link_ids.add(("review_sessions", value))
            for kind, linked_id in sorted(link_ids):
                connection.execute(
                    "INSERT INTO privacy_erasure_links(intent_id,resource_kind,resource_id) "
                    "VALUES(?,?,?)",
                    (intent_id, kind, linked_id),
                )
            connection.execute(
                "INSERT INTO accounts(actor_id,role,password_hash,disabled) VALUES (?,?,?,1)",
                (tombstone, "student", ""),
            )
            connection.execute(
                "UPDATE study_enrollments SET participant_id=?,pseudonym=?,"
                "withdrawn_at=COALESCE(withdrawn_at,?) WHERE participant_id=?",
                (tombstone, "privacy:" + intent_id, datetime.now(UTC).isoformat(), actor_id),
            )
            connection.execute(
                "DELETE FROM study_surveys WHERE enrollment_id IN (SELECT enrollment_id "
                "FROM study_enrollments WHERE participant_id=?)",
                (tombstone,),
            )
            for table in (
                "billing_quotes",
                "billing_orders",
                "billing_receipts",
                "licenses",
                "entitlements",
            ):
                if connection.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
                ).fetchone():
                    connection.execute(
                        f"UPDATE {table} SET account_id=? WHERE account_id=?", (tombstone, actor_id)
                    )
            connection.execute(
                "UPDATE machine_seen SET actor_id=? WHERE actor_id=?", (tombstone, actor_id)
            )
            connection.execute(
                "UPDATE review_sessions SET reviewer_id=? WHERE reviewer_id=?",
                (tombstone, actor_id),
            )
            audit_rows = connection.execute(
                "SELECT event_id,actor_id,object_id FROM audit WHERE actor_id=? OR object_id=? "
                "OR object_id IN (SELECT resource_id FROM privacy_erasure_links WHERE intent_id=?)",
                (actor_id, actor_id, intent_id),
            ).fetchall()
            for event_id, old_actor_id, old_object_id in audit_rows:
                connection.execute(
                    "UPDATE audit SET actor_id=?,object_id=?,reason=NULL WHERE event_id=?",
                    (
                        "privacy:" + intent_id if old_actor_id == actor_id else old_actor_id,
                        "privacy:" + intent_id
                        if old_object_id == actor_id
                        or any(linked_id == old_object_id for _, linked_id in link_ids)
                        else old_object_id,
                        event_id,
                    ),
                )
            for item in preview["responses"]:
                response_id = item["response_id"]
                response = self.portal.store.get_response(response_id)
                if response is None:
                    continue
                assignments = [
                    row[0]
                    for row in connection.execute(
                        "SELECT assignment_id FROM rating_assignments WHERE response_id=?",
                        (response_id,),
                    )
                ]
                if assignments:
                    marks = ",".join("?" for _ in assignments)
                    connection.execute(
                        f"DELETE FROM research_ratings WHERE assignment_id IN ({marks})",
                        assignments,
                    )
                    connection.execute(
                        f"DELETE FROM adjudications WHERE assignment_id IN ({marks})", assignments
                    )
                    connection.execute(
                        f"DELETE FROM rating_assignments WHERE assignment_id IN ({marks})",
                        assignments,
                    )
                connection.execute(
                    "DELETE FROM review_sessions WHERE response_id=?", (response_id,)
                )
                connection.execute("DELETE FROM machine_seen WHERE response_id=?", (response_id,))
                self._delete(response)
            for table in (
                "step_attempts",
                "achievements",
                "streak_days",
                "review_items",
                "step_review_items",
                "practice_attempts",
            ):
                connection.execute(f"DELETE FROM {table} WHERE owner_id=?", (actor_id,))
            if connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='teacher_override_events'"
            ).fetchone():
                connection.execute(
                    "DELETE FROM teacher_override_events WHERE owner_id=?", (actor_id,)
                )
            connection.execute("DELETE FROM sessions WHERE actor_id=?", (actor_id,))
            connection.execute("DELETE FROM consents WHERE participant_id=?", (actor_id,))
            connection.execute("DELETE FROM consent_events WHERE account_id=?", (actor_id,))
            # Remove mutable identity and activity rows. V10 permits consent-event
            # deletion only while this matching erasure intent is running.
            connection.execute("DELETE FROM account_identities WHERE account_id=?", (actor_id,))
            connection.execute("DELETE FROM account_profiles WHERE account_id=?", (actor_id,))
            connection.execute("DELETE FROM temporary_passwords WHERE account_id=?", (actor_id,))
            connection.execute("DELETE FROM activity_events WHERE account_id=?", (actor_id,))
            # A historical creator/reviewer reference can require a disabled
            # account row to satisfy its FK. Replace any remaining mutable FK
            # alias with the opaque tombstone before deciding whether the row
            # can be removed.
            for table_row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            ).fetchall():
                table = str(table_row[0])
                if table == "accounts":
                    continue
                quoted_table = '"' + table.replace('"', '""') + '"'
                for foreign_key in connection.execute(
                    f"PRAGMA foreign_key_list({quoted_table})"
                ).fetchall():
                    if foreign_key[2] == "accounts" and foreign_key[4] == "actor_id":
                        column = '"' + str(foreign_key[3]).replace('"', '""') + '"'
                        connection.execute(
                            f"UPDATE {quoted_table} SET {column}=? WHERE {column}=?",
                            (tombstone, actor_id),
                        )
            now = datetime.now(UTC).isoformat()
            connection.execute(
                "UPDATE study_enrollments SET withdrawn_at=COALESCE(withdrawn_at,?) "
                "WHERE participant_id=?",
                (now, actor_id),
            )
            connection.execute("DELETE FROM privacy_erasure_links WHERE intent_id=?", (intent_id,))
            connection.execute(
                "UPDATE cleanup_intents SET owner_id=NULL,state='complete',updated_at=? "
                "WHERE intent_id=?",
                (datetime.now(UTC).timestamp(), intent_id),
            )
            # Leave a disabled, credential-scrubbed actor row only when retained
            # append-only or deidentified research rows still have a foreign key to it.
            has_references = False
            for table_row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            ).fetchall():
                table = str(table_row[0])
                if table == "accounts":
                    continue
                quoted_table = '"' + table.replace('"', '""') + '"'
                foreign_keys = connection.execute(
                    f"PRAGMA foreign_key_list({quoted_table})"
                ).fetchall()
                for foreign_key in foreign_keys:
                    if foreign_key[2] != "accounts" or foreign_key[4] != "actor_id":
                        continue
                    # A table may refer to accounts(actor_id) through more than one
                    # column; inspect each matching constraint before deleting the stub.
                    column = foreign_key[3]
                    column_name = column.replace('"', '""')
                    exists = connection.execute(
                        f'SELECT 1 FROM {quoted_table} WHERE "{column_name}"=? LIMIT 1',
                        (actor_id,),
                    ).fetchone()
                    if exists:
                        has_references = True
                        break
                if has_references:
                    break
            if has_references:
                connection.execute(
                    "UPDATE accounts SET disabled=1,password_hash='' WHERE actor_id=?",
                    (actor_id,),
                )
            else:
                connection.execute("DELETE FROM accounts WHERE actor_id=?", (actor_id,))
            self.portal.audit(
                actor,
                "participant_erased",
                "privacy:" + intent_id,
            )
        return {
            "erased": actor_id,
            "row_count": preview["row_count"],
            "blob_cleanup": self.cleanup_pending(),
        }

    def retention(self, token: str, *, days: int = 180, apply: bool = False) -> dict:
        actor = self.portal.actor(token, frozenset({ActorRole.ADMIN}))
        if not 1 <= days <= 36500:
            raise ValueError("retention days must be between 1 and 36500")
        cutoff = datetime.now(UTC) - timedelta(days=days)

        def eligible_responses(connection):
            return connection.execute(
                "SELECT * FROM responses WHERE julianday(created_at)<julianday(?) "
                "AND audio_deleted_at IS NULL AND status NOT IN (?,?)",
                (cutoff.isoformat(), ResponseStatus.RUNNING, ResponseStatus.QUEUED),
            ).fetchall()

        def eligible_attempts(connection, table):
            return connection.execute(
                f"SELECT attempt_id FROM {table} WHERE julianday(created_at)<julianday(?) "
                "AND lower(status) IN ('completed','failed','cancelled','expired','void')",
                (cutoff.isoformat(),),
            ).fetchall()

        rows = eligible_responses(self.portal.store.connection)
        owned_attempts = {}
        for table in ("practice_attempts", "step_attempts"):
            owned_attempts[table] = eligible_attempts(self.portal.store.connection, table)
        override_count = 0
        if owned_attempts["step_attempts"]:
            old_step_ids = [row[0] for row in owned_attempts["step_attempts"]]
            placeholders = ",".join("?" for _ in old_step_ids)
            override_count = self.portal.store.connection.execute(
                "SELECT COUNT(*) FROM teacher_override_events WHERE attempt_id IN ("
                + placeholders
                + ")",
                old_step_ids,
            ).fetchone()[0]
        job_cutoff = cutoff.timestamp()
        old_jobs = self.portal.store.connection.execute(
            "SELECT job_id FROM durable_jobs WHERE state IN ('succeeded','failed') "
            "AND updated_at<?",
            (job_cutoff,),
        ).fetchall()
        old_intents = self.portal.store.connection.execute(
            "SELECT intent_id FROM cleanup_intents WHERE state='complete' AND updated_at<?",
            (job_cutoff,),
        ).fetchall()
        result = {
            "dry_run": not apply,
            "days": days,
            "row_count": len(rows)
            + sum(map(len, owned_attempts.values()))
            + override_count
            + len(old_jobs)
            + len(old_intents),
            "response_ids": [row[0] for row in rows],
            "attempt_ids": {
                table: [row[0] for row in entries] for table, entries in owned_attempts.items()
            },
            "obsolete_job_ids": [row[0] for row in old_jobs],
            "completed_cleanup_ids": [row[0] for row in old_intents],
            "teacher_override_event_count": override_count,
        }
        if not apply:
            return result
        with self.portal.store.transaction() as connection:
            # Recheck the admin session and eligibility under the write lock. A
            # response that became active or a job that was rescheduled after the
            # preview is therefore left untouched.
            actor = self.portal.actor(token, frozenset({ActorRole.ADMIN}))
            rows = eligible_responses(connection)
            owned_attempts = {
                table: eligible_attempts(connection, table)
                for table in ("practice_attempts", "step_attempts")
            }
            old_jobs = connection.execute(
                "SELECT job_id FROM durable_jobs WHERE state IN ('succeeded','failed') "
                "AND updated_at<?",
                (job_cutoff,),
            ).fetchall()
            old_intents = connection.execute(
                "SELECT intent_id FROM cleanup_intents WHERE state='complete' AND updated_at<?",
                (job_cutoff,),
            ).fetchall()
            override_count = 0
            if owned_attempts["step_attempts"]:
                old_step_ids = [row[0] for row in owned_attempts["step_attempts"]]
                placeholders = ",".join("?" for _ in old_step_ids)
                override_count = connection.execute(
                    "SELECT COUNT(*) FROM teacher_override_events WHERE attempt_id IN ("
                    + placeholders
                    + ")",
                    old_step_ids,
                ).fetchone()[0]
            result.update(
                row_count=len(rows)
                + sum(map(len, owned_attempts.values()))
                + override_count
                + len(old_jobs)
                + len(old_intents),
                response_ids=[row[0] for row in rows],
                attempt_ids={
                    table: [row[0] for row in entries] for table, entries in owned_attempts.items()
                },
                obsolete_job_ids=[row[0] for row in old_jobs],
                completed_cleanup_ids=[row[0] for row in old_intents],
                teacher_override_event_count=override_count,
            )
            # Delete mutable learner evidence before parent attempts; immutable
            # submitted research rows remain outside this retention policy.
            old_practice = [row[0] for row in owned_attempts["practice_attempts"]]
            if old_practice:
                placeholders = ",".join("?" for _ in old_practice)
                if connection.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' "
                    "AND name='learning_audio_artifacts'"
                ).fetchone():
                    for blob_id, sha256, size_bytes in connection.execute(
                        "SELECT blob_id,sha256,size_bytes FROM learning_audio_artifacts "
                        f"WHERE practice_attempt_id IN ({placeholders})",
                        old_practice,
                    ).fetchall():
                        self._queue_blob_ref(
                            BlobRef(blob_id=blob_id, sha256=sha256, size_bytes=size_bytes)
                        )
                connection.execute(
                    f"DELETE FROM review_items WHERE source_attempt IN ({placeholders})",
                    old_practice,
                )
                connection.execute(
                    f"DELETE FROM practice_attempts WHERE attempt_id IN ({placeholders})",
                    old_practice,
                )
            ids = [row[0] for row in owned_attempts["step_attempts"]]
            if ids:
                placeholders = ",".join("?" for _ in ids)
                # Teacher feedback is personal learning data. Retention erases
                # it together with its source attempt under an explicit,
                # short-lived privacy-erasure intent so append-only audit
                # protections cannot leave orphan feedback behind.
                events = connection.execute(
                    "SELECT DISTINCT owner_id,attempt_id FROM teacher_override_events "
                    f"WHERE attempt_id IN ({placeholders})",
                    ids,
                ).fetchall()
                cleanup_at = datetime.now(UTC)
                cleanup_stamp = cleanup_at.isoformat()
                for event_owner, source_attempt in events:
                    connection.execute(
                        """INSERT INTO cleanup_intents(
                            intent_id,owner_id,resource_kind,resource_id,state,attempt,
                            available_at,created_at,updated_at,last_reason
                        ) VALUES(?,?,'privacy_erasure',?,'running',0,?,?,?,NULL)
                        ON CONFLICT(resource_kind,resource_id) DO UPDATE SET
                            state='running',updated_at=excluded.updated_at""",
                        (
                            uuid.uuid4().hex,
                            event_owner,
                            f"learning-override-retention:{source_attempt}",
                            cleanup_at.timestamp(),
                            cleanup_stamp,
                            cleanup_stamp,
                        ),
                    )
                if events:
                    connection.execute(
                        f"DELETE FROM teacher_override_events WHERE attempt_id IN ({placeholders})",
                        ids,
                    )
                    connection.execute(
                        "UPDATE cleanup_intents SET state='complete',updated_at=? "
                        "WHERE resource_kind='privacy_erasure' AND resource_id LIKE "
                        "'learning-override-retention:%' AND state='running'",
                        (cleanup_stamp,),
                    )
                if connection.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' "
                    "AND name='learning_audio_artifacts'"
                ).fetchone():
                    for blob_id, sha256, size_bytes in connection.execute(
                        "SELECT blob_id,sha256,size_bytes FROM learning_audio_artifacts "
                        f"WHERE step_attempt_id IN ({placeholders})",
                        ids,
                    ).fetchall():
                        self._queue_blob_ref(
                            BlobRef(blob_id=blob_id, sha256=sha256, size_bytes=size_bytes)
                        )
                connection.execute(
                    f"DELETE FROM step_review_items WHERE source_step_attempt IN ({placeholders})",
                    ids,
                )
                connection.execute(
                    f"DELETE FROM step_attempts WHERE attempt_id IN ({placeholders})", ids
                )
            if old_jobs:
                ids = [row[0] for row in old_jobs]
                placeholders = ",".join("?" for _ in ids)
                connection.execute(
                    f"DELETE FROM durable_jobs WHERE job_id IN ({placeholders})", ids
                )
            if old_intents:
                ids = [row[0] for row in old_intents]
                placeholders = ",".join("?" for _ in ids)
                connection.execute(
                    f"DELETE FROM cleanup_intents WHERE intent_id IN ({placeholders})", ids
                )
            for row in rows:
                response = self.portal.store._response_from_row(row)
                self._queue_blob(response)
                connection.execute(
                    "UPDATE responses SET audio_deleted_at=? WHERE response_id=?",
                    (datetime.now(UTC).isoformat(), response.response_id),
                )
                stored = connection.execute(
                    "SELECT report_json FROM diagnostic_reports WHERE response_id=?",
                    (response.response_id,),
                ).fetchone()
                if stored:
                    report = json.loads(stored[0])
                    report.update(comments=[], evidence_issues=[], evidence_refs=[])
                    report["limitations"].append(
                        "Audio và nhận xét chứa từ đã được xóa theo retention; "
                        "chỉ giữ kết quả tổng hợp và provenance."
                    )
                    connection.execute(
                        "UPDATE diagnostic_reports SET report_json=? WHERE response_id=?",
                        (json.dumps(report), response.response_id),
                    )
            self.portal.audit(
                actor, "retention_applied", "retention", reason=f"days={days};rows={len(rows)}"
            )
        result["blob_cleanup"] = self.cleanup_pending()
        return result

    def orphans(self, token: str, *, apply: bool = False) -> dict:
        actor = self.portal.actor(token, frozenset({ActorRole.ADMIN}))
        referenced = {
            row[0]
            for row in self.portal.store.connection.execute(
                "SELECT blob_id FROM responses WHERE audio_deleted_at IS NULL"
            )
        }
        # Lesson media can be shared by every learner and must never be treated
        # as an orphan simply because no response points at it.
        if self.portal.store.connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='learning_media'"
        ).fetchone():
            referenced.update(
                row[0]
                for row in self.portal.store.connection.execute(
                    "SELECT blob_id FROM learning_media WHERE blob_id IS NOT NULL"
                )
            )
        if self.portal.store.connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='learning_audio_artifacts'"
        ).fetchone():
            referenced.update(
                row[0]
                for row in self.portal.store.connection.execute(
                    "SELECT blob_id FROM learning_audio_artifacts"
                )
            )
        ids = [
            name
            for name in self.blobs.orphan_ids(referenced)
            if re.fullmatch(r"(?:[0-9a-f]{32}|tmp-[0-9a-f]{32}\.part)", name)
            and not (self.blobs.root / name).is_symlink()
            and (self.blobs.root / name).stat().st_mtime < time.time() - 3600
        ]
        if apply:
            with self.portal.store.transaction() as connection:
                actor = self.portal.actor(token, frozenset({ActorRole.ADMIN}))
                referenced = {
                    row[0]
                    for row in connection.execute(
                        "SELECT blob_id FROM responses WHERE audio_deleted_at IS NULL"
                    )
                }
                referenced.update(
                    row[0]
                    for row in connection.execute(
                        "SELECT blob_id FROM learning_media WHERE blob_id IS NOT NULL"
                    )
                )
                if connection.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' "
                    "AND name='learning_audio_artifacts'"
                ).fetchone():
                    referenced.update(
                        row[0]
                        for row in connection.execute(
                            "SELECT blob_id FROM learning_audio_artifacts"
                        )
                    )
                for name in ids:
                    if name in referenced:
                        continue
                    (self.blobs.root / name).unlink(missing_ok=True)
                self.portal.audit(actor, "orphans_cleaned", "blobs", reason=f"rows={len(ids)}")
        return {
            "dry_run": not apply,
            "row_count": len(ids),
            "blob_ids": ids,
            "minimum_age_seconds": 3600,
        }

    def backup(self, token: str, destination: Path) -> dict:
        actor = self.portal.actor(token, frozenset({ActorRole.ADMIN}))
        destination = self._safe_path(destination)
        data_dir = self.portal.store.data_dir
        if destination == data_dir or data_dir in destination.parents:
            raise ValueError("backup destination must be outside data directory")
        if destination.is_symlink():
            raise ValueError("backup destination cannot be a symlink")
        destination.mkdir(parents=True, exist_ok=False)
        destination.chmod(0o700)
        try:
            snapshot = sqlite3.connect(destination / "metadata.sqlite3")
            try:
                # A second read connection avoids SQLite backup deadlock when
                # the application connection is holding a write transaction.
                source = sqlite3.connect(
                    f"file:{(data_dir / 'metadata.sqlite3').as_posix()}?mode=ro", uri=True
                )
                try:
                    source.backup(snapshot)
                finally:
                    source.close()
                refs = {}
                for blob_id, sha256, size_bytes in snapshot.execute(
                    "SELECT blob_id,sha256,size_bytes FROM responses WHERE audio_deleted_at IS NULL"
                ):
                    prior = refs.setdefault(blob_id, (sha256, size_bytes))
                    if prior != (sha256, size_bytes):
                        raise ValueError("shared media metadata conflict")
                if snapshot.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' AND name='learning_media'"
                ).fetchone():
                    for blob_id, sha256, size_bytes in snapshot.execute(
                        "SELECT blob_id,sha256,size_bytes FROM learning_media "
                        "WHERE blob_id IS NOT NULL"
                    ):
                        prior = refs.setdefault(blob_id, (sha256, size_bytes))
                        if prior != (sha256, size_bytes):
                            raise ValueError("shared media metadata conflict")
                if snapshot.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' "
                    "AND name='learning_audio_artifacts'"
                ).fetchone():
                    for blob_id, sha256, size_bytes in snapshot.execute(
                        "SELECT blob_id,sha256,size_bytes FROM learning_audio_artifacts"
                    ):
                        prior = refs.setdefault(blob_id, (sha256, size_bytes))
                        if prior != (sha256, size_bytes):
                            raise ValueError("shared media metadata conflict")
                blob_dir = destination / "blobs"
                blob_dir.mkdir()
                for blob_id, (sha256, size_bytes) in sorted(refs.items()):
                    data = self.blobs.read(
                        BlobRef(blob_id=blob_id, sha256=sha256, size_bytes=size_bytes)
                    )
                    (blob_dir / blob_id).write_bytes(data)
                for item in destination.rglob("*"):
                    if item.is_file():
                        item.chmod(0o600)
                if snapshot.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                    raise ValueError("invalid backup")
                if snapshot.execute("PRAGMA foreign_key_check").fetchone() is not None:
                    raise ValueError("backup has foreign-key violations")
                response_count = int(
                    snapshot.execute(
                        "SELECT COUNT(*) FROM responses WHERE audio_deleted_at IS NULL"
                    ).fetchone()[0]
                )
            finally:
                snapshot.close()
            sensitive_files = []
            for filename in ("billing-hmac.key", "google-flow-hmac.key"):
                key_file = data_dir / filename
                if key_file.exists() or key_file.is_symlink():
                    data = self._read_protected_file(key_file)
                    target = destination / filename
                    target.write_bytes(data)
                    target.chmod(0o600)
                    sensitive_files.append(filename)
            files = {
                str(item.relative_to(destination)): hashlib.sha256(item.read_bytes()).hexdigest()
                for item in sorted(destination.rglob("*"))
                if item.is_file()
            }
            manifest = {
                "schema_version": self.portal.store.SCHEMA_VERSION,
                "blob_count": len(refs),
                "response_count": response_count,
                "created_at": datetime.now(UTC).isoformat(),
                "includes": ["metadata", "blobs"],
                "media_families": ["responses", "learning_media", "learning_audio_artifacts"],
                "learning_tables": [
                    "learning_audio_artifacts",
                    "review_items",
                    "step_review_items",
                    "teacher_override_events",
                    "learning_seed_manifest",
                ],
                "sensitive_files": sensitive_files,
                "files": files,
            }
            (destination / "manifest.json").write_text(
                json.dumps(manifest, sort_keys=True, indent=2) + "\n", encoding="utf-8"
            )
            (destination / "manifest.json").chmod(0o600)
        except Exception:
            shutil.rmtree(destination, ignore_errors=True)
            raise
        try:
            with self.portal.store.transaction() as connection:
                actor = self.portal.actor(token, frozenset({ActorRole.ADMIN}))
                self.portal.store.record_audit(
                    connection,
                    AuditEvent(
                        event_id=uuid.uuid4().hex,
                        actor_id=actor.actor_id,
                        action="backup_created",
                        object_id="backup",
                        recorded_at=datetime.now(UTC),
                        reason=None,
                    ),
                )
        except Exception:
            shutil.rmtree(destination, ignore_errors=True)
            raise
        return manifest

    def restore_backup(self, source: Path, destination: Path, token: str) -> dict:
        """Validate a complete snapshot, then atomically stage it in a fresh directory."""
        actor = self.portal.actor(token, frozenset({ActorRole.ADMIN}))
        if source.is_symlink():
            raise ValueError("backup source cannot be a symlink")
        source = self._safe_path(source, must_exist=True)
        destination = self._safe_path(destination)
        active = self.portal.store.data_dir.resolve()
        if (
            destination == active
            or destination in active.parents
            or active in destination.parents
            or destination == source
            or source in destination.parents
            or destination in source.parents
        ):
            raise ValueError("restore paths overlap protected data")
        if destination.exists():
            raise FileExistsError("restore destination must be fresh")
        if any(item.is_symlink() for item in source.rglob("*")):
            raise ValueError("backup contains symlinks")
        manifest_path = source / "manifest.json"
        import stat

        descriptor = None
        try:
            descriptor = os.open(manifest_path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
            manifest_info = os.fstat(descriptor)
            if not stat.S_ISREG(manifest_info.st_mode) or manifest_info.st_size > 1_048_576:
                raise ValueError("backup manifest is unsafe")
            chunks = []
            size = 0
            while size <= 1_048_576:
                chunk = os.read(descriptor, min(65536, 1_048_577 - size))
                if not chunk:
                    break
                chunks.append(chunk)
                size += len(chunk)
            if size != manifest_info.st_size or size > 1_048_576:
                raise ValueError("backup manifest changed while being read")
            manifest = json.loads(b"".join(chunks).decode("utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError("backup manifest is invalid") from error
        finally:
            if descriptor is not None:
                os.close(descriptor)
        if not isinstance(manifest, dict):
            raise ValueError("backup manifest is invalid")
        files = manifest.get("files")
        source_schema_version = manifest.get("schema_version")
        expected_learning_tables = [
            "learning_audio_artifacts",
            "review_items",
            "step_review_items",
            "teacher_override_events",
            "learning_seed_manifest",
        ]
        if (
            type(source_schema_version) is not int
            or source_schema_version not in {10, self.portal.store.SCHEMA_VERSION}
            or not isinstance(files, dict)
            or not isinstance(manifest.get("sensitive_files", []), list)
            or (
                source_schema_version == self.portal.store.SCHEMA_VERSION
                and manifest.get("learning_tables") != expected_learning_tables
            )
            or (source_schema_version == 10 and "learning_tables" in manifest)
        ):
            raise ValueError("backup manifest is invalid")
        if any(
            not isinstance(relative, str)
            or not isinstance(expected, str)
            or re.fullmatch(r"[0-9a-f]{64}", expected) is None
            for relative, expected in files.items()
        ):
            raise ValueError("backup manifest is invalid")
        if any(
            not isinstance(filename, str)
            or filename not in {"billing-hmac.key", "google-flow-hmac.key"}
            for filename in manifest.get("sensitive_files", [])
        ):
            raise ValueError("backup sensitive file manifest is invalid")
        actual = {
            item.relative_to(source).as_posix()
            for item in source.rglob("*")
            if item.is_file() and item.name != "manifest.json"
        }
        if actual != set(files) or "metadata.sqlite3" not in actual:
            raise ValueError("backup manifest file list is incomplete")
        for relative, expected in files.items():
            relative_path = Path(relative)
            if relative_path.is_absolute() or ".." in relative_path.parts:
                raise ValueError("backup manifest path is unsafe")
            path = source / relative_path
            if (
                path.is_symlink()
                or not path.is_file()
                or hashlib.sha256(path.read_bytes()).hexdigest() != expected
            ):
                raise ValueError("backup checksum verification failed")
        database = source / "metadata.sqlite3"
        connection = sqlite3.connect(f"file:{database.as_posix()}?mode=ro", uri=True)
        try:
            if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise ValueError("backup database integrity check failed")
            if connection.execute("PRAGMA user_version").fetchone()[0] != source_schema_version:
                raise ValueError("backup schema version mismatch")
            if connection.execute("PRAGMA foreign_key_check").fetchone() is not None:
                raise ValueError("backup foreign-key check failed")
            refs = {}
            for blob_id, sha256, size_bytes in connection.execute(
                "SELECT blob_id,sha256,size_bytes FROM responses WHERE audio_deleted_at IS NULL"
            ):
                prior = refs.setdefault(blob_id, (sha256, size_bytes))
                if prior != (sha256, size_bytes):
                    raise ValueError("shared media metadata conflict")
            if connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='learning_media'"
            ).fetchone():
                for blob_id, sha256, size_bytes in connection.execute(
                    "SELECT blob_id,sha256,size_bytes FROM learning_media WHERE blob_id IS NOT NULL"
                ):
                    prior = refs.setdefault(blob_id, (sha256, size_bytes))
                    if prior != (sha256, size_bytes):
                        raise ValueError("shared media metadata conflict")
            if connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='learning_audio_artifacts'"
            ).fetchone():
                for blob_id, sha256, size_bytes in connection.execute(
                    "SELECT blob_id,sha256,size_bytes FROM learning_audio_artifacts"
                ):
                    prior = refs.setdefault(blob_id, (sha256, size_bytes))
                    if prior != (sha256, size_bytes):
                        raise ValueError("shared media metadata conflict")
            for blob_id, (expected_hash, expected_size) in refs.items():
                blob = source / "blobs" / blob_id
                if (
                    blob_id not in {Path(item).name for item in files if item.startswith("blobs/")}
                    or not blob.is_file()
                ):
                    raise ValueError("backup is missing referenced media")
                content = blob.read_bytes()
                if (
                    len(content) != expected_size
                    or hashlib.sha256(content).hexdigest() != expected_hash
                ):
                    raise ValueError("backup media does not match database reference")
        finally:
            connection.close()
        destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        staging = destination.with_name(destination.name + ".staging-" + uuid.uuid4().hex)
        try:
            shutil.copytree(source, staging, symlinks=False)
            for filename in manifest.get("sensitive_files", []):
                if filename not in {"billing-hmac.key", "google-flow-hmac.key"}:
                    raise ValueError("backup sensitive file manifest is invalid")
                protected = staging / filename
                if not protected.is_file() or protected.is_symlink():
                    raise ValueError("backup protected key is missing")
                protected.chmod(0o600)
            restored_store = None
            try:
                from aicefr.storage.sqlite import SQLiteStore

                restored_store = SQLiteStore(staging)
                restored_store.connection.execute("SELECT * FROM entitlements LIMIT 1").fetchall()
                restored_store.connection.execute(
                    "SELECT * FROM diagnostic_reports LIMIT 1"
                ).fetchall()
                restored_store.connection.execute("SELECT * FROM learning_media LIMIT 1").fetchall()
                restored_store.connection.execute(
                    "SELECT * FROM learning_audio_artifacts LIMIT 1"
                ).fetchall()
                restored_store.connection.execute(
                    "SELECT * FROM teacher_override_events LIMIT 1"
                ).fetchall()
                restored_store.connection.execute(
                    "SELECT * FROM learning_seed_manifest LIMIT 1"
                ).fetchall()
            finally:
                if restored_store is not None:
                    restored_store.close()
            if "billing-hmac.key" in manifest.get("sensitive_files", []):
                from aicefr.billing.secrets import KeyRing

                KeyRing(staging)
            with self.portal.store.transaction() as connection:
                self.portal.actor(token, frozenset({ActorRole.ADMIN}))
                os.replace(staging, destination)
                self.portal.store.record_audit(
                    connection,
                    AuditEvent(
                        event_id=uuid.uuid4().hex,
                        actor_id=actor.actor_id,
                        action="backup_restored",
                        object_id="restore:" + uuid.uuid4().hex,
                        recorded_at=datetime.now(UTC),
                        reason=None,
                    ),
                )
        except Exception:
            shutil.rmtree(staging, ignore_errors=True)
            if destination.exists():
                shutil.rmtree(destination, ignore_errors=True)
            raise
        return {
            "restored": True,
            "schema_version": self.portal.store.SCHEMA_VERSION,
            "source_schema_version": source_schema_version,
            "blob_count": len(refs),
        }

    @staticmethod
    def _safe_path(path: Path, *, must_exist: bool = False) -> Path:
        candidate = path.expanduser().absolute()
        for item in (candidate, *candidate.parents):
            if item.is_symlink():
                raise ValueError("filesystem path cannot contain symlinks")
        if must_exist and not candidate.exists():
            raise FileNotFoundError("filesystem path is unavailable")
        return candidate.resolve(strict=must_exist)

    @staticmethod
    def _read_protected_file(path: Path) -> bytes:
        import stat

        try:
            info = path.lstat()
            if (
                not stat.S_ISREG(info.st_mode)
                or info.st_nlink != 1
                or info.st_uid != os.getuid()
                or info.st_mode & 0o077
            ):
                raise ValueError("protected key file is unsafe")
            descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
            try:
                opened = os.fstat(descriptor)
                if (
                    not stat.S_ISREG(opened.st_mode)
                    or opened.st_nlink != 1
                    or opened.st_uid != os.getuid()
                    or opened.st_ino != info.st_ino
                    or opened.st_dev != info.st_dev
                    or opened.st_mode & 0o077
                    or opened.st_size > 4096
                ):
                    raise ValueError("protected key file is unsafe")
                data = os.read(descriptor, 4097)
                if len(data) != opened.st_size or len(data) > 4096:
                    raise ValueError("protected key file is unsafe")
                return data
            finally:
                os.close(descriptor)
        except OSError as error:
            raise ValueError("protected key file is unavailable") from error
