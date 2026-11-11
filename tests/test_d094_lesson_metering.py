"""D094: a recording on the lesson path is metered, with free recordings each day and a cap.

The ledger on its own first:

* a recording takes a place among the day's (Vietnam time); the first places
  of a day are free, the others hold their price -- the month's free runs
  first, then the wallet -- and past the cap nothing more is measured;
* a recording that gets no result gives its place and its runs back, so a
  silence or a crash never uses up a free recording;
* a new day starts from nothing, and a request from the day before never
  takes the wallet back a day; twelve recordings at once never overrun the
  free places, the cap or the wallet.

Then the application: the five recording endpoints of the lesson path go
through it, a refusal measures nothing, the charge follows the speech, the
learner reads the price and what is left today, an administrator sets the
three numbers -- and with metering off nothing is held, counted or refused
(BR-29, BR-30).
"""

from __future__ import annotations

import inspect
import threading

import pytest
from dbutil import email_of
from fastapi import HTTPException
from test_billing import boot
from test_d089_drill import take, with_words
from test_lessons_integration import (
    KEYWORDS,
    SAMPLE,
    account_id,
    encode,
    login_as,
    pcm,
    record,
    submit_assessment,
    wav,
)

from aicefr.metering.pricing import DEFAULT_PRICES, PriceList, lesson_units
from aicefr.services.core.learning import drill_api, lessons_api
from aicefr.services.core.metering.facade import MeteringFacade
from aicefr.storage.audit_repository import AuditLog
from aicefr.storage.metering_repository import (
    DailyCapReached,
    InsufficientCredits,
    LedgerState,
    MeteredAction,
    MeteringRepository,
)

pytestmark = pytest.mark.integration

DAY = "2026-11-07"
NEXT_DAY = "2026-11-08"
MINUTE = lesson_units(DEFAULT_PRICES, 60.0)  # 100: a tenth of a run
# What the administrator's form sent before D094.
PRICE_KEYS = ("first_minute_runs", "extra_minute_runs", "upgrade_runs", "passage_runs",
              "idpoint_per_run", "free_runs", "packs")  # fmt: skip


@pytest.fixture
def ledger(tmp_path) -> MeteringRepository:
    return MeteringRepository(tmp_path / "metering.db")


def hold(ledger, key: str, units: int = MINUTE, day: str = DAY, free: int = 5, cap: int = 30):
    return ledger.hold_lesson("a1", key, units, day, free, cap)


# ================================================================= the ledger


def test_the_first_recordings_of_a_day_are_free_and_hold_nothing(ledger):
    entries = [hold(ledger, f"k{i}") for i in range(5)]
    assert [(e["held"], e["free_slot"], e["day"]) for e in entries] == [(0, True, DAY)] * 5
    assert ledger.lesson_today("a1", DAY) == {"used": 5, "free_used": 5}
    assert ledger.balance("a1") == {"wallet": 0, "free_left": 3000}  # the month's runs untouched


def test_past_the_free_ones_the_months_free_runs_pay_first_then_the_wallet(ledger):
    ledger.grant("a1", 150, "admin", "r1", None)
    for i in range(5):
        hold(ledger, f"free-{i}")
    sixth = hold(ledger, "k6")
    assert (sixth["held"], sixth["free_slot"], sixth["from_free"]) == (MINUTE, False, MINUTE)
    for i in range(29):  # the month's three runs go a tenth at a time
        hold(ledger, f"paid-{i}", free=5, cap=100)
    assert ledger.balance("a1") == {"wallet": 150, "free_left": 0}
    from_wallet = hold(ledger, "k-wallet", free=5, cap=100)
    assert (from_wallet["from_free"], from_wallet["from_wallet"]) == (0, MINUTE)
    assert ledger.balance("a1") == {"wallet": 50, "free_left": 0}


def test_no_runs_left_refuses_and_gives_the_place_back(ledger):
    ledger = MeteringRepository(ledger.db_path, free_units=0)
    hold(ledger, "free", free=1)
    with pytest.raises(InsufficientCredits) as refused:
        hold(ledger, "paid", free=1)
    assert (refused.value.needed, refused.value.available) == (MINUTE, 0)
    assert ledger.lesson_today("a1", DAY) == {"used": 1, "free_used": 1}
    assert ledger.entry("paid", MeteredAction.LESSON) is None


def test_past_the_cap_nothing_more_is_counted_or_taken(ledger):
    for i in range(3):
        hold(ledger, f"k{i}", free=1, cap=3)
    with pytest.raises(DailyCapReached) as full:
        hold(ledger, "k3", free=1, cap=3)
    assert full.value.cap == 3
    assert ledger.lesson_today("a1", DAY) == {"used": 3, "free_used": 1}
    assert ledger.balance("a1")["free_left"] == 3000 - 2 * MINUTE
    assert ledger.entry("k3", MeteredAction.LESSON) is None


def test_a_recording_with_no_result_gives_its_place_and_runs_back(ledger):
    free = hold(ledger, "free", free=1)
    hold(ledger, "paid", free=1)
    assert ledger.balance("a1")["free_left"] == 3000 - MINUTE
    ledger.settle("free", MeteredAction.LESSON, result=False)
    ledger.settle("paid", MeteredAction.LESSON, result=False)
    assert ledger.lesson_today("a1", DAY) == {"used": 0, "free_used": 0}
    assert ledger.balance("a1")["free_left"] == 3000
    assert ledger.entry(free["key"], MeteredAction.LESSON)["state"] == LedgerState.RELEASED.value
    # The free place came back: the next recording is free again.
    assert hold(ledger, "again", free=1)["free_slot"] is True


def test_a_measured_recording_keeps_its_place_and_pays_what_was_said(ledger):
    hold(ledger, "free", free=1)
    paid = hold(ledger, "long", units=3 * MINUTE, free=1)  # a 150-second step holds three minutes
    ledger.settle("free", MeteredAction.LESSON, result=True, charge=MINUTE)
    ledger.settle("long", MeteredAction.LESSON, result=True, charge=MINUTE)  # 40 s said
    free_entry = ledger.entry("free", MeteredAction.LESSON)
    assert (free_entry["state"], free_entry["charged"]) == ("charged", 0)  # free stays free
    paid_entry = ledger.entry(paid["key"], MeteredAction.LESSON)
    assert (paid_entry["state"], paid_entry["charged"]) == ("charged", MINUTE)
    assert ledger.balance("a1")["free_left"] == 3000 - MINUTE
    assert ledger.lesson_today("a1", DAY) == {"used": 2, "free_used": 1}


def test_holding_the_same_key_twice_counts_once(ledger):
    first = hold(ledger, "k")
    again = hold(ledger, "k")
    assert first["entry_id"] == again["entry_id"]
    assert ledger.lesson_today("a1", DAY) == {"used": 1, "free_used": 1}


def test_a_new_day_starts_afresh_and_yesterday_never_comes_back(ledger):
    for i in range(3):
        hold(ledger, f"k{i}", free=2, cap=3)
    with pytest.raises(DailyCapReached):
        hold(ledger, "late", free=2, cap=3)
    tomorrow = hold(ledger, "k-tomorrow", day=NEXT_DAY, free=2, cap=3)
    assert (tomorrow["day"], tomorrow["free_slot"]) == (NEXT_DAY, True)
    # A request computed a moment before midnight counts in the new day.
    late = hold(ledger, "k-late", day=DAY, free=2, cap=3)
    assert late["day"] == NEXT_DAY
    assert ledger.lesson_today("a1", NEXT_DAY) == {"used": 2, "free_used": 2}
    # Giving back yesterday's recording does not touch today's count.
    ledger.settle("k0", MeteredAction.LESSON, result=False)
    assert ledger.lesson_today("a1", NEXT_DAY) == {"used": 2, "free_used": 2}


def _at_once(n: int, go) -> tuple[list[int], list[Exception]]:
    taken, refused = [], []

    def run(i: int) -> None:
        try:
            go(i)
            taken.append(i)
        except (DailyCapReached, InsufficientCredits) as e:
            refused.append(e)

    threads = [threading.Thread(target=run, args=(i,)) for i in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return taken, refused


def test_twelve_recordings_at_once_never_overrun_the_free_places_or_the_wallet(ledger):
    ledger = MeteringRepository(ledger.db_path, free_units=0)
    ledger.grant("a1", 2 * MINUTE, "admin", "r1", None)
    taken, refused = _at_once(12, lambda i: hold(ledger, f"k{i}", free=5, cap=30))
    assert (len(taken), len(refused)) == (7, 5)  # five free, two paid
    assert all(isinstance(e, InsufficientCredits) for e in refused)
    assert ledger.lesson_today("a1", DAY) == {"used": 7, "free_used": 5}
    assert ledger.balance("a1") == {"wallet": 0, "free_left": 0}


def test_twelve_recordings_at_once_never_overrun_the_cap(ledger):
    ledger.grant("a1", 100 * MINUTE, "admin", "r1", None)
    taken, refused = _at_once(12, lambda i: hold(ledger, f"k{i}", free=2, cap=6))
    assert (len(taken), len(refused)) == (6, 6)
    assert all(isinstance(e, DailyCapReached) for e in refused)
    assert ledger.lesson_today("a1", DAY) == {"used": 6, "free_used": 2}


# ================================================================= the facade


@pytest.fixture
def facade(ledger, tmp_path, monkeypatch) -> MeteringFacade:
    monkeypatch.setattr(MeteringFacade, "today", staticmethod(lambda: DAY))
    return MeteringFacade(ledger, AuditLog(tmp_path / "metering.db", "metering"), enabled=True)


def test_the_charge_follows_the_speech_not_the_steps_limit(facade, ledger):
    for i in range(5):
        assert facade.hold_lesson(account_id="a1", key=f"free-{i}", max_seconds=30) is None
    assert facade.hold_lesson(account_id="a1", key="k", max_seconds=150) is None
    assert ledger.entry("k", MeteredAction.LESSON)["held"] == 3 * MINUTE
    facade.settle_lesson(key="k", result=True, speaking_seconds=61.0)
    assert ledger.entry("k", MeteredAction.LESSON)["charged"] == 2 * MINUTE
    assert ledger.balance("a1")["free_left"] == 3000 - 2 * MINUTE


def test_the_facade_refuses_as_data_with_the_status_to_answer(ledger, tmp_path, monkeypatch):
    monkeypatch.setattr(MeteringFacade, "today", staticmethod(lambda: DAY))
    poor = MeteringFacade(
        MeteringRepository(ledger.db_path, free_units=0),
        AuditLog(tmp_path / "metering.db", "metering"),
        True,
        PriceList(lesson_free_per_day=0, lesson_daily_cap=1),
    )
    refused = poor.hold_lesson(account_id="a2", key="k1", max_seconds=30)
    assert refused["status"] == 402
    assert refused["message"].startswith("Bản ghi này cần 0.1 lượt")
    assert "Nạp thêm IDPoint" in refused["message"]
    poor.store.grant("a2", MINUTE, "admin", "r", None)
    assert poor.hold_lesson(account_id="a2", key="k2", max_seconds=30) is None
    full = poor.hold_lesson(account_id="a2", key="k3", max_seconds=30)
    assert full["status"] == 429 and "1 bản ghi" in full["message"]


def test_the_quote_says_what_is_left_today(facade):
    q = facade.lesson_quote(account_id="a1")
    assert q == {
        "minute_runs": 0.1,
        "minute_idpoint": 200,
        "free_per_day": 5,
        "free_locked": False,
        "free_left_today": 5,
        "daily_cap": 30,
        "left_today": 30,
        "runs_left": 3.0,
    }
    for i in range(6):
        facade.hold_lesson(account_id="a1", key=f"k{i}", max_seconds=30)
    q = facade.lesson_quote(account_id="a1")
    assert (q["free_left_today"], q["left_today"], q["runs_left"]) == (0, 24, 2.9)


def test_with_metering_off_the_facade_holds_counts_and_refuses_nothing(ledger, tmp_path):
    off = MeteringFacade(ledger, AuditLog(tmp_path / "metering.db", "metering"), enabled=False)
    assert off.hold_lesson(account_id="a1", key="k", max_seconds=30) is None
    off.settle_lesson(key="k", result=True, speaking_seconds=10.0)
    assert off.lesson_quote(account_id="a1") is None
    assert ledger.history("a1") == [] and ledger.lesson_today("a1", DAY)["used"] == 0


# ================================================================= the application


@pytest.fixture
def metered(tmp_path, monkeypatch):
    monkeypatch.setattr(MeteringFacade, "today", staticmethod(lambda: DAY))
    return boot(
        tmp_path,
        monkeypatch,
        AICEFR_METERING="on",
        AICEFR_LESSON_FREE_PER_DAY="2",
        AICEFR_LESSON_DAILY_CAP="4",
    )


def lesson_entries(m, name: str) -> list[dict]:
    # The history is newest first (to the second, then by insertion): oldest first here.
    rows = m.core_parts.state["metering"].history(account_id(m, name), limit=100)
    return [e for e in reversed(rows) if e["action"] == "lesson"]


def test_steps_are_free_then_charged_by_speech_then_capped(metered):
    m = metered
    student = login_as(m, "SV-L01")
    quote = student.get("/api/v1/me/credits/lesson").json()
    assert quote == {
        "metering": True,
        "minute_runs": 0.1,
        "minute_idpoint": 200,
        "free_per_day": 2,
        "free_left_today": 2,
        "free_locked": False,
        "daily_cap": 4,
        "left_today": 4,
        "runs_left": 3.0,
    }
    for _ in range(4):
        record(student, SAMPLE, KEYWORDS, audio=wav(4.5))
    entries = lesson_entries(m, "SV-L01")
    assert [(e["state"], e["free_slot"], e["charged"]) for e in entries] == [
        ("charged", True, 0),
        ("charged", True, 0),
        ("charged", False, MINUTE),  # 4.5 seconds said: one started minute
        ("charged", False, MINUTE),
    ]
    attempts = len(m.lessons.attempts())
    full = record(student, SAMPLE, KEYWORDS, audio=wav(4.5), expect=429)
    assert "4 bản ghi" in full["detail"]
    assert len(m.lessons.attempts()) == attempts  # refused before anything was measured
    credits = student.get("/api/v1/me/credits").json()
    assert credits["free_runs_left"] == 2.8
    assert credits["lesson"]["left_today"] == 0
    shown = [(h["action"], h["free_slot"]) for h in credits["history"]]
    assert shown.count(("lesson", True)) == 2 and shown.count(("lesson", False)) == 2


def test_a_recording_nothing_could_be_measured_from_costs_nothing(metered):
    m = metered
    student = login_as(m, "SV-L02")
    rejected = record(student, SAMPLE, KEYWORDS, audio=encode(pcm(("tone", 0.5))))
    assert rejected["result"]["measured"] is False
    [entry] = lesson_entries(m, "SV-L02")
    assert (entry["state"], entry["charged"]) == ("released", 0)
    quote = student.get("/api/v1/me/credits/lesson").json()
    assert (quote["free_left_today"], quote["left_today"]) == (2, 4)  # the place came back


def test_a_failure_of_the_speech_service_gives_everything_back(metered, monkeypatch):
    m = metered
    student = login_as(m, "SV-L03", raise_errors=False)

    def down(*args, **kwargs):
        raise HTTPException(503, "chưa liên lạc được máy chấm, hãy thử lại sau ít phút")

    monkeypatch.setattr(lessons_api, "_measure", down)
    record(student, SAMPLE, KEYWORDS, expect=503)
    [entry] = lesson_entries(m, "SV-L03")
    assert entry["state"] == "released"
    assert student.get("/api/v1/me/credits/lesson").json()["left_today"] == 4


def test_no_runs_left_is_a_402_and_a_top_up_lets_the_learner_go_on(metered):
    m = metered
    admin = login_as(m, "AD-L01", "admin")
    prices = admin.get("/api/v1/admin/prices").json()
    body = {k: prices[k] for k in PRICE_KEYS if k != "free_runs"}
    body.update(free_runs=0, lesson_minute_runs=0.2, lesson_free_per_day=1, lesson_daily_cap=10)
    saved = admin.put("/api/v1/admin/prices", json=body)
    assert saved.status_code == 200, saved.text
    assert (saved.json()["lesson_minute_runs"], saved.json()["lesson_daily_cap"]) == (0.2, 10)

    student = login_as(m, "SV-L04")
    record(student, SAMPLE, KEYWORDS, audio=wav(4.5))  # the day's one free recording
    attempts = len(m.lessons.attempts())
    poor = record(student, SAMPLE, KEYWORDS, audio=wav(4.5), expect=402)
    assert "Nạp thêm IDPoint" in poor["detail"]
    assert len(m.lessons.attempts()) == attempts
    granted = admin.post(
        "/api/v1/admin/credits/grant",
        json={"email": email_of("SV-L04"), "runs": 1, "reference": "t1"},
    )
    assert granted.status_code == 200, granted.text
    record(student, SAMPLE, KEYWORDS, audio=wav(4.5))
    assert student.get("/api/v1/me/credits").json()["wallet_runs"] == 0.8


def test_a_drill_take_is_a_lesson_recording_too(metered):
    m = metered
    student = login_as(m, "SV-L05")
    rid = submit_assessment(student)
    with_words(m, rid)
    r = take(student, rid, "three")
    assert r.status_code == 200, r.text
    [entry] = lesson_entries(m, "SV-L05")
    assert entry["free_slot"] is True


def test_every_recording_endpoint_of_the_lesson_path_is_metered():
    """The five handlers that send a learner's recording to the speech service."""
    handlers = [
        lessons_api.learn_attempt,
        lessons_api.retell_round,
        lessons_api.learn_review_attempt,
        drill_api.drill_take,
        drill_api.passage_take,
    ]
    for handler in handlers:
        source = inspect.getsource(handler)
        assert "run_in_threadpool(_metered, account," in source, handler.__name__
    # And nothing else measures a learner's recording without it.
    for module in (lessons_api, drill_api):
        source = inspect.getsource(module)
        measured = source.count("_measure(") - source.count("def _measure(")
        staff = 2 if module is lessons_api else 0  # a teacher's preview and model audio
        assert measured == staff + len([h for h in handlers if h.__module__ == module.__name__]), (
            module.__name__
        )


def test_a_teachers_preview_is_never_charged(metered):
    m = metered
    teacher = login_as(m, "GV-L01", "teacher")
    r = teacher.post(
        "/api/v1/teach/preview",
        files={"audio": ("step.wav", wav(), "audio/wav")},
        data={"lesson_id": SAMPLE, "step_id": KEYWORDS},
    )
    assert r.status_code == 200, r.text
    assert m.core_parts.state["metering"].history(account_id(m, "GV-L01")) == []


def test_a_price_list_saved_before_d094_keeps_the_defaults(metered):
    m = metered
    store = m.core_parts.state["metering"]
    store.set_price_list(  # what an administrator saved before this decision
        {"first_minute_runs": 1.0, "extra_minute_runs": 0.7, "upgrade_runs": 0.3,
         "passage_runs": 0.1, "idpoint_per_run": 2000, "free_runs": 3.0,
         "packs": [{"runs": 10, "price_vnd": 19000}]},
    )  # fmt: skip
    student = login_as(m, "SV-L06")
    quote = student.get("/api/v1/me/credits/lesson").json()
    # The deployment's settings (AICEFR_LESSON_*: 2 and 4 here), not zeros.
    assert (quote["minute_runs"], quote["free_per_day"], quote["daily_cap"]) == (0.1, 2, 4)


def test_the_admin_form_refuses_impossible_lesson_numbers(metered):
    admin = login_as(metered, "AD-L02", "admin")
    prices = admin.get("/api/v1/admin/prices").json()
    body = {k: prices[k] for k in PRICE_KEYS}
    too_many_free = {**body, "lesson_free_per_day": 40, "lesson_daily_cap": 30}
    assert admin.put("/api/v1/admin/prices", json=too_many_free).status_code == 422
    no_cap = {**body, "lesson_daily_cap": 0}
    assert admin.put("/api/v1/admin/prices", json=no_cap).status_code == 422


def test_with_metering_off_lessons_are_never_held_counted_or_refused(tmp_path, monkeypatch):
    m = boot(tmp_path, monkeypatch, AICEFR_LESSON_DAILY_CAP="1", AICEFR_LESSON_FREE_PER_DAY="0")
    student = login_as(m, "SV-L07")
    for _ in range(3):
        record(student, SAMPLE, KEYWORDS, audio=wav(4.5))
    assert m.core_parts.state["metering"].history(account_id(m, "SV-L07")) == []
    assert student.get("/api/v1/me/credits/lesson").json() == {"metering": False}
