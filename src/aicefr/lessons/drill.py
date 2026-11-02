"""Say again the words the machine did not hear clearly (D089).

The report marks in orange the words the recogniser was unsure of
(`Word.is_uncertain`). This turns them into practice, four steps per word:

1. listen to yourself: the word as recorded, with a little room on each side;
2. listen to a model: the word, then the few words around it, read slowly by
   the browser's own voice;
3. a tip, when the spelling gives one of the five Vietnamese-learner patterns
   a chance to show (`pronunciation.vietnamese`);
4. say the phrase again: it is measured as a read-aloud step, and the word
   passes when the machine hears it clearly (`WordStatus.HEARD`) twice in a
   row. A take where it did not goes to spaced review (`ReviewItem`).

What this is, and is not: an orange word is one the machine heard poorly, not
one the learner said wrong. Noise, speed and rare words lower the probability
too, and an accent is not an error (AGENTS.md). So the screen says "máy nghe
chưa rõ", and what is reported is the share of such words falling over time --
never a promise about the band.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from aicefr.contracts import Word
from aicefr.lessons.model import Step, StepKind, StepResult, Strictness, WordStatus
from aicefr.lessons.text import _STRIP, FILLERS, normalize_word, split_words
from aicefr.pronunciation.vietnamese import PATTERN_NAMES, PATTERN_TIPS, Pattern, opportunities

DRILL_VERSION = "drill-v1"
# Words offered from one recording; the least clear first.
MAX_WORDS = 8
# Room around the word when it is played back, so it does not start clipped.
PAD_S = 0.2
# The phrase: one word before the target, two after, never across a pause
# longer than this (that would join two thoughts into one "phrase").
BEFORE, AFTER = 1, 2
MAX_GAP_S = 1.0
# Clear takes in a row that close a word.
PASS_STREAK = 2
# Takes kept per word: enough to show the way there, bounded.
MAX_TAKES = 20
# The specific patterns of a word first, the general "final consonant" last,
# as `pronunciation.vietnamese.classify` tries them.
PATTERN_ORDER = (
    Pattern.ED_ENDING,
    Pattern.S_ENDING,
    Pattern.TH_SOUND,
    Pattern.CLUSTER,
    Pattern.FINAL_CONSONANT,
)

_PLAIN = re.compile(r"[a-z]+(?:'[a-z]+)?")


@dataclass(frozen=True)
class DrillWord:
    """One word to say again, where it is in the recording and the phrase around it."""

    word: str  # lower-case, as it is matched
    index: int  # position in the transcript's words
    prob: float
    start_s: float
    end_s: float
    phrase: str
    phrase_start_s: float
    phrase_end_s: float
    target: int  # position of the word among the phrase's written words

    def view(self) -> dict:
        pattern = pattern_of(self.word)
        return {
            "word": self.word,
            "index": self.index,
            "prob": self.prob,
            "start_s": round(max(0.0, self.start_s - PAD_S), 2),
            "end_s": round(self.end_s + PAD_S, 2),
            "phrase": self.phrase,
            "phrase_start_s": round(max(0.0, self.phrase_start_s - PAD_S), 2),
            "phrase_end_s": round(self.phrase_end_s + PAD_S, 2),
            "pattern": pattern.value if pattern else None,
            "pattern_name": PATTERN_NAMES[pattern] if pattern else None,
            "tip": PATTERN_TIPS[pattern] if pattern else None,
        }


def _clean(text: str) -> str:
    return text.strip().strip(_STRIP).replace("’", "'")


def _plain(text: str) -> str | None:
    """The word as one plain lower-case token, or None for numbers, fillers, contractions."""
    if not _PLAIN.fullmatch(_clean(text).lower()):
        return None  # "15", "co-op", "U.S.": not a word to say again on its own
    toks = normalize_word(text)
    if len(toks) != 1:
        return None
    tok = toks[0]
    if len(tok) < 2 or tok in FILLERS or not _PLAIN.fullmatch(tok):
        return None
    return tok


def _counts(text: str) -> bool:
    """A spoken word, short ones included ("I", "a"); not a number or a filler."""
    word = _clean(text).lower()
    return bool(_PLAIN.fullmatch(word)) and word not in FILLERS


def pick(words: list[Word]) -> list[DrillWord]:
    """The words to say again: unsure, plain, one per spelling, the least clear first."""
    seen: set[str] = set()
    found: list[DrillWord] = []
    ranked = sorted(
        (i for i, w in enumerate(words) if w.is_uncertain), key=lambda i: (words[i].prob, i)
    )
    for i in ranked:
        word = _plain(words[i].text)
        if word is None or word in seen:
            continue
        seen.add(word)
        found.append(_drill_word(words, i, word))
        if len(found) >= MAX_WORDS:
            break
    return sorted(found, key=lambda d: d.index)


def _spoken(w: Word) -> str:
    """The word as written in the phrase; empty for punctuation and fillers ("um")."""
    text = _clean(w.text)
    return "" if text.lower() in FILLERS else text


def _drill_word(words: list[Word], i: int, word: str) -> DrillWord:
    # Walk out from the word, counting only words a learner would say again:
    # a filler in between is skipped, a long pause ends the phrase.
    lo, taken = i, 0
    while taken < BEFORE and lo > 0 and words[lo].start_s - words[lo - 1].end_s <= MAX_GAP_S:
        lo -= 1
        taken += bool(_spoken(words[lo]))
    hi, taken = i, 0
    while (
        taken < AFTER
        and hi + 1 < len(words)
        and words[hi + 1].start_s - words[hi].end_s <= MAX_GAP_S
    ):
        hi += 1
        taken += bool(_spoken(words[hi]))
    before = [t for t in map(_spoken, words[lo:i]) if t]
    after = [t for t in map(_spoken, words[i + 1 : hi + 1]) if t]
    target_text = _clean(words[i].text)
    return DrillWord(
        word=word,
        index=i,
        prob=round(float(words[i].prob or 0.0), 4),
        start_s=words[i].start_s,
        end_s=words[i].end_s,
        phrase=" ".join([*before, target_text, *after]),
        phrase_start_s=words[lo].start_s,
        phrase_end_s=words[hi].end_s,
        target=len(split_words(" ".join(before))),
    )


def pattern_of(word: str) -> Pattern | None:
    """The first pattern the word's spelling gives a chance to show, if any.

    A chance, not a finding: "worked" can lose its -ed, so the -ed tip is the
    useful one to read before saying it again.
    """
    chances = opportunities(word)
    return next((p for p in PATTERN_ORDER if p in chances), None)


def step_for(drill: DrillWord | dict) -> Step:
    """The phrase as a read-aloud step, the word highlighted."""
    phrase = drill.phrase if isinstance(drill, DrillWord) else drill["phrase"]
    word = drill.word if isinstance(drill, DrillWord) else drill["word"]
    return Step(
        step_id="drill",
        kind=StepKind.READ_ALOUD,
        title="Nói lại cụm từ",
        text=phrase,
        hint_words=[word],
        max_seconds=12,
        strictness=Strictness.NORMAL,
    )


@dataclass(frozen=True)
class Judgement:
    measured: bool
    passed: bool
    said: str | None  # what the machine heard instead, when it differs
    pattern: Pattern | None  # the pattern that gap names, when one does


def judge(result: StepResult, target: int) -> Judgement:
    """Whether the machine heard the target word clearly in this take."""
    if not result.measured:
        return Judgement(False, False, None, None)
    mark = next((m for m in result.words if m.index == target), None)
    if mark is None:
        return Judgement(True, False, None, None)
    pattern = Pattern(mark.pattern) if mark.pattern else None
    return Judgement(True, mark.final is WordStatus.HEARD, mark.said, pattern)


def next_streak(streak: int, passed: bool) -> int:
    """Clear takes in a row after this one: a take that is not clear starts again."""
    return streak + 1 if passed else 0


def unsure_share(words: list[Word]) -> float | None:
    """Share of the words with a probability that the machine was unsure of.

    None when no word carries one: a recogniser that reports none says nothing
    about the speaker (`Word.is_uncertain`).
    """
    scored = [w for w in words if w.prob is not None and _counts(w.text)]
    if not scored:
        return None
    return sum(1 for w in scored if w.is_uncertain) / len(scored)
