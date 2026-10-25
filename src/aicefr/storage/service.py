"""Owner and consent gated response service over SQLite metadata and BlobStore."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import datetime

from aicefr.auth.service import (
    ConsentService,
    authorize_owner,
    utc_now,
)
from aicefr.contracts import Actor, AuditEvent, ReasonCode, ResponseRecord, ResponseStatus
from aicefr.storage.blob import BlobStore
from aicefr.storage.sqlite import SQLiteStore


class ResponseService:
    def __init__(
        self,
        metadata: SQLiteStore,
        blobs: BlobStore,
        consents: ConsentService,
        *,
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        self.metadata = metadata
        self.blobs = blobs
        self.consents = consents
        self.clock = clock

    def submit(
        self,
        actor: Actor,
        *,
        task_id: str,
        task_version: str,
        consent_version: str,
        audio_bytes: bytes,
        initial_status: ResponseStatus = ResponseStatus.QUEUED,
    ) -> ResponseRecord:
        self.consents.require_audio_storage(actor, consent_version)
        blob = self.blobs.store(audio_bytes)
        try:
            now = self.clock()
            record = ResponseRecord(
                response_id=uuid.uuid4().hex,
                owner_id=actor.actor_id,
                task_id=task_id,
                task_version=task_version,
                blob=blob,
                status=initial_status,
                created_at=now,
            )
            event = AuditEvent(
                event_id=uuid.uuid4().hex,
                actor_id=actor.actor_id,
                action="response_submitted",
                object_id=record.response_id,
                recorded_at=now,
            )
            self.metadata.save_response(record, event)
            return record
        except Exception:
            self.blobs.compensate(blob)
            raise

    def transition_status(
        self,
        *,
        response_id: str,
        expected_revision: int,
        status: ResponseStatus,
        actor_id: str,
        action: str,
        reason: ReasonCode | None = None,
    ) -> ResponseRecord:
        """Ghi trạng thái pipeline cùng audit event, dùng optimistic locking."""
        now = self.clock()
        return self.metadata.update_response_status(
            response_id,
            expected_revision=expected_revision,
            status=status,
            status_reason=reason,
            event=AuditEvent(
                event_id=uuid.uuid4().hex,
                actor_id=actor_id,
                action=action,
                object_id=response_id,
                recorded_at=now,
                reason=reason,
            ),
        )

    def get_response(self, actor: Actor, response_id: str) -> ResponseRecord:
        record = self.metadata.get_response(response_id)
        authorize_owner(actor, record.owner_id if record else None)
        assert record is not None
        return record

    def get_blob(self, actor: Actor, response_id: str) -> bytes:
        record = self.get_response(actor, response_id)
        return self.blobs.read(record.blob)

    def report_orphans(self) -> tuple[str, ...]:
        return self.blobs.orphan_ids(self.metadata.referenced_blob_ids())
