"""Fixture data controls with committed cleanup intents and append-only audit."""

from __future__ import annotations

import json
import re
import shutil
import sqlite3
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

from aicefr.auth.service import AuthorizationError, ResourceNotFound
from aicefr.contracts import ActorRole, ResponseStatus
from aicefr.portal.contracts import DeleteRequest
from aicefr.portal.service import PortalService
from aicefr.storage.blob import BlobStore
from aicefr.storage.sqlite import ConcurrentResponseUpdate


class DataControl:
    def __init__(self, portal: PortalService, blobs: BlobStore) -> None:
        self.portal, self.blobs = portal, blobs

    def _queue_blob(self, response) -> None:
        self.portal.store.connection.execute(
            "INSERT OR IGNORE INTO blob_deletions VALUES (?,?)",
            (response.blob.blob_id, datetime.now(UTC).isoformat()),
        )

    def cleanup_pending(self) -> dict:
        """A crash leaves a durable intent; retry never removes a referenced live blob."""
        removed, pending = 0, 0
        store = self.portal.store
        for (blob_id,) in store.connection.execute("SELECT blob_id FROM blob_deletions").fetchall():
            live = store.connection.execute(
                "SELECT 1 FROM responses WHERE blob_id=? AND audio_deleted_at IS NULL",
                (blob_id,),
            ).fetchone()
            if live:
                pending += 1
                continue
            try:
                self.blobs._path(blob_id).unlink(missing_ok=True)
            except OSError:
                pending += 1
            else:
                with store.transaction() as connection:
                    connection.execute("DELETE FROM blob_deletions WHERE blob_id=?", (blob_id,))
                removed += 1
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
        rows = self.portal.store.connection.execute(
            "SELECT r.response_id,r.revision,r.status,r.size_bytes,c.revision,d.report_json "
            "FROM responses r LEFT JOIN review_candidates c ON c.response_id=r.response_id "
            "LEFT JOIN diagnostic_reports d ON d.response_id=r.response_id WHERE r.owner_id=? "
            "ORDER BY r.response_id",
            (actor_id,),
        ).fetchall()
        from hashlib import sha256

        fingerprint = sha256(json.dumps(rows, separators=(",", ":")).encode()).hexdigest()
        return {
            "actor_id": actor_id,
            "row_count": len(rows),
            "audio_bytes": sum(row[3] for row in rows),
            "fingerprint": fingerprint,
            "responses": [
                {"response_id": row[0], "revision": row[1], "status": row[2]} for row in rows
            ],
            "note": "Xóa dữ liệu cá nhân, thông tin đăng nhập, hồ sơ, liên kết và bài nộp. "
            "Lịch sử consent và audit giả danh được giữ; tài khoản bị vô hiệu hóa nếu "
            "cần giữ tham chiếu lịch sử. Backup đã tạo không bị sửa.",
        }

    def erase(self, token: str, actor_id: str, confirm_id: str, fingerprint: str) -> dict:
        actor = self.portal.actor(token, frozenset({ActorRole.ADMIN}))
        if confirm_id != actor_id:
            raise ValueError("confirmation must match participant ID")
        with self.portal.store.transaction() as connection:
            preview = self.erasure_preview(token, actor_id)
            if fingerprint != preview["fingerprint"]:
                raise ConcurrentResponseUpdate("erasure preview is stale")
            for item in preview["responses"]:
                self._delete(self.portal.store.get_response(item["response_id"]))
            connection.execute("DELETE FROM sessions WHERE actor_id=?", (actor_id,))
            connection.execute("DELETE FROM consents WHERE participant_id=?", (actor_id,))
            # New M11 side tables retain explicit ownership references. Remove mutable
            # identity and activity rows before deleting the synthetic account. Consent
            # events are append-only; when present, retain only a disabled credential
            # stub so their FK and immutable evidence remain valid.
            connection.execute("DELETE FROM account_identities WHERE account_id=?", (actor_id,))
            connection.execute("DELETE FROM account_profiles WHERE account_id=?", (actor_id,))
            connection.execute("DELETE FROM temporary_passwords WHERE account_id=?", (actor_id,))
            connection.execute("DELETE FROM activity_events WHERE account_id=?", (actor_id,))
            now = datetime.now(UTC).isoformat()
            connection.execute(
                "UPDATE study_enrollments SET withdrawn_at=COALESCE(withdrawn_at,?) "
                "WHERE participant_id=?",
                (now, actor_id),
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
                actor, "participant_erased", actor_id, reason=f"responses={preview['row_count']}"
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
        rows = self.portal.store.connection.execute(
            "SELECT * FROM responses WHERE julianday(created_at)<julianday(?) "
            "AND audio_deleted_at IS NULL AND status NOT IN (?,?)",
            (cutoff.isoformat(), ResponseStatus.RUNNING, ResponseStatus.QUEUED),
        ).fetchall()
        result = {
            "dry_run": not apply,
            "days": days,
            "row_count": len(rows),
            "response_ids": [row[0] for row in rows],
        }
        if not apply:
            return result
        with self.portal.store.transaction() as connection:
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
        ids = [
            name
            for name in self.blobs.orphan_ids(referenced)
            if re.fullmatch(r"(?:[0-9a-f]{32}|tmp-[0-9a-f]{32}\.part)", name)
            and not (self.blobs.root / name).is_symlink()
            and (self.blobs.root / name).stat().st_mtime < time.time() - 3600
        ]
        if apply:
            with self.portal.store.transaction():
                for name in ids:
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
        destination = destination.expanduser().resolve()
        data_dir = self.portal.store.data_dir
        if destination == data_dir or data_dir in destination.parents:
            raise ValueError("backup destination must be outside data directory")
        destination.mkdir(parents=True, exist_ok=False)
        destination.chmod(0o700)
        try:
            snapshot = sqlite3.connect(destination / "metadata.sqlite3")
            try:
                self.portal.store.connection.backup(snapshot)
                rows = snapshot.execute(
                    "SELECT * FROM responses WHERE audio_deleted_at IS NULL"
                ).fetchall()
                blob_dir = destination / "blobs"
                blob_dir.mkdir()
                for row in rows:
                    response = self.portal.store._response_from_row(row)
                    (blob_dir / response.blob.blob_id).write_bytes(self.blobs.read(response.blob))
                if snapshot.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                    raise ValueError("invalid backup")
            finally:
                snapshot.close()
            manifest = {
                "schema_version": self.portal.store.SCHEMA_VERSION,
                "response_count": len(rows),
                "created_at": datetime.now(UTC).isoformat(),
                "includes": ["metadata", "blobs"],
            }
            (destination / "manifest.json").write_text(
                json.dumps(manifest, indent=2), encoding="utf-8"
            )
        except Exception:
            shutil.rmtree(destination)
            raise
        self.portal.audit(actor, "backup_created", "backup")
        return manifest
