#!/usr/bin/env python3
"""Install a supplied wheel in a clean venv and exercise the offline runtime."""

from __future__ import annotations

import argparse
import array
import http.client
import json
import math
import os
import shutil
import socket
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
import venv
import wave
from pathlib import Path
from typing import Any
from urllib.parse import urlencode


def run(
    command: list[str], *, env: dict[str, str], input_text: str | None = None, cwd: Path
) -> str:
    result = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
        input=input_text,
        cwd=cwd,
    )
    if result.returncode:
        raise RuntimeError(
            f"command failed ({result.returncode}): {Path(command[0]).name} "
            f"{command[1:3]}: {result.stderr.strip() or result.stdout.strip()}"
        )
    return result.stdout


def clean_environment() -> dict[str, str]:
    environment = os.environ.copy()
    for name in ("PYTHONPATH", "PYTHONHOME", "PYTHONUSERBASE", "VIRTUAL_ENV"):
        environment.pop(name, None)
    if os.name == "nt":
        environment.setdefault("PYTHONUTF8", "1")
    return environment


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, file, code, message, headers, new_url):
        return None


def request(base: str, path: str, *, payload: dict | None = None, cookie: str | None = None) -> Any:
    data = json.dumps(payload).encode() if payload is not None else None
    headers = {"Origin": base}
    if data is not None:
        headers["Content-Type"] = "application/json"
    if cookie:
        headers["Cookie"] = cookie
    req = urllib.request.Request(base + path, data=data, headers=headers)
    opener = urllib.request.build_opener(NoRedirect)
    try:
        return opener.open(req, timeout=3)
    except urllib.error.HTTPError as error:
        return error


def form_request(base: str, path: str, *, payload: dict[str, str], cookie: str) -> Any:
    data = urlencode(payload).encode()
    req = urllib.request.Request(
        base + path,
        data=data,
        headers={
            "Origin": base,
            "Content-Type": "application/x-www-form-urlencoded",
            "Cookie": cookie,
        },
    )
    opener = urllib.request.build_opener(NoRedirect)
    try:
        return opener.open(req, timeout=3)
    except urllib.error.HTTPError as error:
        return error


def free_port() -> int:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--wheel", required=True, type=Path)
    parser.add_argument("--evidence-dir", required=True, type=Path)
    parser.add_argument("--python-dependency-cache", type=Path)
    args = parser.parse_args()
    wheel = args.wheel.resolve()
    evidence = args.evidence_dir.resolve()
    evidence.mkdir(parents=True, exist_ok=True)
    if not wheel.is_file() or wheel.suffix != ".whl":
        parser.error("--wheel must name a built wheel")

    report: dict[str, object] = {
        "wheel": wheel.name,
        "source_tree_import": None,
        "steps": {},
        "limitations": ["Model inference NOT_RUN; model artifacts are intentionally absent."],
    }
    with tempfile.TemporaryDirectory(prefix="aicefr-wheel-smoke-") as temp:
        root = Path(temp)
        venv_dir = root / "venv"
        venv.EnvBuilder(with_pip=True, clear=True).create(venv_dir)
        python = venv_dir / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        clean_env = clean_environment()
        pip = [str(python), "-m", "pip", "install", "--no-index"]
        if args.python_dependency_cache:
            pip.extend(["--find-links", str(args.python_dependency_cache.resolve())])
        run([*pip, str(wheel)], env=clean_env, cwd=root)
        imported_from = run(
            [str(python), "-c", "import aicefr; print(aicefr.__file__)"],
            env=clean_env,
            cwd=root,
        ).strip()
        report["source_tree_import"] = (
            not Path(imported_from).resolve().is_relative_to(venv_dir.resolve())
        )
        if report["source_tree_import"]:
            raise RuntimeError("aicefr did not import from the clean venv site-packages")

        data_dir = root / "data"
        config_path = root / "runtime.json"
        config_path.write_text(
            json.dumps(
                {
                    "consent_version": "consent-v2",
                    "allowed_media_types": ["audio/wav"],
                    "tasks": [{"task_id": "smoke", "task_version": "1"}],
                    "asr_model_dir": str(root / "missing-asr-model"),
                    "model_artifact": str(root / "missing-model.json"),
                    "qc": {
                        "version": "wheel-smoke-v1",
                        "accepted_formats": ["wav"],
                        "max_input_bytes": 2000000,
                        "min_duration_s": 1.0,
                        "max_duration_s": 10.0,
                        "max_input_sample_rate_hz": 16000,
                        "silence_threshold": 0.01,
                        "clipping_threshold": 0.99,
                        "review_silence_ratio": 0.5,
                        "reject_silence_ratio": 0.95,
                        "review_clipping_ratio": 0.1,
                        "reject_clipping_ratio": 0.5,
                    },
                }
            ),
            encoding="utf-8",
        )
        password = "wheel-smoke-secret"
        for actor, role in (("fixture-admin", "admin"), ("fixture-student", "student")):
            run(
                [
                    str(python),
                    "-m",
                    "aicefr.local",
                    "init-demo",
                    "--data-dir",
                    str(data_dir),
                    "--actor-id",
                    actor,
                    "--role",
                    role,
                    "--password-stdin",
                ],
                env=clean_env,
                input_text=password + "\n",
                cwd=root,
            )

        port = free_port()
        base = f"http://127.0.0.1:{port}"
        server = subprocess.Popen(
            [
                str(python),
                "-m",
                "aicefr.local",
                "serve",
                "--data-dir",
                str(data_dir),
                "--config",
                str(config_path),
                "--bind",
                "127.0.0.1",
                "--port",
                str(port),
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=clean_env,
            cwd=root,
        )
        try:
            for _ in range(100):
                if server.poll() is not None:
                    raise RuntimeError("wheel-installed CLI exited before HTTP readiness")
                try:
                    live = request(base, "/live")
                    break
                except (OSError, urllib.error.URLError, http.client.HTTPException):
                    time.sleep(0.1)
            else:
                raise RuntimeError("wheel-installed CLI did not start")
            report["steps"]["cli_boot"] = live.status == 200
            report["steps"]["liveness"] = json.loads(live.read()) == {"alive": True}
            ready = request(base, "/ready")
            report["steps"]["missing_model_readiness_503"] = ready.status == 503
            report["steps"]["login_page"] = request(base, "/login").status == 200
            login = request(
                base, "/login", payload={"actor_id": "fixture-admin", "password": password}
            )
            cookie = login.headers.get("Set-Cookie", "").split(";", 1)[0]
            report["steps"]["login"] = login.status == 303 and cookie.startswith("aicefr_session=")
            report["steps"]["authenticated_page"] = (
                request(base, "/admin", cookie=cookie).status == 200
            )
            student_login = request(
                base,
                "/login",
                payload={"actor_id": "fixture-student", "password": password},
            )
            student_cookie = student_login.headers.get("Set-Cookie", "").split(";", 1)[0]
            report["steps"]["student_login"] = (
                student_login.status == 303
                and student_cookie.startswith("aicefr_session=")
            )
            accepted = form_request(
                base,
                "/student/consent/accept",
                payload={"audio_storage_allowed": "true", "research_allowed": "false"},
                cookie=student_cookie,
            )
            consent_page = request(base, "/student/consent", cookie=student_cookie)
            consent_html = consent_page.read().decode("utf-8")
            consent_response = request(base, "/api/v1/me/consent", cookie=student_cookie)
            consent_record = (
                json.loads(consent_response.read()) if consent_response.status == 200 else {}
            )
            report["steps"]["current_consent_version"] = (
                accepted.status == 303
                and "/static/consent-v2.pdf" in consent_html
                and consent_record.get("consent_version") == "consent-v2"
            )
            report["steps"]["audio_storage_opt_in"] = (
                consent_record.get("audio_storage_allowed") is True
            )
            for asset in ("/recorder.js", "/report.js"):
                response = request(base, asset)
                report["steps"][asset.removeprefix("/")] = (
                    response.status == 200 and len(response.read()) > 0
                )
        finally:
            server.terminate()
            try:
                server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait()

        audio = root / "fixture.wav"
        with wave.open(str(audio), "wb") as stream:
            stream.setnchannels(1)
            stream.setsampwidth(2)
            stream.setframerate(16000)
            samples = array.array("h", [0] * 22400)
            samples.extend(
                int(4000 * math.sin(2 * math.pi * 220 * index / 16000)) for index in range(9600)
            )
            stream.writeframes(samples.tobytes())
        score = json.loads(
            run(
                [
                    str(python),
                    "-m",
                    "aicefr.local",
                    "score",
                    "--data-dir",
                    str(data_dir),
                    "--config",
                    str(config_path),
                    "--actor-id",
                    "fixture-student",
                    "--password-stdin",
                    "--audio",
                    str(audio),
                    "--task-id",
                    "smoke",
                    "--task-version",
                    "1",
                ],
                env=clean_env,
                input_text=password + "\n",
                cwd=root,
            )
        )
        response_id = score["status"]["response_id"]
        backup_dir = root / "backup"
        run(
            [
                str(python),
                "-m",
                "aicefr.local",
                "maintenance",
                "--data-dir",
                str(data_dir),
                "--config",
                str(config_path),
                "--actor-id",
                "fixture-admin",
                "--password-stdin",
                "backup",
                "--destination",
                str(backup_dir),
            ],
            env=clean_env,
            input_text=password + "\n",
            cwd=root,
        )
        restored = root / "restored"
        restored.mkdir()
        shutil.copy2(backup_dir / "metadata.sqlite3", restored / "metadata.sqlite3")
        if (backup_dir / "blobs").is_dir():
            shutil.copytree(backup_dir / "blobs", restored / "blobs")
        code = (
            "import json,sys; from aicefr.storage.sqlite import SQLiteStore; "
            "from aicefr.report.sqlite import SQLiteReportRepository; "
            "s=SQLiteStore(sys.argv[1]); r=SQLiteReportRepository(s).get(sys.argv[2]); "
            "print(json.dumps({'found':r is not None,"
            "'response_id':r.response_id if r else None})); s.close()"
        )
        restored_report = json.loads(
            run(
                [str(python), "-c", code, str(restored), response_id],
                env=clean_env,
                cwd=root,
            )
        )
        report["steps"]["backup_restore_report"] = restored_report == {
            "found": True,
            "response_id": response_id,
        }
        assessment = score["report"]
        report["steps"]["report_created_without_models"] = bool(
            assessment
            and assessment["assessment_status"] == "NOT_EVALUATED"
            and assessment["overall_score"] is None
        )

    report["passed"] = all(report["steps"].values())
    output = evidence / "w5-foundation-smoke.json"
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
