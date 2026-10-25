from __future__ import annotations

from io import BytesIO

import pytest

from aicefr.api.student import StudentApi
from aicefr.api.wsgi import StudentTeacherApp
from aicefr.auth.memory import MemoryIdentityRepository
from aicefr.auth.service import AuthService, ConsentService
from aicefr.contracts import ActorRole


class _StudentSubmitSpy:
    def __init__(self) -> None:
        self.requests = []

    def submit(self, token, request):
        self.requests.append((token, request))
        raise AssertionError("stale consent must stop before the student service")


def _multipart(consent_version: str) -> tuple[str, bytes]:
    boundary = "review-consent-boundary"
    parts = {
        "task_id": "fixture-task",
        "task_version": "v1",
        "consent_version": consent_version,
    }
    body = b"".join(
        f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode()
        for name, value in parts.items()
    )
    body += (
        f'--{boundary}\r\nContent-Disposition: form-data; name="audio"; filename="sample.wav"\r\n'
        "Content-Type: audio/wav\r\n\r\nfixture-audio\r\n"
        f"--{boundary}--\r\n"
    ).encode()
    return f"multipart/form-data; boundary={boundary}", body


@pytest.mark.parametrize(
    ("field_version", "stored_version"),
    [("old-v1", "old-v1"), ("current-v2", "old-v1"), ("current-v2", None)],
)
def test_local_submit_rejects_stale_or_missing_configured_consent_without_dispatch(
    field_version, stored_version
):
    identities = MemoryIdentityRepository()
    auth = AuthService(identities, identities)
    actor = auth.bootstrap_fixture_account("fixture-student", ActorRole.STUDENT, "fixture-password")
    token = auth.login(actor.actor_id, "fixture-password")
    consents = ConsentService(identities)
    if stored_version is not None:
        consents.activate(actor, stored_version)
    submit_spy = _StudentSubmitSpy()
    app = StudentTeacherApp(
        StudentApi(submit_spy),
        auth=auth,
        consents=consents,
        consent_version="current-v2",
    )
    content_type, body = _multipart(field_version)
    captured = {}
    environ = {
        "REQUEST_METHOD": "POST",
        "PATH_INFO": "/student/responses",
        "CONTENT_LENGTH": str(len(body)),
        "CONTENT_TYPE": content_type,
        "HTTP_COOKIE": f"aicefr_session={token}",
        "HTTP_HOST": "127.0.0.1:8000",
        "HTTP_ORIGIN": "http://127.0.0.1:8000",
        "wsgi.url_scheme": "http",
        "wsgi.input": BytesIO(body),
    }

    def start_response(status, headers):
        captured["status"] = status

    response = b"".join(app(environ, start_response)).decode()

    assert captured["status"].startswith("403")
    assert "đã thay đổi" in response
    assert submit_spy.requests == []


def test_local_submit_rejects_audio_without_storage_choice_before_reading_body():
    identities = MemoryIdentityRepository()
    auth = AuthService(identities, identities)
    actor = auth.bootstrap_fixture_account("fixture-student", ActorRole.STUDENT, "fixture-password")
    token = auth.login(actor.actor_id, "fixture-password")
    consents = ConsentService(identities)
    consents.activate(actor, "current-v2", research_allowed=True)
    submit_spy = _StudentSubmitSpy()
    app = StudentTeacherApp(
        StudentApi(submit_spy),
        auth=auth,
        consents=consents,
        consent_version="current-v2",
    )
    content_type, body = _multipart("current-v2")
    stream = BytesIO(body)
    captured = {}
    environ = {
        "REQUEST_METHOD": "POST",
        "PATH_INFO": "/student/responses",
        "CONTENT_LENGTH": str(len(body)),
        "CONTENT_TYPE": content_type,
        "HTTP_COOKIE": f"aicefr_session={token}",
        "HTTP_HOST": "127.0.0.1:8000",
        "HTTP_ORIGIN": "http://127.0.0.1:8000",
        "wsgi.url_scheme": "http",
        "wsgi.input": stream,
    }

    def start_response(status, headers):
        captured["status"] = status

    b"".join(app(environ, start_response))

    assert captured["status"].startswith("403")
    assert stream.tell() == 0
    assert submit_spy.requests == []
