"""Versioned normalization and English lemma equivalence for lesson evidence."""

from __future__ import annotations

import re

NORMALIZATION_VERSION = "lesson-text-v1"
LEMMA_VERSION = "simplemma-en-irregular-v1"

_CONTRACTIONS = {
    "can't": "can not",
    "cannot": "can not",
    "won't": "will not",
    "shan't": "shall not",
    "don't": "do not",
    "doesn't": "does not",
    "didn't": "did not",
    "isn't": "is not",
    "aren't": "are not",
    "wasn't": "was not",
    "weren't": "were not",
    "haven't": "have not",
    "hasn't": "has not",
    "hadn't": "had not",
    "wouldn't": "would not",
    "couldn't": "could not",
    "shouldn't": "should not",
    "mustn't": "must not",
    "i'm": "i am",
    "you're": "you are",
    "we're": "we are",
    "they're": "they are",
    "it's": "it is",
    "he's": "he is",
    "she's": "she is",
    "that's": "that is",
    "there's": "there is",
    "i've": "i have",
    "you've": "you have",
    "we've": "we have",
    "they've": "they have",
    "i'll": "i will",
    "you'll": "you will",
    "we'll": "we will",
    "they'll": "they will",
    "he'll": "he will",
    "she'll": "she will",
    "i'd": "i would",
    "you'd": "you would",
    "we'd": "we would",
    "they'd": "they would",
    "let's": "let us",
}
# Canonical forms keep common British/American variants equivalent.
_SPELLING = {
    "colour": "color",
    "colours": "colors",
    "favourite": "favorite",
    "favourites": "favorites",
    "honour": "honor",
    "honours": "honors",
    "neighbour": "neighbor",
    "neighbours": "neighbors",
    "centre": "center",
    "centres": "centers",
    "theatre": "theater",
    "theatres": "theaters",
    "organise": "organize",
    "organised": "organized",
    "organising": "organizing",
    "realise": "realize",
    "realised": "realized",
    "travelling": "traveling",
    "travelled": "traveled",
    "learnt": "learned",
    "grey": "gray",
}
_IRREGULAR_LEMMAS = {
    "went": "go",
    "gone": "go",
    "was": "be",
    "were": "be",
    "been": "be",
    "did": "do",
    "done": "do",
    "had": "have",
    "has": "have",
    "hasn't": "have",
    "children": "child",
    "mice": "mouse",
    "men": "man",
    "women": "woman",
    "better": "good",
    "best": "good",
    "worse": "bad",
    "worst": "bad",
    "bought": "buy",
    "caught": "catch",
    "taught": "teach",
    "thought": "think",
    "brought": "bring",
    "sought": "seek",
    "left": "leave",
    "felt": "feel",
    "kept": "keep",
    "slept": "sleep",
    "wrote": "write",
    "written": "write",
    "ran": "run",
    "spoke": "speak",
    "spoken": "speak",
    "ate": "eat",
    "eaten": "eat",
    "saw": "see",
    "seen": "see",
    "made": "make",
    "took": "take",
    "taken": "take",
    "gave": "give",
    "given": "give",
    "found": "find",
    "knew": "know",
    "known": "know",
}
_FINAL_E_VERBS = frozenset(
    {
        "bake",
        "close",
        "dance",
        "face",
        "hope",
        "include",
        "like",
        "live",
        "love",
        "manage",
        "move",
        "place",
        "reduce",
        "save",
        "use",
    }
)
_SMALL = {
    0: "zero",
    1: "one",
    2: "two",
    3: "three",
    4: "four",
    5: "five",
    6: "six",
    7: "seven",
    8: "eight",
    9: "nine",
    10: "ten",
    11: "eleven",
    12: "twelve",
    13: "thirteen",
    14: "fourteen",
    15: "fifteen",
    16: "sixteen",
    17: "seventeen",
    18: "eighteen",
    19: "nineteen",
}
_TENS = {
    20: "twenty",
    30: "thirty",
    40: "forty",
    50: "fifty",
    60: "sixty",
    70: "seventy",
    80: "eighty",
    90: "ninety",
}
_ORDINAL = {
    "one": "first",
    "two": "second",
    "three": "third",
    "four": "fourth",
    "five": "fifth",
    "eight": "eighth",
    "nine": "ninth",
    "twelve": "twelfth",
}


def _number_words(number: int) -> str:
    if number < 20:
        return _SMALL[number]
    if number < 100:
        return _TENS[number // 10 * 10] + ("-" + _SMALL[number % 10] if number % 10 else "")
    if number < 1000:
        rest = number % 100
        return _SMALL[number // 100] + " hundred" + (" " + _number_words(rest) if rest else "")
    if number < 1_000_000:
        rest = number % 1000
        return (
            _number_words(number // 1000)
            + " thousand"
            + (" " + _number_words(rest) if rest else "")
        )
    return str(number)


def _replace_number(match: re.Match[str]) -> str:
    value = int(match.group(1))
    suffix = match.group(2)
    if value >= 1_000_000:
        return match.group(0)
    words = _number_words(value)
    if suffix:
        parts = words.split("-")
        last = parts[-1].split()[-1]
        ordinal = _ORDINAL.get(last, last + "th")
        if " " in parts[-1]:
            first, last = parts[-1].rsplit(" ", 1)
            parts[-1] = first + " " + ordinal
        else:
            parts[-1] = ordinal
        words = "-".join(parts)
    return words


def normalize_text(text: str) -> tuple[str, ...]:
    """Normalize punctuation, contractions, numerals, hyphens, and spelling."""
    value = text.lower().replace("’", "'").replace("‘", "'")
    for contraction, expansion in sorted(_CONTRACTIONS.items(), key=lambda item: -len(item[0])):
        value = re.sub(rf"(?<![a-z]){re.escape(contraction)}(?![a-z])", expansion, value)
    value = re.sub(r"\b(\d+)(st|nd|rd|th)?\b", _replace_number, value)
    tokens = re.findall(r"[a-z]+(?:'[a-z]+)?", value)
    normalized: list[str] = []
    for token in tokens:
        normalized.append(_SPELLING.get(token, token))
    return tuple(normalized)


def lemma(word: str) -> str:
    token = normalize_text(word)
    if not token:
        return ""
    value = token[0]
    if value in _IRREGULAR_LEMMAS:
        return _IRREGULAR_LEMMAS[value]
    try:
        from simplemma import lemmatize

        result = lemmatize(value, lang="en")
        if value.endswith("ed") and result.endswith("e") and result not in _FINAL_E_VERBS:
            result = result[:-1]
        return _IRREGULAR_LEMMAS.get(result, result)
    except (ImportError, Exception):
        return value


def same_word(left: str, right: str) -> bool:
    """Return true for exact, normalized spelling, or English lemma equivalence."""
    left_tokens, right_tokens = normalize_text(left), normalize_text(right)
    if len(left_tokens) != 1 or len(right_tokens) != 1:
        return left_tokens == right_tokens
    return lemma(left_tokens[0]) == lemma(right_tokens[0])


def find_phrase(phrase: str, words: tuple[str, ...] | list[str]) -> tuple[int, ...] | None:
    """Find the first contiguous lemma-equivalent phrase and return its token indexes."""
    expected = normalize_text(phrase)
    if not expected:
        return None
    for start in range(len(words) - len(expected) + 1):
        if all(same_word(expected[index], words[start + index]) for index in range(len(expected))):
            return tuple(range(start, start + len(expected)))
    return None
