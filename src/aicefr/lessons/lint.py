"""Warn a teacher about content that will trip the machine, while authoring (D025).

Each warning names a concrete trap: a digit the recogniser may write as a word
or the other way round, a British spelling, a sentence too long for the band, a
gap whose answer and distractor differ only by an ending -- something the
recogniser cannot hear reliably. Nothing here blocks publishing: the teacher
knows the class; the linter knows the machine.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass

from aicefr.contracts import Band
from aicefr.lessons.generate import READING_WPM, sentences
from aicefr.lessons.model import GAP_PATTERN, TEXT_KINDS, Lesson, Stage, StepKind
from aicefr.lessons.text import BRITISH, find_phrase, lemma, phrase_tokens, tokens

# Longest sentence, in words, that a learner at the band reads comfortably.
SENTENCE_WORDS = {Band.A2: 14, Band.B1: 20, Band.B2: 28}

# Words that sound like another word: a key word or a gap answer from this list
# cannot be told apart by listening.
HOMOPHONES = [
    {"to", "two", "too"},
    {"there", "their"},
    {"right", "write"},
    {"hear", "here"},
    {"see", "sea"},
    {"by", "buy", "bye"},
    {"new", "knew"},
    {"no", "know"},
    {"one", "won"},
    {"for", "four"},
    {"eight", "ate"},
    {"son", "sun"},
    {"meet", "meat"},
    {"week", "weak"},
    {"wear", "where"},
    {"whole", "hole"},
    {"flower", "flour"},
    {"road", "rode"},
    {"hour", "our"},
    {"peace", "piece"},
]

_DIGIT = re.compile(r"\d")


def _names(sentence: str) -> list[str]:
    """Capitalised words that do not open the sentence: likely proper names."""
    words = [w.strip(".,!?;:\"'()") for w in sentence.split()[1:]]
    return [w for w in words if len(w) > 1 and w[0].isupper() and w[1:].islower()]


@dataclass(frozen=True)
class Issue:
    level: str  # "warn" or "info"
    message: str
    step_id: str | None = None
    field: str | None = None

    def as_dict(self) -> dict:
        return asdict(self)


def _homophone(word: str) -> set[str] | None:
    w = word.lower()
    return next((g for g in HOMOPHONES if w in g), None)


def _text_issues(text: str, band: Band, step_id: str | None, field: str) -> list[Issue]:
    out: list[Issue] = []
    if _DIGIT.search(text):
        out.append(
            Issue(
                "warn",
                "Văn bản có chữ số. Viết số bằng chữ (3 → three): máy nhận dạng lúc chép "
                "thành chữ số, lúc thành chữ.",
                step_id,
                field,
            )
        )
    british = sorted({w for w in re.findall(r"[A-Za-z]+", text) if w.lower() in BRITISH})
    if british:
        pairs = ", ".join(f"{w} → {BRITISH[w.lower()]}" for w in british[:4])
        out.append(
            Issue(
                "info",
                f"Cách viết Anh: {pairs}. Hệ thống coi hai cách viết là một, nhưng nên "
                "thống nhất trong cả lộ trình.",
                step_id,
                field,
            )
        )
    limit = SENTENCE_WORDS[band]
    long = [s for s in sentences(text) if len(tokens(s)) > limit]
    if long:
        out.append(
            Issue(
                "info",
                f"Có {len(long)} câu dài hơn {limit} từ, hơi dài cho mức {band.value}: "
                f"«{long[0][:60]}…».",
                step_id,
                field,
            )
        )
    for s in sentences(text):
        names = _names(s)
        if names:
            out.append(
                Issue(
                    "info",
                    f"Tên riêng ({', '.join(sorted(set(names))[:3])}) dễ bị máy chép sai; "
                    "đừng đặt chúng làm từ khóa hay chỗ trống.",
                    step_id,
                    field,
                )
            )
            break
    return out


def lint_lesson(lesson: Lesson) -> list[Issue]:
    out: list[Issue] = []
    if not lesson.steps:
        out.append(Issue("warn", "Bài học chưa có bước nào."))
        return out
    if not lesson.free_step_ids:
        out.append(
            Issue(
                "warn",
                "Bài chưa có bước Nói tự do. Luyện trên văn bản soạn sẵn ít khi tự chuyển "
                "thành nói tự do, nên mỗi bài nên kết thúc bằng một lượt nói tự do.",
            )
        )
    elif lesson.steps[-1].kind is not StepKind.FREE:
        out.append(Issue("info", "Bước Nói tự do nên là bước cuối của bài."))
    order = [s.stage for s in lesson.steps]
    ranks = {Stage.MODEL: 0, Stage.CONTROLLED: 1, Stage.GUIDED: 2, Stage.FREE: 3}
    if any(ranks[a] > ranks[b] for a, b in zip(order, order[1:], strict=False)):
        out.append(
            Issue(
                "info",
                "Các bước không đi theo thứ tự Mẫu → Có kiểm soát → Có hướng dẫn → Tự do.",
            )
        )
    if lesson.model_text:
        out += _text_issues(lesson.model_text, lesson.band, None, "model_text")
        said = tokens(lesson.model_text)
        absent = [k for k in lesson.keywords if find_phrase(said, phrase_tokens(k)) is None]
        if absent:
            out.append(
                Issue(
                    "warn",
                    f"Từ khóa không có trong đoạn văn mẫu: {', '.join(absent)}.",
                    None,
                    "keywords",
                )
            )

    for step in lesson.steps:
        sid = step.step_id
        if step.kind in TEXT_KINDS and step.text.strip() and step.text != lesson.model_text:
            out += _text_issues(step.text, lesson.band, sid, "text")
        if step.kind in TEXT_KINDS and not step.text.strip():
            out.append(Issue("warn", "Bước này chưa có văn bản.", sid, "text"))

        if step.kind is StepKind.READ_ALOUD:
            said = tokens(step.text)
            absent = [w for w in step.hint_words if find_phrase(said, phrase_tokens(w)) is None]
            if absent:
                out.append(
                    Issue(
                        "warn",
                        f"Từ gợi ý không có trong văn bản: {', '.join(absent)}.",
                        sid,
                        "hint_words",
                    )
                )
            seconds = len(said) / READING_WPM[lesson.band] * 60
            if seconds > step.max_seconds:
                out.append(
                    Issue(
                        "warn",
                        f"Đọc hết đoạn này mất khoảng {round(seconds)} giây ở mức "
                        f"{lesson.band.value}, lâu hơn thời gian ghi tối đa "
                        f"{step.max_seconds} giây.",
                        sid,
                        "max_seconds",
                    )
                )

        if step.kind is StepKind.REPEAT and not step.model_audio:
            out.append(
                Issue(
                    "info",
                    "Chưa có giọng mẫu: sinh viên sẽ đọc câu thay vì nghe rồi nhắc lại.",
                    sid,
                    "model_audio",
                )
            )

        if step.kind is StepKind.GAP:
            blanks = len(GAP_PATTERN.findall(step.text))
            if blanks == 0:
                out.append(Issue("warn", "Đoạn văn chưa có chỗ trống (viết ___).", sid, "text"))
            if blanks != len(step.answers):
                out.append(
                    Issue(
                        "warn",
                        f"Có {blanks} chỗ trống nhưng {len(step.answers)} đáp án.",
                        sid,
                        "answers",
                    )
                )
            bank = {w.lower() for w in step.hint_words}
            absent = [a for a in step.answers if a.lower() not in bank]
            if absent:
                out.append(
                    Issue(
                        "warn",
                        f"Đáp án không có trong ngân hàng từ: {', '.join(absent)}.",
                        sid,
                        "hint_words",
                    )
                )
            if len(step.hint_words) <= blanks:
                out.append(
                    Issue(
                        "info", "Thêm ít nhất một từ gây nhiễu vào ngân hàng từ.", sid, "hint_words"
                    )
                )
            lemmas: dict[str, list[str]] = {}
            for w in step.hint_words:
                lemmas.setdefault(lemma(w.lower()), []).append(w)
            twins = [ws for ws in lemmas.values() if len(ws) > 1]
            if twins:
                out.append(
                    Issue(
                        "warn",
                        f"Từ chỉ khác đuôi ({' / '.join(twins[0])}): máy khó nghe ra khác biệt, "
                        "nên dùng các từ khác hẳn nhau.",
                        sid,
                        "hint_words",
                    )
                )
            for a in step.answers:
                group = _homophone(a)
                if group:
                    out.append(
                        Issue(
                            "warn",
                            f"Đáp án «{a}» đồng âm với {', '.join(sorted(group - {a.lower()}))}: "
                            "nghe không phân biệt được.",
                            sid,
                            "answers",
                        )
                    )
                if " " in a.strip():
                    out.append(Issue("warn", f"Đáp án «{a}» nên là một từ.", sid, "answers"))

        if step.kind is StepKind.KEYWORDS:
            if not step.keywords:
                out.append(Issue("warn", "Bước ghép câu chưa có từ khóa.", sid, "keywords"))
            for k in step.keywords:
                group = _homophone(k)
                if group:
                    out.append(
                        Issue(
                            "warn",
                            f"Từ khóa «{k}» đồng âm với {', '.join(sorted(group - {k.lower()}))}.",
                            sid,
                            "keywords",
                        )
                    )

        if step.kind is StepKind.STARTER and not step.starter.strip():
            out.append(Issue("warn", "Bước này chưa có khung câu.", sid, "starter"))
        if step.kind is StepKind.PICTURE:
            if not step.image:
                out.append(Issue("warn", "Bước mô tả tranh chưa có ảnh.", sid, "image"))
            if not step.hint_words:
                out.append(
                    Issue("info", "Chưa có ngân hàng từ cho bước mô tả tranh.", sid, "hint_words")
                )
        if step.kind is StepKind.OUTLINE and not step.markers:
            out.append(Issue("warn", "Bước nói theo dàn ý chưa có từ nối.", sid, "markers"))
        if step.kind in (StepKind.FREE, StepKind.OUTLINE, StepKind.STARTER, StepKind.PICTURE):
            if not step.text.strip():
                out.append(Issue("warn", "Bước này chưa có đề hay câu hỏi.", sid, "text"))
    return out
