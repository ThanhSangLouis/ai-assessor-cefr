"""Web Push (D088): a notification on the device when no SpeakUp tab is open.

The live stream (D086) tells an open tab. When the learner has closed it, the
same two events -- a response scored, a response reviewed -- go to every
browser the learner allowed, as a Web Push message:

* the server signs each request with its VAPID key pair (RFC 8292), so a push
  service only accepts messages for these subscriptions from this server;
* the message is encrypted for the browser (RFC 8291, aes128gcm): the push
  service carries it without reading it. It holds a title, a sentence and the
  address to open -- no score, no name;
* sending is an HTTPS call to the push service, so it runs on two threads of
  its own: the action that caused it never waits, and never fails because of
  it. A browser the push service no longer knows (404, 410) is forgotten.

Without AICEFR_VAPID_PUBLIC_KEY and AICEFR_VAPID_PRIVATE_KEY nothing is sent
and the account page does not offer notifications.

`pywebpush` (MPL-2.0) does the signing and the encryption.
"""

from __future__ import annotations

import base64
import json
import logging
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor

from aicefr.storage.push_repository import PushRepository, PushSubscription

logger = logging.getLogger(__name__)

# A message the device cannot take now waits this long at the push service.
TTL_S = 24 * 3600
TIMEOUT_S = 10.0
GONE = (404, 410)

# (subscription info, JSON payload) -> HTTP status of the push service.
Send = Callable[[dict, str], int]


def generate_vapid_keys() -> tuple[str, str]:
    """A new VAPID key pair: (public, private), both base64url without padding.

    The public key is the uncompressed P-256 point the browser takes as
    `applicationServerKey`; the private key is the raw 32-byte scalar.
    """
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ec

    key = ec.generate_private_key(ec.SECP256R1())
    public = key.public_key().public_bytes(
        serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
    )
    private = key.private_numbers().private_value.to_bytes(32, "big")
    return _b64(public), _b64(private)


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _webpush_sender(private_key: str, subject: str) -> Send:
    from pywebpush import WebPushException, webpush

    def send(info: dict, data: str) -> int:
        try:
            r = webpush(
                subscription_info=info,
                data=data,
                vapid_private_key=private_key,
                vapid_claims={"sub": subject},
                ttl=TTL_S,
                timeout=TIMEOUT_S,
                headers={"Urgency": "normal"},
            )
        except WebPushException as e:
            return e.response.status_code if e.response is not None else 0
        return r.status_code

    return send


class PushSender:
    def __init__(
        self,
        store: PushRepository,
        public_key: str,
        private_key: str,
        subject: str,
        *,
        send: Send | None = None,
        run: Callable[[Callable[[], None]], object] | None = None,
    ) -> None:
        self.store = store
        self.public_key = public_key
        self.enabled = bool(public_key and private_key)
        self._send = send or (_webpush_sender(private_key, subject) if self.enabled else None)
        if run is None:
            pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="push")
            run = pool.submit
        self._run = run

    def notify(self, account_id: str | None, title: str, body: str, url: str, tag: str) -> None:
        """Send to every browser of this account, on the sender's threads. Never raises."""
        if not (self.enabled and account_id):
            return
        payload = json.dumps(
            {"title": title, "body": body, "url": url, "tag": tag}, ensure_ascii=False
        )
        try:
            self._run(lambda: self._deliver(account_id, payload))
        except Exception:  # noqa: BLE001 - e.g. the pool is shutting down
            logger.exception("could not queue a push message")

    def _deliver(self, account_id: str, payload: str) -> None:
        try:
            subscriptions: list[PushSubscription] = self.store.of(account_id)
        except Exception:  # noqa: BLE001 - on a thread of its own: log, never raise
            logger.exception("could not read the push subscriptions of %s", account_id)
            return
        for sub in subscriptions:
            try:
                status = self._send(sub.info(), payload)
            except Exception:  # noqa: BLE001 - one browser, not the others
                logger.exception("push to one browser failed")
                continue
            if status in GONE:
                self.store.drop(sub.endpoint)
            elif not 200 <= status < 300:
                logger.warning("push service answered %s", status)
