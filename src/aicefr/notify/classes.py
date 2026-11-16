"""Email about classes (D109): the invitation, and word that a student joined.

The assessment service, which keeps the classes, publishes `classroom.invited`
and `classroom.joined` (`contracts.py`); these handlers, in the identity
service where the addresses are, turn each into email -- the same Observer as
the payment email (D096). Only to a verified address that has a mailbox: an
address nobody proved theirs could be anyone's, and a demo address only
bounces. The invitation is the step a student needs to answer, and the joined
note is what a teacher needs to know, so neither depends on the study reminders
being on.

The bus delivers an event at least once. A key per event, claimed before
sending, keeps a second delivery from sending a second email; an email the
provider refused is logged and not retried.
"""

from __future__ import annotations

import logging

from aicefr.notify.email import EmailError, EmailSender, has_mailbox
from aicefr.notify.messages import class_invite_email, class_joined_email
from aicefr.storage.db import now_iso, setting_once

logger = logging.getLogger(__name__)

KEY = "class_email:"


def _reachable(who: dict | None) -> bool:
    return bool(who) and has_mailbox(who.get("email")) and bool(who.get("email_verified"))


def _name(who: dict | None) -> str:
    if not who:
        return "Giảng viên"
    return who.get("full_name") or who.get("email") or "Giảng viên"


def _send(auth, sender: EmailSender, key: str, email) -> bool:
    if not setting_once(auth.db, KEY + key, now_iso())[1]:
        return False  # delivered before
    try:
        sender.send(email)
    except EmailError as e:
        logger.warning("class email %s not sent: %s", key, e)
        return False
    return True


def on_invited(payload: dict, auth, sender: EmailSender, site: str) -> bool:
    """Tell the student a teacher invited them; True when the email went out."""
    student = auth.get(str(payload.get("account_id", "")))
    if not _reachable(student):
        return False  # the sidebar badge and the reminder still say it
    email = class_invite_email(
        student["email"],
        student.get("full_name") or "bạn",
        str(payload["class_name"]),
        _name(auth.get(str(payload.get("by", "")))),
        site,
    )
    key = f"invite:{payload['class_id']}:{student['account_id']}:{payload.get('at', '')}"
    return _send(auth, sender, key, email)


def on_joined(payload: dict, auth, sender: EmailSender, site: str) -> int:
    """Tell each teacher of the class that a student joined; how many emails went out."""
    student = auth.get(str(payload.get("account_id", "")))
    if student is None:
        return 0
    sent = 0
    for teacher_id in payload.get("teacher_ids") or []:
        teacher = auth.get(str(teacher_id))
        if not _reachable(teacher):
            continue
        email = class_joined_email(
            teacher["email"],
            teacher.get("full_name") or "thầy cô",
            student.get("full_name") or student.get("email") or "Một sinh viên",
            student.get("email") or "",
            str(payload["class_name"]),
            str(payload["class_id"]),
            str(payload.get("via", "invite")),
            int(payload.get("members") or 0),
            site,
        )
        at = payload.get("at", "")
        key = f"joined:{payload['class_id']}:{student['account_id']}:{teacher_id}:{at}"
        sent += _send(auth, sender, key, email)
    return sent
