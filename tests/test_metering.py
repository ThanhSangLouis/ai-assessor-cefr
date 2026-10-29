"""D049: the ledger of the metered channel, and its pages.

The ledger on its own first: free runs before the wallet, a hold that does not
fit takes nothing, one key is held and settled once, a result is charged for
what the recording lasted. Then the application with `AICEFR_METERING=on`, and
without it: the school deployment never holds or refuses anything (BR-29, BR-30).
"""

from __future__ import annotations

import threading

import pytest
from test_billing import boot
from test_lessons_integration import account_id, login_as, submit_assessment, wav

from aicefr.contracts import TaskPurpose
from aicefr.metering.pricing import (
    DEFAULT_PRICES,
    as_runs,
    hold_for,
    units_for,
    usage_of,
)
from aicefr.storage.metering_repository import (
    InsufficientCredits,
    LedgerState,
    MeteringRepository,
    cycle,
)

pytestmark = pytest.mark.integration


@pytest.fixture
def ledger(tmp_path) -> MeteringRepository:
    return MeteringRepository(tmp_path / "metering.db")


# ================================================================= the ledger


def test_free_runs_are_used_before_the_wallet(ledger):
    ledger.grant("a1", 5000, "admin", "r1", None)
    entry = ledger.hold("a1", TaskPurpose.ASSESSMENT, "resp-1", 4000)
    assert (entry["from_free"], entry["from_wallet"]) == (3000, 1000)
    assert ledger.balance("a1") == {"wallet": 4000, "free_left": 0}


def test_a_hold_beyond_free_and_wallet_is_refused_and_takes_nothing(ledger):
    ledger.grant("a1", 500, "admin", "r1", None)
    with pytest.raises(InsufficientCredits) as refused:
        ledger.hold("a1", TaskPurpose.ASSESSMENT, "resp-1", 5000)
    assert (refused.value.needed, refused.value.available) == (5000, 3500)
    assert ledger.balance("a1") == {"wallet": 500, "free_left": 3000}
    assert ledger.entry("resp-1", TaskPurpose.ASSESSMENT) is None


def test_holding_the_same_key_twice_takes_once(ledger):
    first = ledger.hold("a1", TaskPurpose.ASSESSMENT, "resp-1", 1000)
    again = ledger.hold("a1", TaskPurpose.ASSESSMENT, "resp-1", 1000)
    assert first["entry_id"] == again["entry_id"]
    assert ledger.free_left("a1") == 2000


def test_a_result_charges_what_was_used_and_returns_the_rest(ledger):
    ledger.grant("a1", 5000, "admin", "r1", None)
    ledger.hold("a1", TaskPurpose.ASSESSMENT, "long", 5000)  # 3000 free + 2000 wallet
    done = ledger.settle("long", TaskPurpose.ASSESSMENT, result=True, charge=2000)
    assert (done["state"], done["charged"]) == (LedgerState.CHARGED, 2000)
    # 3000 back, to the wallet first: 2000 from the wallet, then 1000 of the free runs.
    assert ledger.balance("a1") == {"wallet": 5000, "free_left": 1000}


def test_no_result_releases_everything(ledger):
    ledger.hold("a1", TaskPurpose.ASSESSMENT, "resp-1", 1000)
    done = ledger.settle("resp-1", TaskPurpose.ASSESSMENT, result=False)
    assert (done["state"], done["charged"]) == (LedgerState.RELEASED, 0)
    assert ledger.free_left("a1") == 3000


def test_settling_twice_changes_nothing(ledger):
    ledger.hold("a1", TaskPurpose.ASSESSMENT, "resp-1", 1000)
    ledger.settle("resp-1", TaskPurpose.ASSESSMENT, result=True, charge=1000)
    again = ledger.settle("resp-1", TaskPurpose.ASSESSMENT, result=False)
    assert (again["state"], again["charged"]) == (LedgerState.CHARGED, 1000)
    assert ledger.free_left("a1") == 2000


def test_stale_holds_are_released(ledger):
    ledger.hold("a1", TaskPurpose.ASSESSMENT, "resp-1", 1000)
    assert ledger.release_stale("9999-12-31T00:0:0+0:0") == ["resp-1"]
    assert ledger.entry("resp-1", TaskPurpose.ASSESSMENT)["state"] == LedgerState.RELEASED
    assert ledger.release_stale("9999-12-31T00:0:0+0:0") == []


def test_a_top_up_is_credited_once_per_reference(ledger):
    assert ledger.grant("a1", 2000, "netid", "stmt-7", None) is True
    assert ledger.grant("a1", 2000, "netid", "stmt-7", None) is False
    assert ledger.wallet("a1") == 2000
    with pytest.raises(ValueError):
        ledger.grant("a1", 0, "admin", "zero", None)


def test_concurrent_holds_never_overdraw(ledger):
    """Twelve submissions at once with three free runs and two paid: five go through."""
    ledger.grant("a1", 2000, "admin", "r1", None)
    taken, refused = [], []

    def submit(i: int) -> None:
        try:
            ledger.hold("a1", TaskPurpose.ASSESSMENT, f"resp-{i}", 1000)
            taken.append(i)
        except InsufficientCredits:
            refused.append(i)

    threads = [threading.Thread(target=submit, args=(i,)) for i in range(12)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert (len(taken), len(refused)) == (5, 7)
    assert ledger.balance("a1") == {"wallet": 0, "free_left": 0}


# ================================================================= the application


@pytest.fixture
def metered(tmp_path, monkeypatch):
    return boot(tmp_path, monkeypatch, AICEFR_METERING="on")


def test_with_metering_off_nothing_is_held_or_refused(tmp_path, monkeypatch):
    m = boot(tmp_path, monkeypatch)
    student = login_as(m, "SV-001")
    for _ in range(5):  # more than the free runs of a metered deployment
        submit_assessment(student)
    assert student.get("/api/v1/me/credits").json() == {"metering": False}
    assert m.core_parts.state["metering"].history(account_id(m, "SV-001")) == []


def test_a_submission_is_held_then_charged_and_shows_in_my_credits(metered):
    """The fake recogniser gives an estimate a teacher should confirm: a result, so charged."""
    m = metered
    student = login_as(m, "SV-001")
    rid = submit_assessment(student)  # 35 seconds: two windows of audio tokens
    report = m.repo.get(rid)
    assert report.assessment is not None
    entry = m.core_parts.state["metering"].entry(rid, TaskPurpose.ASSESSMENT)
    expected = units_for(DEFAULT_PRICES, TaskPurpose.ASSESSMENT, 35.0)  # one run
    assert (entry["state"], entry["charged"]) == (LedgerState.CHARGED, expected)
    # The tokens it used are kept with the charge, for the cost per request.
    assert (entry["input_tokens"], entry["usage_estimated"]) == (4500, True)
    assert entry["output_tokens"] == usage_of(35.0, None, len(report.asr.words)).output_tokens
    body = student.get("/api/v1/me/credits").json()
    assert body["metering"] is True and body["free_runs_left"] == as_runs(3000 - expected)
    assert body["one_minute"] == {"assessment": 1.0, "practice": 0.5}
    assert body["prices"]["idpoint_per_run"] == 2000
    assert (
        body["history"][0]["state"] == LedgerState.CHARGED and "entry_id" not in body["history"][0]
    )


def test_the_submission_screen_quotes_the_most_a_task_costs(metered):
    student = login_as(metered, "SV-001")
    q = student.get("/api/v1/me/credits/quote", params={"seconds": 90}).json()
    assert (q["runs"], q["idpoint"], q["free_runs_left"]) == (1.7, 3400, 3.0)
    assert student.get("/api/v1/me/credits/quote", params={"seconds": 0}).status_code == 422


def test_a_failed_scoring_releases_the_hold(metered):
    """The speech service reports a failure: nothing is charged, the free run comes back."""
    from aicefr.contracts import Response, ResponseStatus
    from aicefr.services.core.assessment import scoring

    m = metered
    login_as(m, "SV-001")
    who = account_id(m, "SV-001")
    m.repo.save(Response(response_id="r-fail", status=ResponseStatus.QUEUED, config_version="v1"),
                "SV-001", "P3", account_id=who)  # fmt: skip
    assert (
        m.core_parts.facade.metering.hold(
            account_id=who, action="assessment", key="r-fail", max_seconds=60
        )
        is None
    )
    held = hold_for(DEFAULT_PRICES, TaskPurpose.ASSESSMENT, 60)
    assert m.core_parts.state["metering"].free_left(who) == 3000 - held
    scoring.on_scoring({"response_id": "r-fail", "failed": "PROCESSING_INTERRUPTED"})
    assert m.repo.status_of("r-fail")["status"] == "FAILED"
    assert (
        m.core_parts.state["metering"].entry("r-fail", TaskPurpose.ASSESSMENT)["state"]
        == LedgerState.RELEASED
    )
    assert m.core_parts.state["metering"].free_left(who) == 3000


def test_a_submission_without_runs_left_is_refused_with_402(metered):
    m = metered
    student = login_as(m, "SV-001")
    ledger = m.core_parts.state["metering"]
    assert ledger._take_free(account_id(m, "SV-001"), cycle(), 3000) == 3000  # free runs spent
    before = m.repo.list_by_account(account_id(m, "SV-001"))
    r = student.post(
        "/api/v1/responses",
        files={"audio": ("answer.wav", wav(35.0), "audio/wav")},
        data={"task_id": "P3"},
    )
    assert r.status_code == 402, r.text
    assert "lượt" in r.json()["detail"]
    # Refused before anything was kept: no response, no recording left behind.
    assert m.repo.list_by_account(account_id(m, "SV-001")) == before
    assert not list((m.settings.upload_dir).glob("*.wav"))


def test_only_an_administrator_grants_runs(metered):
    m = metered
    login_as(m, "SV-001")
    admin = login_as(m, "QT-01", "admin")
    teacher = login_as(m, "GV-01", "teacher")
    body = {"pseudonym": "SV-001", "runs": 2, "reference": "phiếu-1"}
    assert teacher.post("/api/v1/admin/credits/grant", json=body).status_code == 403
    first = admin.post("/api/v1/admin/credits/grant", json=body).json()
    again = admin.post("/api/v1/admin/credits/grant", json=body).json()
    assert (first["credited"], again["credited"], again["wallet_runs"]) == (True, False, 2)
    assert (
        admin.post("/api/v1/admin/credits/grant", json={**body, "pseudonym": "SV-404"}).status_code
        == 404
    )


def test_the_metered_deployment_runs_no_research_study(metered):
    m = metered
    admin = login_as(m, "QT-01", "admin")
    r = admin.post("/api/v1/admin/studies", json={"name": "Không được chạy"})
    assert r.status_code == 409 and "tính lượt" in r.json()["detail"]


def test_granting_on_the_school_deployment_is_refused(tmp_path, monkeypatch):
    m = boot(tmp_path, monkeypatch)
    admin = login_as(m, "QT-01", "admin")
    r = admin.post(
        "/api/v1/admin/credits/grant",
        json={"pseudonym": "QT-01", "runs": 1, "reference": "x"},
    )
    assert r.status_code == 409
