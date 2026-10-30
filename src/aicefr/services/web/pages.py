"""Every page of the product, drawn by the web service (D043).

A page is a template plus what the template must quote: who is signed in (from
the gateway), and the limits in force -- QC thresholds, upload size, the model's
band thresholds -- asked of the assessment service, so that a page never shows
one number while the machine applies another. The data on a page is fetched by
its script from the service that owns it.
"""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from aicefr.api.deps import ROLE_HOME, optional_account
from aicefr.api.web import templates
from aicefr.auth import google, passwords
from aicefr.config import Settings
from aicefr.research.agreement import BANDS, CRITERIA
from aicefr.services import Peers
from aicefr.storage.auth_repository import (
    AVATAR_COLORS,
    AVATAR_ICONS,
    DAILY_GOALS,
    Account,
    Role,
)
from aicefr.storage.rating_repository import UNSCORABLE_REASONS

router = APIRouter()


@dataclass
class Services:
    settings: Settings
    peers: Peers


_services: Services | None = None


def configure(services: Services) -> None:
    global _services
    _services = services


def svc() -> Services:
    if _services is None:  # pragma: no cover - configured when the service is built
        raise RuntimeError("web pages used before configure()")
    return _services


def _limits() -> dict:
    return svc().peers.assessment.page_limits()


def _page(request: Request, template: str, account: Account | None, nav: str, **extra):
    return templates.TemplateResponse(
        request, template, {"account": account, "nav_here": nav, **extra}
    )


def _response_nav(account: Account | None) -> str:
    """Navigation item to mark on a page about one response.

    A student reaches it from their own list; a teacher from the review queue.
    """
    if account is not None and account.role in (Role.TEACHER, Role.ADMIN):
        return "queue"
    return "mine"


# ================================================================= everyone


@router.get("/", response_class=HTMLResponse, tags=["web"])
def page_home(request: Request, account: Account | None = Depends(optional_account)):
    """The submission screen; the product page for a visitor (D026).

    A teacher or an administrator, who has nothing to submit, goes to the start
    page of the role. The thresholds quoted are the ones in force.
    """
    lim = _limits()
    if account is None:
        return _page(
            request,
            "landing.html",
            None,
            "home",
            min_duration_s=lim["min_duration_s"],
            max_duration_s=lim["max_duration_s"],
            max_size_mib=lim["max_size_mib"],
        )
    if account.role in (Role.TEACHER, Role.ADMIN):
        return RedirectResponse(ROLE_HOME[account.role], status_code=303)
    return _page(
        request,
        "submit.html",
        account,
        "submit",
        prep_seconds=lim["prep_seconds"],
        min_duration_s=lim["min_duration_s"],
        max_duration_s=lim["max_duration_s"],
        sample_rate_hz=lim["sample_rate_hz"],
        max_size_mib=lim["max_size_mib"],
    )


@router.get("/login", response_class=HTMLResponse, tags=["web"])
def page_login(request: Request):
    """The login form, with Google next to it when this instance has it turned on (D029).

    `?google=<code>` says why a Google round trip came back here; only known
    codes are shown, as fixed sentences.
    """
    return templates.TemplateResponse(
        request,
        "login.html",
        {
            "nav_here": "login",
            "google_enabled": svc().settings.google_enabled,
            "google_signup": svc().settings.google_signup,
            "self_signup": svc().settings.self_signup,
            "google_error": google.MESSAGES.get(request.query_params.get("google", "")),
        },
    )


def _signed_out_page(request: Request, account: Account | None, template: str):
    """Sign-up and recovery (D065) are for somebody signed out; a signed-in
    person goes to the start page of their role. Off with AICEFR_SELF_SIGNUP=0."""
    settings = svc().settings
    if not settings.self_signup:
        return RedirectResponse("/login", status_code=303)
    if account is not None:
        return RedirectResponse(ROLE_HOME.get(account.role, "/"), status_code=303)
    return templates.TemplateResponse(
        request,
        template,
        {
            "nav_here": "login",
            "min_length": passwords.MIN_LENGTH,
            "google_enabled": settings.google_enabled,
            "google_signup": settings.google_signup,
        },
    )


@router.get("/signup", response_class=HTMLResponse, tags=["web"])
def page_signup(request: Request, account: Account | None = Depends(optional_account)):
    """A student opens an account with a password (D065)."""
    return _signed_out_page(request, account, "signup.html")


@router.get("/forgot", response_class=HTMLResponse, tags=["web"])
def page_forgot(request: Request, account: Account | None = Depends(optional_account)):
    """A forgotten password replaced with the recovery code (D065)."""
    return _signed_out_page(request, account, "forgot.html")


@router.get("/bands", response_class=HTMLResponse, tags=["web"])
def page_bands(request: Request, account: Account | None = Depends(optional_account)):
    """What A1 to C2 describe, and what the machine measures of each aspect (D028, D059).

    Open to visitors too: it explains a result, it does not show one. The five
    thresholds are those of the model in force, the same numbers `to_band` uses.
    """
    from aicefr.report.bands import page_rows
    from aicefr.scoring.band_map import band_spans

    lim = _limits()
    spans = [
        {"band": b.value, "low": None if lo == float("-inf") else lo,
         "high": None if hi == float("inf") else hi}
        for b, lo, hi in band_spans(lim["band_thresholds"])
    ]  # fmt: skip
    return _page(
        request,
        "bands.html",
        account,
        "bands",
        rows=page_rows(),
        spans=spans,
        model_version=lim["model_version"],
    )


@router.get("/terms", include_in_schema=False)
@router.get("/consent", include_in_schema=False)
def page_terms_gone() -> RedirectResponse:
    """The terms page and the consent screen before it are gone (D064); old links go home."""
    return RedirectResponse("/", status_code=301)


@router.get("/account", response_class=HTMLResponse, tags=["web"])
def page_account(request: Request, account: Account | None = Depends(optional_account)):
    """The signed-in person's own account: profile, security, history, data (D028, D029).

    `?google=<code>` reports how a Google round trip ended. Only known codes are
    shown, as fixed sentences: nothing typed into the URL reaches the page.
    """
    if account is None:
        return RedirectResponse("/login?next=/account", status_code=303)
    code = request.query_params.get("google", "")
    google_note = "Đã liên kết tài khoản Google." if code == "linked" else google.MESSAGES.get(code)
    return _page(
        request,
        "account.html",
        account,
        "account",
        min_length=passwords.MIN_LENGTH,
        home=ROLE_HOME.get(account.role, "/"),
        google_enabled=svc().settings.google_enabled,
        google_note=google_note,
        google_ok=code == "linked",
        avatar_icons=AVATAR_ICONS,
        avatar_colors=AVATAR_COLORS,
        daily_goals=DAILY_GOALS,
    )


# ================================================================= students


@router.get("/my-responses", response_class=HTMLResponse, tags=["web"])
def page_my_responses(request: Request, account: Account | None = Depends(optional_account)):
    """A student's own submission history. FR-04."""
    return _page(request, "my_responses.html", account, "mine")


@router.get("/progress/{response_id}", response_class=HTMLResponse, tags=["web"])
def page_progress(
    request: Request, response_id: str, account: Account | None = Depends(optional_account)
):
    """Processing progress screen. FR-05."""
    return _page(request, "progress.html", account, _response_nav(account), response_id=response_id)


@router.get("/my-progress", response_class=HTMLResponse, tags=["web"])
def page_my_progress(request: Request, account: Account | None = Depends(optional_account)):
    """A student's own results over time. FR-27: "am I getting better", not "what happened"."""
    return _page(request, "my_progress.html", account, "progress")


@router.get("/my-assignments", response_class=HTMLResponse, tags=["web"])
def page_my_assignments(request: Request, account: Account | None = Depends(optional_account)):
    """What a student's classes set them, and joining a class with its code (D054)."""
    return _page(request, "my_assignments.html", account, "assignments")


@router.get("/teach/classes", response_class=HTMLResponse, tags=["web"])
def page_classes(request: Request, account: Account | None = Depends(optional_account)):
    """A teacher's classes and what each has been set (D054)."""
    return _page(request, "classes.html", account, "classes", class_id="")


@router.get("/teach/classes/{class_id}", response_class=HTMLResponse, tags=["web"])
def page_class(
    request: Request, class_id: str, account: Account | None = Depends(optional_account)
):
    return _page(request, "classes.html", account, "classes", class_id=class_id)


@router.get("/credits", response_class=HTMLResponse, tags=["web"])
def page_credits(request: Request, account: Account | None = Depends(optional_account)):
    """A learner's runs: what is left, what each recording cost, and the packs on sale (D053)."""
    return _page(request, "credits.html", account, "credits")


@router.get("/practice", response_class=HTMLResponse, tags=["web"])
def page_practice(request: Request, account: Account | None = Depends(optional_account)):
    """The learner's lesson path: next lesson, today, reviews, units (D025, M13)."""
    return _page(request, "practice_path.html", account, "practice")


@router.get("/practice/review", response_class=HTMLResponse, tags=["web"])
def page_practice_review(request: Request, account: Account | None = Depends(optional_account)):
    """Today's spaced review (D025, M15). Declared before /practice/{task_id}."""
    return _page(request, "lesson.html", account, "practice", mode="review", lesson_id="")


@router.get("/practice/lessons/{lesson_id}", response_class=HTMLResponse, tags=["web"])
def page_lesson(
    request: Request,
    lesson_id: str,
    account: Account | None = Depends(optional_account),
):
    """One lesson, step by step (D025, M14). A teacher always gets the draft as a preview.

    A teacher cannot record a learner's attempt, so the learner view would end
    in a refusal at the first step; the preview runs the same steps and stores
    nothing.
    """
    lim = _limits()
    teacher_preview = account is not None and account.is_staff
    return _page(
        request,
        "lesson.html",
        account,
        "teach" if teacher_preview else "practice",
        mode="preview" if teacher_preview else "lesson",
        lesson_id=lesson_id,
        max_size_mib=lim["max_size_mib"],
        sample_rate_hz=lim["sample_rate_hz"],
        min_duration_s=lim["min_duration_s"],
    )


@router.get("/practice/results/{response_id}", response_class=HTMLResponse, tags=["web"])
def page_practice_result(
    request: Request, response_id: str, account: Account | None = Depends(optional_account)
):
    """Result of one practice attempt (D023). Declared before `/practice/{task_id}`."""
    return _page(request, "practice_result.html", account, "practice", response_id=response_id)


@router.get("/practice/{task_id}", response_class=HTMLResponse, tags=["web"])
def page_practice_task(
    request: Request, task_id: str, account: Account | None = Depends(optional_account)
):
    """One practice task: missions, tips, recorder. D023."""
    lim = _limits()
    return _page(
        request,
        "practice_task.html",
        account,
        "practice",
        task_id=task_id,
        sample_rate_hz=lim["sample_rate_hz"],
        max_size_mib=lim["max_size_mib"],
        min_duration_s=lim["min_duration_s"],
    )


@router.get("/report/{response_id}", response_class=HTMLResponse, tags=["web"])
def page_report(
    request: Request, response_id: str, account: Account | None = Depends(optional_account)
):
    """Result report. The QC limits in force go to the page so that a rejection
    reason quotes the threshold actually applied, not a number copied into the
    script."""
    lim = _limits()
    return _page(
        request,
        "report.html",
        account,
        _response_nav(account),
        response_id=response_id,
        min_duration_s=lim["min_duration_s"],
        max_duration_s=lim["max_duration_s"],
        max_size_mib=lim["max_size_mib"],
    )


# ================================================================= staff


@router.get("/admin", response_class=HTMLResponse, tags=["web"])
def page_admin(request: Request, account: Account | None = Depends(optional_account)):
    """Administration screen. FR-08, FR-34, FR-35, FR-36."""
    return _page(request, "admin.html", account, "admin")


@router.get("/admin/study", response_class=HTMLResponse, tags=["web"])
def page_study(request: Request, account: Account | None = Depends(optional_account)):
    """The feedback study (D040)."""
    return _page(request, "admin_study.html", account, "admin")


@router.get("/review/stats", response_class=HTMLResponse, tags=["web"])
def page_cohort_stats(request: Request, account: Account | None = Depends(optional_account)):
    """Class-level statistics for teachers. FR-29.

    Declared BEFORE `/review/{response_id}`: routes match in declaration order,
    and with the parameterised route first this path would be read as the
    review of a response whose id is "stats".
    """
    return _page(request, "cohort_stats.html", account, "stats")


@router.get("/review/{response_id}", response_class=HTMLResponse, tags=["web"])
def page_review_one(
    request: Request, response_id: str, account: Account | None = Depends(optional_account)
):
    """Single-response review screen, two-column layout. FR-30, FR-31."""
    return _page(request, "review_one.html", account, "queue", response_id=response_id)


@router.get("/review", response_class=HTMLResponse, tags=["web"])
def page_queue(request: Request, account: Account | None = Depends(optional_account)):
    return _page(request, "queue.html", account, "queue")


@router.get("/rate", response_class=HTMLResponse, tags=["web"])
def page_rate_list(request: Request, account: Account | None = Depends(optional_account)):
    """A rater's own sheets, batch by batch, in their own order (D030)."""
    return _page(request, "rate_list.html", account, "rate")


@router.get("/rate/{assignment_id}", response_class=HTMLResponse, tags=["web"])
def page_rate_one(
    request: Request, assignment_id: str, account: Account | None = Depends(optional_account)
):
    """One sheet: the task, the recording, the form. Nothing about the machine."""
    return _page(
        request,
        "rate_one.html",
        account,
        "rate",
        assignment_id=assignment_id,
        criteria=CRITERIA,
        bands=BANDS,
        unscorable_reasons=UNSCORABLE_REASONS,
    )


@router.get("/teach", response_class=HTMLResponse, tags=["web"])
def page_teach(request: Request, account: Account | None = Depends(optional_account)):
    """Teachers author paths, units and lessons (D025, M16)."""
    return _page(request, "teach_paths.html", account, "teach")


@router.get("/teach/insights", response_class=HTMLResponse, tags=["web"])
def page_teach_insights(request: Request, account: Account | None = Depends(optional_account)):
    """How the class moves through a path; listen and correct the machine (D025, M18)."""
    return _page(request, "teach_insights.html", account, "teach")


@router.get("/teach/lessons/{lesson_id}", response_class=HTMLResponse, tags=["web"])
def page_teach_lesson(
    request: Request, lesson_id: str, account: Account | None = Depends(optional_account)
):
    """The lesson builder (D025, M17)."""
    return _page(
        request,
        "teach_lesson.html",
        account,
        "teach",
        lesson_id=lesson_id,
        max_size_mib=_limits()["max_size_mib"],
    )
