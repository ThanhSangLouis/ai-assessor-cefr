"""The class diagram is the design the code follows, attribute by attribute.

`tests/test_diagrams.py` checks that every class drawn exists. This goes one
level down: every attribute and operation drawn on an entity of
`docs/sdd/diagrams/02_class.drawio` must be found in the code, in one of three
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
DIAGRAM = ROOT / "docs" / "sdd" / "diagrams" / "02_class.drawio"
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
def drawn() -> dict[str, list[str]]:
    """Each entity drawn and the names of its attributes and operations."""
    cells = list(ET.parse(DIAGRAM).getroot().iter("mxCell"))
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


def found(entity: str, attribute: str) -> bool:
    own = members_of(entity, ENTITY_CLASS[entity]) or set()
    if snake(attribute) in own:
        return True
    where = ELSEWHERE.get((entity, attribute))
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
