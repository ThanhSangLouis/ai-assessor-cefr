"""Authenticated local account, scoring and maintenance commands."""

from __future__ import annotations

import getpass
import json
import sys

from aicefr.api.student import SubmitRequest
from aicefr.contracts import CURRENT_CONSENT_VERSION, ActorRole
from aicefr.local.app import create_runtime, load_config
from aicefr.portal.contracts import AccountChange


def add_commands(commands) -> None:
    for name in ("accounts", "maintenance", "score"):
        parser = commands.add_parser(name, help=f"Local {name} (tài khoản fixture)")
        from pathlib import Path

        parser.add_argument("--data-dir", type=Path, required=True)
        parser.add_argument("--config", type=Path, required=True)
        parser.add_argument("--actor-id", required=True)
        parser.add_argument("--password-stdin", action="store_true")
        if name == "accounts":
            parser.add_argument("action", choices=("list", "unlock", "disable", "enable"))
            parser.add_argument("--target")
        elif name == "maintenance":
            parser.add_argument("action", choices=("backup", "retention", "orphans", "cleanup"))
            parser.add_argument("--destination", type=Path)
            parser.add_argument("--days", type=int, default=180)
            parser.add_argument("--apply", action="store_true", help="Mặc định chỉ xem trước")
        else:
            parser.add_argument("--audio", type=Path, required=True)
            parser.add_argument("--task-id", required=True)
            parser.add_argument("--task-version", required=True)


def run_command(args) -> int:
    password = (
        sys.stdin.readline().rstrip("\r\n")
        if args.password_stdin
        else getpass.getpass("Mật khẩu: ")
    )
    runtime = None
    try:
        config = {**load_config(args.config), "async_pipeline": False}
        runtime = create_runtime(args.data_dir, config=config)
        token = runtime.auth.login(args.actor_id, password)
        if args.command == "accounts":
            if args.action == "list":
                result = runtime.portal.accounts(token)
            else:
                if not args.target:
                    raise ValueError("account target required")
                change = (
                    AccountChange(unlock=True)
                    if args.action == "unlock"
                    else AccountChange(disabled=args.action == "disable")
                )
                result = runtime.portal.change_account(token, args.target, change)
        elif args.command == "maintenance":
            runtime.portal.actor(token, frozenset({ActorRole.ADMIN}))
            if args.action == "backup":
                if not args.destination:
                    raise ValueError("backup destination required")
                result = runtime.data.backup(token, args.destination)
            elif args.action == "retention":
                result = runtime.data.retention(token, days=args.days, apply=args.apply)
            elif args.action == "orphans":
                result = runtime.data.orphans(token, apply=args.apply)
            else:
                pending = runtime.store.connection.execute(
                    "SELECT COUNT(*) FROM blob_deletions"
                ).fetchone()[0]
                result = (
                    runtime.data.cleanup_pending()
                    if args.apply
                    else {"dry_run": True, "pending": pending}
                )
        else:
            actor = runtime.portal.actor(token, frozenset({ActorRole.STUDENT}))
            runtime.consents.require_audio_storage(
                actor, config.get("consent_version", CURRENT_CONSENT_VERSION)
            )
            with args.audio.open("rb") as handle:
                data = handle.read(runtime.responses.blobs.max_bytes + 1)
            mime = {
                ".wav": "audio/wav",
                ".flac": "audio/flac",
                ".ogg": "audio/ogg",
                ".mp3": "audio/mpeg",
                ".webm": "audio/webm",
                ".mp4": "audio/mp4",
                ".m4a": "audio/mp4",
            }[args.audio.suffix.lower()]
            status = runtime.app._student_api.submit(
                token,
                SubmitRequest(
                    task_id=args.task_id,
                    task_version=args.task_version,
                    consent_version=config.get("consent_version", CURRENT_CONSENT_VERSION),
                    filename=args.audio.name,
                    content_type=mime,
                    audio_bytes=data,
                ),
            )
            view = runtime.app._student_api.get_report(token, status.response_id)
            result = {
                "status": view.status.model_dump(mode="json"),
                "report": view.report.model_dump(mode="json") if view.report else None,
            }
        runtime.auth.logout(token)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except Exception:
        print(
            "Không thể thực hiện lệnh; kiểm tra tài khoản, tham số và cấu hình local.",
            file=sys.stderr,
        )
        return 2
    finally:
        if runtime:
            runtime.close()
