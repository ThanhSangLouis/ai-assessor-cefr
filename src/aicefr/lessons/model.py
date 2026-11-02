"""Data model of a lesson path and of one measured step attempt (D025).

The step configuration is ONE model with optional fields rather than a union of
nine classes. A teacher edits it in a form and it is stored as JSON; one shape
keeps the editor, the storage and the export format simple, and the validators
below check that each kind has the fields it needs.
"""

from __future__ import annotations

import re
import uuid
from enum import Enum

from pydantic import AliasChoices, BaseModel, Field, field_validator, model_validator

from aicefr.contracts import Band, Criterion, Mission, MissionHit, ReasonCode

# Bump when a rule in checks.py changes what it measures, so an old result can
# be told apart from a new one measured differently.
STEP_RULES_VERSION = "step-v1"

# A blank in a gap text: three or more underscores.
GAP_PATTERN = re.compile(r"_{3,}")


class PathStatus(str, Enum):
    """A path is drafted, then published to learners, and archived when retired."""

    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class StepKind(str, Enum):
    READ_ALOUD = "read_aloud"  # read a given text aloud, hint words highlighted
    REPEAT = "repeat"  # listen to a model sentence, then repeat it
    LOOK_UP = "look_up"  # read a sentence, it disappears, say it
    GAP = "gap"  # read a text with blanks, filling them from a word bank
    KEYWORDS = "keywords"  # make your own sentence with given words
    STARTER = "starter"  # answer a question starting with a sentence frame
    PICTURE = "picture"  # describe a picture or situation using a word bank
    OUTLINE = "outline"  # a short talk following an outline, with planning time
    FREE = "free"  # free speech on a parallel topic, possibly in shrinking rounds


class Stage(str, Enum):
    """The four rungs of the ladder every lesson climbs."""

    MODEL = "model"
    CONTROLLED = "controlled"
    GUIDED = "guided"
    FREE = "free"


STAGE_OF: dict[StepKind, Stage] = {
    StepKind.READ_ALOUD: Stage.MODEL,
    StepKind.REPEAT: Stage.MODEL,
    StepKind.LOOK_UP: Stage.CONTROLLED,
    StepKind.GAP: Stage.CONTROLLED,
    StepKind.KEYWORDS: Stage.GUIDED,
    StepKind.STARTER: Stage.GUIDED,
    StepKind.PICTURE: Stage.GUIDED,
    StepKind.OUTLINE: Stage.GUIDED,
    StepKind.FREE: Stage.FREE,
}
STAGE_ORDER = (Stage.MODEL, Stage.CONTROLLED, Stage.GUIDED, Stage.FREE)

STAGE_NAMES = {
    Stage.MODEL: "Mẫu",
    Stage.CONTROLLED: "Có kiểm soát",
    Stage.GUIDED: "Có hướng dẫn",
    Stage.FREE: "Tự do",
}
KIND_NAMES = {
    StepKind.READ_ALOUD: "Đọc to có từ gợi ý",
    StepKind.REPEAT: "Nghe và nhắc lại",
    StepKind.LOOK_UP: "Đọc rồi nói lại",
    StepKind.GAP: "Đọc đoạn có chỗ trống",
    StepKind.KEYWORDS: "Ghép câu từ từ khóa",
    StepKind.STARTER: "Trả lời có khung câu",
    StepKind.PICTURE: "Mô tả tranh",
    StepKind.OUTLINE: "Nói theo dàn ý",
    StepKind.FREE: "Nói tự do",
}

# Kinds whose result marks each word of a reference text.
TEXT_KINDS = frozenset({StepKind.READ_ALOUD, StepKind.REPEAT, StepKind.LOOK_UP, StepKind.GAP})


class Topic(str, Enum):
    """What a unit talks about (D027). The path runs A1 → C2 (D059), and within each
    level the units change topic, so practice stays varied as the level rises."""

    DAILY_LIFE = "daily_life"
    EDUCATION = "education"
    TRAVEL = "travel"
    CAREER = "career"
    FOOD = "food"
    HEALTH = "health"
    TECHNOLOGY = "technology"
    ENVIRONMENT = "environment"
    PEOPLE = "people"
    SOCIETY = "society"


TOPIC_NAMES = {
    Topic.DAILY_LIFE: "Đời sống hằng ngày",
    Topic.EDUCATION: "Giáo dục",
    Topic.TRAVEL: "Du lịch",
    Topic.CAREER: "Nghề nghiệp",
    Topic.FOOD: "Ẩm thực",
    Topic.HEALTH: "Sức khoẻ",
    Topic.TECHNOLOGY: "Công nghệ",
    Topic.ENVIRONMENT: "Môi trường",
    Topic.PEOPLE: "Con người",
    Topic.SOCIETY: "Xã hội",
}


class Strictness(str, Enum):
    EASY = "easy"
    NORMAL = "normal"
    STRICT = "strict"


def new_id(prefix: str) -> str:
    return f"{prefix}{uuid.uuid4().hex[:10]}"


def _words(items: list[str]) -> list[str]:
    """Trim, drop empties and duplicates, keep the teacher's order."""
    out: list[str] = []
    for item in items:
        text = " ".join(str(item).split())
        if text and text.lower() not in {x.lower() for x in out}:
            out.append(text)
    return out


class Step(BaseModel):
    """One exercise of a lesson, as the teacher configured it."""

    step_id: str = Field(default_factory=lambda: new_id("s"))
    kind: StepKind
    title: str = Field(default="", max_length=120)
    instruction: str = Field(default="", max_length=600)
    # The English text of the step: the passage to read (READ_ALOUD), the
    # sentence to repeat or recall (REPEAT, LOOK_UP), the text with blanks
    # (GAP), the question (STARTER, PICTURE, OUTLINE) or the prompt (FREE).
    text: str = Field(default="", max_length=2000)
    # Highlighted words (READ_ALOUD) or the word bank (GAP, PICTURE).
    hint_words: list[str] = Field(default_factory=list, max_length=20)
    # GAP: the expected word of each blank, in order. Never sent to students.
    answers: list[str] = Field(default_factory=list, max_length=10)
    keywords: list[str] = Field(default_factory=list, max_length=12)
    starter: str = Field(default="", max_length=120)
    outline: list[str] = Field(default_factory=list, max_length=8)
    # OUTLINE: ordered groups of linking words, e.g. [["first"], ["then", "next"]].
    markers: list[list[str]] = Field(default_factory=list, max_length=6)
    use_at_least: int = Field(default=0, ge=0, le=20)
    min_words: int = Field(default=0, ge=0, le=200)
    show_seconds: int = Field(default=0, ge=0, le=60)
    prep_seconds: int = Field(default=0, ge=0, le=300)
    min_seconds: int = Field(default=0, ge=0, le=180)
    max_seconds: int = Field(default=60, ge=3, le=180)
    # FREE: the time limit of each round, e.g. [45, 35, 25] for 4/3/2.
    rounds: list[int] = Field(default_factory=list, max_length=4)
    strictness: Strictness = Strictness.NORMAL
    model_audio: str | None = None
    image: str | None = None
    image_alt: str = Field(default="", max_length=300)
    # FREE: optional D023 missions measured on top of time and pauses.
    missions: list[Mission] = Field(default_factory=list, max_length=4)
    tip: str = Field(default="", max_length=400)

    @field_validator("hint_words", "answers", "keywords", "outline")
    @classmethod
    def _clean_list(cls, v: list[str]) -> list[str]:
        return _words(v) if v else []

    @field_validator("markers")
    @classmethod
    def _clean_markers(cls, v: list[list[str]]) -> list[list[str]]:
        return [g for g in (_words(group) for group in v) if g]

    @field_validator("rounds")
    @classmethod
    def _rounds_in_range(cls, v: list[int]) -> list[int]:
        for seconds in v:
            if not 10 <= seconds <= 180:
                raise ValueError("mỗi lượt nói dài từ 10 đến 180 giây")
        return v

    @model_validator(mode="after")
    def _window(self) -> Step:
        if self.min_seconds > self.max_seconds:
            raise ValueError("thời gian tối thiểu lớn hơn thời gian tối đa")
        return self

    @property
    def stage(self) -> Stage:
        return STAGE_OF[self.kind]

    @property
    def blank_count(self) -> int:
        return len(GAP_PATTERN.findall(self.text)) if self.kind is StepKind.GAP else 0

    @property
    def display_title(self) -> str:
        return self.title or KIND_NAMES[self.kind]

    def round_limits(self) -> list[int]:
        """The time limit of every round; one round of max_seconds when none is set."""
        if self.kind is StepKind.FREE and self.rounds:
            return list(self.rounds)
        return [self.max_seconds]

    def for_student(self) -> dict:
        """What the browser of a learner receives: everything but the answers."""
        data = self.model_dump(mode="json", exclude={"answers"})
        data["stage"] = self.stage.value
        data["stage_name"] = STAGE_NAMES[self.stage]
        data["kind_name"] = KIND_NAMES[self.kind]
        data["display_title"] = self.display_title
        data["blank_count"] = self.blank_count
        data["round_limits"] = self.round_limits()
        return data


class Lesson(BaseModel):
    """One lesson: a model text, its key words and a ladder of steps."""

    lesson_id: str = Field(default_factory=lambda: new_id("l"))
    title: str = Field(min_length=1, max_length=160)
    summary: str = Field(default="", max_length=600)
    band: Band
    criterion: Criterion | None = None
    model_text: str = Field(default="", max_length=3000)
    keywords: list[str] = Field(default_factory=list, max_length=12)
    steps: list[Step] = Field(default_factory=list, max_length=12)
    # Share of steps that must pass, besides the free step being done.
    pass_ratio: float = Field(default=0.8, ge=0.3, le=1.0)
    # Shipped with the system (D085). Versions saved before call it `sample`.
    built_in: bool = Field(default=False, validation_alias=AliasChoices("built_in", "sample"))

    @field_validator("keywords")
    @classmethod
    def _clean_keywords(cls, v: list[str]) -> list[str]:
        return _words(v) if v else []

    @model_validator(mode="after")
    def _unique_step_ids(self) -> Lesson:
        ids = [s.step_id for s in self.steps]
        if len(ids) != len(set(ids)):
            raise ValueError("hai bước trùng mã")
        return self

    def step(self, step_id: str) -> Step | None:
        return next((s for s in self.steps if s.step_id == step_id), None)

    @property
    def free_step_ids(self) -> list[str]:
        return [s.step_id for s in self.steps if s.kind is StepKind.FREE]

    def for_student(self) -> dict:
        data = self.model_dump(mode="json", exclude={"steps"})
        data["steps"] = [s.for_student() for s in self.steps]
        return data


# ---------------------------------------------------------------- results


class WordStatus(str, Enum):
    HEARD = "heard"
    MISSED = "missed"  # the machine did not hear it -- never "wrong"
    UNSURE = "unsure"  # heard with low confidence, or a different form of it


class WordMark(BaseModel):
    """One word of the reference text, as the learner sees it marked."""

    index: int
    text: str
    status: WordStatus
    start_s: float | None = None
    said: str | None = None  # what the machine heard instead, when it differs
    content: bool = True  # a content word, as opposed to a, the, of...
    teacher: WordStatus | None = None  # a teacher's correction, when there is one
    # D039: the Vietnamese-learner pattern the gap between `text` and `said`
    # names ("ed_ending", "th_sound"...), when one does.
    pattern: str | None = None

    @property
    def final(self) -> WordStatus:
        return self.teacher or self.status


class GapStatus(str, Enum):
    CORRECT = "correct"
    DISTRACTOR = "distractor"
    OTHER = "other"
    MISSING = "missing"


class GapMark(BaseModel):
    index: int
    expected: str
    said: str | None = None
    status: GapStatus
    start_s: float | None = None


class Signal(BaseModel):
    """One measured quantity, with its Vietnamese label and whether it met its target."""

    key: str
    label: str
    value: float | None = None
    unit: str = ""
    target: float | None = None
    met: bool | None = None
    text: str = ""  # the sentence shown to the learner


class StepResult(BaseModel):
    step_id: str
    kind: StepKind
    passed: bool
    # False when nothing could be measured (no speech, wrong language...).
    measured: bool = True
    words: list[WordMark] = Field(default_factory=list)
    gaps: list[GapMark] = Field(default_factory=list)
    found: list[MissionHit] = Field(default_factory=list)
    missing: list[str] = Field(default_factory=list)
    signals: list[Signal] = Field(default_factory=list)
    changes: list[str] = Field(default_factory=list)  # FREE: compared with round 1
    tip: str = ""
    transcript: str = ""
    round: int | None = None
    speaking_s: float = 0.0
    reasons: list[ReasonCode] = Field(default_factory=list)
    teacher_reviewed: bool = False
    teacher_note: str = ""
    rules_version: str = STEP_RULES_VERSION

    def missed_words(self) -> list[str]:
        """Words worth reviewing later: hint, key or gap words the machine did not hear."""
        out = list(self.missing)
        out += [g.expected for g in self.gaps if g.status is not GapStatus.CORRECT]
        return _words(out)
