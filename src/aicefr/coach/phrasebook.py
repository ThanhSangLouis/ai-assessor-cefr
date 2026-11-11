"""The phrase book: phrases from the learner's upgraded answers, reviewed a few a day (D070).

Every upgraded answer (D069) comes with a few phrases worth using. Read once on
a report, they are gone by the next week; said again in a sentence of one's own
on spaced days, some of them stay. A card's words live in the upgrade they came
from (`response.coach_upgrade.phrases`); where it is in its reviews is a
`ReviewItem` of kind "phrase" in the learning store (D104), one per phrase, the
same box-and-due-day record the lesson words use. A phrase whose upgrade is
erased is no card any more, whatever its record says.

Scheduling is the Leitner system, five boxes with growing gaps. Remembered
moves a card one box up; forgotten sends it back to the first box, due the
next day. The learner judges themselves -- nothing here listens to the
recording -- and the screen says so.
"""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta

from aicefr.practice.streak import LOCAL_TZ

# Days until the next review once a card is in that box. Box 0 is new: due now.
INTERVAL_DAYS = (0, 1, 3, 7, 16, 35)
LAST_BOX = len(INTERVAL_DAYS) - 1
# A card in this box or higher is counted as learned.
LEARNED_BOX = 3
PER_DAY = 5

_SENTENCE = re.compile(r"(?<=[.!?])\s+")


def key_of(phrase: str) -> str:
    """One card per phrase, however the model capitalised or spaced it."""
    return " ".join(phrase.lower().split())


def example_of(phrase: str, upgraded: str) -> str:
    """The sentence of the upgraded answer that uses the phrase, or nothing."""
    k = key_of(phrase)
    return next((s.strip() for s in _SENTENCE.split(upgraded or "") if k in key_of(s)), "")


def _day(stamp: str | None, fallback: date) -> str:
    """The day part of a stored time, or `fallback` when there is none."""
    return (stamp or "")[:10] or fallback.isoformat()


def cards(upgrades: list[dict], states: dict[str, dict], today: date) -> list[dict]:
    """One card per distinct phrase, from upgrades given oldest first.

    The same phrase suggested twice is one card, with the example and meaning
    of the first. `states` is each reviewed phrase's record by key (box, due
    day); a phrase never reviewed is in box 0, due from the day it was offered.
    """
    out: dict[str, dict] = {}
    for u in upgrades:
        for p in u.get("phrases") or []:
            phrase = (p.get("phrase") or "").strip()
            if not phrase:
                continue
            k = key_of(phrase)
            if k in out:
                continue
            state = states.get(k) or {}
            out[k] = {
                "key": k,
                "phrase": phrase,
                "meaning_vi": p.get("meaning_vi") or "",
                "example": example_of(phrase, u.get("upgraded") or ""),
                "response_id": u["response_id"],
                "box": int(state.get("box") or 0),
                "due": state.get("due") or _day(u.get("created_at"), today),
            }
    return list(out.values())


def due_today(all_cards: list[dict], today: date, limit: int = PER_DAY) -> list[dict]:
    """At most `limit` cards whose day has come, the longest waiting first."""
    due = [c for c in all_cards if c["due"] <= today.isoformat()]
    return sorted(due, key=lambda c: (c["due"], c["box"]))[:limit]


def reviewed(card: dict, remembered: bool, today: date) -> dict:
    """The card's box and due day after one review."""
    box = min(card["box"] + 1, LAST_BOX) if remembered else 1
    return {"box": box, "due": (today + timedelta(days=INTERVAL_DAYS[box])).isoformat()}


def summary(all_cards: list[dict], today: date) -> dict:
    return {
        "total": len(all_cards),
        "due_count": sum(1 for c in all_cards if c["due"] <= today.isoformat()),
        "learned": sum(1 for c in all_cards if c["box"] >= LEARNED_BOX),
        "per_day": PER_DAY,
    }


def today() -> date:
    """The learner's day: Vietnam time, as the lesson reviews count it."""
    return datetime.now(LOCAL_TZ).date()
