"""D088 unit layer: Web Push without a browser.

* only a browser's push service is accepted as an endpoint (the server sends a
  request there: anything else would let a learner aim it at its own network);
* a generated VAPID key pair is in the form browsers and pywebpush take, and a
  real message is signed and encrypted so that only the browser reads it;
* the sender reaches every browser of the account, forgets the ones the push
  service says are gone, and carries a title, a sentence and an address only.
"""

from __future__ import annotations

import base64
import json

import pytest

from aicefr.notify.push import PushSender, _webpush_sender, generate_vapid_keys
from aicefr.services.core.assessment.push_api import push_service
from aicefr.storage.push_repository import PushSubscription

pytestmark = pytest.mark.unit


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


@pytest.mark.parametrize(
    "endpoint, ok",
    [
        ("https://fcm.googleapis.com/fcm/send/abc:def", True),
        ("https://updates.push.services.mozilla.com/wpush/v2/gAAA", True),
        ("https://web.push.apple.com/QGuQ", True),
        ("https://wns2-par02p.notify.windows.com/w/?token=x", True),
        ("http://fcm.googleapis.com/fcm/send/abc", False),  # not HTTPS
        ("https://fcm.googleapis.com:8443/fcm/send/abc", False),  # another port
        ("https://fcm.googleapis.com.evil.example/fcm/send/abc", False),
        ("https://user:pw@fcm.googleapis.com/fcm/send/abc", False),
        ("https://localhost/internal", False),
        ("https://169.254.169.254/latest/meta-data/", False),  # the cloud's metadata
        ("https://core:8000/internal/identity/session", False),
        ("not a url at all", False),
    ],
)
def test_only_a_browsers_push_service_is_an_endpoint(endpoint, ok):
    assert push_service(endpoint) is ok


def test_a_vapid_key_pair_is_a_p256_point_and_its_scalar():
    public, private = generate_vapid_keys()
    point, scalar = _unb64(public), _unb64(private)
    assert len(point) == 65 and point[0] == 4  # what a browser takes as applicationServerKey
    assert len(scalar) == 32
    assert "=" not in public + private
    assert generate_vapid_keys() != (public, private)


def test_a_real_message_is_signed_and_only_the_browser_can_read_it(monkeypatch):
    """pywebpush end to end, the push service replaced by a capture."""
    import http_ece
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ec

    browser = ec.generate_private_key(ec.SECP256R1())
    secret = b"0123456789abcdef"
    info = {
        "endpoint": "https://fcm.googleapis.com/fcm/send/test",
        "keys": {
            "p256dh": _b64(
                browser.public_key().public_bytes(
                    serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
                )
            ),
            "auth": _b64(secret),
        },
    }
    sent = {}

    class Answer:
        status_code = 201
        text = ""
        headers: dict = {}

    def post(url, data=None, headers=None, timeout=None, **_kw):
        sent.update(url=url, data=data, headers=headers)
        return Answer()

    monkeypatch.setattr("pywebpush.requests.post", post)
    public, private = generate_vapid_keys()
    payload = json.dumps({"title": "Bài nói đã chấm xong", "url": "/report/r1"}, ensure_ascii=False)
    status = _webpush_sender(private, "mailto:no-reply@speakup.fit")(info, payload)

    assert status == 201 and sent["url"] == info["endpoint"]
    assert sent["headers"]["content-encoding"] == "aes128gcm"
    assert sent["headers"]["ttl"] == str(24 * 3600)
    # Signed with our key: the push service checks it against the public key.
    assert f"k={public}" in sent["headers"]["authorization"]
    assert payload.encode() not in sent["data"]  # the push service sees ciphertext
    plain = http_ece.decrypt(sent["data"], private_key=browser, auth_secret=secret)
    assert json.loads(plain) == json.loads(payload)


class _Store:
    def __init__(self, subs):
        self.subs = subs
        self.dropped = []

    def of(self, account_id):
        return [s for s in self.subs if s.account_id == account_id]

    def drop(self, endpoint):
        self.dropped.append(endpoint)


def _sub(n: int, account: str = "a1") -> PushSubscription:
    return PushSubscription(f"https://fcm.googleapis.com/fcm/send/{n}", account, "p" * 87, "a" * 22)


def test_the_sender_reaches_every_browser_and_forgets_the_gone_ones():
    store = _Store([_sub(1), _sub(2), _sub(3), _sub(4), _sub(9, "someone-else")])
    answers = {"1": 201, "2": 410, "3": 404, "4": 500}
    sent = []

    def send(info, data):
        sent.append((info["endpoint"].rsplit("/", 1)[1], json.loads(data)))
        if info["endpoint"].endswith("/4"):
            raise ConnectionError("the push service is down")
        return answers[info["endpoint"].rsplit("/", 1)[1]]

    push = PushSender(store, "pub", "priv", "mailto:x", send=send, run=lambda job: job())
    push.notify("a1", "Bài nói đã chấm xong", "Mở để xem.", "/report/r1", "response-r1")

    assert [n for n, _ in sent] == ["1", "2", "3", "4"]  # one failing browser stops none
    assert sorted(store.dropped) == [_sub(2).endpoint, _sub(3).endpoint]  # 410 and 404 only
    assert sent[0][1] == {
        "title": "Bài nói đã chấm xong",
        "body": "Mở để xem.",
        "url": "/report/r1",
        "tag": "response-r1",
    }


def test_without_keys_or_an_account_nothing_is_sent():
    sent = []
    store = _Store([_sub(1)])
    off = PushSender(
        store, "", "", "mailto:x", send=lambda *a: sent.append(a) or 201, run=lambda j: j()
    )
    off.notify("a1", "t", "b", "/", "x")
    on = PushSender(
        store, "pub", "priv", "mailto:x", send=lambda *a: sent.append(a) or 201, run=lambda j: j()
    )
    on.notify(None, "t", "b", "/", "x")
    assert sent == [] and not off.enabled and on.enabled
