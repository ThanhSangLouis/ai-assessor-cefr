"""Typed M07 API boundary over M08 session resolution."""

from __future__ import annotations

from aicefr.auth.errors import AuthorizationError
from aicefr.auth.service import AuthService
from aicefr.contracts import ActorRole, ReviewCandidate
from aicefr.review.service import ReviewActionRequest, ReviewOutcome, ReviewService


class ReviewApi:
    def __init__(self, auth: AuthService, service: ReviewService, research=None) -> None:
        self._auth = auth
        self._service = service
        self._research = research

    def get_queue(self, session_token: str) -> tuple[ReviewCandidate, ...]:
        actor = self._teacher(session_token)
        queue = self._service.queue(actor)
        if self._research is None:
            return queue
        hidden = self._research.blinded_response_ids(actor.actor_id)
        return tuple(item for item in queue if item.response_id not in hidden)

    def claim(
        self, session_token: str, response_id: str, expected_revision: int
    ) -> ReviewCandidate:
        actor = self._teacher(session_token)
        self._assert_not_blinded(actor.actor_id, response_id)
        candidate = self._service.claim(actor, response_id, expected_revision)
        if self._research is not None:
            self._research.mark_review_started(actor.actor_id, response_id)
        return candidate

    def decide(
        self, session_token: str, response_id: str, request: ReviewActionRequest
    ) -> ReviewOutcome:
        actor = self._teacher(session_token)
        self._assert_not_blinded(actor.actor_id, response_id)
        outcome = self._service.decide(actor, response_id, request)
        if self._research is not None:
            self._research.mark_review_ended(actor.actor_id, response_id, "decision")
        return outcome

    def release(
        self, session_token: str, response_id: str, expected_revision: int
    ) -> ReviewCandidate:
        actor = self._teacher(session_token)
        self._assert_not_blinded(actor.actor_id, response_id)
        candidate = self._service.release(actor, response_id, expected_revision)
        if self._research is not None:
            self._research.mark_review_ended(actor.actor_id, response_id, "release")
        return candidate

    def _assert_not_blinded(self, actor_id: str, response_id: str) -> None:
        if self._research is not None and response_id in self._research.blinded_response_ids(
            actor_id
        ):
            raise AuthorizationError("access denied")

    def _teacher(self, session_token: str):
        return self._auth.resolve(
            session_token, allowed_roles=frozenset({ActorRole.TEACHER, ActorRole.ADMIN})
        )
