"""Email the buyer when a run-pack order is settled (D096).

The billing service publishes `billing.order_settled` once per order that ends
paid or failed; this handler, in the identity service where the addresses
are, turns it into one email. Only to a verified address, as with reminders:
an address nobody proved theirs could be anyone's. A payment email is part of
the purchase, not a reminder, so turning reminders off does not stop it.

The bus delivers an event at least once (Redis Streams). A key per order and
outcome, claimed before sending, keeps a second delivery from sending a second
email; an email the provider refused is logged and not retried, as a reminder.
"""

from __future__ import annotations

import logging

from aicefr.notify.email import EmailError, EmailSender
from aicefr.notify.messages import payment_email
from aicefr.storage.db import now_iso, setting_once

logger = logging.getLogger(__name__)

KEY = "payment_email:"


def on_order_settled(
    payload: dict,
    auth,  # aicefr.storage.auth_repository.AuthRepository
    sender: EmailSender,
    site: str,
) -> bool:
    """Send the buyer's email for one settled order; True when one went out."""
    if payload.get("status") not in ("paid", "failed"):
        return False
    who = auth.get(str(payload.get("account_id", "")))
    if who is None or not who.get("email") or not who.get("email_verified"):
        return False  # no address to trust: the result page and receipt still say it
    key = f"{KEY}{payload['order_id']}:{payload['status']}"
    if not setting_once(auth.db, key, now_iso())[1]:
        return False  # delivered before
    email = payment_email(who["email"], who.get("full_name") or "bạn", payload, site)
    try:
        sender.send(email)
    except EmailError as e:
        logger.warning("payment email for %s not sent: %s", payload["order_id"], e)
        return False
    return True
