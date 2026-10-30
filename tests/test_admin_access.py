"""Who may call what, checked over every route the application serves. FR-32, NFR-07.

Each router guards itself with `ADMIN_ONLY`, `STAFF_ONLY`, `STUDENT_ONLY` or
`require_login`. A route that forgets its guard is invisible to the per-feature
tests, which only call the routes they know about. These tests read the guard
off every route the application actually serves and call each one as a
visitor, a student, a teacher, an administrator who still holds a temporary
password, and an administrator, so a route added tomorrow is covered too.
"""

from __future__ import annotations

import importlib
import re

import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from aicefr.storage.auth_repository import Role

PASSWORD = "matkhau-kiem-thu"
ROLE_REFUSAL = "tài khoản không có quyền thực hiện việc này"

# API routes anyone may call, and why.
PUBLIC_API = {
    ("POST", "/api/v1/auth/login"),  # signing in
    ("POST", "/api/v1/auth/logout"),  # ending a session that may already be gone
    # D065: opening an account and replacing a forgotten password, both before
    # any session exists; rate limited per address and, for recovery, locked
    # after five wrong codes like a login.
    ("POST", "/api/v1/auth/signup"),
    ("POST", "/api/v1/auth/recover"),
    # Payment gateways call back without a session; each checks its signature.
    ("GET", "/api/v1/billing/notify/{gateway}"),
    ("POST", "/api/v1/billing/notify/{gateway}"),
}


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from aicefr.api import main as m

    importlib.reload(m)
    return m.app


def _routes(routes):
    """Every APIRoute, including those of routers included into the application."""
    for r in routes:
        inner = getattr(r, "original_router", None)
        if inner is not None:
            yield from _routes(inner.routes)
        elif isinstance(r, APIRoute):
            yield r


def _guard(route: APIRoute) -> str:
    """ "admin", "staff", "student", "login" or "none", read off the route's dependencies."""

    def walk(dep, found: set):
        call = dep.call
        name = getattr(call, "__name__", "")
        if name == "check" and call.__closure__:
            for cell in call.__closure__:
                roles = cell.cell_contents
                if isinstance(roles, tuple) and roles and isinstance(roles[0], Role):
                    found.add(frozenset(roles))
        elif name == "require_login":
            found.add("login")
        for d in dep.dependencies:
            walk(d, found)
        return found

    found = walk(route.dependant, set())
    if frozenset({Role.ADMIN}) in found:
        return "admin"
    if frozenset({Role.TEACHER, Role.ADMIN}) in found:
        return "staff"
    if frozenset({Role.STUDENT}) in found:
        return "student"
    return "login" if "login" in found else "none"


def _calls(app, guard: str):
    """(method, url, template) for every API route with this guard."""
    for route in _routes(app.routes):
        if not route.path.startswith("/api/") or _guard(route) != guard:
            continue
        url = re.sub(r"\{[^}]+\}", "x0", route.path)
        for method in sorted(route.methods - {"HEAD"}):
            yield method, url, route.path


def _client(app, pseudonym: str | None, role: str = "student", temporary: bool = False):
    c = TestClient(app)
    if pseudonym is None:
        return c
    auth = app.state.auth_repo
    auth.create_account(pseudonym, PASSWORD, Role(role), must_change_password=temporary)
    r = c.post("/api/v1/auth/login", json={"pseudonym": pseudonym, "password": PASSWORD})
    assert r.status_code == 200, r.text
    return c


def _detail(r):
    if "json" not in r.headers.get("content-type", ""):
        return None
    body = r.json()
    return body.get("detail") if isinstance(body, dict) else None


def _refused(client, guard: str, app, expected: int, only_role_refusal: bool = False):
    wrong = []
    for method, url, path in _calls(app, guard):
        r = client.request(method, url)
        if r.status_code != expected:
            wrong.append(f"{method} {path}: {r.status_code}")
        elif only_role_refusal and _detail(r) != ROLE_REFUSAL:
            wrong.append(f"{method} {path}: {_detail(r)}")
    return wrong


def test_the_guards_are_where_the_paths_say(app) -> None:
    """Every /api/v1/admin route is admin-only; every other API route has a guard
    unless it is one of the few that must be public."""
    wrong = []
    for route in _routes(app.routes):
        if not route.path.startswith("/api/"):
            continue
        guard = _guard(route)
        if route.path.startswith("/api/v1/admin/") and guard != "admin":
            wrong.append(f"{route.path}: {guard}")
        for method in route.methods - {"HEAD"}:
            if guard == "none" and (method, route.path) not in PUBLIC_API:
                wrong.append(f"{method} {route.path}: no guard")
    assert not wrong, wrong
    assert len(list(_calls(app, "admin"))) >= 40


def test_a_visitor_is_asked_to_sign_in_everywhere_guarded(app) -> None:
    visitor = _client(app, None)
    wrong = []
    for guard in ("admin", "staff", "student", "login"):
        wrong += _refused(visitor, guard, app, 401)
    assert not wrong, wrong


def test_a_student_is_refused_every_admin_and_staff_route(app) -> None:
    student = _client(app, "SV-AC1")
    wrong = _refused(student, "admin", app, 403, only_role_refusal=True)
    wrong += _refused(student, "staff", app, 403, only_role_refusal=True)
    assert not wrong, wrong


def test_a_teacher_is_refused_every_admin_and_student_route(app) -> None:
    teacher = _client(app, "GV-AC1", "teacher")
    wrong = _refused(teacher, "admin", app, 403, only_role_refusal=True)
    wrong += _refused(teacher, "student", app, 403, only_role_refusal=True)
    assert not wrong, wrong


def test_an_admin_on_a_temporary_password_reaches_nothing_admin(app) -> None:
    """D028: a password somebody else has seen opens only the password change."""
    admin = _client(app, "QT-AC0", "admin", temporary=True)
    assert not _refused(admin, "admin", app, 403)


def test_an_admin_passes_every_admin_route(app) -> None:
    """Whatever an admin route answers (404 for a made-up id, 422 for no body),
    it is never the sign-in or the role refusal."""
    admin = _client(app, "QT-AC1", "admin")
    wrong = []
    for method, url, path in _calls(app, "admin"):
        r = admin.request(method, url)
        detail = _detail(r)
        if r.status_code == 401 or detail == ROLE_REFUSAL:
            wrong.append(f"{method} {path}: {r.status_code} {detail}")
    assert not wrong, wrong


def test_an_admin_is_refused_every_student_route(app) -> None:
    admin = _client(app, "QT-AC2", "admin")
    assert not _refused(admin, "student", app, 403, only_role_refusal=True)


def test_a_disabled_admin_is_signed_out_at_once(app) -> None:
    first = _client(app, "QT-AC3", "admin")
    second = _client(app, "QT-AC4", "admin")
    target = app.state.auth_repo.get_by_pseudonym("QT-AC4")["account_id"]
    assert first.post(f"/api/v1/admin/accounts/{target}/disable").status_code == 200
    assert second.get("/api/v1/admin/accounts").status_code == 401
    r = second.post("/api/v1/auth/login", json={"pseudonym": "QT-AC4", "password": PASSWORD})
    assert r.status_code == 401


def test_a_demoted_admin_loses_admin_routes_on_the_next_call(app) -> None:
    first = _client(app, "QT-AC5", "admin")
    second = _client(app, "QT-AC6", "admin")
    target = app.state.auth_repo.get_by_pseudonym("QT-AC6")["account_id"]
    r = first.post(f"/api/v1/admin/accounts/{target}/role", json={"role": "teacher"})
    assert r.status_code == 200
    assert second.get("/api/v1/admin/accounts").status_code == 403


def test_an_admin_cannot_lock_themself_out(app) -> None:
    """Not their own account: no disabling, demoting, resetting or signing out
    everywhere, so the last administrator can never shut the door on everyone."""
    admin = _client(app, "QT-AC7", "admin")
    me = app.state.auth_repo.get_by_pseudonym("QT-AC7")["account_id"]
    base = f"/api/v1/admin/accounts/{me}"
    assert admin.post(f"{base}/disable").status_code == 409
    assert admin.post(f"{base}/role", json={"role": "student"}).status_code == 409
    assert admin.post(f"{base}/reset-password").status_code == 409
    assert admin.post(f"{base}/revoke-sessions").status_code == 409
    assert admin.get("/api/v1/admin/accounts").status_code == 200


@pytest.mark.parametrize("path", ["/admin", "/admin/study"])
def test_admin_pages_open_only_for_an_admin(app, path: str) -> None:
    visitor = TestClient(app, follow_redirects=False)
    r = visitor.get(path)
    assert r.status_code == 303 and r.headers["location"] == f"/login?next={path}"

    others = (("SV-AP1", "student", "/practice"), ("GV-AP1", "teacher", "/review"))
    for pseudonym, role, home in others:
        c = _client(app, pseudonym, role)
        c.follow_redirects = False
        r = c.get(path)
        assert r.status_code == 303 and r.headers["location"] == home, (role, r.status_code)

    temporary = _client(app, "QT-AP0", "admin", temporary=True)
    temporary.follow_redirects = False
    assert temporary.get(path).headers["location"] == "/account?first=1"

    admin = _client(app, "QT-AP1", "admin")
    assert admin.get(path).status_code == 200
