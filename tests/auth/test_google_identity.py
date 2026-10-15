from __future__ import annotations

import base64
import concurrent.futures
import hashlib
import hmac
import json
import urllib.parse
from datetime import UTC, datetime, timedelta

import pytest
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from aicefr.auth.errors import LockoutError
from aicefr.auth.google import (
    GoogleConfig,
    GoogleIdentityError,
    GoogleIdentityService,
)
from aicefr.contracts import Actor, ActorRole
from aicefr.storage.google_identity import GoogleIdentityRepository, google_subject_hash
from aicefr.storage.sqlite import SQLiteStore


def _b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


class Clock:
    def __init__(self) -> None:
        self.now = datetime(2026, 10, 15, tzinfo=UTC)

    def __call__(self) -> datetime:
        return self.now


class FakeAuth:
    def __init__(self, actor_id: str = "fixture-student") -> None:
        self.actor = Actor(actor_id=actor_id, role=ActorRole.STUDENT)
        self.tokens = {"valid-session": self.actor}
        self.disabled = False
        self.locked = False
        self.issued: list[str] = []

    def resolve(self, token: str, **_kwargs: object) -> Actor:
        if token not in self.tokens or self.disabled:
            raise ValueError("unavailable")
        return self.tokens[token]

    def issue_session(self, actor_id: str, *, method: str) -> str:
        if self.locked:
            raise LockoutError(120)
        if self.disabled or actor_id != self.actor.actor_id or method != "google":
            raise ValueError("unavailable")
        self.issued.append(actor_id)
        return "new-opaque-session"


class SignedProvider:
    def __init__(self, key: rsa.RSAPrivateKey, kid: str = "fixture-kid") -> None:
        self.key = key
        self.kid = kid
        self.claims: dict[str, object] = {}
        self.requests: list[tuple[str, str, dict[str, str] | None]] = []

    def request_json(self, method: str, url: str, **kwargs: object) -> dict[str, object]:
        data = kwargs.get("data")
        self.requests.append((method, url, data if isinstance(data, dict) else None))
        if url.endswith("/token"):
            return {"id_token": self.jwt(self.claims)}
        public = self.key.public_key().public_numbers()
        return {
            "keys": [
                {
                    "kty": "RSA",
                    "kid": self.kid,
                    "alg": "RS256",
                    "use": "sig",
                    "n": _b64(public.n.to_bytes((public.n.bit_length() + 7) // 8, "big")),
                    "e": _b64(public.e.to_bytes((public.e.bit_length() + 7) // 8, "big")),
                }
            ]
        }

    def jwt(self, claims: dict[str, object], *, key: rsa.RSAPrivateKey | None = None) -> str:
        header = _b64(
            json.dumps(
                {"alg": "RS256", "kid": self.kid, "typ": "JWT"}, separators=(",", ":")
            ).encode()
        )
        body = _b64(json.dumps(claims, separators=(",", ":")).encode())
        message = f"{header}.{body}".encode("ascii")
        signature = (key or self.key).sign(message, padding.PKCS1v15(), hashes.SHA256())
        return f"{header}.{body}.{_b64(signature)}"


@pytest.fixture
def setup(tmp_path):
    clock = Clock()
    store = SQLiteStore(tmp_path / "identity-data")
    store.connection.execute(
        "INSERT INTO accounts(actor_id,role,password_hash) VALUES(?,?,?)",
        ("fixture-student", "student", "synthetic-password-hash"),
    )
    repository = GoogleIdentityRepository(store)
    auth = FakeAuth()
    signing_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    provider = SignedProvider(signing_key)
    config = GoogleConfig(
        enabled=True,
        client_id="fixture-client.apps.googleusercontent.com",
        client_secret="fixture-client-secret",
        redirect_uri="http://localhost:8000/auth/google/callback",
        data_dir=tmp_path / "identity-data",
    )
    service = GoogleIdentityService(
        auth,
        repository,
        config,
        key=b"k" * 32,
        clock=clock,
        transport=provider,
    )
    yield clock, store, repository, auth, provider, service
    store.close()


def _start(service: GoogleIdentityService, intent: str = "login", token: str | None = None):
    started = service.start(intent, token)
    params = urllib.parse.parse_qs(urllib.parse.urlsplit(started.authorization_url).query)
    return started, {key: values[0] for key, values in params.items()}


def _claims(clock: Clock, params: dict[str, str], **changes: object) -> dict[str, object]:
    now = int(clock.now.timestamp())
    return {
        "iss": "https://accounts.google.com",
        "aud": "fixture-client.apps.googleusercontent.com",
        "sub": "synthetic-google-subject-012345",
        "iat": now,
        "exp": now + 300,
        "nonce": params["nonce"],
        **changes,
    }


def test_login_uses_pkce_openid_only_and_authenticates_only_linked_subject(setup):
    clock, store, repository, auth, provider, service = setup
    started, params = _start(service)
    assert params["scope"] == "openid"
    assert params["code_challenge_method"] == "S256"
    assert "code_verifier" not in params
    assert (
        repository.account_for_subject(google_subject_hash("synthetic-google-subject-012345"))
        is None
    )
    provider.claims = _claims(clock, params)
    with pytest.raises(GoogleIdentityError, match="google_identity_unlinked"):
        service.callback(started.flow_cookie, params["state"], "synthetic-code")
    assert not auth.issued
    assert (
        "synthetic-google-subject-012345"
        not in store.connection.execute("SELECT payload FROM runtime_settings")
        .fetchall()
        .__repr__()
    )


def test_login_for_existing_linked_account_issues_opaque_session(setup):
    clock, _store, repository, auth, provider, service = setup
    subject = "synthetic-google-subject-012345"
    repository.link_subject(auth.actor.actor_id, google_subject_hash(subject), clock.now)
    started, params = _start(service)
    provider.claims = _claims(clock, params, sub=subject)
    result = service.callback(started.flow_cookie, params["state"], "synthetic-code")
    assert result.outcome == "authenticated"
    assert result.actor_id == auth.actor.actor_id
    assert result.session_token == "new-opaque-session"
    assert auth.issued == [auth.actor.actor_id]


def test_google_login_preserves_lockout_response(setup):
    clock, _store, repository, auth, provider, service = setup
    subject = "synthetic-google-subject-012345"
    repository.link_subject(auth.actor.actor_id, google_subject_hash(subject), clock.now)
    started, params = _start(service)
    provider.claims = _claims(clock, params, sub=subject)
    auth.locked = True
    with pytest.raises(LockoutError) as error:
        service.callback(started.flow_cookie, params["state"], "synthetic-code")
    assert error.value.retry_after == 120


def test_link_binds_actor_and_session_and_stores_only_subject_hash(setup):
    clock, store, repository, auth, provider, service = setup
    auth.tokens["changed-session"] = auth.actor
    started, params = _start(service, "link", "valid-session")
    provider.claims = _claims(clock, params)
    with pytest.raises(GoogleIdentityError, match="google_flow_invalid"):
        service.callback(started.flow_cookie, params["state"], "synthetic-code", "changed-session")
    result = service.callback(
        started.flow_cookie, params["state"], "synthetic-code", "valid-session"
    )
    assert result.outcome == "linked"
    row = store.connection.execute(
        "SELECT account_id,provider,subject_hash FROM account_identities"
    ).fetchone()
    assert row == (
        auth.actor.actor_id,
        "google",
        google_subject_hash("synthetic-google-subject-012345"),
    )
    assert "synthetic-google-subject-012345" not in repr(row)
    sensitive_storage = repr(
        store.connection.execute("SELECT * FROM account_identities").fetchall()
        + store.connection.execute("SELECT * FROM audit").fetchall()
        + store.connection.execute("SELECT * FROM activity_events").fetchall()
        + store.connection.execute("SELECT * FROM runtime_settings").fetchall()
    )
    for secret in (
        "synthetic-google-subject-012345",
        "synthetic-code",
        "code_verifier",
        "fixture-client-secret",
    ):
        assert secret not in sensitive_storage


@pytest.mark.parametrize(
    "changes",
    [
        {"iss": "https://attacker.example"},
        {"aud": "other-client"},
        {"aud": ["fixture-client.apps.googleusercontent.com", "other-client"]},
        {"azp": "other-client"},
        {"nonce": "wrong"},
        {"exp": 1},
        {"iat": 1},
    ],
)
def test_rejects_invalid_oidc_claims_before_session_or_link(setup, changes):
    clock, _store, _repository, auth, provider, service = setup
    started, params = _start(service)
    provider.claims = _claims(clock, params, **changes)
    with pytest.raises(GoogleIdentityError, match="google_assertion_invalid"):
        service.callback(started.flow_cookie, params["state"], "synthetic-code")
    assert not auth.issued


def test_rejects_bad_signature_and_changed_signed_flow(setup):
    clock, _store, _repository, auth, provider, service = setup
    started, params = _start(service)
    other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    provider.claims = _claims(clock, params)
    # Sign with an untrusted key while advertising the known key id.
    provider.request_json = lambda method, url, **kwargs: (
        {"id_token": provider.jwt(provider.claims, key=other_key)}
        if url.endswith("/token")
        else SignedProvider.request_json(provider, method, url, **kwargs)
    )
    with pytest.raises(GoogleIdentityError, match="google_assertion_invalid"):
        service.callback(started.flow_cookie, params["state"], "synthetic-code")
    assert not auth.issued
    with pytest.raises(GoogleIdentityError, match="google_flow_invalid"):
        service.callback(
            started.flow_cookie[:-1] + ("A" if started.flow_cookie[-1] != "A" else "B"),
            params["state"],
            "synthetic-code",
        )


def test_replay_consumed_before_exchange_and_stale_cookie_rejected(setup):
    clock, _store, _repository, _auth, provider, service = setup
    started, params = _start(service)
    provider.claims = _claims(clock, params)
    with pytest.raises(GoogleIdentityError, match="google_identity_unlinked"):
        service.callback(started.flow_cookie, params["state"], "synthetic-code")
    calls = len(provider.requests)
    with pytest.raises(GoogleIdentityError, match="google_flow_replayed"):
        service.callback(started.flow_cookie, params["state"], "synthetic-code")
    assert len(provider.requests) == calls
    started, params = _start(service)
    clock.now += timedelta(minutes=10)
    with pytest.raises(GoogleIdentityError, match="google_flow_invalid"):
        service.callback(started.flow_cookie, params["state"], "synthetic-code")


def test_duplicate_subject_cannot_link_two_local_accounts(setup):
    clock, _store, repository, auth, provider, service = setup
    repository.link_subject(auth.actor.actor_id, google_subject_hash("already-linked"), clock.now)
    started, params = _start(service, "link", "valid-session")
    provider.claims = _claims(clock, params, sub="already-linked")
    with pytest.raises(GoogleIdentityError, match="google_identity_already_linked"):
        service.callback(started.flow_cookie, params["state"], "synthetic-code", "valid-session")


def test_disabled_account_and_domain_policy_fail_closed(setup):
    clock, _store, repository, auth, provider, service = setup
    subject = "synthetic-google-subject-012345"
    repository.link_subject(auth.actor.actor_id, google_subject_hash(subject), clock.now)
    started, params = _start(service)
    provider.claims = _claims(clock, params, sub=subject)
    auth.disabled = True
    with pytest.raises(GoogleIdentityError, match="account_unavailable"):
        service.callback(started.flow_cookie, params["state"], "synthetic-code")
    assert not auth.issued


def test_link_cookie_is_signed_and_config_status_never_returns_secret(setup):
    _clock, _store, _repository, _auth, _provider, service = setup
    assert service.status()["client_secret_set"] is True
    assert "fixture-client-secret" not in repr(service.status())
    assert "fixture-client-secret" not in repr(service.start().authorization_url)


def test_disabled_or_incomplete_config_is_reported_without_crypto_path(tmp_path):
    config = GoogleConfig(
        enabled=True,
        client_id="",
        client_secret="secret",
        redirect_uri="http://example.com/cb",
        data_dir=tmp_path,
    )
    assert config.status()["ready"] is False
    assert "client_secret" not in config.status()["missing_fields"]
    https_without_secure_mode = GoogleConfig(
        enabled=True,
        client_id="fixture-client.apps.googleusercontent.com",
        client_secret="secret",
        redirect_uri="https://app.example/auth/google/callback",
        data_dir=tmp_path,
    )
    assert "secure_redirect_uri" in https_without_secure_mode.status()["missing_fields"]
    invalid_domain = GoogleConfig(
        enabled=True,
        client_id="fixture-client.apps.googleusercontent.com",
        client_secret="secret",
        redirect_uri="http://localhost:8000/auth/google/callback",
        data_dir=tmp_path,
        allowed_domain="not a domain",
    )
    assert "allowed_domain" in invalid_domain.status()["missing_fields"]
    secure_config = GoogleConfig(
        enabled=True,
        client_id="fixture-client.apps.googleusercontent.com",
        client_secret="secret",
        redirect_uri="https://app.example/auth/google/callback",
        data_dir=tmp_path,
        secure_deployment=True,
    )
    assert secure_config.status()["ready"] is True
    assert secure_config.cookie_secure is True


def test_allowed_hosted_domain_is_enforced(setup):
    from dataclasses import replace

    clock, store, repository, auth, provider, _service = setup
    config = replace(
        GoogleConfig(
            enabled=True,
            client_id="fixture-client.apps.googleusercontent.com",
            client_secret="fixture-client-secret",
            redirect_uri="http://localhost:8000/auth/google/callback",
            data_dir=store.data_dir,
        ),
        allowed_domain="example.edu",
    )
    service = GoogleIdentityService(
        auth, repository, config, key=b"k" * 32, clock=clock, transport=provider
    )
    started, params = _start(service)
    provider.claims = _claims(clock, params, hd="attacker.example")
    with pytest.raises(GoogleIdentityError, match="google_domain_rejected"):
        service.callback(started.flow_cookie, params["state"], "synthetic-code")


def test_unlink_removes_only_current_accounts_google_identity(setup):
    clock, _store, repository, auth, _provider, service = setup
    repository.link_subject(
        auth.actor.actor_id, google_subject_hash("subject-to-unlink"), clock.now
    )
    assert service.is_linked("valid-session") is True
    service.unlink("valid-session")
    assert service.is_linked("valid-session") is False
    assert repository.account_for_subject(google_subject_hash("subject-to-unlink")) is None
    assert service.unlink("valid-session") is None


def test_config_defaults_and_repository_validation(tmp_path):
    incomplete = GoogleConfig()
    assert incomplete.cookie_secure is True
    assert set(incomplete.status()["missing_fields"]) == {
        "enabled",
        "client_id",
        "client_secret",
        "redirect_uri",
        "data_dir",
        "secure_redirect_uri",
    }
    with pytest.raises(ValueError, match="identity repository storage required"):
        GoogleIdentityService(FakeAuth(), object(), incomplete)


def test_invalid_signed_flow_shapes_and_maximum_cookie_are_rejected(setup):
    _clock, _store, _repository, _auth, _provider, service = setup

    def signed(claims: dict[str, object]) -> str:
        payload = _b64(json.dumps(claims, separators=(",", ":")).encode())
        body = f"v1.{payload}"
        signature = _b64(hmac.new(b"k" * 32, body.encode("ascii"), hashlib.sha256).digest())
        return f"{body}.{signature}"

    started, params = _start(service)
    payload = started.flow_cookie.split(".")[1]
    valid = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
    malformed_shapes = [
        {**valid, "unexpected": "field"},
        {**valid, "issued_at": True},
        {**valid, "v": 2},
        {**valid, "nonce": ""},
    ]
    for claims in malformed_shapes:
        with pytest.raises(GoogleIdentityError, match="google_flow_invalid"):
            service.callback(signed(claims), params["state"], "code")
    with pytest.raises(GoogleIdentityError, match="google_flow_invalid"):
        service.callback("x" * 4097, params["state"], "code")
    service._random_bytes = lambda _size: b"x" * 4096
    with pytest.raises(GoogleIdentityError, match="google_flow_invalid"):
        service.start()


def test_jwt_header_and_jwks_policy_reject_unsupported_shapes(setup):
    _clock, _store, _repository, _auth, _provider, service = setup
    for header in (
        {"alg": "none", "kid": "fixture-kid"},
        {"alg": "HS256", "kid": "fixture-kid"},
        {"alg": "RS256", "kid": "fixture-kid", "jku": "https://attacker.example/jwks"},
        {"alg": "RS256"},
    ):
        token = f"{_b64(json.dumps(header).encode())}.{_b64(b'{}')}.{_b64(b'sig')}"
        with pytest.raises(ValueError):
            service._verified_claims(token)

    class InvalidJwks:
        def request_json(self, *_args, **_kwargs):
            return {"keys": "invalid"}

    service._transport = InvalidJwks()
    with pytest.raises(ValueError, match="invalid jwks"):
        service._refresh_jwks()


def test_unlink_and_link_status_require_an_active_session(setup):
    _clock, _store, _repository, _auth, _provider, service = setup
    with pytest.raises(GoogleIdentityError, match="session_unavailable"):
        service.unlink("unknown")
    with pytest.raises(GoogleIdentityError, match="session_unavailable"):
        service.is_linked("unknown")


def test_start_and_callback_input_failures_do_not_reach_provider(setup):
    clock, _store, _repository, auth, provider, service = setup
    with pytest.raises(GoogleIdentityError, match="google_flow_invalid"):
        service.start("signup")
    with pytest.raises(GoogleIdentityError, match="session_unavailable"):
        service.start("link")
    with pytest.raises(GoogleIdentityError, match="session_unavailable"):
        service.start("link", "unknown-session")

    with pytest.raises(GoogleIdentityError, match="google_flow_invalid"):
        service.callback("", "bad", "code")
    started, params = _start(service)
    with pytest.raises(GoogleIdentityError, match="google_flow_invalid"):
        service.callback(started.flow_cookie, "different-valid-state-value-012345678901", "code")
    with pytest.raises(GoogleIdentityError, match="google_flow_invalid"):
        service.callback(started.flow_cookie, params["state"], "bad\ncode")
    assert provider.requests == []

    link_started, link_params = _start(service, "link", "valid-session")
    with pytest.raises(GoogleIdentityError, match="session_unavailable"):
        service.callback(link_started.flow_cookie, link_params["state"], "code")
    assert not auth.issued


def test_provider_errors_and_malformed_assertions_are_safe(setup):
    clock, _store, _repository, _auth, provider, service = setup

    class ProviderFailure:
        def request_json(self, *_args, **_kwargs):
            raise RuntimeError("secret provider response")

    service._transport = ProviderFailure()
    started, params = _start(service)
    with pytest.raises(GoogleIdentityError, match="google_provider_unavailable") as error:
        service.callback(started.flow_cookie, params["state"], "code")
    assert "secret provider response" not in str(error.value)
    assert error.value.__cause__ is None

    service._transport = provider
    started, params = _start(service)
    provider.request_json = lambda *_args, **_kwargs: {"access_token": "ignored"}
    with pytest.raises(GoogleIdentityError, match="google_assertion_invalid"):
        service.callback(started.flow_cookie, params["state"], "code")


def test_bad_subject_future_issued_token_and_unknown_jwk_are_rejected(setup):
    clock, _store, _repository, _auth, provider, service = setup
    started, params = _start(service)
    provider.claims = _claims(clock, params, sub="")
    with pytest.raises(GoogleIdentityError, match="google_assertion_invalid"):
        service.callback(started.flow_cookie, params["state"], "code")

    started, params = _start(service)
    provider.claims = _claims(clock, params, iat=int(clock.now.timestamp()) + 120)
    with pytest.raises(GoogleIdentityError, match="google_assertion_invalid"):
        service.callback(started.flow_cookie, params["state"], "code")

    started, params = _start(service)
    provider.claims = _claims(clock, params)
    provider.kid = "not-in-jwks"
    provider.request_json = lambda method, url, **kwargs: (
        {"id_token": provider.jwt(provider.claims)} if url.endswith("/token") else {"keys": []}
    )
    with pytest.raises(GoogleIdentityError, match="google_assertion_invalid"):
        service.callback(started.flow_cookie, params["state"], "code")


def test_injected_verifier_still_requires_claim_validation(setup):
    clock, _store, repository, auth, provider, _service = setup
    config = GoogleConfig(
        enabled=True,
        client_id="fixture-client.apps.googleusercontent.com",
        client_secret="fixture-client-secret",
        redirect_uri="http://localhost:8000/auth/google/callback",
        data_dir=repository.storage.data_dir,
    )
    identity = GoogleIdentityService(
        auth,
        repository,
        config,
        key=b"k" * 32,
        clock=clock,
        transport=provider,
        verifier=lambda _token: {"iss": "wrong"},
    )
    started, params = _start(identity)
    provider.request_json = lambda *_args, **_kwargs: {"id_token": "injected-test-token"}
    with pytest.raises(GoogleIdentityError, match="google_assertion_invalid"):
        identity.callback(started.flow_cookie, params["state"], "code")


def test_link_session_is_rechecked_after_provider_exchange(setup):
    clock, _store, _repository, auth, provider, service = setup
    started, params = _start(service, "link", "valid-session")
    provider.claims = _claims(clock, params)
    original_request = provider.request_json

    def revoke_during_exchange(method, url, **kwargs):
        response = original_request(method, url, **kwargs)
        if url.endswith("/token"):
            auth.tokens.pop("valid-session")
        return response

    provider.request_json = revoke_during_exchange
    with pytest.raises(GoogleIdentityError, match="session_unavailable"):
        service.callback(started.flow_cookie, params["state"], "code", "valid-session")


def test_runtime_key_is_private_and_unsafe_key_file_disables_service(tmp_path):
    store = SQLiteStore(tmp_path / "key-data")
    store.connection.execute(
        "INSERT INTO accounts(actor_id,role,password_hash) VALUES(?,?,?)",
        ("fixture-student", "student", "synthetic-password-hash"),
    )
    config = GoogleConfig(
        enabled=True,
        client_id="fixture-client.apps.googleusercontent.com",
        client_secret="fixture-secret",
        redirect_uri="http://localhost:8000/auth/google/callback",
        data_dir=tmp_path / "key-data",
    )
    service = GoogleIdentityService(FakeAuth(), GoogleIdentityRepository(store), config)
    key_path = tmp_path / "key-data" / "google-flow-hmac.key"
    assert key_path.stat().st_mode & 0o777 == 0o600
    assert service.status()["ready"] is True
    key_path.chmod(0o644)
    unsafe = GoogleIdentityService(FakeAuth(), GoogleIdentityRepository(store), config)
    assert unsafe.status()["ready"] is False
    store.close()


def test_runtime_key_refuses_symlink(tmp_path):
    data_dir = tmp_path / "symlink-data"
    initial = SQLiteStore(data_dir)
    initial.close()
    target = tmp_path / "unprotected-key"
    target.write_bytes(b"k" * 32)
    (data_dir / "google-flow-hmac.key").symlink_to(target)
    store = SQLiteStore(data_dir)
    store.connection.execute(
        "INSERT INTO accounts(actor_id,role,password_hash) VALUES(?,?,?)",
        ("fixture-student", "student", "synthetic-password-hash"),
    )
    config = GoogleConfig(
        enabled=True,
        client_id="fixture-client.apps.googleusercontent.com",
        client_secret="fixture-secret",
        redirect_uri="http://localhost:8000/auth/google/callback",
        data_dir=data_dir,
    )
    service = GoogleIdentityService(FakeAuth(), GoogleIdentityRepository(store), config)
    assert service.status()["ready"] is False
    store.close()


def test_flow_reservation_is_consumed_once_across_sqlite_connections(tmp_path):
    data_dir = tmp_path / "concurrent-data"
    first = SQLiteStore(data_dir)
    repository = GoogleIdentityRepository(first)
    now = datetime(2026, 10, 15, tzinfo=UTC)
    repository.reserve_flow("a" * 64, now + timedelta(minutes=10), now=now)
    first.close()

    def consume() -> bool:
        store = SQLiteStore(data_dir)
        try:
            return GoogleIdentityRepository(store).consume_flow("a" * 64, now)
        finally:
            store.close()

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(lambda _index: consume(), range(2)))
    assert sorted(outcomes) == [False, True]


def test_google_flow_storage_expires_and_discards_malformed_rows(tmp_path):
    store = SQLiteStore(tmp_path / "flow-storage")
    repository = GoogleIdentityRepository(store)
    now = datetime(2026, 10, 15, tzinfo=UTC)
    prefix = repository.FLOW_PREFIX
    store.connection.execute(
        "INSERT INTO runtime_settings VALUES(?,?,1,?,?,?)",
        (
            prefix + "expired",
            json.dumps({"expires_at": (now - timedelta(seconds=1)).isoformat()}),
            "v1",
            "test",
            now.isoformat(),
        ),
    )
    store.connection.execute(
        "INSERT INTO runtime_settings VALUES(?,?,1,?,?,?)",
        (prefix + "malformed", "not-json", "v1", "test", now.isoformat()),
    )
    store.connection.execute(
        "INSERT INTO runtime_settings VALUES(?,?,1,?,?,?)",
        ("unrelated-setting", "{}", "v1", "test", now.isoformat()),
    )
    repository.reserve_flow("new-state", now + timedelta(minutes=10), now=now)
    assert (
        store.connection.execute(
            "SELECT 1 FROM runtime_settings WHERE key=?", (prefix + "expired",)
        ).fetchone()
        is None
    )
    assert (
        store.connection.execute(
            "SELECT 1 FROM runtime_settings WHERE key=?", (prefix + "malformed",)
        ).fetchone()
        is None
    )
    assert store.connection.execute(
        "SELECT 1 FROM runtime_settings WHERE key='unrelated-setting'"
    ).fetchone()

    store.connection.execute(
        "INSERT INTO runtime_settings VALUES(?,?,1,?,?,?)",
        (prefix + "invalid-consume", "{}", "v1", "test", now.isoformat()),
    )
    assert repository.consume_flow("invalid-consume", now) is False
    assert repository.consume_flow("new-state", now + timedelta(minutes=10)) is False
    store.close()
