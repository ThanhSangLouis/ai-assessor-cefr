"""Account creation commands. Implements the administrative part of FR-32.

Teacher and administrator accounts are only ever made here: the teacher role
can change scores, so it cannot be left for the user to pick. The one way to
self-register is Google sign-up (D063), and it only makes students.

Run:
    python -m aicefr.accounts_cli them --email gv-01@demo.speakup.fit --vai-tro teacher
    python -m aicefr.accounts_cli liet-ke
    AICEFR_SEED_PASSWORD=... python -m aicefr.accounts_cli seed
"""

from __future__ import annotations

import argparse
import getpass
import os
import sys

from pymongo.errors import PyMongoError

from aicefr.auth import contact
from aicefr.config import get_settings
from aicefr.storage.auth_repository import AuthRepository, EmailTaken, Role

MIN_PASSWORD_LENGTH = 8
SEED_PASSWORD_ENV = "AICEFR_SEED_PASSWORD"

# The accounts a fresh deployment needs to be shown and tested: every role, a
# class's worth of students. On a subdomain that receives no mail.
SEED_DOMAIN = "demo.speakup.fit"
SEED_ACCOUNTS: tuple[tuple[str, Role], ...] = (
    (f"qt-01@{SEED_DOMAIN}", Role.ADMIN),
    *((f"gv-{i:02d}@{SEED_DOMAIN}", Role.TEACHER) for i in range(1, 4)),
    *((f"sv-{i:03d}@{SEED_DOMAIN}", Role.STUDENT) for i in range(1, 11)),
)


def _add(args: argparse.Namespace) -> int:
    repo = AuthRepository(args.db)

    # Check the email BEFORE asking for a password, so a bad one does not mean
    # typing a password twice and then reading a traceback.
    try:
        email = contact.normalize_email(args.email)
    except ValueError as e:
        print(f"Email không hợp lệ: {e}", file=sys.stderr)
        return 1

    if repo.get_by_email(email) is not None:
        print(f"Email {email!r} đã có tài khoản.", file=sys.stderr)
        return 1

    password = args.password or getpass.getpass("Mật khẩu: ")
    if len(password) < MIN_PASSWORD_LENGTH:
        print(f"Mật khẩu phải từ {MIN_PASSWORD_LENGTH} ký tự trở lên.", file=sys.stderr)
        return 1
    if not args.password and password != getpass.getpass("Nhập lại mật khẩu: "):
        print("Hai lần nhập không khớp.", file=sys.stderr)
        return 1

    try:
        aid = repo.create_account(email, password, Role(args.role))
    except EmailTaken:
        print(f"Email {email!r} đã có tài khoản.", file=sys.stderr)
        return 1
    print(f"Đã tạo tài khoản {email} · vai trò {args.role} · mã {aid}")
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
    for email, role in SEED_ACCOUNTS:
        if repo.get_by_email(email) is None:
            aid = repo.create_account(email, password, role)
            repo.set_email_reminders(aid, False)  # the demo domain receives no mail
            made.append(email)
    kept = len(SEED_ACCOUNTS) - len(made)
    print(f"Đã tạo {len(made)} tài khoản ({', '.join(made) or 'không có'}); giữ nguyên {kept}.")
    return 0


def _list(args: argparse.Namespace) -> int:
    rows = AuthRepository(args.db).list_accounts()
    if not rows:
        print("Chưa có tài khoản nào.")
        return 0
    print(f"{'Email':<32} {'Vai trò':<10} {'Sai':<5} {'Khóa đến':<22} Tình trạng")
    for r in rows:
        state = "đã tắt" if r["disabled"] else "đang dùng"
        print(
            f"{r['email']:<32} {r['role']:<10} {r['failed_attempts']:<5} "
            f"{r['locked_until'] or '—':<22} {state}"
        )
    return 0


def _unlock(args: argparse.Namespace) -> int:
    """Unlock an account that was locked after too many failed logins."""
    if not AuthRepository(args.db).unlock_email(args.email):
        print(f"Không có tài khoản {args.email!r}.", file=sys.stderr)
        return 1
    print(f"Đã gỡ khóa {args.email}.")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Quản lý tài khoản hệ thống SpeakUp")
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
    p_add.add_argument("--email", dest="email", required=True, help="email đăng nhập")
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
        "seed",
        help=f"tạo bộ tài khoản mẫu còn thiếu (qt-01, gv-01..03, sv-001..010 @{SEED_DOMAIN})",
    )
    p_seed.add_argument(
        "--mat-khau",
        dest="password",
        default=None,
        help=f"mật khẩu chung của tài khoản mới tạo; bỏ trống thì đọc {SEED_PASSWORD_ENV}",
    )
    p_seed.set_defaults(func=_seed)

    p_unlock = sub.add_parser("mo-khoa", help="gỡ khóa tài khoản")
    p_unlock.add_argument("--email", dest="email", required=True)
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
