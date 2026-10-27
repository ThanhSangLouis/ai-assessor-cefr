"""Layer 1 -- UNIT: the rules of Google sign-in and of session labels (D029).

Pure functions only: no app, no database, no network. The token checks are
the part of sign-in with Google that decides who gets in, so each claim that
can be wrong has its own refusal here.
"""

from __future__ import annotations

import base64
import json
import time
import urllib.error

import pytest

from aicefr.auth import google
from aicefr.auth.sessions import device_label

pytestmark = pytest.mark.unit

CONFIG = google.GoogleConfig(client_id="client-1", client_secret="s" * 16)
NONCE = "nonce-1"


def token(**claims) -> str:
    now = int(time.time())
    body = {
        "iss": "https://accounts.google.com",
        "aud": "client-1",
        "sub": "123",
        "iat": now,
        "exp": now + 600,
        "nonce": NONCE,
    }
    body.update(claims)
    body = {k: v for k, v in body.items() if v is not None}
    raw = base64.urlsafe_b64encode(json.dumps(body).encode()).decode().rstrip("=")
    return f"eyJhbGciOiJSUzI1NiJ9.{raw}.sig"


def test_a_good_token_gives_a_hash_of_the_subject_and_nothing_else_kept():
    who = google.verify_id_token(CONFIG, token(email="a@b.vn"), NONCE)
    assert who.subject_hash == google.subject_hash("123")
    assert len(who.subject_hash) == 64 and "123" not in who.subject_hash
    assert who.email == "a@b.vn"


@pytest.mark.parametrize(
    "claims",
    [
        {"iss": "https://accounts.google.com.evil"},
        {"aud": "client-2"},
        {"aud": ["client-1", "client-2"], "azp": "client-2"},
        {"exp": int(time.time()) - 3600},
        {"iat": int(time.time()) + 3600},
        {"nonce": "nonce-2"},
        {"nonce": None},
        {"sub": None},
        {"exp": None},
    ],
)
def test_each_wrong_claim_is_refused(claims):
    with pytest.raises(google.GoogleError) as e:
        google.verify_id_token(CONFIG, token(**claims), NONCE)
    assert e.value.code == "token"


def test_both_spellings_of_the_google_issuer_are_accepted():
    for issuer in ("https://accounts.google.com", "accounts.google.com"):
        google.verify_id_token(CONFIG, token(iss=issuer), NONCE)


def test_a_token_for_several_audiences_needs_us_as_authorised_party():
    google.verify_id_token(CONFIG, token(aud=["client-1", "client-2"], azp="client-1"), NONCE)


def test_a_malformed_token_is_refused():
    for bad in ("not-a-jwt", "a.b", "a.%%%.c", "a.WzFd.c"):
        with pytest.raises(google.GoogleError):
            google.verify_id_token(CONFIG, bad, NONCE)


def test_a_non_ascii_nonce_is_refused_not_crashed():
    with pytest.raises(google.GoogleError):
        google.verify_id_token(CONFIG, token(nonce="nonce-é"), NONCE)


def test_the_domain_rule_needs_the_hd_claim_and_a_verified_email():
    school = google.GoogleConfig("client-1", "s" * 16, allowed_domain="example.edu.vn")
    with pytest.raises(google.GoogleError) as e:
        google.verify_id_token(school, token(email_verified=True), NONCE)
    assert e.value.code == "domain"
    with pytest.raises(google.GoogleError) as e:
        google.verify_id_token(school, token(hd="example.edu.vn", email_verified=False), NONCE)
    assert e.value.code == "unverified"
    google.verify_id_token(school, token(hd="example.edu.vn", email_verified=True), NONCE)


def test_a_flow_survives_the_cookie_and_expires_after_ten_minutes():
    key = b"k" * 32
    flow = google.new_flow("link", "/my-progress", "acc-1")
    back = google.decode_flow(google.encode_flow(flow, key), key)
    assert back == flow
    assert google.decode_flow(google.encode_flow(flow, key), key, now=flow.started + 601) is None
    for junk in (None, "", "%%%", "e30", base64.urlsafe_b64encode(b"[1,2]").decode()):
        assert google.decode_flow(junk, key) is None


def test_only_same_site_paths_are_kept_as_where_to_go_next():
    assert google.safe_next("/practice?x=1") == "/practice?x=1"
    for bad in ("https://evil.example", "//evil.example", "/\\evil.example", "javascript:x", None):
        assert google.safe_next(bad) == ""


def test_a_failed_exchange_says_so_without_leaking_the_reason():
    def down(_url, _fields):
        raise urllib.error.URLError("connection refused")

    flow = google.new_flow("login", "")
    with pytest.raises(google.GoogleError) as e:
        google.exchange_code(CONFIG, "code", flow, "http://localhost/cb", post=down)
    assert e.value.code == "exchange"
    with pytest.raises(google.GoogleError):
        google.exchange_code(CONFIG, "code", flow, "http://localhost/cb", post=lambda *_: {})


@pytest.mark.parametrize(
    "agent, label",
    [
        (
            "Mozilla/5.0 (Windows NT 10.0) AppleWebKit/537.36 Chrome/141 Safari/537.36 Edg/141",
            "Edge · Windows",
        ),
        (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15) AppleWebKit Chrome/141 Safari/537",
            "Chrome · macOS",
        ),
        (
            "Mozilla/5.0 (X11; Linux x86_64; rv:131.0) Gecko/20100101 Firefox/131.0",
            "Firefox · Linux",
        ),
        (
            "Mozilla/5.0 (Linux; Android 15) AppleWebKit Chrome/141 Mobile Safari/537",
            "Chrome · Android",
        ),
        (
            "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0) AppleWebKit Version/18.0 Safari/604",
            "Safari · iPhone/iPad",
        ),
        ("curl/8.7.1", "Trình duyệt khác · hệ điều hành khác"),
        (None, None),
    ],
)
def test_a_session_gets_a_coarse_device_name_not_a_fingerprint(agent, label):
    assert device_label(agent) == label
