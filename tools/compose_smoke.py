"""Walk the running stack through its gateway, as a browser would (D043).

    docker compose up -d --build
    python tools/compose_smoke.py            # against http://localhost:8000

Creates two throwaway accounts with random passwords (kept in memory only),
then checks that every service answers through the gateway and that the paths
between them work (D044): a recording scored by the speech service over
RabbitMQ, a lesson step measured by it, the pages and the sidebar (web) asking
core, the personal export and erasure across responses and lesson attempts.
And that the gateway does not trust what a browser says about itself.
Exits 1 at the first check that fails.
"""

from __future__ import annotations

import argparse
import base64
import http.cookiejar
import io
import json
import math
import secrets
import struct
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid
import wave


def tone(seconds: float, rate: int = 16_000) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(
            b"".join(
                struct.pack("<h", int(0.2 * 32767 * math.sin(2 * math.pi * 220 * i / rate)))
                for i in range(int(seconds * rate))
            )
        )
    return buf.getvalue()


class Browser:
    def __init__(self, base: str) -> None:
        self.base = base.rstrip("/")
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar())
        )

    def call(self, method: str, path: str, body=None, headers=None, form=None, files=None):
        data, head = None, dict(headers or {})
        if body is not None:
            data, head["Content-Type"] = json.dumps(body).encode(), "application/json"
        elif files is not None or form is not None:
            boundary = uuid.uuid4().hex
            parts = []
            for k, v in (form or {}).items():
                head_line = f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"'
                parts.append(f"{head_line}\r\n\r\n{v}\r\n".encode())
            for k, (name, content, kind) in (files or {}).items():
                parts.append(
                    f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"; filename="{name}"'
                    f"\r\nContent-Type: {kind}\r\n\r\n".encode()
                    + content
                    + b"\r\n"
                )
            data = b"".join(parts) + f"--{boundary}--\r\n".encode()
            head["Content-Type"] = f"multipart/form-data; boundary={boundary}"
        req = urllib.request.Request(self.base + path, data=data, method=method, headers=head)
        try:
            with self.opener.open(req, timeout=60) as r:
                raw = r.read()
                return r.status, (json.loads(raw) if raw[:1] in (b"{", b"[") else raw.decode())
        except urllib.error.HTTPError as e:
            raw = e.read()
            try:
                return e.code, json.loads(raw)
            except ValueError:
                return e.code, raw.decode(errors="replace")

    def login(self, pseudonym: str, password: str) -> Browser:
        status, body = self.call(
            "POST", "/api/v1/auth/login", {"pseudonym": pseudonym, "password": password}
        )
        check(status == 200, f"login {pseudonym}", body)
        return self


RESULTS: list[tuple[str, bool]] = []


def check(ok: bool, what: str, detail=None) -> None:
    RESULTS.append((what, ok))
    print(f"{'OK  ' if ok else 'FAIL'} {what}" + ("" if ok else f": {detail}"))
    if not ok:
        sys.exit(1)


def create_account(pseudonym: str, role: str) -> str:
    password = secrets.token_urlsafe(18)
    subprocess.run(
        ["docker", "compose", "exec", "-T", "core", "python", "-m", "aicefr.accounts_cli",
         "them", "--but-danh", pseudonym, "--vai-tro", role, "--mat-khau", password],
        check=True,
        capture_output=True,
    )  # fmt: skip
    return password


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--base", default="http://localhost:8000")
    args = ap.parse_args(argv)
    tag = secrets.token_hex(2).upper()
    student_id, admin_id = f"SV-{tag}", f"QT-{tag}"
    student_pw, admin_pw = create_account(student_id, "student"), create_account(admin_id, "admin")

    anon = Browser(args.base)
    status, page = anon.call("GET", "/")
    check(status == 200 and "<html" in page.lower(), "web: the product page through the gateway")
    status, _ = anon.call("GET", "/internal/identity/session")
    check(status == 404, "gateway: /internal/ is never forwarded")
    forged = base64.urlsafe_b64encode(
        json.dumps({"account_id": "x", "pseudonym": "QT-99", "role": "admin"}).encode()
    ).decode()
    status, _ = anon.call("GET", "/api/v1/stats", headers={"X-Aicefr-Account": forged})
    check(status == 401, "gateway: an account header sent by the browser is ignored")

    student = Browser(args.base).login(student_id, student_pw)
    status, me = student.call("GET", "/api/v1/me")
    check(status == 200 and me["pseudonym"] == student_id, "core: who am I")
    status, consent = student.call(
        "POST",
        "/api/v1/me/consent",
        form={"audio_storage_allowed": "true", "research_use_allowed": "true"},
    )
    check(status == 200 and consent["may_submit"], "core: consent signed")

    status, sub = student.call(
        "POST", "/api/v1/responses", form={"task_id": "P3"},
        files={"audio": ("a.wav", tone(35), "audio/wav")},
    )  # fmt: skip
    check(status == 202, "core: a recording accepted", sub)
    rid = sub["response_id"]
    deadline = time.time() + 90
    while True:
        status, st = student.call("GET", f"/api/v1/responses/{rid}/status")
        if not st.get("is_pending") or time.time() > deadline:
            break
        time.sleep(1)
    check(
        st.get("is_pending") is False and st["status"] != "FAILED",
        "speech over RabbitMQ: the recording was scored",
        st,
    )
    status, report = student.call("GET", f"/api/v1/responses/{rid}")
    check(status == 200 and report["response_id"] == rid, "core: the report")

    lesson = "lesson-a2-neighborhood"
    status, step = student.call(
        "POST", f"/api/v1/learn/lessons/{lesson}/steps/{lesson}-s5/attempts",
        files={"audio": ("s.wav", tone(4), "audio/wav")},
    )  # fmt: skip
    check(status == 200 and "result" in step, "core -> speech: a lesson step measured", step)

    status, badges = student.call("GET", "/api/v1/me/badges")
    check(status == 200 and "reviews_due" in badges, "web -> core: the sidebar counts")
    status, export = student.call("GET", "/api/v1/me/export.json")
    check(
        status == 200 and export["response_count"] == 1 and export["lesson_attempt_count"] == 1,
        "core: the export gathers responses, consent and lesson attempts",
        export if status != 200 else None,
    )

    admin = Browser(args.base).login(admin_id, admin_pw)
    status, audit = admin.call("GET", "/api/v1/audit?limit=200")
    actions = {e["action"] for e in audit} if status == 200 else set()
    check({"consent.sign", "export.personal"} <= actions, "core: the audit log")
    status, plan = admin.call("GET", "/api/v1/admin/billing")
    check(status == 200, "core: the plan screen", plan)
    status, erased = admin.call(
        "POST", "/api/v1/admin/erase", {"speaker_id": student_id, "confirm_speaker_id": student_id}
    )
    check(
        status == 200 and erased["lesson_attempts"] == 1,
        "core: erasure reached the lesson attempts",
        erased,
    )

    # The core role owns its schema and nothing else.
    denied = subprocess.run(
        ["docker", "compose", "exec", "-T", "postgres", "psql", "-U", "postgres", "-d", "aicefr",
         "-c", "SET ROLE core; CREATE TABLE public.smoke (i int);"],
        capture_output=True,
        text=True,
    )  # fmt: skip
    check(
        denied.returncode != 0 and "permission denied" in denied.stderr,
        "postgres: the core role cannot write outside its schema",
        denied.stdout + denied.stderr,
    )
    status, page = student.call("GET", "/my-progress")
    check(status == 200 and student_id in page, "web: a page with the signed-in account")

    print(f"\n{len(RESULTS)} checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
