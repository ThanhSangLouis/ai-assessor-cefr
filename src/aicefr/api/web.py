"""Presentation-layer setup: Jinja2 templates and static files.

Three screens used to live as inline HTML strings inside the Python code,
206 lines of them, with quotes escaped by hand inside onclick attributes.
Nothing linted them, nothing tested them, and fixing one spot broke another.
Splitting them into templates and static files means every piece now lives in
a file of its own proper format.

See decision QD-05 in docs/plan/QUYET_DINH.md.
"""

from __future__ import annotations

from pathlib import Path

from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

PACKAGE_DIR = Path(__file__).parent
TEMPLATE_DIR = PACKAGE_DIR / "templates"
STATIC_DIR = PACKAGE_DIR / "static"

templates = Jinja2Templates(directory=str(TEMPLATE_DIR))


def asset(path: str) -> str:
    """A static URL carrying the file's own modification time as a version.

    Without this, a browser that has already seen `/static/report.js` keeps
    serving its cached copy after a deploy, and the student reads an old screen
    against a new API. It is not a theoretical risk: it cost a debugging session
    here, where a screen kept rendering without a block that was demonstrably in
    the file on disk and in the HTTP response.

    The version is the mtime rather than a content hash because the cost has to
    be paid on every page render: `stat` is one syscall, hashing the file is
    reading it. A missing file falls back to the bare path -- a 404 on a script
    is a problem to fix, not a reason for the page to fail to render.
    """
    try:
        stamp = int((STATIC_DIR / path).stat().st_mtime)
    except OSError:
        return f"/static/{path}"
    return f"/static/{path}?v={stamp}"


templates.env.globals["asset"] = asset


def mount_static(app) -> None:
    """Mount the static file directory onto the application."""
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
