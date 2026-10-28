"""Layer 1 -- UNIT: the signed flow cookie and PKCE of sign-in with Google (D036).

Pure functions only. The PKCE transform is checked against the worked example
of RFC 7636, Appendix B, so "S256" here means what the standard means by it,
not what this module happens to compute.

Test case ids (TC-GG-Uxx) are listed in `docs/test/TEST_PLAN_D036.md`.
"""

from __future__ import annotations

import base64
import json
import re
from dataclasses import asdict, replace

import pytest

from aicefr.auth import google

pytestmark = pytest.mark.unit

KEY = bytes(range(32))


def test_the_flow_cookie_is_signed_and_any_change_breaks_it():
    flow = google.new_flow("link", "/account", "acc-victim")
    cookie = google.encode_flow(flow, KEY)
    payload, signature = cookie.split(".")

    assert google.decode_flow(cookie, KEY) == flow
    # The same flow under another deployment's key, or with no signature at all.
    assert google.decode_flow(cookie, bytes(32)) is None
    assert google.decode_flow(payload, KEY) is None
    # One character changed in either half.
    flipped = payload[:-1] + ("A" if payload[-1] != "A" else "B")
    assert google.decode_flow(f"{flipped}.{signature}", KEY) is None
    assert google.decode_flow(f"{payload}.{signature[:-1]}x", KEY) is None
    # A flow written by someone else -- another account to link to, their own
    # PKCE verifier -- signed with a key they made up.
    theirs = replace(flow, account_id="acc-other", verifier="v" * 64)
    raw = json.dumps(asdict(theirs)).encode()
    forged = base64.urlsafe_b64encode(raw).decode().rstrip("=")
    assert google.decode_flow(f"{forged}.{signature}", KEY) is None
    assert google.decode_flow(google.encode_flow(theirs, b"made-up"), KEY) is None
    # Not even read: bytes a browser may send that are not ASCII.
    assert google.decode_flow(cookie + "é", KEY) is None


def test_the_pkce_challenge_is_s256_as_rfc_7636_shows():
    # RFC 7636, Appendix B: this verifier gives this challenge.
    verifier = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
    assert google._challenge(verifier) == "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM"
    # A fresh verifier: 43 to 128 characters from the unreserved set, and new
    # every time, as are state and nonce.
    flows = [google.new_flow("login", "") for _ in range(20)]
    for flow in flows:
        assert re.fullmatch(r"[A-Za-z0-9._~-]{43,128}", flow.verifier)
    assert len({f.verifier for f in flows}) == len({f.state for f in flows}) == 20
    url = google.authorization_url(
        google.GoogleConfig("c.apps.googleusercontent.com", "s"), flows[0], "http://localhost/cb"
    )
    assert "code_challenge_method=S256" in url and flows[0].verifier not in url
    assert google.cookie_name(True) == "__Host-aicefr_oauth"
    assert google.cookie_name(False) == "aicefr_oauth"
