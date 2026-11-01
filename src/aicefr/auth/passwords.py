"""Password hashing and verification. Implements part of FR-32 and NFR-07.

NFR-07 mandates bcrypt with a cost of at least 12, and the acceptance test is
that the hash carries the prefix "$2b$12$". Do not invent a hashing algorithm
and do not pick your own parameters here: this is the place where a mistake is
the most silent and the consequences the most severe.
"""

from __future__ import annotations

import secrets

import bcrypt

COST = 12

MIN_LENGTH = 8
# bcrypt reads at most 72 bytes of a password, and bcrypt 5 refuses longer input
# outright. Saying so at the form beats a 500 at the hashing call.
MAX_BYTES = 72

# Temporary passwords are read off a printed slip and typed once, so the
# alphabet leaves out the characters people confuse on paper: i, l, o, 0, 1.
TEMPORARY_ALPHABET = "abcdefghjkmnpqrstuvwxyz23456789"


def hash_password(password: str) -> str:
    """Hash a password and return a string safe to store in the database."""
    if not password:
        raise ValueError("password must not be empty")
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=COST)).decode("ascii")


# A real bcrypt hash of a value nobody will guess, used to spend the same time
# on a login for an account that does not exist as on one that does. Without
# it, "unknown pseudonym" answers in about 5 ms and "wrong password" in about
# 300 ms, which tells an attacker exactly which accounts are real.
DUMMY_HASH = "$2b$12$C6UzMDM.H6dfI/f/IKcEe.wt7VqQxHhpx1WHqZ8Vw0sWBQbSdpG0O"


def waste_equivalent_time(password: str) -> None:
    """Spend a bcrypt verification's worth of time and discard the result."""
    verify_password(password, DUMMY_HASH)


def verify_password(password: str, stored_hash: str) -> bool:
    """Compare a password against the stored hash.

    Every exception is caught and turned into False: a corrupted hash in the
    database must neither crash the application nor count as a successful login.
    """
    try:
        return bcrypt.checkpw(password.encode("utf-8"), stored_hash.encode("ascii"))
    except (ValueError, TypeError):
        return False


def check_new_password(new: str, pseudonym: str, current: str | None = None) -> None:
    """Raise ValueError, worded for the person choosing it, if `new` is not acceptable.

    Deliberately short: a length floor and two refusals that matter for this
    system. Composition rules ("one capital, one symbol") push people towards
    Password1! and a sticky note; length does more for a pseudonymous account
    that is already rate limited and locked after five failures (NFR-07).
    """
    if len(new) < MIN_LENGTH:
        raise ValueError(f"mật khẩu phải từ {MIN_LENGTH} ký tự trở lên")
    if len(new.encode("utf-8")) > MAX_BYTES:
        raise ValueError(f"mật khẩu dài quá {MAX_BYTES} byte")
    if new.strip().lower() == pseudonym.strip().lower():
        raise ValueError("mật khẩu không được trùng với mã tài khoản")
    if current is not None and new == current:
        raise ValueError("mật khẩu mới phải khác mật khẩu đang dùng")


def temporary_password() -> str:
    """A one-time password for a new or reset account, e.g. "k7mq-x3pa-r9tz".

    Twelve characters from a 31-symbol alphabet, about 59 bits: plenty for a
    password that has to be replaced at the first login and sits behind the
    login lockout anyway.
    """
    raw = "".join(secrets.choice(TEMPORARY_ALPHABET) for _ in range(12))
    return f"{raw[:4]}-{raw[4:8]}-{raw[8:]}"


def recovery_code() -> str:
    """A one-time code that replaces a forgotten password, e.g. "k7mq-x3pa-r9tz-c4wn" (D065).

    The system has no email address to send a reset link to (FR-33), so the
    person keeps this code instead, the way a bank's backup codes are kept.
    Sixteen characters from the same 31-symbol alphabet as a temporary
    password, about 79 bits; stored only as a bcrypt hash, and every use
    replaces it.
    """
    raw = "".join(secrets.choice(TEMPORARY_ALPHABET) for _ in range(16))
    return "-".join(raw[i : i + 4] for i in range(0, 16, 4))


def normalize_code(code: str) -> str:
    """What a person typed, as the code was hashed: lower case, no spaces, dashes kept.

    Codes are read off paper or a phone and retyped; case and stray spaces are
    not the point of the check.
    """
    raw = "".join(ch for ch in code.lower() if ch.isalnum())
    return "-".join(raw[i : i + 4] for i in range(0, len(raw), 4))
