"""The learner's own answer, rewritten one band higher (D069).

The learner reads what the machine heard next to the same ideas said one band
higher, change by change, then says it again. Comparing one's own output with a
better version of it is what makes the gap noticeable; a model answer written
from scratch shows a level, not the way from here to there.

What leaves the system is the transcript and the task prompt, nothing else: no
pseudonym, no recording, no score history. The language model is a third
party (`providers.py`); a wrong rewrite is possible, so the page says it is a
suggestion, and every change the model claims must point at words the learner
actually said, or it is dropped.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

PROMPT_VERSION = "upgrade-v1"
MAX_CHANGES = 8
MAX_PHRASES = 6
MAX_INPUT_WORDS = 600

SYSTEM = """You are an English speaking coach for Vietnamese university students.
You receive a speaking task and what a student said (an automatic transcript, so
it may contain recognition errors). Rewrite the student's answer as it would be
said by a speaker one CEFR band higher than the student's current band.

Rules:
- Keep the student's ideas, examples and order. Do not add new arguments.
- It must sound spoken, not written: natural connectors, contractions allowed.
- Keep roughly the same length (between 0.8 and 1.5 times the student's words).
- Upgrade vocabulary, connectors and grammar to the target band, not beyond it.
- "changes": up to 8 of the most useful edits. "from" must be words copied
  exactly from the student's transcript; "to" is your version; "why_vi" explains
  the gain in one short Vietnamese sentence.
- "phrases": up to 6 useful words or phrases from your version, with a short
  Vietnamese meaning in "meaning_vi".
Answer with JSON only."""

# The answer's shape, for providers that enforce it (Claude's structured
# outputs) and as a description for the others.
SCHEMA = {
    "type": "object",
    "properties": {
        "upgraded": {"type": "string"},
        "changes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "from": {"type": "string"},
                    "to": {"type": "string"},
                    "why_vi": {"type": "string"},
                },
                "required": ["from", "to", "why_vi"],
                "additionalProperties": False,
            },
        },
        "phrases": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "phrase": {"type": "string"},
                    "meaning_vi": {"type": "string"},
                },
                "required": ["phrase", "meaning_vi"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["upgraded", "changes", "phrases"],
    "additionalProperties": False,
}


class UpgradeError(RuntimeError):
    """The provider failed or answered something unusable; nothing is stored."""


@dataclass
class Upgrade:
    upgraded: str
    changes: list[dict] = field(default_factory=list)
    phrases: list[dict] = field(default_factory=list)


def user_message(task_prompt: str, transcript: str, band: str, target: str) -> str:
    words = transcript.split()
    if len(words) > MAX_INPUT_WORDS:
        transcript = " ".join(words[:MAX_INPUT_WORDS])
    return json.dumps(
        {
            "task": task_prompt,
            "student_band": band,
            "target_band": target,
            "student_transcript": transcript,
            "answer_format": SCHEMA,
        },
        ensure_ascii=False,
    )


def _norm(text: str) -> str:
    return re.sub(r"[^\w']+", " ", text.lower()).strip()


def parse(raw: str, transcript: str) -> Upgrade:
    """Read the provider's JSON, keep what is grounded in the transcript, or raise."""
    text = raw.strip()
    # Some providers wrap JSON in a code fence despite being asked not to.
    fenced = re.search(r"\{.*\}", text, re.S)
    if fenced:
        text = fenced.group(0)
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise UpgradeError("câu trả lời của mô hình không phải JSON") from e
    upgraded = str(data.get("upgraded") or "").strip()
    if not upgraded:
        raise UpgradeError("mô hình không trả về bản nâng cấp")
    n_in, n_out = len(transcript.split()), len(upgraded.split())
    if n_in and not (0.4 * n_in <= n_out <= 2.5 * n_in + 20):
        raise UpgradeError("bản nâng cấp dài hoặc ngắn bất thường so với bài nói")

    said = f" {_norm(transcript)} "
    changes = []
    for c in data.get("changes") or []:
        if not isinstance(c, dict):
            continue
        before, after = str(c.get("from", "")).strip(), str(c.get("to", "")).strip()
        why = str(c.get("why_vi", "")).strip()
        # A change must point at words the learner said; anything else is the
        # model talking about a speech that did not happen.
        if before and after and _norm(before) != _norm(after) and f" {_norm(before)} " in said:
            changes.append({"from": before, "to": after, "why_vi": why[:200]})
        if len(changes) == MAX_CHANGES:
            break
    phrases = []
    for p in data.get("phrases") or []:
        if isinstance(p, dict) and str(p.get("phrase", "")).strip():
            phrases.append(
                {
                    "phrase": str(p["phrase"]).strip()[:80],
                    "meaning_vi": str(p.get("meaning_vi", "")).strip()[:120],
                }
            )
        if len(phrases) == MAX_PHRASES:
            break
    return Upgrade(upgraded=upgraded[:4000], changes=changes, phrases=phrases)
