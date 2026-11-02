"""A first draft of a lesson, written by the language model for a teacher (D075).

The teacher names the band, the criterion and what the lesson is about; the
model writes what the "Bài học mới" form asks for -- a title, a one-line
summary for the learners, an English model text, its key words and the free
speaking prompt -- and the teacher reads, corrects and saves it like any
lesson they wrote themselves. Nothing is published by the model: the steps
are built from the text by the fixed rules of D025, and the teacher reviews
them before publishing.

What leaves the system is the band, the criterion and the teacher's own few
words about the topic; nothing about any learner.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from aicefr.coach.upgrade import UpgradeError

PROMPT_VERSION = "lesson-draft-v1"
MAX_KEYWORDS = 8
# Words of the model text for each band: short and plain at A1, longer above.
WORDS = {"A1": (40, 70), "A2": (60, 100), "B1": (90, 140), "B2": (120, 180),
         "C1": (150, 220), "C2": (180, 260)}  # fmt: skip

SYSTEM = """You write speaking lessons for Vietnamese learners of English.
Given a CEFR band, a speaking criterion and a topic, write ONE short lesson:

- "title": a short Vietnamese title for the lesson.
- "summary": one Vietnamese sentence telling the learner what they will practise.
- "model_text": a natural spoken English monologue AT the given band (vocabulary
  and grammar of that band, not above), first person, about the topic. Write
  numbers as words (twenty, not 20) and use American spelling.
- "keywords": 4 to 8 useful English words or short phrases that appear in
  model_text exactly as written there.
- "free_prompt": one Vietnamese question or instruction asking the learner to
  speak freely about their own experience of the topic.

Answer with JSON only, with exactly these five keys."""

SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "summary": {"type": "string"},
        "model_text": {"type": "string"},
        "keywords": {"type": "array", "items": {"type": "string"}},
        "free_prompt": {"type": "string"},
    },
    "required": ["title", "summary", "model_text", "keywords", "free_prompt"],
    "additionalProperties": False,
}


@dataclass(frozen=True)
class Draft:
    title: str
    summary: str
    model_text: str
    keywords: list[str] = field(default_factory=list)
    free_prompt: str = ""

    def as_dict(self) -> dict:
        return {
            "title": self.title,
            "summary": self.summary,
            "model_text": self.model_text,
            "keywords": list(self.keywords),
            "free_prompt": self.free_prompt,
            "prompt_version": PROMPT_VERSION,
        }


def user_message(band: str, criterion: str | None, topic: str) -> str:
    lo, hi = WORDS.get(band, (80, 140))
    return json.dumps(
        {
            "band": band,
            "criterion": criterion or "any",
            "topic": topic,
            "model_text_words": f"{lo}-{hi}",
        },
        ensure_ascii=False,
    )


def _text(value, limit: int) -> str:
    return " ".join(str(value or "").split())[:limit]


def parse(raw: str) -> Draft:
    """The draft from the model's answer, or UpgradeError worded for the teacher.

    Key words the model claims but that are not in its own text are dropped:
    a lesson step asks the learner to say them in that text.
    """
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError) as e:
        raise UpgradeError("câu trả lời của mô hình không đọc được") from e
    if not isinstance(data, dict):
        raise UpgradeError("câu trả lời của mô hình không đọc được")
    text = _text(data.get("model_text"), 3000)
    title = _text(data.get("title"), 160)
    if not text or not title:
        raise UpgradeError("câu trả lời của mô hình thiếu tên bài hoặc đoạn văn mẫu")
    lowered = text.lower()
    keywords: list[str] = []
    for k in data.get("keywords") or []:
        word = _text(k, 40).strip(" .,;")
        if word and re.search(rf"\b{re.escape(word.lower())}\b", lowered) and word not in keywords:
            keywords.append(word)
    return Draft(
        title=title,
        summary=_text(data.get("summary"), 600),
        model_text=text,
        keywords=keywords[:MAX_KEYWORDS],
        free_prompt=_text(data.get("free_prompt"), 600),
    )
