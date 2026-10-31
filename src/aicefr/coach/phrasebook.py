"""The phrase book: phrases from the learner's upgraded answers, reviewed a few a day (D070).

Every upgraded answer (D069) comes with a few phrases worth using. Read once on
a report, they are gone by the next week; said again in a sentence of one's own
on spaced days, some of them stay. This module keeps no store of its own: the
phrases and their review state live inside the upgrade they came from
(`response.coach_upgrade.phrases`), so erasing a response erases its cards.

Scheduling is the Leitner system, five boxes with growing gaps. Remembered
moves a card one box up; forgotten sends it back to the first box, due the
next day. The learner judges themselves -- nothing here listens to the
recording -- and the screen says so.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta

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


def _iso(t: datetime) -> str:
    return t.astimezone(UTC).isoformat(timespec="seconds")


def cards(upgrades: list[dict], now: datetime) -> list[dict]:
    """One card per distinct phrase, from upgrades given oldest first.

    The same phrase suggested twice is one card: the state of the occurrence
    reviewed most recently wins, the example and meaning of the first stay.
    """
    out: dict[str, dict] = {}
    for u in upgrades:
        for p in u.get("phrases") or []:
            phrase = (p.get("phrase") or "").strip()
            if not phrase:
                continue
            k = key_of(phrase)
            card = out.get(k)
            if card is None:
                card = out[k] = {
                    "key": k,
                    "phrase": phrase,
                    "meaning_vi": p.get("meaning_vi") or "",
                    "example": example_of(phrase, u.get("upgraded") or ""),
                    "response_id": u["response_id"],
                    "box": 0,
                    "due": u.get("created_at") or _iso(now),
                    "reviews": 0,
                    "reviewed_at": None,
                }
            if (p.get("reviewed_at") or "") > (card["reviewed_at"] or ""):
                card.update(
                    box=int(p.get("box") or 0),
                    due=p.get("due") or card["due"],
                    reviews=int(p.get("reviews") or 0),
                    reviewed_at=p["reviewed_at"],
                )
    return list(out.values())


def due_today(all_cards: list[dict], now: datetime, limit: int = PER_DAY) -> list[dict]:
    """At most `limit` cards whose day has come, the longest waiting first."""
    stamp = _iso(now)
    due = [c for c in all_cards if (c["due"] or "") <= stamp]
    return sorted(due, key=lambda c: (c["due"] or "", c["box"]))[:limit]


def reviewed(card: dict, remembered: bool, now: datetime) -> dict:
    """The card's state after one review."""
    box = min(card["box"] + 1, LAST_BOX) if remembered else 1
    return {
        "box": box,
        "due": _iso(now + timedelta(days=INTERVAL_DAYS[box])),
        "reviews": card["reviews"] + 1,
        "reviewed_at": _iso(now),
    }


def apply(phrases: list[dict], key: str, state: dict) -> list[dict]:
    """The phrase list of one upgrade with `state` set on every entry for `key`."""
    return [{**p, **state} if key_of(p.get("phrase") or "") == key else p for p in phrases]


def summary(all_cards: list[dict], now: datetime) -> dict:
    return {
        "total": len(all_cards),
        "due_count": sum(1 for c in all_cards if (c["due"] or "") <= _iso(now)),
        "learned": sum(1 for c in all_cards if c["box"] >= LEARNED_BOX),
        "per_day": PER_DAY,
    }


def now_utc() -> datetime:
    return datetime.now(UTC)
