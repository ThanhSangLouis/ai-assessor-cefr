"""Detecting the repetition loops Whisper produces on silence.

A well known failure mode: given silence, noise, or the tail of a recording
after the speaker has stopped, Whisper does not emit nothing -- it emits a token
and then repeats it, sometimes hundreds of times.

Observed on a real submission to this system: a 95-second recording of about 186
spoken words came back with 398 words, of which the single token "Ti" appeared
**212 times**. The damage is not that the transcript looks odd; it is that every
count-based feature is poisoned at once:

    n_words        186  ->  398      (training range 36-151)
    words_per_sec  2.0  ->  4.19     (training range 0.80-2.66)
    ttr            ~0.6 ->  0.32     (repetition destroys type-token ratio)

The scorer then refused to score, correctly, but reported OUT_OF_DISTRIBUTION --
telling the student their speech was unusual when in fact the recogniser had
malfunctioned. The reason code matters: one says "your recording is unusual",
the other says "our transcript is not trustworthy".
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from aicefr.contracts import Word

# A token repeated this many times in a row is not speech.
MAX_CONSECUTIVE_REPEATS = 6

# A single token taking this share of the whole transcript is not speech either.
#
# The threshold has to survive ordinary English. "The" is roughly 5-7% of spoken
# English overall, but in a short passage it swings far higher: a 23-word
# sentence in these tests hits 21.7% with no repetition at all. So the share
# test only applies to transcripts long enough for the proportion to mean
# something, and the bar is set well above anything natural.
#
# The case this was written for was not marginal: one token at 53% of the
# transcript, repeated 212 times in a row. The consecutive-run test catches
# that on its own; the share test is a second net for repetition that is
# scattered rather than contiguous.
MAX_SINGLE_TOKEN_SHARE = 0.35
MIN_WORDS_FOR_SHARE = 60

# Whisper does not only loop on single tokens. On a real submission it produced:
#
#   "... Keep the classroom for discussion and practice. Keep the classroom for
#    discussion and practice. Keep the classroom stop reading as best if we put
#    them here in your classroom and practice. Keep the classroomOhRIio past
#    step when they process down that path ... finger Thank you."
#
# Every token in that tail is different enough that the single-token tests see
# nothing: no token repeats six times in a row, none reaches 35% of the
# transcript. But the speaker said none of it. The phrase repeats instead.
#
# Two occurrences of a phrase can be a person making a point twice. Three in a
# row is a machine stuck in a loop, so that is where the line sits.
MIN_PHRASE_LEN = 3
MAX_PHRASE_LEN = 10
MIN_PHRASE_REPEATS = 3

# Whisper marks invented words with a probability near zero. A run of them at
# the very end of a transcript is the signature of the recogniser continuing
# past where the speaker stopped -- in the same submission, the closing tokens
# "classroom", "past" and "finger" all came back at 0.00.
TAIL_LOW_PROB = 0.05
MIN_TAIL_LOW_PROB_RUN = 5

# The clearest signature of all, and the one that needs no thresholds tuned by
# taste: the clock stops.
#
# Measured on the recording a student sent in (95 seconds, WebM from the browser
# recorder, transcribed by whisper-large-v3-turbo). The speaker really did say
# "Keep the classroom for discussion and practice." between 88.4s and 92.3s.
# Then the recogniser said it again -- seven words, every one of them stamped
# start = end = 92.6s:
#
#     173  92.3  0.98  practice.     <- người nói thật, đồng hồ chạy
#     174  92.6  0.00  Keep          <- bắt đầu lặp
#     175  92.6  0.76  the
#     ...
#     180  92.6  0.99  practice.     <- bảy từ, cùng một mốc 92.6
#
# Speech cannot happen at zero duration. Probabilities lie (0.76, 0.92, 0.99
# above), word choice lies, but the timeline does not: if seven words occupy no
# time at all, the recogniser generated them rather than heard them.
MAX_STALLED_S_PER_WORD = 0.05
MIN_STALLED_RUN = 4


@dataclass(frozen=True)
class RepetitionFinding:
    """What was found, and where the trustworthy part of the transcript ends."""

    detected: bool
    token: str | None
    repeats: int
    share: float
    keep_until_index: int
    # "token" | "phrase" | "low_prob_tail" -- kept so the log says which of the
    # three nets caught it, which is the first thing anyone tuning them needs.
    kind: str = "token"

    def log_summary(self) -> str:
        """Ban cho LOG: khong co chu nao cua loi noi.

        `describe()` trich nguyen cum tu bi lap (toi 10 tu cua nguoi noi) va tung
        duoc ghi thang vao log, trai quy tac "khong ghi transcript vao log".
        """
        if not self.detected:
            return "no-repetition"
        return (
            f"kind={self.kind} repeats={self.repeats} share={self.share:.2f} "
            f"keep_until={self.keep_until_index}"
        )

    def describe(self) -> str:
        if not self.detected:
            return "không phát hiện lặp bất thường"
        if self.kind == "phrase":
            return f"cụm từ {self.token!r} lặp {self.repeats} lần liên tiếp"
        if self.kind == "stalled_clock":
            return (
                f"{self.repeats} từ cuối nằm cùng một mốc thời gian — "
                "máy sinh ra chứ không phải nghe được"
            )
        if self.kind == "low_prob_tail":
            return f"{self.repeats} từ cuối bản chép lời có độ tin cậy gần bằng 0"
        return (
            f"từ {self.token!r} lặp {self.repeats} lần liên tiếp, "
            f"chiếm {self.share:.0%} bản chép lời"
        )


def _normalise(text: str) -> str:
    return text.strip().strip(".,!?;:").lower()


def _phrase_loop(tokens: list[str]) -> tuple[int, int, str] | None:
    """Find a phrase repeated back to back at least MIN_PHRASE_REPEATS times.

    Returns (start index of the second occurrence, repeat count, the phrase) --
    the first occurrence is kept, because a speaker who said it once probably
    did say it once.

    Longest phrase first: a loop over "keep the classroom for discussion and
    practice" also contains a loop over "the classroom", and reporting the short
    version would cut in the wrong place.
    """
    n = len(tokens)
    for k in range(MAX_PHRASE_LEN, MIN_PHRASE_LEN - 1, -1):
        if n < k * MIN_PHRASE_REPEATS:
            continue
        for start in range(n - k * MIN_PHRASE_REPEATS + 1):
            phrase = tokens[start : start + k]
            if not all(phrase):
                continue
            repeats = 1
            while tokens[start + repeats * k : start + (repeats + 1) * k] == phrase:
                repeats += 1
            if repeats >= MIN_PHRASE_REPEATS:
                return start + k, repeats, " ".join(phrase)
    return None


def _stalled_clock(words: list[Word]) -> int | None:
    """Index where a run of words stops advancing in time, or None.

    Looks for the LAST such run: a recogniser that stalls usually stalls at the
    end, and cutting at the last stall keeps any earlier speech that genuinely
    was fast.
    """
    n = len(words)
    i = n - 1
    best: int | None = None
    while i > 0:
        end = i
        start = i
        while start > 0:
            span = words[end].end_s - words[start - 1].start_s
            count = end - start + 2
            if span / max(count, 1) > MAX_STALLED_S_PER_WORD:
                break
            start -= 1
        if end - start + 1 >= MIN_STALLED_RUN:
            best = start
            break
        i -= 1
    return best


def _low_prob_tail(words: list[Word]) -> int:
    """How many words at the very end came back with a near-zero probability."""
    run = 0
    for w in reversed(words):
        if w.prob is not None and w.prob <= TAIL_LOW_PROB:
            run += 1
        else:
            break
    return run


def detect_repetition(words: list[Word]) -> RepetitionFinding:
    """Find a degenerate repetition loop and where the real speech stops.

    Returns the index where the trustworthy part ends, so the caller can keep
    what the speaker actually said and discard the loop -- rather than throwing
    away a whole submission because of a tail the person never spoke.
    """
    if not words:
        return RepetitionFinding(False, None, 0, 0.0, 0)

    tokens = [_normalise(w.text) for w in words]

    # Longest run of one token repeated consecutively.
    worst_token, worst_run, worst_start = None, 1, 0
    run_token, run_len, run_start = tokens[0], 1, 0
    for i in range(1, len(tokens)):
        if tokens[i] and tokens[i] == run_token:
            run_len += 1
        else:
            if run_len > worst_run:
                worst_token, worst_run, worst_start = run_token, run_len, run_start
            run_token, run_len, run_start = tokens[i], 1, i
    if run_len > worst_run:
        worst_token, worst_run, worst_start = run_token, run_len, run_start

    counts = Counter(t for t in tokens if t)
    top_token, top_count = counts.most_common(1)[0] if counts else (None, 0)
    share = top_count / len(tokens) if tokens else 0.0

    by_run = worst_run >= MAX_CONSECUTIVE_REPEATS
    by_share = len(tokens) >= MIN_WORDS_FOR_SHARE and share >= MAX_SINGLE_TOKEN_SHARE

    if not (by_run or by_share):
        # Second net, and the most reliable: the clock stopped advancing.
        stalled = _stalled_clock(words)
        if stalled is not None:
            return RepetitionFinding(
                detected=True,
                token=None,
                repeats=len(words) - stalled,
                share=share,
                keep_until_index=stalled,
                kind="stalled_clock",
            )

        # Third net: a whole phrase looping. Checked before the low-probability
        # tail because it cuts earlier and more precisely -- the loop usually
        # starts while the recogniser is still confident, and only degenerates
        # into gibberish afterwards.
        phrase = _phrase_loop(tokens)
        if phrase is not None:
            cut, repeats, text = phrase
            return RepetitionFinding(
                detected=True,
                token=text,
                repeats=repeats,
                share=share,
                keep_until_index=cut,
                kind="phrase",
            )

        # Third net: the recogniser kept going after the speaker stopped and
        # marked what it invented with a probability of about zero.
        tail = _low_prob_tail(words)
        if tail >= MIN_TAIL_LOW_PROB_RUN:
            return RepetitionFinding(
                detected=True,
                token=None,
                repeats=tail,
                share=share,
                keep_until_index=len(words) - tail,
                kind="low_prob_tail",
            )

        return RepetitionFinding(False, None, worst_run, share, len(words))

    # Keep everything before the loop starts. If the offender is spread out
    # rather than consecutive, fall back to the first occurrence of the run.
    keep_until = worst_start if by_run else len(words)
    return RepetitionFinding(
        detected=True,
        token=worst_token if by_run else top_token,
        repeats=worst_run,
        share=share,
        keep_until_index=max(keep_until, 0),
    )
