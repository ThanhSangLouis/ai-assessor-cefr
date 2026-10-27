"""Rules for participant pseudonyms. Implements the privacy constraint of FR-01.

Lives in the auth package, not in the API schemas, because the check belongs
where a pseudonym is *created* -- account registration -- rather than where one
happens to be submitted. It used to run on a form field at submission time,
which meant two things at once: the rule was enforced in the wrong place, and a
student could submit under somebody else's pseudonym.

The rule is an allowlist, not a blocklist. A blocklist of forbidden substrings
loses by construction: it has to anticipate every spelling of every identifier,
and it lets through `<svg onload=...>`, which then runs in a teacher's browser.
"""

from __future__ import annotations

import re

# Letters, digits, hyphen and underscore. Nothing that can open an HTML tag,
# close an attribute, or look like an email address.
PATTERN = re.compile(r"^[A-Za-z0-9_-]{2,32}$")

# Kept as a second, narrower net: a pseudonym made only of allowed characters
# can still *be* a student number.
FORBIDDEN = ("mssv", "cmnd", "cccd", "sdt", "phone")


def validate_pseudonym(pseudonym: str) -> str:
    """Return the pseudonym, or raise ValueError explaining what is wrong."""
    value = pseudonym.strip()
    if not PATTERN.match(value):
        raise ValueError(
            "bút danh chỉ gồm chữ cái, chữ số, dấu gạch ngang và gạch dưới, dài từ 2 đến 32 ký tự"
        )
    low = value.lower()
    if any(token in low for token in FORBIDDEN):
        raise ValueError("bút danh không được chứa thông tin định danh thật")
    if re.fullmatch(r"\d{7,12}", value):
        raise ValueError("bút danh không được là một dãy số giống mã số sinh viên")
    return value
