"""Account creation commands. Implements the administrative part of FR-32.

Teacher and administrator accounts are only ever made here: the teacher role
can change scores, so it cannot be left for the user to pick. The one way to
self-register is Google sign-up (D063), and it only makes students.

Run:
    python -m aicefr.accounts_cli them --but-danh GV-01 --vai-tro teacher
    python -m aicefr.accounts_cli liet-ke
    AICEFR_SEED_PASSWORD=... python -m aicefr.accounts_cli seed
"""

from __future__ import annotations

import argparse
import getpass
import os
import sys

from pymongo.errors import PyMongoError

from aicefr.auth.pseudonyms import validate_pseudonym
from aicefr.config import get_settings
from aicefr.storage.auth_repository import AuthRepository, Role

MIN_PASSWORD_LENGTH = 8
SEED_PASSWORD_ENV = "AICEFR_SEED_PASSWORD"

# The accounts a fresh deployment needs to be shown and tested: every role, a
# class's worth of students. Pseudonyms only, as everywhere (FR-33).
SEED_ACCOUNTS: tuple[tuple[str, Role], ...] = (
    ("QT-01", Role.ADMIN),
    *((f"GV-{i:02d}", Role.TEACHER) for i in range(1, 4)),
    *((f"SV-{i:03d}", Role.STUDENT) for i in range(1, 11)),
)


def _add(args: argparse.Namespace) -> int:
    repo = AuthRepository(args.db)

    # Validate the pseudonym BEFORE asking for a password. The repository
    # validates it too -- that is the authoritative check -- but it runs after
    # the password prompt, so a rejected pseudonym meant typing a password
    # twice and then reading a traceback.
    try:
        validate_pseudonym(args.pseudonym)
    except ValueError as e:
        print(f"Bút danh không hợp lệ: {e}", file=sys.stderr)
        return 1

    if repo.get_by_pseudonym(args.pseudonym) is not None:
        print(f"Bút danh {args.pseudonym!r} đã tồn tại.", file=sys.stderr)
        return 1

    password = args.password or getpass.getpass("Mật khẩu: ")
    if len(password) < MIN_PASSWORD_LENGTH:
        print(f"Mật khẩu phải từ {MIN_PASSWORD_LENGTH} ký tự trở lên.", file=sys.stderr)
        return 1
    if not args.password and password != getpass.getpass("Nhập lại mật khẩu: "):
        print("Hai lần nhập không khớp.", file=sys.stderr)
        return 1

    aid = repo.create_account(args.pseudonym, password, Role(args.role))
    print(f"Đã tạo tài khoản {args.pseudonym} · vai trò {args.role} · mã {aid}")
    return 0


def _seed(args: argparse.Namespace) -> int:
    """Create the seed accounts that do not exist yet; leave the others untouched.

    Safe to run on every deploy: an existing account keeps its password, role
    and history. The password comes from the option or AICEFR_SEED_PASSWORD,
    never from a default, so no deployment ends up with a password printed in
    this repository.
    """
    password = args.password or os.getenv(SEED_PASSWORD_ENV, "")
    if len(password) < MIN_PASSWORD_LENGTH:
        print(
            f"Cần --mat-khau hoặc {SEED_PASSWORD_ENV}, từ {MIN_PASSWORD_LENGTH} ký tự trở lên.",
            file=sys.stderr,
        )
        return 1
    repo = AuthRepository(args.db)
    made = []
    for pseudonym, role in SEED_ACCOUNTS:
        if repo.get_by_pseudonym(pseudonym) is None:
            repo.create_account(pseudonym, password, role)
            made.append(pseudonym)
    kept = len(SEED_ACCOUNTS) - len(made)
    print(f"Đã tạo {len(made)} tài khoản ({', '.join(made) or 'không có'}); giữ nguyên {kept}.")
    return 0


def _list(args: argparse.Namespace) -> int:
    rows = AuthRepository(args.db).list_accounts()
    if not rows:
        print("Chưa có tài khoản nào.")
        return 0
    print(f"{'Bút danh':<20} {'Vai trò':<10} {'Sai':<5} {'Khóa đến':<22} Tình trạng")
    for r in rows:
        state = "đã tắt" if r["disabled"] else "đang dùng"
        print(
            f"{r['pseudonym']:<20} {r['role']:<10} {r['failed_attempts']:<5} "
            f"{r['locked_until'] or '—':<22} {state}"
        )
    return 0


def _unlock(args: argparse.Namespace) -> int:
    """Unlock an account that was locked after too many failed logins."""
    if not AuthRepository(args.db).unlock_pseudonym(args.pseudonym):
        print(f"Không có tài khoản {args.pseudonym!r}.", file=sys.stderr)
        return 1
    print(f"Đã gỡ khóa {args.pseudonym}.")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Quản lý tài khoản hệ thống AI Assessor CEFR")
    # The core service's store (D044): AICEFR_CORE_DB, else AICEFR_DB, as
    # the service reads it. A hard-coded "aicefr.db" once wrote accounts into a
    # database the application never read.
    ap.add_argument(
        "--db",
        default=get_settings().store("core"),
        help="kho dữ liệu của dịch vụ tài khoản (URL mongodb://)",
    )
    sub = ap.add_subparsers(dest="command", required=True)

    # The option names stay Vietnamese: they are the documented user interface.
    # Only the `dest` is English, so the code reads in English.
    p_add = sub.add_parser("them", help="tạo tài khoản mới")
    p_add.add_argument(
        "--but-danh",
        dest="pseudonym",
        required=True,
        help="mã bút danh, không dùng họ tên hay MSSV",
    )
    p_add.add_argument(
        "--vai-tro",
        dest="role",
        required=True,
        choices=[v.value for v in Role],
        help="vai trò",
    )
    p_add.add_argument(
        "--mat-khau",
        dest="password",
        default=None,
        help="chỉ dùng khi chạy tự động; bỏ trống để nhập kín, tránh lộ trong lịch sử lệnh",
    )
    p_add.set_defaults(func=_add)

    sub.add_parser("liet-ke", help="liệt kê tài khoản").set_defaults(func=_list)

    p_seed = sub.add_parser(
        "seed", help="tạo bộ tài khoản mẫu còn thiếu (QT-01, GV-01..03, SV-001..010)"
    )
    p_seed.add_argument(
        "--mat-khau",
        dest="password",
        default=None,
        help=f"mật khẩu chung của tài khoản mới tạo; bỏ trống thì đọc {SEED_PASSWORD_ENV}",
    )
    p_seed.set_defaults(func=_seed)

    p_unlock = sub.add_parser("mo-khoa", help="gỡ khóa tài khoản")
    p_unlock.add_argument("--but-danh", dest="pseudonym", required=True)
    p_unlock.set_defaults(func=_unlock)

    args = ap.parse_args(argv)
    try:
        return args.func(args)
    except PyMongoError as e:
        print(f"Lỗi cơ sở dữ liệu: {e}", file=sys.stderr)
        return 2
    except ValueError as e:
        # Backstop: a rule enforced deeper in the stack should still reach the
        # operator as one readable line, never as a traceback.
        print(f"Lỗi: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
