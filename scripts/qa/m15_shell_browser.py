"""Browser QA for M15-TASK-001A: semantic shell, tokens, responsive viewports, light/dark,

reduced motion, print media verification, and WCAG AA contrast / skip-link integrity.
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

from aicefr.api.identity import IdentityApi
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
        "/password-change": IdentityApi._password_page(message="Thông báo thử nghiệm"),
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

        static_files = {
            "/recorder.js": ROOT / "src/aicefr/api/static/recorder.js",
            "/report.js": ROOT / "src/aicefr/api/static/report.js",
        }
        if path in static_files and static_files[path].is_file():
            content = static_files[path].read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "application/javascript; charset=utf-8")
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
    source_fingerprint: str | None = None,
    head_revision: str | None = None,
) -> dict[str, object]:
    output_dir = output_dir.resolve()
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
        "prompt_id": "M15-W5-N01-001A-A2R2",
        "base_revision": base_revision,
        "head_revision": head_revision,
        "source_fingerprint": source_fingerprint,
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
                        evidence["console_errors"].append(f"[{route}] {msg.text}")
                        if msg.type == "error"
                        else None
                    ),
                )
                page.on(
                    "requestfailed",
                    lambda req: evidence["failed_requests"].append(f"[{route}] {req.url}"),
                )

                url = f"{base_url}{route}"
                page.goto(url, wait_until="domcontentloaded")

                # 1. Skip link and main landmark assertion
                skip_link = page.locator(".skip-link")
                assert skip_link.count() == 1, f"Missing skip link on {route}"
                assert skip_link.get_attribute("href") == "#main"

                main_elem = page.locator("main#main")
                assert main_elem.count() == 1, f"Missing main#main landmark on {route}"
                assert main_elem.get_attribute("tabindex") == "-1", (
                    f"main#main missing tabindex=-1 on {route}"
                )

                # Heading check: exactly one H1
                h1_elem = page.locator("h1")
                assert h1_elem.count() == 1, (
                    f"Expected exactly one H1 on {route}, found {h1_elem.count()}"
                )

                # Test keyboard tab to skip link
                page.keyboard.press("Tab")
                is_skip_focused = page.evaluate(
                    "() => Boolean(document.activeElement?.classList.contains('skip-link'))"
                )
                assert is_skip_focused, (
                    f"Skip link did not receive focus on first Tab on {route} ({viewport_name})"
                )

                # Bounding box check: skip link must NOT overlap H1
                skip_box = skip_link.bounding_box()
                h1_box = h1_elem.first.bounding_box()
                assert skip_box is not None, f"Skip link bounding box is None on {route}"
                assert h1_box is not None, f"H1 bounding box is None on {route}"
                assert skip_box["y"] + skip_box["height"] <= h1_box["y"], (
                    f"Skip link overlaps H1 on {route} at {viewport_name}: "
                    f"skip_bottom={skip_box['y'] + skip_box['height']}, h1_top={h1_box['y']}"
                )

                # Press Enter to activate skip link -> focus must move to main#main
                # with visible focus indicator
                page.keyboard.press("Enter")
                url_hash = page.evaluate("() => window.location.hash")
                assert url_hash == "#main", (
                    f"hash not #main after skip Enter on {route} ({viewport_name})"
                )

                focus_check = page.evaluate(
                    """() => {
                        const active = document.activeElement;
                        const main = document.querySelector('main#main');
                        if (!main) return null;
                        const cs = getComputedStyle(main);
                        const r = main.getBoundingClientRect();
                        return {
                            activeId: active ? active.id : null,
                            outlineStyle: cs.outlineStyle,
                            outlineWidth: parseFloat(cs.outlineWidth) || 0,
                            outlineColor: cs.outlineColor,
                            outlineOffset: parseFloat(cs.outlineOffset) || 0,
                            top: r.top,
                            inViewport: r.top >= 0 && r.top < window.innerHeight,
                            width: r.width,
                            height: r.height,
                        };
                    }"""
                )
                assert focus_check is not None, f"main#main element missing on {route}"
                assert focus_check["activeId"] == "main", (
                    f"main#main not focused after skip Enter on {route} ({viewport_name}), "
                    f"got {focus_check['activeId']}"
                )
                assert focus_check["outlineStyle"] != "none", (
                    f"main#main has outlineStyle='none' on focus at {route} ({viewport_name})"
                )
                assert focus_check["outlineWidth"] >= 2.0, (
                    f"main#main outlineWidth {focus_check['outlineWidth']} < 2px on "
                    f"{route} ({viewport_name})"
                )
                assert focus_check["outlineColor"] not in ("transparent", "rgba(0, 0, 0, 0)"), (
                    f"main#main outlineColor is transparent on {route} ({viewport_name})"
                )
                assert focus_check["inViewport"], (
                    f"main#main not in viewport after skip Enter on {route} ({viewport_name})"
                )
                assert focus_check["width"] > 0 and focus_check["height"] > 0, (
                    f"main#main has invalid dimensions on {route} ({viewport_name})"
                )

                # 2. Check no horizontal overflow and no clipping of main, forms, and actions
                clipping_check = page.evaluate(
                    """() => {
                        const doc = document.documentElement;
                        const winW = window.innerWidth;
                        const main = document.querySelector('main#main');
                        const mainRect = main ? main.getBoundingClientRect() : null;
                        const mainOk = mainRect
                            ? (mainRect.left >= 0 && mainRect.right <= winW + 1
                               && mainRect.width > 0 && mainRect.height > 0)
                            : false;

                        // Check all forms on page
                        const forms = Array.from(document.querySelectorAll('form'));
                        const formsChecked = forms.map(f => {
                            const fr = f.getBoundingClientRect();
                            return {
                                action: f.getAttribute('action') || '',
                                valid: fr.width > 0 && fr.left >= 0 && fr.right <= winW + 1,
                                left: fr.left,
                                right: fr.right,
                            };
                        });

                        // Check all primary action elements
                        const candidates = Array.from(
                            document.querySelectorAll(
                                'button:not([disabled]), input[type=submit]:not([disabled]), '
                                + 'a:not(.skip-link)'
                            )
                        );
                        const visibleActions = candidates.filter(el => {
                            const cs = getComputedStyle(el);
                            return cs.display !== 'none'
                                && cs.visibility !== 'hidden'
                                && el.offsetParent !== null;
                        });

                        const actionsChecked = visibleActions.map(el => {
                            const r = el.getBoundingClientRect();
                            const cs = getComputedStyle(el);

                            let ancestorClipped = false;
                            let curr = el.parentElement;
                            while (curr && curr !== document.documentElement) {
                                const acs = getComputedStyle(curr);
                                if (acs.overflowX === 'hidden' || acs.overflowX === 'clip') {
                                    const ar = curr.getBoundingClientRect();
                                    if (r.right > ar.right + 1 || r.left < ar.left - 1) {
                                        ancestorClipped = true;
                                        break;
                                    }
                                }
                                curr = curr.parentElement;
                            }

                            const withinViewportH = r.left >= 0 && r.right <= winW + 1;
                            const hasSize = r.width > 0 && r.height > 0;
                            const interactable = cs.pointerEvents !== 'none';

                            return {
                                tag: el.tagName.toLowerCase(),
                                text: (el.innerText || el.value || '').trim().slice(0, 30),
                                width: r.width,
                                height: r.height,
                                left: r.left,
                                right: r.right,
                                withinViewportH,
                                ancestorClipped,
                                interactable,
                                valid: withinViewportH && hasSize
                                    && !ancestorClipped && interactable,
                            };
                        });

                        return {
                            scrollWidth: doc.scrollWidth,
                            clientWidth: doc.clientWidth,
                            mainOk,
                            formsChecked,
                            actionsChecked,
                        };
                    }"""
                )
                assert clipping_check["scrollWidth"] <= clipping_check["clientWidth"] + 1, (
                    f"Horizontal overflow detected on {route} at {viewport_name}: "
                    f"scrollWidth={clipping_check['scrollWidth']}, "
                    f"clientWidth={clipping_check['clientWidth']}"
                )
                assert clipping_check["mainOk"], (
                    f"main landmark is clipped or outside viewport on {route} at {viewport_name}"
                )
                for f_info in clipping_check["formsChecked"]:
                    assert f_info["valid"], (
                        f"Form '{f_info['action']}' clipped on {route} at {viewport_name}: "
                        f"left={f_info['left']}, right={f_info['right']}"
                    )
                for a_info in clipping_check["actionsChecked"]:
                    assert a_info["valid"], (
                        f"Action '{a_info['tag']}: {a_info['text']}' clipped on {route} at "
                        f"{viewport_name}: withinViewportH={a_info['withinViewportH']}, "
                        f"ancestorClipped={a_info['ancestorClipped']}, "
                        f"interactable={a_info['interactable']}"
                    )
                num_actions = len(clipping_check["actionsChecked"])

                # 3. Check computed WCAG AA contrast for button and link (normal & hover)
                contrast_results = page.evaluate(
                    """() => {
                        function parseRgb(colorStr) {
                            const m = colorStr.match(/rgba?\\((\\d+),\\s*(\\d+),\\s*(\\d+)/);
                            if (!m) return [0, 0, 0];
                            return [parseInt(m[1]), parseInt(m[2]), parseInt(m[3])];
                        }
                        function lum([r, g, b]) {
                            const a = [r, g, b].map(v => {
                                v /= 255;
                                return v <= 0.03928
                                    ? v / 12.92
                                    : Math.pow((v + 0.055) / 1.055, 2.4);
                            });
                            return a[0] * 0.2126 + a[1] * 0.7152 + a[2] * 0.0722;
                        }
                        function contrast(c1, c2) {
                            const l1 = lum(parseRgb(c1));
                            const l2 = lum(parseRgb(c2));
                            const lighter = Math.max(l1, l2);
                            const darker = Math.min(l1, l2);
                            return (lighter + 0.05) / (darker + 0.05);
                        }
                        function getEffectiveBg(el) {
                            let curr = el;
                            while (curr) {
                                const bg = getComputedStyle(curr).backgroundColor;
                                if (bg && bg !== 'transparent' && bg !== 'rgba(0, 0, 0, 0)') {
                                    return bg;
                                }
                                curr = curr.parentElement;
                            }
                            return getComputedStyle(document.body).backgroundColor
                                || 'rgb(255, 255, 255)';
                        }
                        const btns = Array.from(
                            document.querySelectorAll('button, input[type=submit]')
                        );
                        const btn = btns.find(b => !b.disabled && b.offsetParent !== null);
                        let btnNormal = null;
                        if (btn) {
                            const cs = getComputedStyle(btn);
                            btnNormal = contrast(cs.color, cs.backgroundColor);
                        }
                        const link = Array.from(document.querySelectorAll('a:not(.skip-link)'))
                            .find(a => a.offsetParent !== null);
                        let linkNormal = null;
                        if (link) {
                            const cs = getComputedStyle(link);
                            const parentBg = getEffectiveBg(link);
                            linkNormal = contrast(cs.color, parentBg);
                        }
                        return { btnNormal, linkNormal };
                    }"""
                )
                if contrast_results["btnNormal"] is not None:
                    assert contrast_results["btnNormal"] >= 4.5, (
                        f"Button text contrast {contrast_results['btnNormal']:.2f} < 4.5 on "
                        f"{route} ({color_scheme})"
                    )
                if contrast_results["linkNormal"] is not None:
                    assert contrast_results["linkNormal"] >= 4.5, (
                        f"Link text contrast {contrast_results['linkNormal']:.2f} < 4.5 on "
                        f"{route} ({color_scheme})"
                    )

                # Hover contrast check for button
                active_btn_locator = page.locator(
                    "button:not([disabled]), input[type=submit]:not([disabled])"
                ).first
                if active_btn_locator.count() > 0 and active_btn_locator.is_visible():
                    active_btn_locator.hover()
                    btn_hover_ratio = page.evaluate(
                        """() => {
                            function parseRgb(colorStr) {
                                const m = colorStr.match(/rgba?\\((\\d+),\\s*(\\d+),\\s*(\\d+)/);
                                if (!m) return [0, 0, 0];
                                return [parseInt(m[1]), parseInt(m[2]), parseInt(m[3])];
                            }
                            function lum([r, g, b]) {
                                const a = [r, g, b].map(v => {
                                    v /= 255;
                                    return v <= 0.03928
                                        ? v / 12.92
                                        : Math.pow((v + 0.055) / 1.055, 2.4);
                                });
                                return a[0] * 0.2126 + a[1] * 0.7152 + a[2] * 0.0722;
                            }
                            const btns = Array.from(
                                document.querySelectorAll('button, input[type=submit]')
                            );
                            const btn = btns.find(b => !b.disabled && b.offsetParent !== null);
                            if (!btn) return null;
                            const cs = getComputedStyle(btn);
                            const l1 = lum(parseRgb(cs.color));
                            const l2 = lum(parseRgb(cs.backgroundColor));
                            return (Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05);
                        }"""
                    )
                    if btn_hover_ratio is not None:
                        assert btn_hover_ratio >= 4.5, (
                            f"Button hover contrast {btn_hover_ratio:.2f} < 4.5 on "
                            f"{route} ({color_scheme})"
                        )

                # Hover contrast check for link
                active_link_locator = page.locator("a:not(.skip-link)").first
                if active_link_locator.count() > 0 and active_link_locator.is_visible():
                    active_link_locator.hover()
                    link_hover_ratio = page.evaluate(
                        """() => {
                            function parseRgb(colorStr) {
                                const m = colorStr.match(/rgba?\\((\\d+),\\s*(\\d+),\\s*(\\d+)/);
                                if (!m) return [0, 0, 0];
                                return [parseInt(m[1]), parseInt(m[2]), parseInt(m[3])];
                            }
                            function lum([r, g, b]) {
                                const a = [r, g, b].map(v => {
                                    v /= 255;
                                    return v <= 0.03928
                                        ? v / 12.92
                                        : Math.pow((v + 0.055) / 1.055, 2.4);
                                });
                                return a[0] * 0.2126 + a[1] * 0.7152 + a[2] * 0.0722;
                            }
                            function getEffectiveBg(el) {
                                let curr = el;
                                while (curr) {
                                    const bg = getComputedStyle(curr).backgroundColor;
                                    if (bg && bg !== 'transparent' && bg !== 'rgba(0, 0, 0, 0)') {
                                        return bg;
                                    }
                                    curr = curr.parentElement;
                                }
                                return getComputedStyle(document.body).backgroundColor
                                    || 'rgb(255, 255, 255)';
                            }
                            const links = Array.from(
                                document.querySelectorAll('a:not(.skip-link)')
                            );
                            const link = links.find(a => a.offsetParent !== null);
                            if (!link) return null;
                            const cs = getComputedStyle(link);
                            const l1 = lum(parseRgb(cs.color));
                            const l2 = lum(parseRgb(getEffectiveBg(link)));
                            return (Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05);
                        }"""
                    )
                    if link_hover_ratio is not None:
                        assert link_hover_ratio >= 4.5, (
                            f"Link hover contrast {link_hover_ratio:.2f} < 4.5 on "
                            f"{route} ({color_scheme})"
                        )

                # 4. Screenshot capture
                route_slug = route.strip("/").replace("/", "_")
                shot_filename = f"{route_slug}_{viewport_name}_{color_scheme}.png"
                shot_path = screenshot_dir / shot_filename
                page.screenshot(path=str(shot_path))
                shot_bytes = shot_path.read_bytes()
                shot_hash = _sha256(shot_bytes)
                rel_shot_path = str(shot_path.resolve().relative_to(ROOT.resolve())).replace(
                    "\\", "/"
                )
                evidence["screenshots"][shot_filename] = {
                    "path": rel_shot_path,
                    "sha256": shot_hash,
                    "viewport": f"{width}x{height}",
                    "color_scheme": color_scheme,
                }

                evidence["assertions"].append(
                    f"PASS: {route} at {viewport_name} ({color_scheme}) - skip activation, "
                    f"visible focus outline ({focus_check['outlineWidth']}px "
                    f"{focus_check['outlineStyle']}), 1 H1, contrast >= 4.5, "
                    f"no clipping ({num_actions} primary actions verified)"
                )
                context.close()

            # Test primary routes across viewports and color schemes
            for route in ("/student/upload", "/student/report", "/login", "/password-change"):
                test_page_viewports(route, "desktop", 1280, 800, "light")
                test_page_viewports(route, "desktop", 1280, 800, "dark")
                test_page_viewports(route, "mobile", 390, 844, "light")
                test_page_viewports(route, "mobile-narrow", 360, 640, "light")

            # Test reduced motion on elements with transition/animation
            rm_context = browser.new_context(
                viewport={"width": 1280, "height": 800},
                reduced_motion="reduce",
            )
            rm_page = rm_context.new_page()
            rm_page.goto(f"{base_url}/student/report", wait_until="domcontentloaded")
            durations = rm_page.evaluate(
                """() => {
                    const btn = document.querySelector('button');
                    const inp = document.querySelector('input');
                    const body = document.body;
                    const btnDur = btn
                        ? parseFloat(getComputedStyle(btn).transitionDuration)
                        : 0;
                    return {
                        btnTransition: btnDur,
                        bodyAnim: parseFloat(getComputedStyle(body).animationDuration) || 0,
                    };
                }"""
            )
            assert durations["btnTransition"] <= 0.01, (
                f"Button transition duration not reduced: {durations['btnTransition']}"
            )
            assert durations["bodyAnim"] <= 0.01, (
                f"Body animation duration not reduced: {durations['bodyAnim']}"
            )
            evidence["assertions"].append(
                f"PASS: reduced-motion media query active, btn={durations['btnTransition']}s, "
                f"bodyAnim={durations['bodyAnim']}s <= 0.01"
            )
            rm_context.close()

            # Test print media emulation
            print_context = browser.new_context(viewport={"width": 1280, "height": 800})
            print_page = print_context.new_page()
            print_page.goto(f"{base_url}/student/report", wait_until="domcontentloaded")
            print_page.emulate_media(media="print")

            hidden_elements = print_page.evaluate(
                """() => {
                    const nav = document.querySelector('nav');
                    const skip = document.querySelector('.skip-link');
                    const btns = Array.from(document.querySelectorAll('button'));
                    const forms = Array.from(document.querySelectorAll('form'));
                    return {
                        navHidden: nav ? getComputedStyle(nav).display === 'none' : true,
                        skipHidden: skip ? getComputedStyle(skip).display === 'none' : true,
                        btnsHidden: btns.every(b => getComputedStyle(b).display === 'none'),
                        formsHidden: forms.every(f => getComputedStyle(f).display === 'none'),
                    };
                }"""
            )
            assert hidden_elements["navHidden"], "Nav should be hidden in print"
            assert hidden_elements["skipHidden"], "Skip link should be hidden in print"
            assert hidden_elements["btnsHidden"], "Action buttons should be hidden in print"
            assert hidden_elements["formsHidden"], "Forms should be hidden in print"

            print_shot_path = screenshot_dir / "report_desktop_print.png"
            print_page.screenshot(path=str(print_shot_path))
            evidence["screenshots"]["report_desktop_print.png"] = {
                "path": str(print_shot_path.resolve().relative_to(ROOT.resolve())).replace(
                    "\\", "/"
                ),
                "sha256": _sha256(print_shot_path.read_bytes()),
                "viewport": "1280x800",
                "media": "print",
            }
            evidence["assertions"].append(
                "PASS: print media hides nav, skip link, action buttons, and forms"
            )
            print_context.close()

            browser.close()

        # Check console and failed requests
        assert len(evidence["console_errors"]) == 0, (
            f"Unexpected console errors: {evidence['console_errors']}"
        )
        assert len(evidence["failed_requests"]) == 0, (
            f"Unexpected failed requests: {evidence['failed_requests']}"
        )

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
        default=str(ROOT / "docs/sdd/modules/m15-product-web/evidence/m15-task-001a-a2r2"),
    )
    parser.add_argument(
        "--base-revision",
        default="6baf720f173b440eb961676b09ea290058a39b35",
    )
    parser.add_argument(
        "--source-fingerprint",
        default=None,
        help="Final workspace fingerprint",
    )
    parser.add_argument(
        "--head-revision",
        default=None,
        help="Head git revision if committed",
    )
    args = parser.parse_args()
    results = run_browser_qa(
        Path(args.output_dir),
        args.base_revision,
        source_fingerprint=args.source_fingerprint,
        head_revision=args.head_revision,
    )
    print(
        f"Browser QA completed: {len(results['assertions'])} assertions passed, "
        f"{len(results['screenshots'])} screenshots taken, "
        f"{len(results['console_errors'])} console errors, "
        f"{len(results['failed_requests'])} failed requests."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
