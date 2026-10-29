"""Five patterns of Vietnamese speakers of English, read off lesson word marks (D039).

Vietnamese syllables end in a vowel, a nasal or an unreleased stop, and allow no
consonant clusters; English asks for released final consonants, -ed and -s
endings, clusters and the dental /θ/, /ð/. Where those differences cost
intelligibility the machine can see them: in a read-aloud step the learner says
a known text, and when the recogniser writes "work" for "worked" or "tree" for
"three", the gap between the two spellings names the pattern.

What this is, and is not:
- a reading of spellings, not of sounds. The recogniser's language model tends
  to write the intended word anyway, so the patterns are under-counted, never
  invented; a word it did not hear at all ("missed", nothing written) names no
  pattern;
- about intelligibility only (AGENTS.md): an accent is not an error, and word
  stress and intonation, which spellings cannot show, are left out;
- a count against opportunities. "Three -ed endings dropped" means little
  without "out of how many", so every pattern carries both, and none is
  reported before MIN_OPPORTUNITIES words gave it a chance.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from enum import Enum

PRONUNCIATION_VERSION = "vi-pron-v1"
MIN_OPPORTUNITIES = 8
MAX_EXAMPLES = 5

VOWELS = frozenset("aeiou")
CONSONANTS = frozenset("bcdfghjklmnpqrstvwxz")
# Two- and three-letter onsets Vietnamese has no counterpart for.
CLUSTERS = (
    "scr", "spl", "spr", "str", "squ",
    "bl", "br", "cl", "cr", "dr", "fl", "fr", "gl", "gr", "pl", "pr", "sc", "sk", "sl", "sm",
    "sn", "sp", "st", "sw", "tr", "tw",
)  # fmt: skip
TH_REPLACEMENTS = ("t", "d", "s", "z", "f")


class Pattern(str, Enum):
    ED_ENDING = "ed_ending"
    S_ENDING = "s_ending"
    FINAL_CONSONANT = "final_consonant"
    TH_SOUND = "th_sound"
    CLUSTER = "cluster"


PATTERN_NAMES = {
    Pattern.ED_ENDING: "Đuôi -ed",
    Pattern.S_ENDING: "Đuôi -s, -es",
    Pattern.FINAL_CONSONANT: "Âm cuối",
    Pattern.TH_SOUND: "Âm th (/θ/, /ð/)",
    Pattern.CLUSTER: "Cụm phụ âm đầu",
}
PATTERN_TIPS = {
    Pattern.ED_ENDING: (
        "Đọc rõ đuôi quá khứ: /t/ sau âm vô thanh (worked), /d/ sau âm hữu thanh (played), "
        "/ɪd/ sau t, d (wanted). Thử nói chậm từ đó rồi nối sang từ sau."
    ),
    Pattern.S_ENDING: (
        "Giữ âm /s/ hoặc /z/ ở cuối danh từ số nhiều và động từ ngôi thứ ba (cats, plays, "
        'watches). Nếu từ sau bắt đầu bằng nguyên âm, nối âm cuối sang: "likes it".'
    ),
    Pattern.FINAL_CONSONANT: (
        "Bật nhẹ phụ âm cuối thay vì nuốt mất (night, bike, help). Tiếng Việt kết thúc âm "
        "tiết bằng âm không bật hơi; tiếng Anh cần nghe thấy âm cuối để phân biệt từ."
    ),
    Pattern.TH_SOUND: (
        "Đặt đầu lưỡi giữa hai hàm răng rồi thổi hơi: /θ/ (think, three) không rung, /ð/ "
        "(this, they) có rung. Đừng thay bằng t, d, s hay z."
    ),
    Pattern.CLUSTER: (
        "Nói đủ cả hai phụ âm đầu, không chèn nguyên âm và không bỏ âm nào (street, play, "
        "school). Tập chậm từng cụm: s-t, p-l, t-r, rồi tăng tốc."
    ),
}


def _plain(word: str) -> str:
    return "".join(ch for ch in word.lower() if ch.isalpha())


def _without_silent_e(word: str) -> str:
    """'make' -> 'mak': the written e is not a final sound to drop."""
    if len(word) > 3 and word.endswith("e") and word[-2] in CONSONANTS:
        return word[:-1]
    return word


# Words spelt with a final "ed" that is not the -ed ending: "need", "speed",
# "hundred". A word in "-eed" counts only when it is a verb in "-ee" plus "d".
ED_EE_VERBS = frozenset({"agreed", "disagreed", "freed", "decreed", "guaranteed", "refereed"})
NOT_ED = frozenset(
    {"hundred", "shed", "fled", "sled", "naked", "sacred", "wicked", "kindred", "beloved",
     "ragged", "rugged", "crooked", "wretched", "embed", "biped"}
)  # fmt: skip
# Words spelt with a final "s" that is not the -s ending (plural, third person).
NOT_S = frozenset(
    {"was", "has", "his", "hers", "ours", "yours", "theirs", "this", "thus", "yes", "always",
     "perhaps", "news", "series", "species", "lens", "physics", "mathematics", "economics"}
)  # fmt: skip


def _has_ed_ending(w: str) -> bool:
    if len(w) <= 3 or not w.endswith("ed") or w in NOT_ED:
        return False
    return not w.endswith("eed") or w in ED_EE_VERBS


def _has_s_ending(w: str) -> bool:
    return len(w) > 2 and w.endswith("s") and not w.endswith(("ss", "us", "is")) and w not in NOT_S


def _ends_in_consonant_sound(base: str) -> bool:
    """Whether the spelling ends in a consonant that is said, as far as letters can tell.

    Not w ("how", "new"), r ("for", "here": silent in many accents, and the
    recogniser writes the word anyway), "gh" ("high") or an h after a vowel
    ("oh"). Ch, sh, th and ph are sounds, and count.
    """
    last = base[-1]
    if last not in CONSONANTS or last in "wr":
        return False
    if last == "h":
        return len(base) > 1 and base[-2] in "cstp"
    return True


def opportunities(word: str) -> set[Pattern]:
    """Which patterns a word gives the speaker a chance to show."""
    w = _plain(word)
    out: set[Pattern] = set()
    if len(w) < 2:
        return out
    if _has_ed_ending(w):
        out.add(Pattern.ED_ENDING)
    elif _has_s_ending(w):
        out.add(Pattern.S_ENDING)
    if _ends_in_consonant_sound(_without_silent_e(w)):
        out.add(Pattern.FINAL_CONSONANT)
    if "th" in w:
        out.add(Pattern.TH_SOUND)
    if w.startswith(CLUSTERS):
        out.add(Pattern.CLUSTER)
    return out


def classify(expected: str, said: str | None) -> Pattern | None:
    """The pattern that turns the written word into what the recogniser wrote, if one does.

    Tried in this order: -ed, -s, th, onset cluster, final consonant. The two
    specific patterns of a word's end come first, and the general "final
    consonant dropped" last, so "with" heard as "wit" is a th, not a dropped
    final sound.
    """
    e, s = _plain(expected), _plain(said or "")
    if not e or not s or e == s:
        return None
    chances = opportunities(e)
    if Pattern.ED_ENDING in chances and s in (e[:-2], e[:-1]):
        return Pattern.ED_ENDING
    if Pattern.S_ENDING in chances and s in (e[:-1], e[:-2] if e.endswith("es") else None):
        return Pattern.S_ENDING
    if Pattern.TH_SOUND in chances:
        if s in {e.replace("th", r, 1) for r in TH_REPLACEMENTS}:
            return Pattern.TH_SOUND
    if Pattern.CLUSTER in chances:
        onset = next(c for c in CLUSTERS if e.startswith(c))
        dropped = {e[:i] + e[i + 1 :] for i in range(len(onset))}
        if s in dropped:
            return Pattern.CLUSTER
    if Pattern.FINAL_CONSONANT in chances:
        base = _without_silent_e(e)
        cut = len(base) - len(s)
        if 1 <= cut <= 2 and base.startswith(s) and set(base[len(s) :]) <= CONSONANTS:
            return Pattern.FINAL_CONSONANT
    return None


@dataclass(frozen=True)
class Example:
    word: str
    said: str
    start_s: float | None
    lesson_id: str | None
    step_id: str | None
    attempt_id: str | None
    created_at: str | None


@dataclass
class Finding:
    pattern: Pattern
    opportunities: int = 0
    errors: int = 0
    examples: list[Example] = field(default_factory=list)

    @property
    def enough(self) -> bool:
        return self.opportunities >= MIN_OPPORTUNITIES

    @property
    def rate(self) -> float | None:
        return self.errors / self.opportunities if self.enough else None

    def as_dict(self) -> dict:
        return {
            "pattern": self.pattern.value,
            "name": PATTERN_NAMES[self.pattern],
            "tip": PATTERN_TIPS[self.pattern],
            "opportunities": self.opportunities,
            "errors": self.errors,
            "enough": self.enough,
            "rate": None if self.rate is None else round(self.rate, 4),
            "examples": [e.__dict__ for e in self.examples],
        }


def profile(attempts: Iterable[Mapping]) -> dict:
    """Every pattern's errors against its opportunities, over a set of lesson attempts.

    An attempt is a row of `LessonRepository.attempts`: `result` (a StepResult,
    already with any teacher correction applied), `lesson_id`, `attempt_id`,
    `created_at`. Only measured steps count, and a word a teacher marked as heard
    counts as heard.
    """
    findings = {p: Finding(p) for p in Pattern}
    steps = words = 0
    for row in attempts:
        result = row["result"]
        if not getattr(result, "measured", False) or not result.words:
            continue
        steps += 1
        for mark in result.words:
            words += 1
            for pattern in opportunities(mark.text):
                findings[pattern].opportunities += 1
            final = mark.teacher or mark.status
            if final.value == "heard" or not mark.said:
                continue
            pattern = classify(mark.text, mark.said)
            if pattern is None or pattern not in opportunities(mark.text):
                continue
            f = findings[pattern]
            f.errors += 1
            if len(f.examples) < MAX_EXAMPLES:
                f.examples.append(
                    Example(
                        word=mark.text,
                        said=mark.said,
                        start_s=mark.start_s,
                        lesson_id=row.get("lesson_id"),
                        step_id=getattr(result, "step_id", None),
                        attempt_id=row.get("attempt_id"),
                        created_at=row.get("created_at"),
                    )
                )
    ordered = sorted(
        findings.values(),
        key=lambda f: (not f.enough, -(f.rate or 0.0), -f.errors, f.pattern.value),
    )
    return {
        "version": PRONUNCIATION_VERSION,
        "min_opportunities": MIN_OPPORTUNITIES,
        "steps": steps,
        "words": words,
        "patterns": [f.as_dict() for f in ordered],
    }
