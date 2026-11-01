"""A visitor who opens a signed-in screen goes to the login page and back.

The data of these screens was always refused by the API; the shell of the
screen used to load anyway, empty, for anyone (found 01/11/2026 on production).
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from test_lessons_integration import login_as, m  # noqa: F401  (the fixture `m` is used by name)

pytestmark = pytest.mark.integration

SIGNED_IN = [
    "/practice",
    "/my-responses",
    "/my-progress",
    "/my-assignments",
    "/credits",
    "/review",
    "/review/stats",
    "/rate",
    "/teach",
    "/teach/insights",
    "/teach/classes",
    "/report/r-1",
]
PUBLIC = ["/", "/login", "/signup", "/forgot", "/bands"]


@pytest.mark.parametrize("path", SIGNED_IN)
def test_a_visitor_is_sent_to_log_in_and_back(m, path):  # noqa: F811
    r = TestClient(m.app).get(path, follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"].startswith("/login?next=")
    assert r.headers["location"] == f"/login?next={path}"


@pytest.mark.parametrize("path", PUBLIC)
def test_public_pages_stay_open(m, path):  # noqa: F811
    assert TestClient(m.app).get(path, follow_redirects=False).status_code == 200


def test_a_signed_in_learner_opens_their_page(m):  # noqa: F811
    assert login_as(m, "SV-001").get("/practice").status_code == 200
