"""The daily study reminder by email (D079).

Once a day, from `AICEFR_REMINDER_HOUR` Vietnam time, a learner gets one email
when all of these hold: their email is verified, they left reminders on, they
have not spoken on their lesson path today, and there is a reason -- a streak
to keep or reviews whose day has come (the same rules as the reminders on the
home screen, `practice/nudges.py`). Nobody gets two in a day: the day is taken
on the account before the email goes, so two processes never both send.
"""

from __future__ import annotations

import logging
from datetime import datetime

from aicefr.notify.email import EmailError, EmailSender
from aicefr.notify.messages import reminder_email, unsubscribe_token
from aicefr.practice.streak import LOCAL_TZ

logger = logging.getLogger(__name__)


def reasons(daily: dict, reviews_due: int) -> list[str]:
    """Why to remind this learner today; empty means no email."""
    if daily.get("practiced_today"):
        return []
    out = []
    if daily.get("streak", 0) >= 1:
        out.append(
            f"Chuỗi {daily['streak']} ngày luyện nói của bạn còn chờ hôm nay "
            "(mỗi tuần có một ngày nghỉ mà không mất chuỗi)."
        )
    if reviews_due > 0:
        out.append(f"Bạn có {reviews_due} mục ôn tập đã đến ngày.")
    return out


def send_due(
    now: datetime,
    hour: int,
    auth,  # aicefr.storage.auth_repository.AuthRepository
    learning,  # the learning facade (daily, reviews_due)
    sender: EmailSender,
    site: str,
    secret: bytes,
) -> int:
    """Send today's reminders that are due; how many went out."""
    local = now.astimezone(LOCAL_TZ)
    if hour < 0 or local.hour < hour:
        return 0
    day = local.date().isoformat()
    sent = 0
    for row in auth.reminder_candidates(day):
        who = row["account_id"]
        try:
            why = reasons(
                learning.daily(account_id=who, goal_seconds=row.get("daily_goal_s") or 180),
                learning.reviews_due(account_id=who),
            )
        except Exception:  # noqa: BLE001 - one learner's facts must not stop the others
            logger.exception("reminder: could not read %s", row["pseudonym"])
            continue
        if not why or not auth.claim_reminder(who, day):
            continue
        stop = f"{site}/api/v1/email/unsubscribe?t={unsubscribe_token(secret, who)}"
        email = reminder_email(
            row["email"], row.get("full_name") or row["pseudonym"], why, site, stop
        )
        try:
            sender.send(email)
            sent += 1
        except EmailError as e:
            logger.warning("reminder to %s not sent: %s", row["pseudonym"], e)
    return sent
