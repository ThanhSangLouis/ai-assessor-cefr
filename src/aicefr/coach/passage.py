"""A short passage to read aloud, written around the words a learner still says unclearly (D090).

After D089 a learner says each unclear word again inside its own phrase. The
next step, as Microsoft Reading Coach does with a reader's hardest words, is a
fresh passage that uses those words in new sentences: the learner reads it
aloud, it is measured as a read-aloud step, and each word heard clearly counts
towards that word's two clear takes in a row.

What leaves the system is the band and the words themselves -- no recording,
no transcript, nothing about the learner. One request writes one passage for
up to five words; the passage is kept and read again for free, so a learner
pays once per set of words (`AICEFR_PRICE_PASSAGE_RUNS`).

When the model cannot be asked (switched off, today's cap reached), the
learner's own phrases from their recordings make a passage instead
(`from_phrases`): less natural, free, and nothing leaves the system.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from aicefr.coach.upgrade import UpgradeError
from aicefr.lessons.text import normalize_word, split_words

PROMPT_VERSION = "passage-v1"
# Words per passage: fewer than three is better said in the phrases of D089,
# more than five makes a passage that is about the words, not a text.
MIN_WORDS, MAX_WORDS = 3, 5
# The passage's length for each band: short at A1, never long.
LENGTH = {"A1": (40, 60), "A2": (50, 70), "B1": (60, 90), "B2": (70, 100),
          "C1": (80, 110), "C2": (80, 110)}  # fmt: skip
DEFAULT_BAND = "B1"
# What the model may write: the passage and its JSON, and room for a little
# deliberation. A ceiling against a runaway answer, not a target.
MAX_OUTPUT_TOKENS = 1200
MAX_CHARS = 1500

SYSTEM = """You write short reading passages for Vietnamese learners of English
who practise saying a few words clearly. Given a CEFR band and a list of
English words, write ONE passage to be read aloud:

- natural, everyday English AT the given band (vocabulary and grammar of that
  band, not above), in the length of words asked for;
- every listed word appears at least once, spelled EXACTLY as given (same
  ending, same form), used in a sentence where it makes sense;
- plain sentences that are easy to read aloud: no lists, no headings, no
  quotation marks, no names that are hard to say; write numbers as words;
- nothing unsafe, sad or about real people.

Answer with JSON only: {"text": "<the passage>"}."""

SCHEMA = {
    "type": "object",
    "properties": {"text": {"type": "string"}},
    "required": ["text"],
    "additionalProperties": False,
}


@dataclass(frozen=True)
class Passage:
    text: str
    words: list[str]


def band_of(band: str | None) -> str:
    return band if band in LENGTH else DEFAULT_BAND


def user_message(band: str, words: list[str]) -> str:
    lo, hi = LENGTH[band_of(band)]
    return json.dumps({"band": band_of(band), "words": words, "length_words": f"{lo}-{hi}"})


def places(text: str, words: list[str]) -> dict[str, list[int]]:
    """Where each word stands among the passage's written words (`split_words`)."""
    found: dict[str, list[int]] = {w: [] for w in words}
    for i, written in enumerate(split_words(text)):
        tokens = normalize_word(written)
        if len(tokens) == 1 and tokens[0] in found:
            found[tokens[0]].append(i)
    return found


def check(text: str, words: list[str], band: str | None) -> Passage:
    """The passage if it can be read for these words, or UpgradeError worded for the learner."""
    text = " ".join(str(text or "").split())[:MAX_CHARS]
    if not text:
        raise UpgradeError("mô hình chưa viết được đoạn đọc")
    missing = [w for w, at in places(text, words).items() if not at]
    if missing:
        raise UpgradeError("đoạn mô hình viết thiếu từ " + ", ".join(missing))
    _, hi = LENGTH[band_of(band)]
    if len(split_words(text)) > 2 * hi:
        raise UpgradeError("đoạn mô hình viết quá dài")
    return Passage(text=text, words=list(words))


def parse(raw: str, words: list[str], band: str | None) -> Passage:
    """The passage from the model's answer, checked against the words asked for."""
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError) as e:
        raise UpgradeError("câu trả lời của mô hình không đọc được") from e
    if not isinstance(data, dict):
        raise UpgradeError("câu trả lời của mô hình không đọc được")
    return check(data.get("text"), words, band)


def from_phrases(phrases: list[str], words: list[str]) -> Passage:
    """A passage made of the learner's own phrases, one sentence each: no model asked.

    Each phrase already holds its word (D089 cut it around the word), so the
    passage holds every word.
    """
    sentences = []
    for phrase in phrases:
        p = " ".join(phrase.split()).rstrip(" .,;!?")
        if p:
            sentences.append(p[0].upper() + p[1:] + ".")
    return check(" ".join(sentences), words, None)
