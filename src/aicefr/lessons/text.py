"""Turn a reference text and a transcript into comparable words (D025).

Both sides go through the same normalisation, so a difference in spelling
convention never counts against the learner: the recogniser writes "3" where
the text says "three", "neighborhood" where it says "neighbourhood", "I'm"
where it says "I am". The learner said the same thing in each case.

Word forms are compared through their lemma (`simplemma`, MIT), so "went"
counts for the key word "go". A short table covers the irregular forms the
lemmatiser gets wrong (it maps "gone" to "gan").
"""

from __future__ import annotations

import re
from functools import lru_cache

import simplemma

_STRIP = '.,?!;:"()[]{}…“”‘’«»*'

# Contractions expanded the way they are spoken in full. "'s" is left alone
# when it may be a possessive ("Lan's"), so only the pronoun forms are listed.
CONTRACTIONS: dict[str, tuple[str, ...]] = {
    "i'm": ("i", "am"),
    "you're": ("you", "are"),
    "we're": ("we", "are"),
    "they're": ("they", "are"),
    "he's": ("he", "is"),
    "she's": ("she", "is"),
    "it's": ("it", "is"),
    "that's": ("that", "is"),
    "there's": ("there", "is"),
    "what's": ("what", "is"),
    "who's": ("who", "is"),
    "where's": ("where", "is"),
    "let's": ("let", "us"),
    "i've": ("i", "have"),
    "you've": ("you", "have"),
    "we've": ("we", "have"),
    "they've": ("they", "have"),
    "i'll": ("i", "will"),
    "you'll": ("you", "will"),
    "we'll": ("we", "will"),
    "they'll": ("they", "will"),
    "he'll": ("he", "will"),
    "she'll": ("she", "will"),
    "it'll": ("it", "will"),
    "i'd": ("i", "would"),
    "you'd": ("you", "would"),
    "we'd": ("we", "would"),
    "they'd": ("they", "would"),
    "he'd": ("he", "would"),
    "she'd": ("she", "would"),
    "don't": ("do", "not"),
    "doesn't": ("does", "not"),
    "didn't": ("did", "not"),
    "can't": ("can", "not"),
    "cannot": ("can", "not"),
    "couldn't": ("could", "not"),
    "won't": ("will", "not"),
    "wouldn't": ("would", "not"),
    "shouldn't": ("should", "not"),
    "isn't": ("is", "not"),
    "aren't": ("are", "not"),
    "wasn't": ("was", "not"),
    "weren't": ("were", "not"),
    "haven't": ("have", "not"),
    "hasn't": ("has", "not"),
    "hadn't": ("had", "not"),
    "mustn't": ("must", "not"),
    "gonna": ("going", "to"),
    "wanna": ("want", "to"),
}

# British spelling -> the American spelling the recogniser usually writes.
BRITISH = {
    "colour": "color",
    "colours": "colors",
    "colourful": "colorful",
    "favourite": "favorite",
    "favourites": "favorites",
    "neighbour": "neighbor",
    "neighbours": "neighbors",
    "neighbourhood": "neighborhood",
    "neighbourhoods": "neighborhoods",
    "centre": "center",
    "centres": "centers",
    "theatre": "theater",
    "metre": "meter",
    "metres": "meters",
    "litre": "liter",
    "travelling": "traveling",
    "travelled": "traveled",
    "traveller": "traveler",
    "cancelled": "canceled",
    "organise": "organize",
    "organised": "organized",
    "organising": "organizing",
    "realise": "realize",
    "realised": "realized",
    "recognise": "recognize",
    "apologise": "apologize",
    "analyse": "analyze",
    "programme": "program",
    "programmes": "programs",
    "behaviour": "behavior",
    "honour": "honor",
    "labour": "labor",
    "humour": "humor",
    "flavour": "flavor",
    "practise": "practice",
    "practised": "practiced",
    "licence": "license",
    "defence": "defense",
    "grey": "gray",
    "mum": "mom",
    "jewellery": "jewelry",
    "tyre": "tire",
    "aeroplane": "airplane",
    "learnt": "learned",
    "spelt": "spelled",
    "dreamt": "dreamed",
    "burnt": "burned",
    "enrol": "enroll",
    "fulfil": "fulfill",
    "towards": "toward",
}
AMERICAN = {v: k for k, v in BRITISH.items()}

# Irregular forms the lemmatiser misses or gets wrong, mapped to their base.
IRREGULAR = {
    "gone": "go",
    "went": "go",
    "been": "be",
    "was": "be",
    "were": "be",
    "done": "do",
    "did": "do",
    "seen": "see",
    "saw": "see",
    "taken": "take",
    "took": "take",
    "written": "write",
    "wrote": "write",
    "eaten": "eat",
    "ate": "eat",
    "given": "give",
    "gave": "give",
    "known": "know",
    "knew": "know",
    "spoken": "speak",
    "spoke": "speak",
    "driven": "drive",
    "drove": "drive",
    "chosen": "choose",
    "chose": "choose",
    "forgotten": "forget",
    "forgot": "forget",
    "gotten": "get",
    "got": "get",
    "became": "become",
    "began": "begin",
    "begun": "begin",
    "bought": "buy",
    "brought": "bring",
    "thought": "think",
    "taught": "teach",
    "caught": "catch",
    "felt": "feel",
    "left": "leave",
    "met": "meet",
    "ran": "run",
    "sat": "sit",
    "slept": "sleep",
    "spent": "spend",
    "told": "tell",
    "said": "say",
    "made": "make",
    "had": "have",
    "has": "have",
    "lost": "lose",
    "found": "find",
    "heard": "hear",
    "kept": "keep",
    "came": "come",
    "children": "child",
    "people": "person",
    "better": "good",
    "best": "good",
}

ONES = (
    "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen "
    "fifteen sixteen seventeen eighteen nineteen"
).split()
TENS = "_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()

# Function words: not counted as content when a step checks meaning-bearing
# words (read-and-look-up), and shown as information when they differ.
FUNCTION_WORDS = frozenset(
    """a an the to of in on at for with by from as about into over under after before and or
    but so if because than then i you he she it we they me him her us them my your his its our
    their this that these those is am are was were be been being do does did have has had will
    would can could shall should may might must not no very too also just there here what which
    who whom whose when where why how""".split()
)

FILLERS = frozenset({"um", "uh", "erm", "er", "ah", "hmm", "mm", "uhm", "eh"})


def number_to_words(n: int) -> list[str]:
    """0..999,999 as spoken words, the way a reference text would spell them."""
    if n < 20:
        return [ONES[n]]
    if n < 100:
        tens, ones = divmod(n, 10)
        return [TENS[tens]] + ([ONES[ones]] if ones else [])
    if n < 1000:
        hundreds, rest = divmod(n, 100)
        return [ONES[hundreds], "hundred"] + (number_to_words(rest) if rest else [])
    thousands, rest = divmod(n, 1000)
    return number_to_words(thousands) + ["thousand"] + (number_to_words(rest) if rest else [])


# A number as a recogniser may write it: "7", "2026", "1,000", "250,000".
_NUMBER = re.compile(r"^(?:\d{1,6}|\d{1,3},\d{3})$")
_ORDINAL = re.compile(r"^(\d{1,6})(st|nd|rd|th)$")
_ORDINAL_OF = {
    "one": "first",
    "two": "second",
    "three": "third",
    "five": "fifth",
    "eight": "eighth",
    "nine": "ninth",
    "twelve": "twelfth",
}


def _ordinal(word: str) -> str:
    """The ordinal of the last word of a spelled-out number: twenty -> twentieth."""
    if word in _ORDINAL_OF:
        return _ORDINAL_OF[word]
    if word.endswith("y"):
        return word[:-1] + "ieth"
    return word + "th"


def normalize_word(raw: str) -> list[str]:
    """One written word -> the spoken words it stands for, lower-case, unified spelling."""
    tok = raw.replace("’", "'").replace("‘", "'").lower().strip(_STRIP).strip("'")
    if not tok:
        return []
    if tok in CONTRACTIONS:
        return list(CONTRACTIONS[tok])
    if _NUMBER.match(tok):
        return number_to_words(int(tok.replace(",", "")))
    m = _ORDINAL.match(tok)
    if m:
        words = number_to_words(int(m.group(1)))
        return [*words[:-1], _ordinal(words[-1])]
    tok = BRITISH.get(tok, tok)
    return [tok]


def split_words(text: str) -> list[str]:
    """The written words of a text, keeping punctuation attached, hyphens split."""
    out: list[str] = []
    for raw in text.split():
        parts = [p for p in raw.split("-") if p.strip(_STRIP)]
        out += parts if len(parts) > 1 else [raw]
    return out


def tokens(text: str) -> list[str]:
    """A text as normalised spoken words."""
    out: list[str] = []
    for raw in split_words(text):
        out += normalize_word(raw)
    return out


@lru_cache(maxsize=4096)
def lemma(word: str) -> str:
    w = word.lower()
    if w in IRREGULAR:
        return IRREGULAR[w]
    try:
        return simplemma.lemmatize(w, lang="en").lower()
    except Exception:  # noqa: BLE001 - a lemmatiser failure must not fail a step
        return w


def same_word(a: str, b: str) -> bool:
    """The same word, possibly in another form ("went" and "go", "walks" and "walk")."""
    if a == b:
        return True
    a2, b2 = AMERICAN.get(a, a), AMERICAN.get(b, b)
    if a2 == b2:
        return True
    return lemma(a) == lemma(b)


def is_content(word: str) -> bool:
    return word not in FUNCTION_WORDS


def phrase_tokens(phrase: str) -> list[str]:
    return tokens(phrase)


def find_phrase(said: list[str], phrase: list[str], start: int = 0) -> int | None:
    """Index in `said` where `phrase` occurs (any word form), or None."""
    n = len(phrase)
    if not n:
        return None
    for i in range(start, len(said) - n + 1):
        if all(same_word(said[i + k], phrase[k]) for k in range(n)):
            return i
    return None
