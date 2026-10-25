from datetime import UTC, datetime

import pytest

from aicefr.auth.memory import MemoryIdentityRepository
from aicefr.auth.service import AuthorizationError, ConsentService
from aicefr.contracts import Actor, ActorRole, ConsentState


def test_versioned_consent_withdrawal_blocks_new_submission():
    repository = MemoryIdentityRepository()
    consent = ConsentService(repository, clock=lambda: datetime(2026, 9, 28, tzinfo=UTC))
    student = Actor(actor_id="fixture-student", role=ActorRole.STUDENT)
    teacher = Actor(actor_id="fixture-teacher", role=ActorRole.TEACHER)
    with pytest.raises(AuthorizationError):
        consent.require_active(student, "v1")
    with pytest.raises(AuthorizationError):
        consent.activate(teacher, "v1")
    active = consent.activate(student, "v1")
    assert consent.require_active(student, "v1") == active
    with pytest.raises(AuthorizationError):
        consent.require_active(student, "v2")
    with pytest.raises(AuthorizationError, match="audio storage consent"):
        consent.require_audio_storage(student, "v1")
    withdrawn = consent.withdraw(student)
    assert withdrawn.state == ConsentState.WITHDRAWN
    assert repository.get_consent(student.actor_id) == withdrawn
    with pytest.raises(AuthorizationError):
        consent.require_active(student, "v1")
    with pytest.raises(AuthorizationError):
        consent.withdraw(teacher)
    consent.activate(student, "v2", audio_storage_allowed=True)
    assert consent.require_active(student, "v2").consent_version == "v2"
    assert consent.require_audio_storage(student, "v2").audio_storage_allowed
