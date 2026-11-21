"""The class diagram is the design the code follows, attribute by attribute.

`tests/test_diagrams.py` checks that every class drawn exists. This goes one
level down: every attribute and operation drawn on an entity of
`docs/sdd/diagrams/class/detailed/02_class.drawio` must be found in the code, in one of three
ways:

1. **the same name** on the entity's code class, in snake case
   (`dailyGoalS` -> `Account.daily_goal_s`);
2. **a reference kept as an id**: the diagram draws the relation as an
   attribute typed with the other entity (`learner: Account`), the code keeps
   the other's id (`account_id`) -- `ELSEWHERE` says which field;
3. **a field of the stored document or of the report** that the code class
   does not declare (`Account.emailVerified` is the `email_verified` key the
   auth repository writes; `Response.transcript` is `Transcript.text` in the
   response's report) -- `ELSEWHERE` says where.

`ELSEWHERE` is checked both ways: an entry for an attribute no longer drawn, or
pointing at nothing, fails too. And every business collection in the schema
snapshot belongs to an entity drawn, except the technical ones in `NOT_DRAWN`.
"""

from __future__ import annotations

import ast
import json
import pathlib
import re
import xml.etree.ElementTree as ET
from functools import cache

import pytest

pytestmark = pytest.mark.unit

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "aicefr"
CLASS_DIR = ROOT / "docs" / "sdd" / "diagrams" / "class"
DIAGRAM = CLASS_DIR / "detailed" / "02_class.drawio"
SNAPSHOT = ROOT / "docs" / "db" / "schema_core.json"

# The code class of each entity drawn, by module.
ENTITY_CLASS = {
    "Account": "storage/auth_repository.py",
    "AuditEntry": "contracts.py",
    "Task": "storage/task_repository.py",
    "Response": "contracts.py",
    "Review": "contracts.py",
    "CoachUpgrade": "contracts.py",
    "Classroom": "storage/classroom_repository.py",
    "LessonPath": "storage/lesson_repository.py",
    "Unit": "storage/lesson_repository.py",
    "Lesson": "lessons/model.py",
    "Step": "lessons/model.py",
    "StepAttempt": "storage/lesson_repository.py",
    "WordDrill": "storage/drill_repository.py",
    "DrillPassage": "storage/drill_repository.py",
    "ReviewItem": "storage/lesson_repository.py",
    "Achievement": "storage/lesson_repository.py",
    "LearningPlan": "storage/plan_repository.py",
    "Order": "storage/billing_repository.py",
    "Wallet": "storage/metering_repository.py",
    "PriceList": "metering/pricing.py",
    "LedgerEntry": "storage/metering_repository.py",
}

# Attributes not on their entity's class under their own name. The value is
# "field" (a member of the entity's class under another name), "Class.member"
# (a member of another code class), or "path:key" (a key the module writes).
ELSEWHERE = {
    # References kept as ids.
    ("AuditEntry", "actor"): "actor_id",
    ("Response", "speaker"): 'storage/repository.py:"account_id"',
    ("Response", "task"): 'storage/repository.py:"task_id"',
    ("Review", "reviewer"): "reviewer_id",
    ("Response", "lockedBy"): "ReviewLock.reviewer_id",
    ("Response", "lockedUntil"): "ReviewLock.locked_until",
    ("Classroom", "teachers"): "teacher_ids",
    ("StepAttempt", "learner"): "account_id",
    ("StepAttempt", "step"): "StepResult.step_id",
    # D105: the attempt's round, verdict and speaking time are its result's.
    ("StepAttempt", "round"): "StepResult.round",
    ("StepAttempt", "passed"): "StepResult.passed",
    ("StepAttempt", "speakingS"): "StepResult.speaking_s",
    ("WordDrill", "learner"): "account_id",
    ("WordDrill", "response"): "response_id",
    ("DrillPassage", "learner"): "account_id",
    ("ReviewItem", "learner"): "account_id",
    ("ReviewItem", "lesson"): "lesson_id",
    ("ReviewItem", "drill"): "drill_id",
    ("Achievement", "learner"): "account_id",
    ("LearningPlan", "owner"): "account_id",
    ("Wallet", "owner"): "user_ref",
    ("LedgerEntry", "wallet"): "user_ref",
    ("LedgerEntry", "response"): "key",
    # Another name for the same thing.
    ("Review", "decidedAt"): "created_at",
    ("LearningPlan", "lessons"): "plan",
    # Keys of the stored document the code class does not declare.
    ("Account", "emailVerified"): 'storage/auth_repository.py:"email_verified"',
    ("Account", "emailCodes"): 'storage/auth_repository.py:"email_codes"',
    ("Account", "emailReminders"): 'storage/auth_repository.py:"email_reminders"',
    ("Account", "reminderSentOn"): 'storage/auth_repository.py:"reminder_sent_on"',
    ("AuditEntry", "id"): 'storage/audit_repository.py:"id"',
    ("AuditEntry", "service"): 'storage/audit_repository.py:"service"',
    ("Lesson", "publishedVersion"): 'storage/lesson_repository.py:"published_version"',
    ("Lesson", "versions"): 'storage/lesson_repository.py:"versions"',
    ("Lesson", "media"): 'storage/lesson_repository.py:"media"',
    ("Lesson", "archived"): 'storage/lesson_repository.py:"archived"',
    ("PriceList", "freeRuns"): 'services/core/metering/price_book.py:"free_runs"',
    ("PriceList", "packs"): 'services/core/metering/price_book.py:"packs"',
    ("PriceList", "changedAt"): 'services/core/metering/price_book.py:"changed_at"',
    ("Response", "replayLabels"): 'storage/replay_repository.py:"replay_labels"',
    ("Response", "createdAt"): 'storage/repository.py:"created_at"',
    # The response's report: the scored result the response holds.
    ("Response", "reasonCodes"): "reasons",
    ("Response", "durationMs"): "QcResult.duration_ms",
    ("Response", "transcript"): "Transcript.text",
    ("Response", "overall06"): "Assessment.overall_0_6",
    ("Response", "overallBand"): "Assessment.overall_band",
    ("Response", "criterionScores"): "Assessment.indicators",
    ("Response", "intervalLow"): "ScoreInterval.low",
    ("Response", "intervalHigh"): "ScoreInterval.high",
    ("Response", "feedback"): "Assessment.comments",
    ("Response", "modelVersion"): "Assessment.model_version",
    ("Response", "teacherVerified"): "Assessment.teacher_verified",
    ("Response", "isSingleBand"): "ScoreInterval.is_single_band",
}

# Each entity that is the root of a collection, and its collection. The others
# live inside their root's document (`Review` in `Response`, `Step` in
# `Lesson`, ...): `EMBEDDED` names the root.
COLLECTION = {
    "Account": "account",
    "AuditEntry": "audit_log",
    "Task": "task",
    "Response": "response",
    "Classroom": "classroom",
    "LessonPath": "path",
    "Lesson": "lesson",
    "StepAttempt": "attempt",
    "WordDrill": "word_drill",
    "DrillPassage": "drill_passage",
    "ReviewItem": "review_item",
    "Achievement": "achievement",
    "LearningPlan": "learning_plan",
    "Order": "order",
    "Wallet": "wallet",
    "PriceList": "price_list",
    "LedgerEntry": "ledger",
}
EMBEDDED = {
    "Review": "Response",
    "CoachUpgrade": "Response",
    "Unit": "LessonPath",
    "Step": "Lesson",
}
# Collections of the technical machinery, not of the business: not drawn.
NOT_DRAWN = {
    "session": "login sessions, a mechanism like a cookie",
    "system": "configuration, counters, migrations",
    "push_subscription": "a browser's push endpoint; D088 keeps it on the ERD only",
}


def snake(name: str) -> str:
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", name).lower()


@cache
def code_classes() -> dict[str, list[tuple[str, set[str]]]]:
    """Every class in the code: where it is, and its fields, properties and methods."""
    found: dict[str, list[tuple[str, set[str]]]] = {}
    for path in SRC.rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.ClassDef):
                members = {
                    b.target.id
                    for b in node.body
                    if isinstance(b, ast.AnnAssign) and isinstance(b.target, ast.Name)
                } | {b.name for b in node.body if isinstance(b, ast.FunctionDef)}
                found.setdefault(node.name, []).append((path.relative_to(SRC).as_posix(), members))
    return found


def members_of(name: str, module: str | None = None) -> set[str] | None:
    places = [m for p, m in code_classes().get(name, []) if module in (None, p)]
    return set().union(*places) if places else None


@cache
def drawn(diagram: pathlib.Path = DIAGRAM) -> dict[str, list[str]]:
    """Each entity drawn and the names of its attributes and operations."""
    cells = list(ET.parse(diagram).getroot().iter("mxCell"))
    out: dict[str, list[str]] = {}
    for box in cells:
        title = box.get("value") or ""
        if "swimlane" not in (box.get("style") or "") or "entity" not in title:
            continue
        rows = [c.get("value") or "" for c in cells if c.get("parent") == box.get("id")]
        out[title.split("<br>")[-1]] = [
            m.group(1) for r in rows if (m := re.match(r"[-+] (\w+)", r))
        ]
    return out


def found(entity: str, attribute: str, elsewhere: dict | None = None) -> bool:
    own = members_of(entity, ENTITY_CLASS[entity]) or set()
    if snake(attribute) in own:
        return True
    where = (ELSEWHERE if elsewhere is None else elsewhere).get((entity, attribute))
    if where is None:
        return False
    if ":" in where:
        path, key = where.split(":", 1)
        return (SRC / path).exists() and key in (SRC / path).read_text(encoding="utf-8")
    if "." in where:
        cls, member = where.split(".", 1)
        return member in (members_of(cls) or set())
    return where in own


def test_every_entity_drawn_has_its_code_class():
    assert sorted(drawn()) == sorted(ENTITY_CLASS), "sơ đồ và ENTITY_CLASS lệch nhau"
    missing = [e for e, m in ENTITY_CLASS.items() if members_of(e, m) is None]
    assert not missing, f"không có lớp trong module đã ghi: {missing}"


def test_every_attribute_drawn_is_kept_in_the_code():
    lost = [
        f"{entity}.{attribute}"
        for entity, attributes in drawn().items()
        for attribute in attributes
        if not found(entity, attribute)
    ]
    assert not lost, f"thuộc tính trên sơ đồ không có chỗ lưu trong mã: {lost}"


def test_no_stale_entry_in_the_table_of_other_places():
    gone = [f"{e}.{a}" for e, a in ELSEWHERE if a not in drawn().get(e, [])]
    assert not gone, f"ELSEWHERE còn thuộc tính đã không còn trên sơ đồ: {gone}"
    own_name = [
        f"{e}.{a}" for e, a in ELSEWHERE if snake(a) in (members_of(e, ENTITY_CLASS[e]) or set())
    ]
    assert not own_name, f"ELSEWHERE thừa, mã đã có đúng tên: {own_name}"


def test_every_business_collection_belongs_to_an_entity_drawn():
    collections = set(json.loads(SNAPSHOT.read_text(encoding="utf-8")))
    owned = set(COLLECTION.values())
    stray = sorted(collections - owned - set(NOT_DRAWN))
    assert not stray, f"collection không thuộc thực thể nào trên sơ đồ: {stray}"
    assert set(COLLECTION) | set(EMBEDDED) == set(drawn()), "thực thể chưa có collection hay gốc"
    assert all(root in drawn() for root in EMBEDDED.values())
    code = "\n".join(p.read_text(encoding="utf-8") for p in SRC.rglob("*.py"))
    unused = [c for c in owned if c not in collections and f'"{c}"' not in code]
    assert not unused, f"COLLECTION nhắc collection mã không dùng: {unused}"


def _generator_spec() -> dict[str, list[str]]:
    """Each entity of `tools/gen_class_diagram.py` and its attributes, in order."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "gen_class_diagram", ROOT / "tools/gen_class_diagram.py"
    )
    gen = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(gen)  # type: ignore[union-attr]
    return {
        title.split(gen.BR)[-1]: [
            m.group(1) for line in lines if (m := re.match(r"[-+] (\w+)", line))
        ]
        for _cid, title, lines in gen.CLASSES
    }


def test_every_box_drawn_matches_the_generator_spec():
    """The drawio is routed by hand, the spec is where attributes are added: they must agree.

    The diagram had drifted once: D094's lesson counters were in the spec but
    never drawn on `Wallet`, `PriceList` and `LedgerEntry`, and every other
    check passed, since they only ask that what is drawn exists in the code.
    """
    spec, boxes = _generator_spec(), drawn()
    assert sorted(spec) == sorted(boxes), "sơ đồ và bộ sinh không cùng các thực thể"
    differ = {e: (spec[e], boxes[e]) for e in spec if spec[e] != boxes[e]}
    assert not differ, f"hộp trên sơ đồ khác đặc tả trong bộ sinh: {differ}"


def _page(diagram: pathlib.Path) -> tuple[dict[str, list[str]], list[tuple[str, str, str]]]:
    """Each box's rows as drawn, and each edge as (source, target, style without ports)."""
    cells = list(ET.parse(diagram).getroot().iter("mxCell"))
    name = {
        c.get("id"): (c.get("value") or "").split("<br>")[-1]
        for c in cells
        if "swimlane" in (c.get("style") or "")
    }
    rows: dict[str, list[str]] = {}
    for c in cells:
        if c.get("parent") in name and c.get("vertex") == "1":
            rows.setdefault(name[c.get("parent")], []).append(c.get("value") or "")
    edges = []
    for c in cells:
        if c.get("edge") == "1":
            style = ";".join(
                p
                for p in (c.get("style") or "").split(";")
                if p and not p.startswith(("exit", "entry"))
            )
            edges.append((name[c.get("source")], name[c.get("target")], style))
    return rows, edges


def test_the_core_page_is_a_subset_of_the_detailed_page():
    """The report's compact page keeps the main attributes of the detailed one.

    Both are derived from Nguyên's A4 layout by `tools/derive_class_diagram.py`.
    The core page may leave rows out, but every row it draws is a row of the
    detailed page, word for word, and it draws the very same relations.
    """
    core_rows, core_edges = _page(CORE)
    full_rows, full_edges = _page(DETAILED)
    assert sorted(core_rows) == sorted(full_rows), "hai trang không cùng các hộp"
    extra = {b: [r for r in rs if r not in full_rows[b]] for b, rs in core_rows.items()}
    extra = {b: rs for b, rs in extra.items() if rs}
    assert not extra, f"trang gọn có dòng không có ở trang chi tiết: {extra}"
    assert sorted(core_edges) == sorted(full_edges), "hai trang phải vẽ cùng các quan hệ"


# ---------------------------------------------------------------- detailed page
# `02_class_detailed.drawio`: Nguyên's A4 layout at the detailed level, derived
# by `tools/derive_class_diagram.py`. Same entities; its new names below.
DETAILED = CLASS_DIR / "detailed" / "02_class_detailed.drawio"
CORE = CLASS_DIR / "02_class_core.drawio"
DETAILED_ELSEWHERE = {
    **ELSEWHERE,
    ("DrillPassage", "drills"): "drill_ids",
    ("StepAttempt", "reviewItem"): "review_item_id",
    ("ReviewItem", "step"): "step_id",
    ("Response", "criterionIndicators"): "Assessment.indicators",
}


def test_every_attribute_on_the_detailed_page_is_in_the_code():
    page = drawn(DETAILED)
    assert sorted(page) == sorted(ENTITY_CLASS), "trang chi tiết và ENTITY_CLASS lệch nhau"
    missing = [
        f"{e}.{a}"
        for e, attrs in page.items()
        for a in attrs
        if not found(e, a, DETAILED_ELSEWHERE)
    ]
    assert not missing, f"trang chi tiết vẽ thứ code không có: {missing}"


@pytest.mark.parametrize("page", [DETAILED, CORE], ids=lambda p: p.name)
def test_relationships_follow_the_rules(page: pathlib.Path):
    """Each edge is the kind its attribute says it is.

    Composition: a part that lives and dies with its whole, held by the whole.
    Aggregation: the holder gathers MANY independent parts, a `List` of them.
    Association: the holder keeps ONE attribute typed with the other class
    (an enum included: it is stored, so it is not a dependency).
    Dependency: only for a type used but not stored -- none on this page.
    One edge per attribute typed with an entity; one edge per enum used.
    """
    import html

    cells = list(ET.parse(page).getroot().iter("mxCell"))
    name, enums, attrs = {}, set(), {}
    for c in cells:
        if "swimlane" in (c.get("style") or ""):
            title = c.get("value") or ""
            name[c.get("id")] = title.split("<br>")[-1]
            if "enumeration" in title:
                enums.add(name[c.get("id")])
    for c in cells:
        if c.get("parent") in name and c.get("vertex") == "1":
            attrs.setdefault(name[c.get("parent")], []).append(html.unescape(c.get("value") or ""))
    typed = re.compile(r":\s*(List<)?(\w+)>?\s*$")

    def held(owner: str, target: str) -> list[str]:
        return [a for a in attrs.get(owner, []) if (m := typed.search(a)) and m.group(2) == target]

    def kind(style: str) -> str:
        d = dict(p.split("=", 1) for p in style.split(";") if "=" in p)
        if d.get("startArrow", "").startswith("diamond") or d.get("endArrow", "").startswith(
            "diamond"
        ):
            return "composition" if d.get("startFill", d.get("endFill")) == "1" else "aggregation"
        if d.get("dashed") == "1":
            return "dependency"
        if d.get("endArrow") == "block":
            return "generalization"
        return "association"

    edges: dict[tuple[str, str], list[str]] = {}
    for c in cells:
        if c.get("edge") == "1":
            pair = (name[c.get("source")], name[c.get("target")])
            edges.setdefault(pair, []).append(kind(c.get("style") or ""))
    bad = []
    for (s, t), kinds in edges.items():
        lines = held(s, t)
        if not lines:
            bad.append(f"{s}->{t}: {kinds} nhưng {s} không có thuộc tính kiểu {t}")
        for k in kinds:
            many = any("List<" in a for a in lines)
            if k == "aggregation" and (not many or t in enums):
                bad.append(f"{s}->{t}: aggregation phải gom nhiều {t} độc lập (List<{t}>)")
            if k == "association" and many:
                bad.append(
                    f"{s}->{t}: giữ List<{t}> là aggregation/composition, không phải association"
                )
            if k in ("dependency", "generalization"):
                bad.append(f"{s}->{t}: {k} nhưng {t} được lưu thành thuộc tính")
    for owner in attrs:
        for t in set(name.values()):
            n_attr, n_edge = len(held(owner, t)), len(edges.get((owner, t), []))
            want = (1 if n_attr else 0) if t in enums else n_attr
            if n_edge != want:
                bad.append(f"{owner}: {n_attr} thuộc tính kiểu {t}, {n_edge} đường (cần {want})")
    assert not bad, bad


@pytest.mark.parametrize("page", [DETAILED, CORE], ids=lambda p: p.name)
def test_every_line_starts_and_ends_on_its_box(page: pathlib.Path):
    """A port is a fraction of its box: outside 0..1 the line starts in empty space.

    It happened once: on the core page `ReviewItem` is shorter than on the
    detailed one, and the `ReviewItem -> Step` port fell below its box.
    """
    bad = []
    for c in ET.parse(page).getroot().iter("mxCell"):
        if c.get("edge") == "1":
            for key, value in re.findall(r"(exit[XY]|entry[XY])=([-\d.]+)", c.get("style") or ""):
                if not 0.0 <= float(value) <= 1.0:
                    bad.append(f"{c.get('id')}: {key}={value}")
    assert not bad, f"đầu đường nằm ngoài hộp: {bad}"
