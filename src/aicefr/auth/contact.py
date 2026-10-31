"""The two things that make an account a person's (D071): an email and a full name.

The email is how a person signs in, with a password or with Google, and the
key that makes the two one account. It is kept lower case, so "An@x.vn" and
"an@x.vn" are one person. The full name is what a teacher reads in the class
list and the review queue.

The pseudonym stays, but only inside: it is what research exports and the
audit log carry (FR-33), so a name never leaves the system with a recording.
"""

from __future__ import annotations

import re
import unicodedata

MAX_EMAIL = 254
MAX_NAME = 80
# Deliberately plain: one @, something before it, a dotted domain after it,
# no spaces. Whether the address really receives mail is Google's to prove
# (`email_verified`); a pattern cannot.
EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def normalize_email(raw: str) -> str:
    """The email as stored, or ValueError worded for the person."""
    value = (raw or "").strip().lower()
    if len(value) > MAX_EMAIL or not EMAIL.match(value):
        raise ValueError("email không hợp lệ")
    return value


def normalize_name(raw: str) -> str:
    """The full name as stored -- spaces collapsed, NFC -- or ValueError."""
    value = " ".join(unicodedata.normalize("NFC", raw or "").split())
    if not value:
        raise ValueError("hãy nhập họ và tên")
    if len(value) > MAX_NAME:
        raise ValueError(f"họ và tên dài tối đa {MAX_NAME} ký tự")
    if any(unicodedata.category(c).startswith("C") for c in value):
        raise ValueError("họ và tên có ký tự không hợp lệ")
    return value


def looks_like_email(identifier: str) -> bool:
    """Whether a sign-in name is an email rather than a legacy pseudonym."""
    return "@" in (identifier or "")
