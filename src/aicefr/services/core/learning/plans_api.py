"""Paths composed by the path model (D046): a learner's own, a teacher's draft.

D074: a learner chooses the bands to study, from where they are (suggested
by their latest assessment) to where they want to be, and gets a path of the
published lessons of those bands; a teacher sees the bands of their class,
composes a path for a group of them and assigns it to the group, which then
replaces each learner's own plan.

A learner asks for a path in their own words and gets an ordered list of
published lessons with the reasons each was picked; it stays on their practice
page until they ask again or set it aside. A teacher describes a path, reviews
the proposal, drops what they do not want and saves the rest as a DRAFT path
of copies they then edit and publish like any other (D025). Nothing here writes
lesson content: the model only picks and orders lessons teachers wrote.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, model_validator

from aicefr.api.deps import STAFF_ONLY, STUDENT_ONLY
from aicefr.contracts import Band, Criterion
from aicefr.lessons.composer import (
    BAND_RANK,
    BANDS,
    COMPOSER_VERSION,
    MAX_LENGTH,
    MIN_LENGTH,
    Candidate,
    Goal,
    Learner,
    compose,
    goal_dict,
)
from aicefr.lessons.model import Topic, new_id
from aicefr.lessons.progress import is_complete, lesson_state
from aicefr.pronunciation.vietnamese import Pattern
from aicefr.pronunciation.vietnamese import profile as pronunciation_profile
from aicefr.services.core.learning.lessons_api import (
    AUTHORING,
    PRONUNCIATION_WINDOW,
    _audit,
    _criterion,
    _infos,
    svc,
)
from aicefr.storage.auth_repository import Account, Role
from aicefr.storage.lesson_repository import NotFound
from aicefr.storage.plan_repository import PlanRepository

router = APIRouter()

# A pattern counts as one to work on from this error rate, once there are
# enough chances to measure it (the D039 profile's own threshold).
WEAK_PATTERN_RATE = 0.25

_plans: PlanRepository | None = None


def configure(plans: PlanRepository) -> None:
    global _plans
    _plans = plans


def plans() -> PlanRepository:
    if _plans is None:  # pragma: no cover - configured at import of main
        raise RuntimeError("plans API used before configure()")
    return _plans


class GoalIn(BaseModel):
    band_from: Band | None = None
    band_to: Band | None = None
    criteria: list[Criterion] = Field(default_factory=list, max_length=5)
    topics: list[Topic] = Field(default_factory=list, max_length=10)
    patterns: list[Pattern] = Field(default_factory=list, max_length=5)
    wish: str = Field(default="", max_length=300)
    length: int = Field(default=8, ge=MIN_LENGTH, le=MAX_LENGTH)

    def goal(self) -> Goal:
        return Goal(
            band_from=self.band_from,
            band_to=self.band_to,
            criteria=tuple(self.criteria),
            topics=tuple(self.topics),
            patterns=tuple(self.patterns),
            wish=" ".join(self.wish.split()),
            length=self.length,
        )


class SaveIn(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    description: str = Field(default="", max_length=1000)
    # The lessons to keep, when the teacher dropped some of the proposal.
    lesson_ids: list[str] | None = Field(default=None, max_length=MAX_LENGTH)


def _catalog(published_paths_only: bool) -> tuple[list[Candidate], list[list[Candidate]]]:
    """Published lessons of the paths, each where it sits, and the paths in order.

    A learner's plan draws on published paths only, the ones they can open; a
    teacher's on every path not archived. Only published versions are used, so
    a draft nobody reviewed never enters a plan.
    """
    repo = svc().lessons
    stats = repo.lesson_stats()
    candidates: list[Candidate] = []
    paths: list[list[Candidate]] = []
    for p in repo.paths(published_only=published_paths_only):
        seq: list[Candidate] = []
        for u in repo.outline(p["path_id"], published_only=True):
            topic = Topic(u["topic"]) if u["topic"] in Topic._value2member_map_ else None
            for item in u["lessons"]:
                lesson = item["lesson"]
                st = stats.get(lesson.lesson_id, {})
                seq.append(
                    Candidate(
                        lesson=lesson,
                        path_id=p["path_id"],
                        path_title=p["title"],
                        unit_title=u["title"],
                        topic=topic,
                        criterion=_criterion(lesson, u),
                        position=len(seq),
                        attempts=st.get("attempts", 0),
                        passed=st.get("passed", 0),
                    )
                )
        candidates.extend(seq)
        paths.append(seq)
    return candidates, paths


def _learner(account: Account, candidates: list[Candidate]) -> Learner:
    """The learner's band, weakest criteria, weak sounds and where they are in each lesson."""
    latest = svc().peers.assessment.latest_assessment(account_id=account.account_id)
    weakest = tuple(
        Criterion(c)
        for c in (latest or {}).get("weakest_criteria", [])
        if c in Criterion._value2member_map_
    )
    known = latest and latest.get("band") in Band._value2member_map_
    band = Band(latest["band"]) if known else None
    repo = svc().lessons
    rows = repo.attempts(account_id=account.account_id)
    infos = _infos(rows)
    completed, started = set(), set()
    for c in candidates:
        st = lesson_state(c.lesson, infos)
        if is_complete(c.lesson, st):
            completed.add(c.lesson_id)
        elif st.started:
            started.add(c.lesson_id)
    recent = repo.attempts(account_id=account.account_id, limit=PRONUNCIATION_WINDOW)
    weak = tuple(
        Pattern(f["pattern"])
        for f in pronunciation_profile(recent)["patterns"]
        if f["enough"] and (f["rate"] or 0) >= WEAK_PATTERN_RATE
    )
    return Learner(band, weakest, weak, frozenset(completed), frozenset(started))


def _with_progress(plan: dict, account: Account) -> dict:
    """The stored plan with each lesson's state today and whether it can still be opened."""
    repo = svc().lessons
    infos = _infos(repo.attempts(account_id=account.account_id))
    live = {c.lesson_id: c.lesson for c in _catalog(published_paths_only=True)[0]}
    done = total = 0
    units = []
    for u in plan["units"]:
        lessons = []
        for item in u["lessons"]:
            lesson = live.get(item["lesson_id"])
            if lesson is None:
                status = "unavailable"
            else:
                st = lesson_state(lesson, infos)
                status = "completed" if is_complete(lesson, st) else st.status
            total += 1
            done += status == "completed"
            lessons.append({**item, "status": status})
        units.append({**u, "lessons": lessons})
    return {**plan, "units": units, "lessons_total": total, "lessons_completed": done}


def _view(stored: dict, account: Account) -> dict:
    return {
        "plan_id": stored["plan_id"],
        "created_at": stored["created_at"],
        **_with_progress(stored["plan"], account),
    }


# ================================================================= learners


@router.post("/api/v1/learn/plan", tags=["student"])
def make_my_plan(body: GoalIn, account: Account = STUDENT_ONLY) -> dict:
    """A path of published lessons for what the learner says they want. FR-81."""
    candidates, paths = _catalog(published_paths_only=True)
    if not candidates:
        raise HTTPException(409, "chưa có bài học nào được xuất bản để ghép lộ trình")
    plan = compose(candidates, paths, body.goal(), _learner(account, candidates))
    if not plan.lesson_ids:
        raise HTTPException(422, "không tìm được bài nào hợp với mục tiêu này; thử nới điều kiện")
    data = plan.as_dict()
    plan_id = plans().save(
        account.account_id, "student", goal_dict(plan.goal), data, COMPOSER_VERSION
    )
    return _view(plans().get(plan_id), account)


@router.get("/api/v1/learn/plan", tags=["student"])
def my_plan(account: Account = STUDENT_ONLY) -> dict:
    stored = plans().active(account.account_id)
    if stored is None:
        return {"plan": None}
    return {"plan": _view(stored, account)}


@router.delete("/api/v1/learn/plan", tags=["student"])
def close_my_plan(account: Account = STUDENT_ONLY) -> dict:
    return {"closed": plans().close(account.account_id)}


# ================================================================= bands (D074)

# Lessons a band brings into a learner's path, up to the composer's maximum.
LESSONS_PER_BAND = 6


class BandsIn(BaseModel):
    band_from: Band
    band_to: Band

    @model_validator(mode="after")
    def _ordered(self) -> BandsIn:
        if BAND_RANK[self.band_from] > BAND_RANK[self.band_to]:
            raise ValueError("band bắt đầu phải thấp hơn hoặc bằng band mục tiêu")
        return self


def _next(band: Band) -> Band:
    return BANDS[min(BAND_RANK[band] + 1, len(BANDS) - 1)]


@router.get("/api/v1/learn/bands", tags=["student"])
def my_bands(account: Account = STUDENT_ONLY) -> dict:
    """The learner's bands: a suggestion from their latest assessment, and the plan in force."""
    latest = svc().peers.assessment.latest_assessment(account_id=account.account_id)
    known = latest and latest.get("band") in Band._value2member_map_
    assessed = Band(latest["band"]) if known else None
    start = assessed or BANDS[0]
    stored = plans().active(account.account_id)
    return {
        "assessed_band": assessed.value if assessed else None,
        "suggested_from": start.value,
        "suggested_to": _next(start).value,
        "plan": _view(stored, account) if stored else None,
    }


@router.post("/api/v1/learn/bands", tags=["student"])
def choose_bands(body: BandsIn, account: Account = STUDENT_ONLY) -> dict:
    """A path of the published lessons from `band_from` to `band_to`, replacing their own.

    Each band gets its own share (`LESSONS_PER_BAND`), composed band by band
    and joined in order, so a band with many lessons never crowds out the next.
    """
    candidates, paths = _catalog(published_paths_only=True)
    if not candidates:
        raise HTTPException(409, "chưa có bài học nào được xuất bản để ghép lộ trình")
    learner = _learner(account, candidates)
    chosen = BANDS[BAND_RANK[body.band_from] : BAND_RANK[body.band_to] + 1]
    units: list[dict] = []
    warnings: list[str] = []
    for band in chosen:
        goal = Goal(band_from=band, band_to=band, length=LESSONS_PER_BAND)
        part = compose(candidates, paths, goal, learner).as_dict()
        units.extend(u for u in part["units"] if u["band"] == band.value)
        warnings.extend(w for w in part["warnings"] if "liền kề" in w or "Chỉ tìm được" in w)
    if not units:
        raise HTTPException(422, "chưa có bài đã xuất bản nào ở các band này")
    goal = {"band_from": body.band_from.value, "band_to": body.band_to.value}
    data = {"goal": goal, "units": units, "warnings": list(dict.fromkeys(warnings))}
    plan_id = plans().save(account.account_id, "student", goal, data, COMPOSER_VERSION)
    return _view(plans().get(plan_id), account)


class AssignIn(BaseModel):
    account_ids: list[str] = Field(min_length=1, max_length=200)


@router.post("/api/v1/teach/paths/{path_id}/assign", tags=["teacher"])
def assign_path(path_id: str, body: AssignIn, account: Account = STAFF_ONLY) -> dict:
    """A published path as the plan of each of these learners (D074).

    A teacher assigns to the learners of their own classes, an administrator
    to anyone. The learner sees it in place of their own plan, with who
    assigned it, and may choose their own bands again later.
    """
    repo = svc().lessons
    path = next((p for p in repo.paths(published_only=True) if p["path_id"] == path_id), None)
    if path is None:
        raise HTTPException(404, "không tìm thấy lộ trình đã xuất bản này")
    if account.role is not Role.ADMIN:
        outside = [
            a
            for a in body.account_ids
            if not svc().peers.assessment.teaches(teacher_id=account.account_id, student_id=a)
        ]
        if outside:
            raise HTTPException(403, "có học viên không thuộc lớp bạn phụ trách")
    units = []
    for u in repo.outline(path_id, published_only=True):
        lessons = [
            {
                "lesson_id": item["lesson"].lesson_id,
                "title": item["lesson"].title,
                "summary": item["lesson"].summary,
                "band": item["lesson"].band.value,
                "steps": len(item["lesson"].steps),
                "reasons": [],
            }
            for item in u["lessons"]
        ]
        if lessons:
            units.append(
                {
                    "title": u["title"],
                    "band": u["band"],
                    "topic": u["topic"],
                    "criterion": None,
                    "lessons": lessons,
                }
            )
    if not units:
        raise HTTPException(409, "lộ trình này chưa có bài nào được xuất bản")
    bands = [u["band"] for u in units]
    goal = {
        "band_from": min(bands, key=lambda b: BAND_RANK[Band(b)]),
        "band_to": max(bands, key=lambda b: BAND_RANK[Band(b)]),
        "assigned_by": account.display_name,
        "path_id": path_id,
        "path_title": path["title"],
    }
    data = {"goal": goal, "units": units, "warnings": []}
    for learner in dict.fromkeys(body.account_ids):
        plans().save(learner, "student", goal, data, "teacher-assigned")
    _audit(account, "lesson.path.assign", path_id, f"learners={len(set(body.account_ids))}")
    return {"assigned": len(set(body.account_ids)), "path_title": path["title"]}


# ================================================================= teachers


@router.post("/api/v1/teach/paths/compose", tags=["teacher"], dependencies=[AUTHORING])
def compose_path(body: GoalIn, account: Account = STAFF_ONLY) -> dict:
    """A proposed path from the lessons already published, for the teacher to review. FR-82."""
    candidates, paths = _catalog(published_paths_only=False)
    if not candidates:
        raise HTTPException(409, "chưa có bài học nào được xuất bản để ghép lộ trình")
    plan = compose(candidates, paths, body.goal())
    data = plan.as_dict()
    plan_id = plans().save(
        account.account_id, "teacher", goal_dict(plan.goal), data, COMPOSER_VERSION
    )
    return {"plan_id": plan_id, **data}


@router.post(
    "/api/v1/teach/paths/compose/{plan_id}/save", tags=["teacher"], dependencies=[AUTHORING]
)
def save_composed_path(plan_id: str, body: SaveIn, account: Account = STAFF_ONLY) -> dict:
    """The proposal as a draft path of copies, which the teacher edits and publishes."""
    stored = plans().get(plan_id)
    if stored is None or stored["audience"] != "teacher":
        raise HTTPException(404, "không tìm thấy đề xuất")
    if stored["account_id"] != account.account_id:
        raise HTTPException(403, "đề xuất này của giảng viên khác")
    if stored["path_id"]:
        raise HTTPException(409, "đề xuất này đã được lưu thành lộ trình")
    keep = set(body.lesson_ids) if body.lesson_ids is not None else None
    units = []
    for u in stored["plan"]["units"]:
        ids = [i["lesson_id"] for i in u["lessons"] if keep is None or i["lesson_id"] in keep]
        if ids:
            units.append((u, ids))
    if not units:
        raise HTTPException(422, "cần giữ lại ít nhất một bài")

    repo = svc().lessons
    copies = []
    for u, ids in units:
        lessons = []
        for lesson_id in ids:
            found = repo.published(lesson_id)
            if found is None:
                raise HTTPException(409, "một bài trong đề xuất không còn được xuất bản")
            lesson = found[0].model_copy(deep=True)
            lesson.lesson_id = new_id("l")
            lesson.sample = False
            lessons.append(lesson)
        copies.append((u, lessons))

    bands = [Band(u["band"]) for u, _ in copies]
    description = body.description or (
        f"Ghép từ {sum(len(ls) for _, ls in copies)} bài đã xuất bản bằng model lộ trình"
        f" ({COMPOSER_VERSION}). Mục tiêu: {stored['goal'].get('wish') or 'theo các ô đã chọn'}."
    )
    try:
        path_id = repo.create_path(
            body.title, description[:1000], bands[0], bands[-1], by=account.pseudonym
        )
        for u, lessons in copies:
            unit_id = repo.add_unit(
                path_id,
                u["title"][:160],
                band=Band(u["band"]),
                criterion=Criterion(u["criterion"]) if u["criterion"] else None,
                topic=Topic(u["topic"]) if u["topic"] else None,
            )
            for lesson in lessons:
                repo.add_lesson(unit_id, lesson, by=account.pseudonym)
    except NotFound:  # pragma: no cover - the path was made in this request
        raise HTTPException(409, "không tạo được lộ trình") from None
    plans().saved_as(plan_id, path_id)
    kept = sum(len(ls) for _, ls in copies)
    _audit(account, "lesson.path.compose", path_id, f"plan={plan_id} lessons={kept}")
    return {"path_id": path_id, "lessons": kept}
