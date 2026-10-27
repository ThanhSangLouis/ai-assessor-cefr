"""Measure one recorded step against what the step asked for (D025).

Every rule is a count the learner can redo by listening back: which words of
the text the machine heard, which key words came up and at which second, how
long the longest pause was. No model, no weights.

What the learner must be told, and the screens tell them:

* The counts run on the MACHINE'S TRANSCRIPT, which is never prompted with the
  expected text: a prompt makes the transcript drift toward the text instead of
  what was said. A word the machine did not hear is "máy chưa nghe ra", never
  "sai". On Vietnamese read speech the transcript differs from the text in
  about one word in eight even before any reading error (McGuire 2025), which
  is why the default pass mark for reading is 75% and not 95%.
* Only words that fall inside speech found by the VAD are counted, so words
  the recogniser invents in a silent stretch earn nothing.
* Grammar, content and pronunciation are not judged: the recogniser repairs
  grammar while transcribing and scores against native speech measure accent,
  not intelligibility.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from types import SimpleNamespace

from aicefr.contracts import MissionHit, ReasonCode, Transcript
from aicefr.formatting import vi_decimal as _num
from aicefr.lessons.align import Op, align
from aicefr.lessons.model import (
    GAP_PATTERN,
    STEP_RULES_VERSION,
    GapMark,
    GapStatus,
    Signal,
    Step,
    StepKind,
    StepResult,
    Strictness,
    WordMark,
    WordStatus,
)
from aicefr.lessons.text import (
    FILLERS,
    find_phrase,
    is_content,
    normalize_word,
    phrase_tokens,
    same_word,
    split_words,
    tokens,
)
from aicefr.practice.missions import MissionChecker
from aicefr.pronunciation.vietnamese import classify as classify_pronunciation

# A word heard with a probability under this is shown as "chưa chắc".
UNSURE_PROB = 0.5
# Slack around a VAD segment when deciding whether a word lies inside speech.
SPEECH_SLACK_S = 0.3
# A pause between two speech segments at least this long is counted.
PAUSE_S = 1.0

THRESHOLDS: dict[str, dict[Strictness, float]] = {
    # share of the words of a text heard (read aloud, repeat)
    "coverage": {Strictness.EASY: 0.6, Strictness.NORMAL: 0.75, Strictness.STRICT: 0.85},
    # share of the CONTENT words heard (read-and-look-up)
    "content": {Strictness.EASY: 0.5, Strictness.NORMAL: 0.7, Strictness.STRICT: 0.85},
    "gaps": {Strictness.EASY: 0.5, Strictness.NORMAL: 0.75, Strictness.STRICT: 1.0},
    "keywords": {Strictness.EASY: 0.5, Strictness.NORMAL: 0.67, Strictness.STRICT: 1.0},
    "markers": {Strictness.EASY: 0.34, Strictness.NORMAL: 0.67, Strictness.STRICT: 1.0},
    # share of the target time actually spoken
    "time": {Strictness.EASY: 0.5, Strictness.NORMAL: 0.7, Strictness.STRICT: 0.85},
    # share of the minimum word count required
    "words": {Strictness.EASY: 0.5, Strictness.NORMAL: 1.0, Strictness.STRICT: 1.0},
}


def _need(ratio: float, n: int) -> int:
    """How many of n are needed at this ratio; at least one when n > 0."""
    return 0 if n <= 0 else max(1, math.ceil(ratio * n - 1e-9))


@dataclass(frozen=True)
class Heard:
    """One normalised word the machine heard inside speech."""

    text: str
    start_s: float | None
    end_s: float | None
    prob: float | None


def heard_words(transcript: Transcript, segments: Sequence[tuple[float, float]]) -> list[Heard]:
    """The transcript as normalised words, keeping only those inside VAD speech.

    Without word timings (a recogniser that gives none) nothing can be checked
    against the segments, so every word is kept.
    """
    out: list[Heard] = []
    if not transcript.words:
        return [Heard(t, None, None, None) for t in tokens(transcript.text) if t not in FILLERS]
    spans = sorted(segments)
    for w in transcript.words:
        if not _in_speech(w.start_s, w.end_s, spans):
            continue
        for tok in normalize_word(w.text):
            if tok not in FILLERS:
                out.append(Heard(tok, w.start_s, w.end_s, w.prob))
    return out


def _in_speech(start: float, end: float, spans: Sequence[tuple[float, float]]) -> bool:
    return any(start < e + SPEECH_SLACK_S and end > s - SPEECH_SLACK_S for s, e in spans)


def speaking_span(segments: Sequence[tuple[float, float]]) -> float:
    if not segments:
        return 0.0
    return max(e for _, e in segments) - min(s for s, _ in segments)


def pauses(segments: Sequence[tuple[float, float]]) -> list[tuple[float, float]]:
    """(start, length) of each silence between two speech segments, longest first."""
    seg = sorted(segments)
    gaps = [
        (a_end, b_start - a_end) for (_, a_end), (b_start, _) in zip(seg, seg[1:], strict=False)
    ]
    return sorted((g for g in gaps if g[1] > 0), key=lambda g: -g[1])


# ---------------------------------------------------------------- text marking


@dataclass
class _RefToken:
    text: str
    owner: int  # index of the written word it comes from
    blank: int | None = None  # GAP: index of the blank


def _reference(text: str) -> tuple[list[str], list[_RefToken]]:
    """Written words of a text and their normalised tokens; blanks become placeholders."""
    shown = split_words(text)
    toks: list[_RefToken] = []
    blank = 0
    for i, word in enumerate(shown):
        if GAP_PATTERN.search(word):
            toks.append(_RefToken("", i, blank))
            blank += 1
            continue
        for t in normalize_word(word):
            toks.append(_RefToken(t, i))
    return shown, toks


def _head(word: str) -> str:
    """The first spoken word of a bank entry or an answer."""
    toks = phrase_tokens(word)
    return toks[0] if toks else ""


def _mark_text(
    step: Step, heard: list[Heard], answers: list[str] | None = None
) -> tuple[list[WordMark], list[GapMark]]:
    """Align the heard words with the step's text and mark every written word."""
    shown, ref = _reference(step.text)
    said = [h.text for h in heard]
    bank = step.hint_words
    fillers = [w for w in (_head(o) for o in [*(answers or []), *bank]) if w]

    def equal(r: str, h: str) -> bool:
        # A blank lines up for free only with a word that could fill it, an
        # answer or a bank word; any other word costs a substitution. With "any
        # word is free", speech running on after the sentence ("... a park
        # nearby, okay") tied with the right reading, and the alignment, which
        # resolves ties from the end, put the last word heard into the blank.
        if r == "":
            return any(same_word(h, f) for f in fillers)
        return r == h

    pairs, _ = align([t.text for t in ref], said, equal)
    status: dict[int, list[WordStatus]] = {}
    start: dict[int, float | None] = {}
    said_as: dict[int, str] = {}
    gaps: list[GapMark] = []

    for pair in pairs:
        rt = ref[pair.ref_index]
        h = heard[pair.hyp_index] if pair.hyp_index is not None else None
        if rt.blank is not None:
            expected = answers[rt.blank] if answers and rt.blank < len(answers) else ""
            if h is None:
                gaps.append(GapMark(index=rt.blank, expected=expected, status=GapStatus.MISSING))
                continue
            if expected and same_word(h.text, _head(expected)):
                st = GapStatus.CORRECT
            elif any(same_word(h.text, _head(b)) for b in bank if _head(b)):
                st = GapStatus.DISTRACTOR
            else:
                st = GapStatus.OTHER
            gaps.append(
                GapMark(
                    index=rt.blank, expected=expected, said=h.text, status=st, start_s=h.start_s
                )
            )
            continue
        if pair.op is Op.MATCH and h is not None:
            st = (
                WordStatus.UNSURE
                if (h.prob is not None and h.prob < UNSURE_PROB)
                else WordStatus.HEARD
            )
        elif pair.op is Op.SUBSTITUTE and h is not None and same_word(rt.text, h.text):
            st = WordStatus.UNSURE  # heard, in another form ("walk" for "walks")
            said_as[rt.owner] = h.text
        else:
            st = WordStatus.MISSED
            if h is not None:
                said_as[rt.owner] = h.text
        status.setdefault(rt.owner, []).append(st)
        if h is not None and st is not WordStatus.MISSED and start.get(rt.owner) is None:
            start[rt.owner] = h.start_s

    marks: list[WordMark] = []
    for i, word in enumerate(shown):
        if i not in status:
            continue  # a blank, or punctuation with no spoken word
        sts = status[i]
        if all(s is WordStatus.HEARD for s in sts):
            final = WordStatus.HEARD
        elif all(s is WordStatus.MISSED for s in sts):
            final = WordStatus.MISSED
        else:
            final = WordStatus.UNSURE
        norm = normalize_word(word)
        said_word = said_as.get(i) if final is not WordStatus.HEARD else None
        pattern = classify_pronunciation(word, said_word) if said_word else None
        marks.append(
            WordMark(
                index=i,
                text=word,
                status=final,
                start_s=start.get(i),
                said=said_word,
                content=any(is_content(t) for t in norm),
                pattern=pattern.value if pattern else None,
            )
        )
    gaps.sort(key=lambda g: g.index)
    return marks, gaps


def _covered(marks: list[WordMark], content_only: bool = False) -> tuple[int, int]:
    pool = [m for m in marks if m.content] if content_only else marks
    ok = sum(1 for m in pool if m.final is not WordStatus.MISSED)
    return ok, len(pool)


def _first_missed(marks: list[WordMark]) -> str | None:
    for m in marks:
        if m.final is WordStatus.MISSED and m.content:
            return m.text.strip(".,!?;:\"'“”‘’()")
    return None


# ---------------------------------------------------------------- shared signals


def _timing_signals(segments: Sequence[tuple[float, float]], words: int) -> list[Signal]:
    span = speaking_span(segments)
    gaps = pauses(segments)
    out = [
        Signal(
            key="speaking_s",
            label="Thời gian nói",
            value=round(span, 1),
            unit="giây",
            text=f"Bạn nói {_num(span)} giây",
        ),
    ]
    if span >= 5 and words:
        wpm = words / (span / 60)
        out.append(
            Signal(
                key="wpm",
                label="Số từ mỗi phút",
                value=round(wpm),
                unit="từ/phút",
                text=f"Khoảng {round(wpm)} từ mỗi phút",
            )
        )
    if gaps:
        at, length = gaps[0]
        out.append(
            Signal(
                key="longest_pause",
                label="Quãng ngừng dài nhất",
                value=round(length, 1),
                unit="giây",
                text=f"Quãng ngừng dài nhất {_num(length)} giây, ở giây {_num(at)}",
            )
        )
    if span >= 10:
        per_min = sum(1 for _, length in gaps if length >= PAUSE_S) / (span / 60)
        out.append(
            Signal(
                key="pauses_per_min",
                label="Quãng ngừng trên 1 giây mỗi phút",
                value=round(per_min, 1),
                text=f"{_num(per_min)} quãng ngừng trên 1 giây mỗi phút",
            )
        )
    return out


def _find_items(
    items: list[str], said: list[str], heard: list[Heard]
) -> tuple[list[MissionHit], list[str]]:
    found: list[MissionHit] = []
    missing: list[str] = []
    for item in items:
        at = find_phrase(said, phrase_tokens(item))
        if at is None:
            missing.append(item)
        else:
            found.append(MissionHit(text=item, start_s=heard[at].start_s))
    return found, missing


# ---------------------------------------------------------------- the checker


class StepChecker:
    rules_version = STEP_RULES_VERSION

    def check(
        self,
        step: Step,
        transcript: Transcript,
        segments: Sequence[tuple[float, float]],
        round_index: int | None = None,
        answers: list[str] | None = None,
    ) -> StepResult:
        """Measure one attempt. `answers` are the gap answers (never sent to the browser)."""
        heard = heard_words(transcript, segments)
        said = [h.text for h in heard]
        span = speaking_span(segments)
        base = {
            "step_id": step.step_id,
            "kind": step.kind,
            "transcript": transcript.text,
            "speaking_s": round(span, 2),
            "round": round_index,
            "rules_version": self.rules_version,
        }
        if not heard:
            return StepResult(
                **base,
                passed=False,
                measured=False,
                tip=(
                    "Máy chưa nghe thấy lời nói nào. Kiểm tra micro, nói gần micro hơn rồi ghi lại."
                ),
                reasons=[ReasonCode.ASR_EMPTY_TRANSCRIPT],
            )
        handler = {
            StepKind.READ_ALOUD: self._read,
            StepKind.REPEAT: self._read,
            StepKind.LOOK_UP: self._look_up,
            StepKind.GAP: self._gap,
            StepKind.KEYWORDS: self._keywords,
            StepKind.STARTER: self._starter,
            StepKind.PICTURE: self._picture,
            StepKind.OUTLINE: self._outline,
            StepKind.FREE: self._free,
        }[step.kind]
        return handler(step, heard, said, transcript, segments, base, round_index, answers)

    # ------------------------------------------------------------ text kinds

    def _read(
        self, step, heard, said, transcript, segments, base, round_index, answers
    ) -> StepResult:
        marks, _ = _mark_text(step, heard)
        ok, total = _covered(marks)
        ratio = ok / total if total else 0.0
        target = THRESHOLDS["coverage"][step.strictness]
        passed = total > 0 and ratio >= target
        signals = [
            Signal(
                key="coverage",
                label="Số từ máy nghe ra",
                value=round(ratio, 3),
                unit="%",
                target=target,
                met=passed,
                text=f"Máy nghe ra {ok}/{total} từ ({round(ratio * 100)}%)",
            ),
            *_timing_signals(segments, ok),
        ]
        found, missing = [], []
        if step.hint_words:
            found, missing = _find_items(step.hint_words, said, heard)
            signals.append(
                Signal(
                    key="hints",
                    label="Từ gợi ý máy nghe ra",
                    value=len(found),
                    target=len(step.hint_words),
                    met=not missing,
                    text=f"Từ gợi ý: {len(found)}/{len(step.hint_words)}",
                )
            )
        first = _first_missed(marks)
        if not passed and first:
            verb = (
                "Nghe lại câu mẫu rồi nhắc lại"
                if step.kind is StepKind.REPEAT
                else "Đọc lại câu có từ"
            )
            tip = f"{verb} «{first}»: máy chưa nghe ra đoạn này. Đọc chậm và rõ từng từ."
        elif not passed:
            tip = "Đọc lại cả đoạn, rõ và đều hơn."
        else:
            longest = pauses(segments)[0][1] if pauses(segments) else 0.0
            if first:
                # Passed, but a word was not heard: the one thing to fix is that word.
                tip = f"Đạt. Máy chưa nghe ra «{first}»: đọc lại câu có từ này, rõ từng từ."
            elif longest >= 2.0:
                tip = f"Máy nghe ra đủ ý. Đọc lại liền mạch hơn: có chỗ ngừng {_num(longest)} giây."
            else:
                tip = "Tốt. Lần sau chú ý nhịp và ngữ điệu ở câu dài nhất."
        return StepResult(
            **base,
            passed=passed,
            words=marks,
            found=found,
            missing=missing,
            signals=signals,
            tip=tip,
        )

    def _look_up(
        self, step, heard, said, transcript, segments, base, round_index, answers
    ) -> StepResult:
        marks, _ = _mark_text(step, heard)
        ok, total = _covered(marks, content_only=True)
        if total == 0:
            ok, total = _covered(marks)
        ratio = ok / total if total else 0.0
        target = THRESHOLDS["content"][step.strictness]
        passed = total > 0 and ratio >= target
        missed = [
            m.text.strip(".,!?;:") for m in marks if m.content and m.final is WordStatus.MISSED
        ]
        signals = [
            Signal(
                key="content",
                label="Từ mang nghĩa máy nghe ra",
                value=round(ratio, 3),
                unit="%",
                target=target,
                met=passed,
                text=f"Máy nghe ra {ok}/{total} từ mang nghĩa ({round(ratio * 100)}%)",
            ),
            *_timing_signals(segments, len(said)),
        ]
        if passed:
            tip = "Bạn nhớ được ý chính của câu. Khác biệt ở a, the, of chỉ để tham khảo."
        else:
            shown = "», «".join(missed[:2]) if missed else ""
            tip = (
                f"Đọc câu thêm một lần, ghi nhớ «{shown}», rồi nói lại khi chữ ẩn."
                if shown
                else "Đọc câu thêm một lần rồi nói lại khi chữ ẩn."
            )
        return StepResult(
            **base, passed=passed, words=marks, signals=signals, tip=tip, missing=missed
        )

    def _gap(
        self, step, heard, said, transcript, segments, base, round_index, answers
    ) -> StepResult:
        marks, gaps = _mark_text(step, heard, answers or step.answers)
        n = len(gaps)
        correct = sum(1 for g in gaps if g.status is GapStatus.CORRECT)
        target = THRESHOLDS["gaps"][step.strictness]
        passed = n > 0 and correct >= _need(target, n)
        ok, total = _covered(marks)
        signals = [
            Signal(
                key="gaps",
                label="Chỗ trống điền đúng",
                value=correct,
                target=_need(target, n),
                met=passed,
                text=f"Điền đúng {correct}/{n} chỗ trống",
            ),
            Signal(
                key="coverage",
                label="Phần còn lại máy nghe ra",
                value=round(ok / total, 3) if total else None,
                unit="%",
                text=f"Phần còn lại: máy nghe ra {ok}/{total} từ" if total else "",
            ),
        ]
        wrong = next((g for g in gaps if g.status in (GapStatus.DISTRACTOR, GapStatus.OTHER)), None)
        empty = next((g for g in gaps if g.status is GapStatus.MISSING), None)
        if passed:
            tip = "Bạn chọn đúng từ cho các chỗ trống. Đọc lại một lần cho trôi chảy."
        elif wrong is not None:
            tip = (
                f"Chỗ trống {wrong.index + 1}: máy nghe «{wrong.said}». "
                "Đọc lại câu đó và chọn từ khác trong ngân hàng từ."
            )
        elif empty is not None:
            tip = (
                f"Chỗ trống {empty.index + 1}: máy chưa nghe ra từ nào. "
                "Đọc cả câu, kể cả từ bạn chọn."
            )
        else:
            tip = "Đọc lại đoạn văn, điền từ vào từng chỗ trống."
        return StepResult(**base, passed=passed, words=marks, gaps=gaps, signals=signals, tip=tip)

    # ------------------------------------------------------------ guided kinds

    def _keywords(
        self, step, heard, said, transcript, segments, base, round_index, answers
    ) -> StepResult:
        found, missing = _find_items(step.keywords, said, heard)
        n = len(step.keywords)
        need = _need(THRESHOLDS["keywords"][step.strictness], n)
        min_words = step.min_words or (n + 3)
        need_words = _need(THRESHOLDS["words"][step.strictness], min_words)
        enough_words = len(said) >= need_words
        passed = n > 0 and len(found) >= need and enough_words
        signals = [
            Signal(
                key="keywords",
                label="Từ khóa đã dùng",
                value=len(found),
                target=need,
                met=len(found) >= need,
                text=f"Dùng {len(found)}/{n} từ khóa",
            ),
            Signal(
                key="words",
                label="Số từ",
                value=len(said),
                target=need_words,
                met=enough_words,
                text=f"Câu có {len(said)} từ",
            ),
        ]
        if missing and len(found) < need:
            tip = f"Nói lại một câu có thêm từ «{missing[0]}». Mọi dạng của từ đều được tính."
        elif not enough_words:
            tip = f"Nói thành câu đầy đủ hơn, ít nhất {need_words} từ, đừng chỉ đọc các từ khóa."
        else:
            tip = "Tốt. Thử nói thêm một câu nữa với cùng các từ, theo cách khác."
        return StepResult(
            **base, passed=passed, found=found, missing=missing, signals=signals, tip=tip
        )

    def _starter(
        self, step, heard, said, transcript, segments, base, round_index, answers
    ) -> StepResult:
        frame = phrase_tokens(step.starter)
        at = None
        if frame:
            # The frame should open the answer: allow up to two words before it
            # ("Well, I like...") and accept any form of each word.
            at = find_phrase(said[: len(frame) + 2], frame)
        has_frame = at is not None
        after = len(said) - (at + len(frame)) if has_frame else 0
        min_words = step.min_words or 5
        need_words = _need(THRESHOLDS["words"][step.strictness], min_words)
        enough = after >= need_words
        found, missing = _find_items(step.keywords, said, heard) if step.keywords else ([], [])
        passed = has_frame and enough
        signals = [
            Signal(
                key="starter",
                label="Mở đầu bằng khung câu",
                value=1 if has_frame else 0,
                target=1,
                met=has_frame,
                text="Có mở đầu bằng khung câu" if has_frame else "Chưa nghe thấy khung câu ở đầu",
            ),
            Signal(
                key="words_after",
                label="Số từ sau khung câu",
                value=after,
                target=need_words,
                met=enough,
                text=f"{after} từ sau khung câu",
            ),
        ]
        if not has_frame:
            tip = f"Bắt đầu câu trả lời bằng «{step.starter}»."
        elif not enough:
            tip = f"Nói thêm sau khung câu: ít nhất {need_words} từ, có lý do hoặc ví dụ."
        else:
            tip = "Tốt. Thử thêm một lý do bắt đầu bằng because."
        return StepResult(
            **base, passed=passed, found=found, missing=missing, signals=signals, tip=tip
        )

    def _picture(
        self, step, heard, said, transcript, segments, base, round_index, answers
    ) -> StepResult:
        found, missing = _find_items(step.hint_words, said, heard)
        need = step.use_at_least or min(3, len(step.hint_words))
        if step.strictness is Strictness.EASY:
            need = max(1, need - 1)
        span = speaking_span(segments)
        time_need = step.min_seconds * THRESHOLDS["time"][step.strictness]
        long_enough = span >= time_need
        bank_tokens = {t for w in step.hint_words for t in phrase_tokens(w)}
        content = [w for w in said if is_content(w)]
        recited = (
            bool(content)
            and len(said) <= len(step.hint_words) + 3
            and (
                sum(1 for w in content if any(same_word(w, b) for b in bank_tokens)) / len(content)
                > 0.7
            )
        )
        passed = len(found) >= need and long_enough and not recited
        signals = [
            Signal(
                key="bank",
                label="Từ trong ngân hàng đã dùng",
                value=len(found),
                target=need,
                met=len(found) >= need,
                text=f"Dùng {len(found)}/{len(step.hint_words)} từ gợi ý",
            ),
            *_timing_signals(segments, len(said)),
            Signal(
                key="distinct",
                label="Số từ khác nhau",
                value=len(set(said)),
                text=f"{len(set(said))} từ khác nhau",
            ),
        ]
        if recited:
            tip = "Đừng chỉ đọc danh sách từ: nói thành câu về những gì bạn thấy."
        elif len(found) < need and missing:
            tip = f"Tả thêm một chi tiết có từ «{missing[0]}»."
        elif not long_enough:
            tip = f"Nói dài hơn: mới {_num(span)} giây, cần khoảng {step.min_seconds} giây."
        else:
            tip = "Tốt. Lần sau thêm một câu nói cảm nghĩ của bạn về bức tranh."
        return StepResult(
            **base, passed=passed, found=found, missing=missing, signals=signals, tip=tip
        )

    def _outline(
        self, step, heard, said, transcript, segments, base, round_index, answers
    ) -> StepResult:
        hits: list[MissionHit] = []
        last_at = -1
        in_order = 0
        missing_groups: list[str] = []
        for group in step.markers:
            positions = [
                p for p in (find_phrase(said, phrase_tokens(w)) for w in group) if p is not None
            ]
            if not positions:
                missing_groups.append(group[0])
                continue
            first = min(positions)
            word = next(w for w in group if find_phrase(said, phrase_tokens(w)) == first)
            hits.append(MissionHit(text=word, start_s=heard[first].start_s))
            if first > last_at:
                in_order += 1
                last_at = first
        n = len(step.markers)
        need = _need(THRESHOLDS["markers"][step.strictness], n)
        span = speaking_span(segments)
        time_need = step.min_seconds * THRESHOLDS["time"][step.strictness]
        long_enough = span >= time_need
        kw_found, kw_missing = (
            _find_items(step.keywords, said, heard) if step.keywords else ([], [])
        )
        passed = (n == 0 or in_order >= need) and long_enough
        signals = [
            Signal(
                key="markers",
                label="Từ nối theo dàn ý",
                value=in_order,
                target=need,
                met=n == 0 or in_order >= need,
                text=f"Dùng {in_order}/{n} từ nối đúng thứ tự",
            ),
            *_timing_signals(segments, len(said)),
        ]
        if step.keywords:
            signals.append(
                Signal(
                    key="keywords",
                    label="Ý trong dàn ý",
                    value=len(kw_found),
                    target=len(step.keywords),
                    text=f"Nhắc tới {len(kw_found)}/{len(step.keywords)} ý",
                )
            )
        if missing_groups and in_order < need:
            tip = f"Dùng từ nối «{missing_groups[0]}» để chuyển sang ý tiếp theo của dàn ý."
        elif not long_enough:
            tip = f"Nói dài hơn: mới {_num(span)} giây, cần khoảng {step.min_seconds} giây."
        else:
            tip = "Bài nói đi đúng dàn ý. Lần sau thêm một ví dụ cho ý thứ hai."
        return StepResult(
            **base,
            passed=passed,
            found=hits + kw_found,
            missing=kw_missing,
            signals=signals,
            tip=tip,
        )

    # ------------------------------------------------------------ free speech

    def _free(
        self, step, heard, said, transcript, segments, base, round_index, answers
    ) -> StepResult:
        limits = step.round_limits()
        r = min(max(round_index or 1, 1), len(limits))
        limit = limits[r - 1]
        span = speaking_span(segments)
        need = limit * THRESHOLDS["time"][step.strictness]
        long_enough = span >= need
        signals = _timing_signals(segments, len(said))
        signals.insert(
            0,
            Signal(
                key="time_used",
                label="Thời gian dùng",
                value=round(span, 1),
                unit="giây",
                target=round(need, 1),
                met=long_enough,
                text=f"Nói {_num(span)}/{limit} giây",
            ),
        )
        signals.append(
            Signal(
                key="distinct",
                label="Số từ khác nhau",
                value=len(set(said)),
                text=f"{len(set(said))} từ khác nhau",
            )
        )
        missions_ok = True
        if step.missions:
            spans = sorted(segments)
            kept = transcript.model_copy(
                update={
                    "words": [w for w in transcript.words if _in_speech(w.start_s, w.end_s, spans)]
                }
            )
            task = SimpleNamespace(
                task_id=step.step_id, missions=tuple(step.missions), reference_text=None
            )
            result = MissionChecker().check(task, kept, segments)
            for check in result.checks:
                if check.met is False:
                    missions_ok = False
                signals.append(
                    Signal(
                        key=f"mission_{check.kind.value}",
                        label=check.label,
                        value=check.measured,
                        target=check.target,
                        met=check.met,
                        text=check.label,
                    )
                )
        passed = long_enough and (missions_ok or step.strictness is Strictness.EASY)
        if r < len(limits) and limits[r] < limit:
            tip = (
                f"Lượt {r + 1} ngắn hơn: nói lại cùng nội dung trong {limits[r]} giây, "
                "nhanh và ít ngừng hơn."
            )
        elif r < len(limits):
            tip = f"Lượt {r + 1} cùng thời gian: giữ ý chính và thêm một ví dụ hay một ý phản biện."
        elif not long_enough:
            tip = f"Bạn nói {_num(span)} giây. Lần sau cố nói hết khoảng {limit} giây."
        else:
            tip = "Xong bài nói tự do. Nghe lại lượt cuối và so với lượt đầu."
        return StepResult(**base, passed=passed, signals=signals, tip=tip)


def compare_rounds(first: StepResult, latest: StepResult) -> list[str]:
    """How the last round of free speech differs from the first, in plain words.

    Fluency is what repeating under time pressure trains (Thai & Boers 2016), so
    the comparison is about pace and pauses, not about content.
    """

    def value(result: StepResult, key: str) -> float | None:
        return next((s.value for s in result.signals if s.key == key), None)

    out: list[str] = []
    for key, label, unit, higher_is_better in (
        ("wpm", "Số từ mỗi phút", "", True),
        ("longest_pause", "Quãng ngừng dài nhất", " giây", False),
        ("pauses_per_min", "Quãng ngừng trên 1 giây mỗi phút", "", False),
    ):
        a, b = value(first, key), value(latest, key)
        if a is None or b is None or a == b:
            continue
        shown = (lambda x: str(round(x))) if key == "wpm" else _num
        verb = "tăng" if b > a else "giảm"
        better = (b > a) == higher_is_better
        out.append(
            f"{label} {verb} từ {shown(a)}{unit} còn {shown(b)}{unit}"
            if b < a
            else f"{label} {verb} từ {shown(a)}{unit} lên {shown(b)}{unit}"
        )
        if better:
            out[-1] += ", tốt hơn lượt đầu"
    return out
