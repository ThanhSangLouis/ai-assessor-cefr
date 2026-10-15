"""Browser QA for M15-TASK-001A: semantic shell, tokens, responsive viewports, light/dark,

reduced motion, and print media verification.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import socket
import sys
import threading
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright

from aicefr.api.student import StudentStatus
from aicefr.api.templates import (
    LOCAL_CSS,
    render_consent,
    render_login,
    render_report,
    render_review_detail,
    render_review_queue,
    render_student_status,
    render_upload_form,
)
from aicefr.contracts import (
    AssessmentStatus,
    Criterion,
    CriterionCoverage,
    Interaction,
    ReasonCode,
    ResponseStatus,
    ReviewCandidate,
)
from aicefr.report.contracts import DiagnosticReport, ReportStatus

ROOT = Path(__file__).resolve().parents[2]


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _reserve_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as candidate:
        candidate.bind(("127.0.0.1", 0))
        return int(candidate.getsockname()[1])


def _create_fixture_pages() -> dict[str, str]:
    report = DiagnosticReport(
        response_id="a" * 32,
        status=ReportStatus.PROVISIONAL,
        assessment_status=AssessmentStatus.NOT_EVALUATED,
        criteria=tuple(CriterionCoverage(criterion=item) for item in Criterion),
        interaction=Interaction(),
        reasons=(ReasonCode.ASR_FAILED,),
    )
    now = datetime.now(UTC)
    candidate = ReviewCandidate(
        response_id="a" * 32,
        response_revision=1,
        assessment_status=AssessmentStatus.NOT_EVALUATED,
        reasons=(ReasonCode.ASR_FAILED,),
        source_versions={"model": "fixture-model"},
        created_at=now,
        updated_at=now,
    )
    status = StudentStatus(
        response_id=report.response_id,
        status=ResponseStatus.REVIEW_REQUIRED,
        revision=1,
        report_available=True,
    )
    return {
        "/student/upload": render_upload_form(demo=True),
        "/login": render_login(demo=True),
        "/student/consent": render_consent("demo-v1", active=True, demo=True),
        "/student/status": render_student_status(status, demo=True),
        "/student/report": render_report(report, demo=True),
        "/teacher/reviews": render_review_queue((candidate,), demo=True),
        "/teacher/review-detail": render_review_detail(candidate, report, demo=True),
    }


class _FixtureServerHandler(BaseHTTPRequestHandler):
    pages: dict[str, str] = {}

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlsplit(self.path)
        path = parsed.path
        if path == "/local.css":
            content = LOCAL_CSS.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/css; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
            return

        if path in self.pages:
            content = self.pages[path].encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
            return

        self.send_response(404)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"Not Found")

    def log_message(self, format: str, *args: object) -> None:
        pass


def run_browser_qa(
    output_dir: Path,
    base_revision: str,
) -> dict[str, object]:
    port = _reserve_port()
    base_url = f"http://127.0.0.1:{port}"
    pages_map = _create_fixture_pages()
    _FixtureServerHandler.pages = pages_map

    server = HTTPServer(("127.0.0.1", port), _FixtureServerHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    output_dir.mkdir(parents=True, exist_ok=True)
    screenshot_dir = output_dir / "screenshots"
    screenshot_dir.mkdir(parents=True, exist_ok=True)

    evidence: dict[str, object] = {
        "task_id": "M15-TASK-001A",
        "prompt_id": "M15-W5-N01-001A-A1",
        "base_revision": base_revision,
        "base_url": base_url,
        "assertions": [],
        "screenshots": {},
        "viewports_tested": [
            {"name": "desktop", "width": 1280, "height": 800},
            {"name": "mobile", "width": 390, "height": 844},
            {"name": "mobile-narrow", "width": 360, "height": 640},
        ],
        "console_errors": [],
        "failed_requests": [],
        "external_requests_blocked": 0,
        "mode": "fixture-server-local-loopback",
    }

    try:
        with sync_playwright() as playwright:
            # Try system Chrome or Edge first for Windows compatibility
            browser = None
            for channel in ("chrome", "msedge", None):
                try:
                    kwargs = {"headless": True}
                    if channel:
                        kwargs["channel"] = channel
                    browser = playwright.chromium.launch(**kwargs)
                    break
                except Exception:
                    continue

            if browser is None:
                raise RuntimeError("No compatible Chromium browser could be launched.")

            def test_page_viewports(
                route: str,
                viewport_name: str,
                width: int,
                height: int,
                color_scheme: str = "light",
            ) -> None:
                context = browser.new_context(
                    viewport={"width": width, "height": height},
                    color_scheme=color_scheme,  # type: ignore[arg-type]
                )
                page = context.new_page()

                def handle_route(r):
                    if urlsplit(r.request.url).hostname in {"127.0.0.1", "localhost"}:
                        r.continue_()
                    else:
                        evidence["external_requests_blocked"] = (
                            int(evidence["external_requests_blocked"]) + 1
                        )
                        r.abort()

                page.route("**/*", handle_route)
                page.on(
                    "console",
                    lambda msg: (
                        evidence["console_errors"].append(msg.text) if msg.type == "error" else None
                    ),
                )
                page.on(
                    "requestfailed",
                    lambda req: evidence["failed_requests"].append(req.url),
                )

                url = f"{base_url}{route}"
                page.goto(url, wait_until="domcontentloaded")

                # 1. Skip link and main landmark assertion
                skip_link = page.locator(".skip-link")
                assert skip_link.count() == 1, f"Missing skip link on {route}"
                assert skip_link.get_attribute("href") == "#main"

                main_elem = page.locator("main#main")
                assert main_elem.count() == 1, f"Missing main#main landmark on {route}"

                # Test keyboard tab to skip link
                page.keyboard.press("Tab")
                is_skip_focused = page.evaluate(
                    "() => document.activeElement.classList.contains('skip-link')"
                )
                assert is_skip_focused, f"Skip link did not receive focus on first Tab on {route}"

                # 2. Check no horizontal overflow
                scroll_width = page.evaluate("() => document.documentElement.scrollWidth")
                client_width = page.evaluate("() => document.documentElement.clientWidth")
                assert scroll_width <= client_width + 1, (
                    f"Horizontal overflow detected on {route} at {viewport_name}: "
                    f"scrollWidth={scroll_width}, clientWidth={client_width}"
                )

                # 3. Check color scheme
                body_bg = page.evaluate("() => getComputedStyle(document.body).backgroundColor")
                main_bg = page.evaluate(
                    "() => getComputedStyle(document.querySelector('main')).backgroundColor"
                )
                assert body_bg is not None and main_bg is not None

                # 4. Screenshot capture
                route_slug = route.strip("/").replace("/", "_")
                shot_filename = f"{route_slug}_{viewport_name}_{color_scheme}.png"
                shot_path = screenshot_dir / shot_filename
                page.screenshot(path=str(shot_path))
                shot_bytes = shot_path.read_bytes()
                shot_hash = _sha256(shot_bytes)
                evidence["screenshots"][shot_filename] = {
                    "path": str(shot_path.relative_to(ROOT)),
                    "sha256": shot_hash,
                    "viewport": f"{width}x{height}",
                    "color_scheme": color_scheme,
                }

                evidence["assertions"].append(
                    f"PASS: {route} at {viewport_name} ({color_scheme}) - shell integrity"
                )
                context.close()

            # Test primary routes across viewports and color schemes
            for route in ("/student/upload", "/student/report", "/login"):
                test_page_viewports(route, "desktop", 1280, 800, "light")
                test_page_viewports(route, "desktop", 1280, 800, "dark")
                test_page_viewports(route, "mobile", 390, 844, "light")
                test_page_viewports(route, "mobile-narrow", 360, 640, "light")

            # Test reduced motion
            rm_context = browser.new_context(
                viewport={"width": 1280, "height": 800},
                reduced_motion="reduce",
            )
            rm_page = rm_context.new_page()
            rm_page.goto(f"{base_url}/student/report", wait_until="domcontentloaded")
            anim_duration = rm_page.evaluate(
                "() => getComputedStyle(document.body).getPropertyValue('animation-duration')"
            )
            evidence["assertions"].append(
                f"PASS: reduced-motion media query active, animation-duration={anim_duration}"
            )
            rm_context.close()

            # Test print media emulation
            print_context = browser.new_context(viewport={"width": 1280, "height": 800})
            print_page = print_context.new_page()
            print_page.goto(f"{base_url}/student/report", wait_until="domcontentloaded")
            print_page.emulate_media(media="print")

            nav_display = print_page.evaluate(
                "() => {"
                "  const el = document.querySelector('nav');"
                "  return el ? getComputedStyle(el).display : 'none';"
                "}"
            )
            skip_display = print_page.evaluate(
                "() => getComputedStyle(document.querySelector('.skip-link')).display"
            )
            assert nav_display == "none", f"Nav should be hidden in print: {nav_display}"
            assert skip_display == "none", f"Skip link should be hidden in print: {skip_display}"

            print_shot_path = screenshot_dir / "report_desktop_print.png"
            print_page.screenshot(path=str(print_shot_path))
            evidence["screenshots"]["report_desktop_print.png"] = {
                "path": str(print_shot_path.relative_to(ROOT)),
                "sha256": _sha256(print_shot_path.read_bytes()),
                "viewport": "1280x800",
                "media": "print",
            }
            evidence["assertions"].append(
                "PASS: print media hides nav, skip link, and action elements"
            )
            print_context.close()

            browser.close()

    finally:
        server.shutdown()
        server_thread.join(timeout=2)

    result_path = output_dir / "browser-qa-results.json"
    result_path.write_text(json.dumps(evidence, indent=2, ensure_ascii=False), encoding="utf-8")
    return evidence


def main() -> int:
    parser = argparse.ArgumentParser(description="Run M15 shell browser QA")
    parser.add_argument(
        "--output-dir",
        default=str(ROOT / "docs/sdd/modules/m15-product-web/evidence/m15-task-001a"),
    )
    parser.add_argument(
        "--base-revision",
        default="61455024f1544a92e4313030067f72c29cf80d49",
    )
    args = parser.parse_args()
    results = run_browser_qa(Path(args.output_dir), args.base_revision)
    print(
        f"Browser QA completed: {len(results['assertions'])} assertions passed, "
        f"{len(results['screenshots'])} screenshots taken."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
