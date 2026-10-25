"""One main piece of advice after each attempt, and a comparison with your own last try. D023.

Both choices follow evidence, not taste:

* **ONE piece of advice per attempt, chosen by an ordered rule.** The first
  mission not met, in the task's own mission order. Information-rich feedback
  works far better than reward/punishment feedback (Wisniewski et al. 2020,
  d = 0.99 versus 0.24), but ten pieces of advice at once means the learner
  follows none of them. Each piece points at one concrete place: which second,
  which words are still missing.
* **Compare with YOUR OWN last attempt, not with classmates.** Self-referenced
  (ipsative, Hughes 2011) feedback keeps the learners at the bottom of the
  class motivated; a leaderboard does not.
"""

from __future__ import annotations

from aicefr.contracts import Mission, MissionCheck, MissionKind, PracticeResult
from aicefr.formatting import vi_decimal as _num


def _clock(seconds: float | None) -> str:
    if seconds is None:
        return "?"
    m, s = divmod(int(seconds), 60)
    return f"{m}:{s:02d}"


def _advice(check: MissionCheck, mission: Mission | None) -> str:
    v = check.measured or 0.0
    target = check.target
    if check.kind is MissionKind.SPEAK_SECONDS:
        return (
            f"Bạn nói {_num(v)} giây, còn thiếu {_num(max(0.0, target - v))} giây. Lần sau "
            "thêm một ví dụ hoặc một lý do nữa trước khi kết thúc."
        )
    if check.kind is MissionKind.MAX_PAUSE:
        at = check.hits[0].start_s if check.hits else None
        return (
            f"Khoảng lặng dài nhất {_num(v)} giây, bắt đầu ở {_clock(at)}. Khi bí ý, nói "
            "“well…” hoặc “let me think…” để giữ mạch thay vì im lặng."
        )
    if check.kind is MissionKind.USE_WORDS:
        used = {h.text for h in check.hits}
        unused = [w for w in (mission.words if mission else ()) if w not in used][:3]
        hint = f" Lần sau thử thêm: {', '.join(unused)}." if unused else ""
        return f"Đếm được {int(v)} trên {int(target)} từ cần dùng.{hint}"
    if check.kind is MissionKind.UNIQUE_WORDS:
        return (
            f"Bạn dùng {int(v)} từ khác nhau, mục tiêu {int(target)}. Thêm chi tiết mới "
            "(màu sắc, cảm xúc, lý do) thay vì nhắc lại từ đã nói."
        )
    if check.kind is MissionKind.PAST_VERBS:
        return (
            f"Đếm được {int(v)} động từ quá khứ, mục tiêu {int(target)}. Kể thêm việc bạn "
            "đã làm: went, ate, watched, met."
        )
    if check.kind is MissionKind.CONDITIONALS:
        return (
            f"Đếm được {int(v)} câu điều kiện, mục tiêu {int(target)}. Thêm một câu dạng "
            "“If I had…, I would…”."
        )
    if check.kind is MissionKind.READ_ALOUD:
        missed = ", ".join(h.text for h in check.hits[:5])
        return (
            f"Máy chưa nghe ra: {missed}. Đọc chậm lại ở những từ này và bật rõ âm cuối."
            if missed
            else "Đọc chậm và rõ hơn một chút ở những câu dài."
        )
    return check.label  # pragma: no cover - every mission kind has advice above


def takeaway(result: PracticeResult, missions: tuple[Mission, ...]) -> str:
    """The main piece of advice for this attempt, from the first mission not met.

    `missions` are the missions of the task AS IT IS NOW; they are matched to
    the result by position and kind. If the bank changed the task after this
    attempt, the "words still missing" part is dropped rather than suggesting
    words from a different task.
    """
    for i, check in enumerate(result.checks):
        if check.met is False:
            mission = missions[i] if i < len(missions) else None
            if mission is not None and mission.kind is not check.kind:
                mission = None
            return _advice(check, mission)
    if result.completed is None:
        return (
            "Một số mục tiêu chưa đo được (xem lý do ở từng mục). Hãy thu ở nơi yên tĩnh, "
            "nói rõ và đủ dài rồi thử lại."
        )
    return (
        "Bạn đã hoàn thành mọi mục tiêu của nhiệm vụ này. Thử nhiệm vụ gợi ý tiếp theo, "
        "hoặc nói lại để rút ngắn khoảng lặng dài nhất."
    )


def previous_measures(
    current: PracticeResult, previous: PracticeResult | None
) -> list[float | None]:
    """The previous attempt's measurement on the same task, per mission of this attempt.

    Empty when there is no previous attempt, when the previous attempt could
    not measure that mission, or when the task changed its missions (a
    different kind at the same position): comparing against another mission
    would be a false comparison.
    """
    out: list[float | None] = []
    for i, check in enumerate(current.checks):
        prev = previous.checks[i] if previous and i < len(previous.checks) else None
        out.append(prev.measured if prev is not None and prev.kind is check.kind else None)
    return out
