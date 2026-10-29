"""The seed accounts a deployment gets (D063): every role, created once, never overwritten."""

from __future__ import annotations

import pytest

from aicefr import accounts_cli
from aicefr.storage.auth_repository import AuthRepository, Role


@pytest.fixture
def db(tmp_path) -> str:
    return f"mongomock://seed-{tmp_path.name}"


def test_seed_creates_every_role_and_is_safe_to_run_again(db, monkeypatch, capsys):
    monkeypatch.setenv(accounts_cli.SEED_PASSWORD_ENV, "mat-khau-seed")
    assert accounts_cli.main(["--db", db, "seed"]) == 0
    repo = AuthRepository(db)
    roles = {r["pseudonym"]: r["role"] for r in repo.list_accounts()}
    assert roles["QT-01"] == Role.ADMIN.value
    assert {roles[f"GV-{i:02d}"] for i in range(1, 4)} == {Role.TEACHER.value}
    assert {roles[f"SV-{i:03d}"] for i in range(1, 11)} == {Role.STUDENT.value}
    assert repo.login("SV-001", "mat-khau-seed") is not None

    # A second run makes nothing and keeps a password someone already changed.
    sv1 = repo.get_by_pseudonym("SV-001")["account_id"]
    repo.change_password(sv1, "mat-khau-seed", "mat-khau-moi-123")
    monkeypatch.setenv(accounts_cli.SEED_PASSWORD_ENV, "khac-hoan-toan")
    assert accounts_cli.main(["--db", db, "seed"]) == 0
    assert "Đã tạo 0 tài khoản" in capsys.readouterr().out
    assert len(repo.list_accounts()) == len(accounts_cli.SEED_ACCOUNTS)
    assert repo.login("SV-001", "mat-khau-moi-123") is not None


def test_seed_refuses_without_a_password(db, monkeypatch):
    monkeypatch.delenv(accounts_cli.SEED_PASSWORD_ENV, raising=False)
    assert accounts_cli.main(["--db", db, "seed"]) == 1
    assert AuthRepository(db).list_accounts() == []
