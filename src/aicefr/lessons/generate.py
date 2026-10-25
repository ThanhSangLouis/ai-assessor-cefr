"""Build a lesson from one model text and a few key words (D025).

The teacher writes a short model text, picks the key words and a free-speaking
prompt; this module lays out the four-stage ladder by fixed rules. No language
model writes any content: every sentence a learner sees comes from the
teacher's text or from the templates below, and the teacher edits all of it
before publishing.

Support fades with the band (Kalyuga et al. 2003: help that serves a beginner
gets in the way of a stronger speaker):

    A2  read aloud, repeat, gap, look up, key words, outline, free (7 steps)
    B1  read aloud, gap, look up, key words, outline, free (6 steps)
    B2  read aloud, look up, key words, outline, free (5 steps)

Planning time shrinks the same way (60, 30, 15 seconds) and the free talk grows
longer, repeated in three rounds with shrinking time (4/3/2).
"""

from __future__ import annotations

import re

from aicefr.contracts import Band, Criterion, Mission, MissionKind
from aicefr.lessons.model import Lesson, Step, StepKind
from aicefr.lessons.text import find_phrase, phrase_tokens, tokens

# Words per minute a learner at each band can comfortably read aloud; used to
# size the recording window of a reading step. Conservative on purpose.
READING_WPM = {Band.A2: 80, Band.B1: 100, Band.B2: 120}
PREP_SECONDS = {Band.A2: 60, Band.B1: 30, Band.B2: 15}
OUTLINE_SECONDS = {Band.A2: (30, 60), Band.B1: (45, 75), Band.B2: (60, 90)}
FREE_ROUNDS = {Band.A2: [45, 35, 25], Band.B1: [60, 45, 35], Band.B2: [90, 70, 50]}
MARKERS = {
    Band.A2: [["first", "firstly"], ["then", "next", "after that"], ["finally", "in the end"]],
    Band.B1: [
        ["first", "to begin with"],
        ["after that", "then", "next"],
        ["finally", "in the end"],
    ],
    Band.B2: [
        ["first of all", "to begin with", "firstly"],
        ["on the other hand", "however", "although"],
        ["as a result", "in conclusion", "overall"],
    ],
}
OUTLINE_POINTS = {
    Band.A2: ["Nói đó là gì, ở đâu", "Kể hai hay ba chi tiết", "Nói cảm nghĩ của bạn"],
    Band.B1: ["Mở đầu: chuyện gì, khi nào", "Diễn biến theo thứ tự", "Kết thúc và cảm nghĩ"],
    Band.B2: ["Nêu quan điểm", "Một lý do và một ví dụ", "Một ý phản biện", "Kết luận"],
}

_SENTENCE = re.compile(r"(?<=[.!?])\s+")


def sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENTENCE.split(" ".join(text.split())) if s.strip()]


def _keyword_hits(sentence: str, keywords: list[str]) -> list[str]:
    said = tokens(sentence)
    return [k for k in keywords if find_phrase(said, phrase_tokens(k)) is not None]


def _ranked(text: str, keywords: list[str]) -> list[tuple[str, list[str]]]:
    """Sentences with the key words they contain, most key words first, then shorter."""
    found = [(s, _keyword_hits(s, keywords)) for s in sentences(text)]
    return sorted(found, key=lambda x: (-len(x[1]), len(tokens(x[0]))))


def _blank(sentence: str, words: list[str]) -> tuple[str, list[str]]:
    """Replace the first occurrence of each single key word with a blank, in text order."""
    out = sentence
    blanked: list[tuple[int, str]] = []
    for w in words:
        if " " in w.strip():
            continue  # a blank stands for one word
        m = re.search(rf"\b{re.escape(w)}\b", out, flags=re.IGNORECASE)
        if m:
            blanked.append((m.start(), m.group(0)))
            out = out[: m.start()] + "___" + out[m.end() :]
    blanked.sort()
    return out, [w for _, w in blanked]


def build_lesson(
    title: str,
    band: Band,
    model_text: str,
    keywords: list[str],
    free_prompt: str,
    criterion: Criterion | None = None,
    summary: str = "",
) -> Lesson:
    """Lay out the ladder for one lesson. Every field stays editable afterwards."""
    text = " ".join(model_text.split())
    kws = [k for k in (" ".join(k.split()) for k in keywords) if k]
    ranked = _ranked(text, kws)
    words = len(tokens(text))
    read_seconds = max(15, min(180, round(words / READING_WPM[band] * 60 * 1.6) + 5))

    steps: list[Step] = [
        Step(
            kind=StepKind.READ_ALOUD,
            instruction=(
                "Nghe giọng mẫu (nếu có) rồi đọc to cả đoạn. Từ gợi ý được tô đậm; "
                "đọc rõ, đúng nhịp, không cần nhanh."
            ),
            text=text,
            hint_words=kws,
            max_seconds=read_seconds,
        )
    ]

    # Sentences already given a step, as the teacher wrote them: a gap step
    # stores its sentence with blanks, so its text alone does not tell.
    used: set[str] = set()
    if band is Band.A2 and ranked:
        sentence = ranked[0][0]
        used.add(sentence)
        steps.append(
            Step(
                kind=StepKind.REPEAT,
                instruction="Nghe câu mẫu một lần rồi nhắc lại. Lần thứ hai thử không nhìn chữ.",
                text=sentence,
                max_seconds=max(8, min(30, len(tokens(sentence)) + 5)),
            )
        )

    if band in (Band.A2, Band.B1):
        fillable = [(s, hits) for s, hits in ranked if any(" " not in h for h in hits)]
        # A sentence not used yet when there is one, so the ladder covers more
        # of the text and more of its key words.
        candidates = [c for c in fillable if c[0] not in used] or fillable
        if candidates:
            gap_sentence, hits = candidates[0]
            used.add(gap_sentence)
            gapped, answers = _blank(gap_sentence, hits[:3])
            distractors = [k for k in kws if k not in answers and " " not in k][:2]
            steps.append(
                Step(
                    kind=StepKind.GAP,
                    instruction=(
                        "Đọc to câu, tự điền từ vào chỗ trống. Chọn từ trong ngân hàng từ; "
                        "có từ không dùng đến."
                    ),
                    text=gapped,
                    answers=answers,
                    hint_words=answers + distractors,
                    max_seconds=max(10, min(40, len(tokens(gap_sentence)) + 8)),
                )
            )

    used.add(text)
    look = next(((s, h) for s, h in ranked if len(h) >= 2 and s not in used), None) or next(
        ((s, h) for s, h in ranked if s not in used), None
    )
    if look:
        n = len(tokens(look[0]))
        steps.append(
            Step(
                kind=StepKind.LOOK_UP,
                instruction=(
                    "Đọc câu trong lúc nó còn hiện. Khi chữ ẩn đi, nhìn lên và nói lại câu."
                ),
                text=look[0],
                show_seconds=max(4, min(10, round(n * 0.6))),
                max_seconds=max(8, min(30, n + 6)),
            )
        )

    chosen = [k for k in kws if " " not in k][:3] or kws[:3]
    if chosen:
        steps.append(
            Step(
                kind=StepKind.KEYWORDS,
                instruction=(
                    "Nói một hay hai câu của riêng bạn có các từ dưới đây. Mọi dạng của từ "
                    "đều được tính (go, went, going)."
                ),
                keywords=chosen,
                min_words=len(chosen) + 4,
                max_seconds=30,
            )
        )

    low, high = OUTLINE_SECONDS[band]
    steps.append(
        Step(
            kind=StepKind.OUTLINE,
            instruction=(
                "Chuẩn bị trong thời gian cho phép, rồi nói theo dàn ý. Dùng từ nối để chuyển ý."
            ),
            text=free_prompt,
            outline=OUTLINE_POINTS[band],
            markers=MARKERS[band],
            prep_seconds=PREP_SECONDS[band],
            min_seconds=low,
            max_seconds=high,
        )
    )
    steps.append(
        Step(
            kind=StepKind.FREE,
            instruction=(
                "Nói tự do về đề dưới đây, ba lượt. Mỗi lượt ngắn hơn lượt trước: nói lại "
                "cùng nội dung, nhanh và ít ngừng hơn."
            ),
            text=free_prompt,
            rounds=FREE_ROUNDS[band],
            max_seconds=FREE_ROUNDS[band][0],
        )
    )
    return Lesson(
        title=title,
        summary=summary,
        band=band,
        criterion=criterion,
        model_text=text,
        keywords=kws,
        steps=steps,
    )


def build_word_lesson(
    title: str,
    band: Band,
    keywords: list[str],
    free_prompt: str,
    criterion: Criterion | None = None,
    summary: str = "",
) -> Lesson:
    """A lesson with no model text: key words in threes, then free speech.

    For the words a class keeps leaving out (the insights screen): without a
    text there is nothing to read aloud, so the ladder starts at the guided
    rung and ends, like every lesson, in free speech.
    """
    kws = [k for k in (" ".join(k.split()) for k in keywords) if k]
    steps = [
        Step(
            kind=StepKind.KEYWORDS,
            instruction=(
                "Nói một hay hai câu của riêng bạn có các từ dưới đây. Mọi dạng của từ "
                "đều được tính (go, went, going)."
            ),
            keywords=group,
            min_words=len(group) + 4,
            max_seconds=30,
        )
        for group in (kws[i : i + 3] for i in range(0, len(kws), 3))
    ]
    reuse = kws[:6]
    need = min(3, len(reuse))
    steps.append(
        Step(
            kind=StepKind.FREE,
            instruction="Nói tự do về đề dưới đây, cố dùng lại các từ vừa luyện.",
            text=free_prompt,
            rounds=FREE_ROUNDS[band][:2],
            max_seconds=FREE_ROUNDS[band][0],
            # Measured, so "use the words again" is a promise the feedback keeps.
            missions=(
                [
                    Mission(
                        kind=MissionKind.USE_WORDS,
                        target=need,
                        label=f"Dùng lại ít nhất {need} từ vừa luyện",
                        words=tuple(reuse),
                    )
                ]
                if need
                else []
            ),
        )
    )
    return Lesson(
        title=title,
        summary=summary,
        band=band,
        criterion=criterion,
        keywords=kws,
        steps=steps,
    )
