"""Invariants of the browser code that no Python test can otherwise reach.

These are source-level checks. They exist because a rename broke a headline
feature -- clicking a piece of evidence to jump the audio player -- and every
test stayed green: the markup was rendered correctly, the handler was attached
correctly, and the handler read an attribute that no longer existed. Nothing
threw until a human clicked.
"""

from __future__ import annotations

import pathlib
import re

import pytest

STATIC = pathlib.Path("src/aicefr/api/static")
SCRIPTS = sorted(STATIC.glob("*.js"))
TEMPLATES = pathlib.Path("src/aicefr/api/templates")


def _dataset_names(source: str) -> set[str]:
    """`data-foo-bar=` in markup becomes `dataset.fooBar` in script."""
    return {
        "".join(part.capitalize() if i else part for i, part in enumerate(name.split("-")))
        for name in re.findall(r"data-([a-z][a-z0-9-]*)=", source)
    }


def _without_comments(source: str) -> str:
    """Drop comments, so an explanation that mentions a URL is not a finding."""
    source = re.sub(r"/\*.*?\*/", "", source, flags=re.S)
    return re.sub(r"(?m)^\s*//.*$", "", source)


@pytest.mark.parametrize("script", SCRIPTS, ids=lambda p: p.name)
def test_dataset_reads_match_the_attributes_written(script: pathlib.Path) -> None:
    """Every `dataset.x` read must correspond to a `data-x` written somewhere.

    `data-seconds` was written and `dataset.giay` was read, left over from a
    rename. `parseFloat(undefined)` is NaN, and assigning NaN to
    `player.currentTime` throws, so clicking evidence did nothing at all.
    """
    source = script.read_text(encoding="utf-8")

    written = _dataset_names(source)
    read = set(re.findall(r"\.dataset\.([A-Za-z][A-Za-z0-9]*)", source))

    # Attributes rendered by a template rather than by this script: the
    # response id a page was opened with, the QC limits in force. Read from the
    # templates themselves rather than listed by hand, so a renamed attribute
    # fails here as well.
    from_templates = set().union(
        *(_dataset_names(t.read_text(encoding="utf-8")) for t in TEMPLATES.glob("*.html"))
    )

    missing = read - written - from_templates
    assert not missing, (
        f"{script.name} đọc {sorted(missing)} nhưng không nơi nào ghi thuộc tính tương ứng"
    )


@pytest.mark.parametrize("script", SCRIPTS, ids=lambda p: p.name)
def test_no_external_resources_are_fetched(script: pathlib.Path) -> None:
    """A lab machine may have no route off campus, and the CSP forbids it anyway."""
    source = _without_comments(script.read_text(encoding="utf-8"))
    for pattern in ("http://", "https://"):
        assert pattern not in source, f"{script.name} tải tài nguyên từ bên ngoài"


@pytest.mark.parametrize("script", SCRIPTS, ids=lambda p: p.name)
def test_values_from_other_users_are_escaped(script: pathlib.Path) -> None:
    """Anything a user typed reaches another user's screen, so it must be escaped.

    The review queue was the one screen that interpolated a student's pseudonym
    straight into innerHTML. A pseudonym is chosen by the student and read by a
    teacher: that is a stored XSS with a session that can change scores.
    """
    source = _without_comments(script.read_text(encoding="utf-8"))
    risky = ("speaker_id", "pseudonym", "reason", "transcript", "title", "detail", "note")

    # Only property reads count: `r.speaker_id`, `d.reason`, `t.title`. A bare
    # word like the attribute name in `title="..."` is not user data.
    for field in risky:
        for match in re.finditer(rf"\$\{{[^{{}}]*?\.{field}\b[^{{}}]*?\}}", source):
            fragment = match.group(0)
            assert "escapeHtml" in fragment or "encodeURIComponent" in fragment, (
                f"{script.name}: {fragment} chèn thẳng vào HTML mà không escape"
            )
