"""Layer 2 -- INTEGRATION: blind double rating through the real app and database (D030).

Students submit synthetic recordings through the real pipeline (fake
recogniser), an administrator builds a batch, teachers rate through the API.
Where a test needs the machine to have produced a score, the score is written
into the response row first and the test says so: the fake recogniser's
transcript is too short to be scored, and what is under test here is what the
rating flow does with the machine's output, not the scorer.

Tests named after an acceptance criterion carry the name given in SRS section
3.9e (FR-61..FR-64).
"""

from __future__ import annotations

import csv
import importlib
import io
import json
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf
from dbutil import store
from fastapi.testclient import TestClient

from aicefr.storage.auth_repository import Role

pytestmark = pytest.mark.integration

PASSWORD = "matkhau-kiem-thu"
GOOD = {
    "criteria": {"range": 3, "accuracy": 3, "fluency": 3.5, "coherence": 3, "phonology": 3},
    "overall": 3.0,
    "band": "B1",
    "reason": "Ý rõ, ngập ngừng ở nửa sau.",
}


@pytest.fixture
def m(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from aicefr.api import main

    importlib.reload(main)
    return main


def login_as(m, pseudonym: str, role: str = "student") -> TestClient:
    m.app.state.auth_repo.create_account(pseudonym, PASSWORD, Role(role))
    c = TestClient(m.app)
    r = c.post("/api/v1/auth/login", json={"pseudonym": pseudonym, "password": PASSWORD})
    assert r.status_code == 200, r.text
    return c


def wav(seconds: float = 35.0, sr: int = 16_000) -> bytes:
    t = np.arange(int(sr * seconds)) / sr
    buf = io.BytesIO()
    sf.write(buf, (0.2 * np.sin(2 * np.pi * 220 * t)).astype(np.float32), sr, format="WAV")
    return buf.getvalue()


def submit(client: TestClient) -> str:
    r = client.post(
        "/api/v1/responses",
        files={"audio": ("answer.wav", wav(), "audio/wav")},
        data={"task_id": "P3"},
    )
    assert r.status_code == 202, r.text
    return r.json()["response_id"]


def machine_scored(m, response_id: str, score: float, band: str) -> None:
    """Arrange the machine's output: the fake recogniser's transcript is never scored.

    Written where the pipeline writes it, the stored report and the row, so a
    later teacher review records it as the "old" score like a real one would.
    """
    from aicefr.contracts import Assessment, Band

    report = m.repo.get(response_id)
    assessment = report.assessment or Assessment(model_version="test")
    report.assessment = assessment.model_copy(
        update={"overall_0_6": score, "overall_band": Band(band)}
    )
    store()["response"].update_one(
        {"response_id": response_id},
        {"$set": {"overall_0_6": score, "overall_band": band,
                  "report_json": report.model_dump_json()}},
    )  # fmt: skip


def account_id(m, pseudonym: str) -> str:
    return m.app.state.auth_repo.get_by_pseudonym(pseudonym)["account_id"]


def study(m, students: int = 3, raters: tuple[str, ...] = ("GV-01", "GV-02")):
    """Students with recordings, two (or more) teachers, an administrator."""
    rids = [submit(login_as(m, f"SV-{i:03d}")) for i in range(1, students + 1)]
    teachers = {name: login_as(m, name, "teacher") for name in raters}
    admin = login_as(m, "QT-01", "admin")
    return rids, teachers, admin


def new_batch(m, admin: TestClient, raters: tuple[str, ...] = ("GV-01", "GV-02"), **extra):
    body = {"name": "Đợt thử", "rater_ids": [account_id(m, r) for r in raters], **extra}
    r = admin.post("/api/v1/admin/ratings/batches", json=body)
    assert r.status_code == 200, r.text
    return r.json()


def sheets(teacher: TestClient) -> list[dict]:
    batches = teacher.get("/api/v1/rate/assignments").json()["batches"]
    return [item for b in batches for item in b["items"]]


def rate(teacher: TestClient, assignment_id: str, **changes) -> dict:
    body = {**GOOD, **changes}
    r = teacher.post(f"/api/v1/rate/assignments/{assignment_id}", json=body)
    assert r.status_code == 200, r.text
    return r.json()


def rate_all(teacher: TestClient, **changes) -> None:
    """Open each sheet, as a rater does, then submit it."""
    for item in sheets(teacher):
        if item["state"] != "done":
            teacher.get(f"/api/v1/rate/assignments/{item['assignment_id']}")
            rate(teacher, item["assignment_id"], **changes)


# ================================================================= batches (FR-61)


def test_a_batch_gives_every_eligible_response_two_raters_each_in_their_own_order(m):
    rids, teachers, admin = study(m)
    setup = admin.get("/api/v1/admin/ratings/setup").json()
    assert setup["eligible_new"] == 3
    assert {r["pseudonym"] for r in setup["raters"]} >= {"GV-01", "GV-02"}

    made = new_batch(m, admin, seed=42)
    assert made == {
        "batch_id": made["batch_id"],
        "responses": 3,
        "skipped_seen": 0,
        "raters": 2,
        "seed": 42,
    }
    orders = []
    for teacher in teachers.values():
        mine = sheets(teacher)
        assert sorted(i["position"] for i in mine) == [1, 2, 3]
        orders.append([i["assignment_id"] for i in mine])
    batch = admin.get("/api/v1/admin/ratings/batches").json()[0]
    assert batch["responses"] == 3 and batch["assignments"] == 6 and batch["done"] == 0
    assert admin.get("/api/v1/admin/ratings/setup").json()["eligible_new"] == 0
    assert m.audit(50)[0].action == "rating.batch_create"


def test_a_batch_needs_two_raters_and_something_to_rate(m):
    _, _, admin = study(m, students=0)
    batches = "/api/v1/admin/ratings/batches"
    one = {"name": "Đợt thử", "rater_ids": [account_id(m, "GV-01")]}
    assert admin.post(batches, json=one).status_code == 422
    student = login_as(m, "SV-050")
    with_student = {
        "name": "Đợt thử",
        "rater_ids": [account_id(m, "GV-01"), account_id(m, "SV-050")],
    }
    assert admin.post(batches, json=with_student).status_code == 422
    nothing = {"name": "Đợt rỗng", "rater_ids": [account_id(m, "GV-01"), account_id(m, "GV-02")]}
    r = admin.post(batches, json=nothing)
    assert r.status_code == 422 and "không có bài" in r.json()["detail"]
    assert student.get(batches).status_code == 403


# ================================================================= blind sheet (FR-62)


def test_the_rating_sheet_carries_no_pseudonym_response_id_or_machine_score(m):
    rids, teachers, admin = study(m, students=1)
    machine_scored(m, rids[0], 4.37, "B2")
    new_batch(m, admin)
    teacher = teachers["GV-01"]
    item = sheets(teacher)[0]
    r = teacher.get(f"/api/v1/rate/assignments/{item['assignment_id']}")
    assert r.status_code == 200
    sheet = r.json()
    assert set(sheet) == {
        "assignment_id",
        "batch",
        "position",
        "total",
        "adjudication",
        "task",
        "audio_url",
        "seen_machine",
        "rating",
        "next_assignment_id",
    }
    assert sheet["seen_machine"] is False
    raw = json.dumps(sheet, ensure_ascii=False)
    for leak in (
        rids[0],
        "SV-001",
        "4.37",
        "B2",
        "assessment",
        "evidence",
        "comments",
        "overall_0_6",
    ):
        assert leak not in raw, leak
    assert sheet["task"]["prompt_text"]
    audio = teacher.get(sheet["audio_url"])
    assert audio.status_code == 200
    assert rids[0] not in audio.headers.get("content-disposition", "")
    assert "bai-1.wav" in audio.headers["content-disposition"]
    entry = next(e for e in m.audit(50) if e.action == "AUDIO_ACCESS")
    assert entry.detail == "blind_rating"


def test_a_rater_cannot_open_another_raters_sheet(m):
    _, teachers, admin = study(m, students=1, raters=("GV-01", "GV-02", "GV-03"))
    new_batch(m, admin, raters=("GV-01", "GV-02"))
    theirs = sheets(teachers["GV-01"])[0]["assignment_id"]
    outsider = teachers["GV-03"]
    assert outsider.get(f"/api/v1/rate/assignments/{theirs}").status_code == 404
    assert outsider.get(f"/api/v1/rate/assignments/{theirs}/audio").status_code == 404
    assert outsider.post(f"/api/v1/rate/assignments/{theirs}", json=GOOD).status_code == 404
    student = login_as(m, "SV-077")
    assert student.get(f"/api/v1/rate/assignments/{theirs}").status_code == 403


def test_the_machine_result_stays_closed_to_a_rater_until_they_have_rated(m):
    rids, teachers, admin = study(m, students=1)
    new_batch(m, admin)
    rater = teachers["GV-01"]
    assert rater.get(f"/api/v1/responses/{rids[0]}").status_code == 403
    assert rater.get(f"/api/v1/responses/{rids[0]}/history").status_code == 403
    assert rater.post(f"/api/v1/review/{rids[0]}/lock").status_code == 403
    assert rids[0] not in {q["response_id"] for q in rater.get("/api/v1/review/queue").json()}
    rate_all(rater)
    assert rater.get(f"/api/v1/responses/{rids[0]}").status_code == 200
    assert rids[0] in {q["response_id"] for q in rater.get("/api/v1/review/queue").json()}


def test_a_rating_follows_the_rating_sheet_rules(m):
    _, teachers, admin = study(m, students=1)
    new_batch(m, admin)
    teacher = teachers["GV-01"]
    target = sheets(teacher)[0]["assignment_id"]
    url = f"/api/v1/rate/assignments/{target}"
    bad = [
        {**GOOD, "criteria": {"range": 3}},
        {**GOOD, "overall": 6.5},
        {**GOOD, "overall": 3.25},
        {**GOOD, "band": "D1"},
        {**GOOD, "reason": ""},
        {"unscorable": True, "unscorable_reason": "broken", "overall": 2.0},
        {"unscorable": True},
    ]
    for body in bad:
        assert teacher.post(url, json=body).status_code == 422, body
    rate(teacher, target)
    assert teacher.post(url, json=GOOD).status_code == 409
    done = teacher.get(url).json()["rating"]
    assert done["overall"] == 3.0 and done["band"] == "B1" and done["criteria"]["fluency"] == 3.5


def test_an_unscorable_recording_is_rated_as_such(m):
    _, teachers, admin = study(m, students=1)
    new_batch(m, admin)
    teacher = teachers["GV-01"]
    target = sheets(teacher)[0]["assignment_id"]
    r = teacher.post(
        f"/api/v1/rate/assignments/{target}",
        json={"unscorable": True, "unscorable_reason": "inaudible"},
    )
    assert r.status_code == 200, r.text
    rating = teacher.get(f"/api/v1/rate/assignments/{target}").json()["rating"]
    assert rating["unscorable"] is True and rating["overall"] is None


def test_open_sheets_are_counted_in_the_sidebar_and_a_closed_batch_takes_no_more(m):
    _, teachers, admin = study(m, students=2)
    made = new_batch(m, admin)
    teacher = teachers["GV-01"]
    assert teacher.get("/api/v1/me/badges").json()["ratings"] == 2
    first = sheets(teacher)[0]["assignment_id"]
    rate(teacher, first)
    assert teacher.get("/api/v1/me/badges").json()["ratings"] == 1
    admin.post(f"/api/v1/admin/ratings/batches/{made['batch_id']}/close")
    assert teacher.get("/api/v1/me/badges").json()["ratings"] == 0
    left = next(i for i in sheets(teacher) if i["state"] != "done")["assignment_id"]
    assert teacher.post(f"/api/v1/rate/assignments/{left}", json=GOOD).status_code == 409
    admin.post(f"/api/v1/admin/ratings/batches/{made['batch_id']}/reopen")
    rate(teacher, left)


def all_sheets() -> list[dict]:
    """Every sheet of every batch: sheets live in their batch's document (D060)."""
    return [x for b in store()["rating_batch"].find() for x in b.get("ratings") or []]


def seen_count() -> int:
    """How many (person, response) openings of a machine result are noted."""
    return sum(len(r.get("machine_seen") or []) for r in store()["response"].find())


def raters_of(m, response_id: str) -> set[str]:
    return {x["rater_id"] for x in all_sheets() if x["response_id"] == response_id}


def test_a_teacher_who_opened_the_machine_result_is_not_drawn_to_rate_that_response(m):
    rids, teachers, admin = study(m, students=2, raters=("GV-01", "GV-02", "GV-03"))
    # Before any batch, GV-01 reads the first response's report and GV-02 the
    # second one's history: the machine's result has been in front of them.
    assert teachers["GV-01"].get(f"/api/v1/responses/{rids[0]}").status_code == 200
    assert teachers["GV-02"].get(f"/api/v1/responses/{rids[1]}/history").status_code == 200
    pair = {"name": "Đợt hai người", "rater_ids": [account_id(m, "GV-01"), account_id(m, "GV-02")]}
    # Between the two of them, no response has two blind raters left.
    assert admin.post("/api/v1/admin/ratings/batches", json=pair).status_code == 422

    made = new_batch(m, admin, raters=("GV-01", "GV-02", "GV-03"), seed=5)
    assert made["responses"] == 2 and made["skipped_seen"] == 0
    assert account_id(m, "GV-01") not in raters_of(m, rids[0])
    assert account_id(m, "GV-02") not in raters_of(m, rids[1])

    # A response neither has seen goes to the two of them; the other two are counted out.
    fresh = submit(login_as(m, "SV-010"))
    again = new_batch(m, admin, raters=("GV-01", "GV-02"), only_new=False, seed=6)
    assert again["responses"] == 1 and again["skipped_seen"] == 2
    assert raters_of(m, fresh) == {account_id(m, "GV-01"), account_id(m, "GV-02")}


def test_a_sheet_goes_void_once_its_rater_has_seen_the_machine_result(m):
    rids, teachers, admin = study(m, students=1)
    made = new_batch(m, admin)
    base = f"/api/v1/admin/ratings/batches/{made['batch_id']}"
    teacher = teachers["GV-01"]
    target = sheets(teacher)[0]["assignment_id"]
    assert teacher.get(f"/api/v1/responses/{rids[0]}").status_code == 403
    # Closing the batch lifts the guard, and the teacher reads the machine's result...
    admin.post(f"{base}/close")
    assert teacher.get(f"/api/v1/responses/{rids[0]}").status_code == 200
    # ...so reopening it does not bring back a blind sheet: it takes no rating.
    admin.post(f"{base}/reopen")
    assert teacher.get(f"/api/v1/rate/assignments/{target}").json()["seen_machine"] is True
    assert teacher.post(f"/api/v1/rate/assignments/{target}", json=GOOD).status_code == 409
    assert sheets(teacher)[0]["state"] == "seen"
    assert teacher.get("/api/v1/me/badges").json()["ratings"] == 0
    assert rids[0] in {q["response_id"] for q in teacher.get("/api/v1/review/queue").json()}
    batch = admin.get("/api/v1/admin/ratings/batches").json()[0]
    assert batch["voided"] == 1 and batch["done"] == 0
    # The other rater saw nothing and still rates blind.
    rate_all(teachers["GV-02"])
    assert admin.get("/api/v1/admin/ratings/batches").json()[0]["done"] == 1


def test_a_void_sheet_can_be_handed_to_another_rater(m):
    rids, teachers, admin = study(m, students=1, raters=("GV-01", "GV-02", "GV-03", "GV-04"))
    made = new_batch(m, admin, raters=("GV-01", "GV-02"))
    base = f"/api/v1/admin/ratings/batches/{made['batch_id']}"
    gv01 = account_id(m, "GV-01")
    slot_of_gv01 = next(x["slot"] for x in all_sheets() if x["rater_id"] == gv01)
    admin.post(f"{base}/close")
    assert teachers["GV-01"].get(f"/api/v1/responses/{rids[0]}").status_code == 200
    assert teachers["GV-04"].get(f"/api/v1/responses/{rids[0]}").status_code == 200
    admin.post(f"{base}/reopen")
    assert admin.get("/api/v1/admin/ratings/batches").json()[0]["voided"] == 1

    def hand_to(name: str) -> dict:
        r = admin.post(f"{base}/replace", json={"rater_id": account_id(m, name)})
        assert r.status_code == 200, r.text
        return r.json()

    # GV-02 already rates this response; GV-04 has seen its machine result.
    assert hand_to("GV-02") == {"created": 0, "skipped_own": 1, "skipped_seen": 0}
    assert hand_to("GV-04") == {"created": 0, "skipped_own": 0, "skipped_seen": 1}
    assert hand_to("GV-03") == {"created": 1, "skipped_own": 0, "skipped_seen": 0}
    assert sheets(teachers["GV-01"]) == []
    gv03 = account_id(m, "GV-03")
    taken = next(x["slot"] for x in all_sheets() if x["rater_id"] == gv03)
    assert taken == slot_of_gv01
    batch = admin.get("/api/v1/admin/ratings/batches").json()[0]
    assert batch["voided"] == 0 and batch["assignments"] == 2
    rate_all(teachers["GV-03"])
    rate_all(teachers["GV-02"])
    assert admin.get("/api/v1/admin/ratings/batches").json()[0]["done"] == 2
    assert any(e.action == "rating.replace" for e in m.audit(50))


def test_an_administrator_who_rates_stays_blind_on_the_administration_screens(m):
    rids, teachers, admin = study(m, students=2, raters=("GV-01",))
    made = new_batch(m, admin, raters=("GV-01", "QT-01"))
    base = f"/api/v1/admin/ratings/batches/{made['batch_id']}"
    listed = {r["response_id"] for r in admin.get("/api/v1/responses").json()}
    assert not listed & set(rids)
    assert admin.get(f"/api/v1/responses/{rids[0]}").status_code == 403
    assert admin.get("/api/v1/admin/export/research.json").status_code == 409
    assert admin.get(f"{base}/report").status_code == 409
    assert admin.get(f"{base}/export.csv").status_code == 409
    rate_all(admin)
    listed = {r["response_id"] for r in admin.get("/api/v1/responses").json()}
    assert listed >= set(rids)
    assert admin.get("/api/v1/admin/export/research.json").status_code == 200
    assert admin.get(f"{base}/report").status_code == 200
    assert admin.get(f"{base}/export.csv").status_code == 200


def test_the_waiting_count_leaves_out_what_the_teacher_rates_blind(m):
    rids, teachers, admin = study(m, students=2, raters=("GV-01", "GV-02", "GV-03"))
    assert teachers["GV-01"].get("/api/v1/me/badges").json()["queue"] == 2
    new_batch(m, admin, raters=("GV-01", "GV-02"))
    # The queue of GV-01 hides both responses now, and so does the number beside it.
    assert teachers["GV-01"].get("/api/v1/me/badges").json()["queue"] == 0
    assert teachers["GV-03"].get("/api/v1/me/badges").json()["queue"] == 2
    rate_all(teachers["GV-01"])
    assert teachers["GV-01"].get("/api/v1/me/badges").json()["queue"] == 2


# ================================================================= adjudication (FR-63)


def test_a_disagreement_goes_to_a_third_rater_who_did_not_rate_it(m):
    rids, teachers, admin = study(m, students=2, raters=("GV-01", "GV-02", "GV-03"))
    made = new_batch(m, admin, raters=("GV-01", "GV-02"))
    rate_all(teachers["GV-01"], overall=2.5, band="A2")
    rate_all(teachers["GV-02"], overall=3.5, band="B1")
    batch = admin.get("/api/v1/admin/ratings/batches").json()[0]
    assert batch["needs_adjudication"] == 2

    own = admin.post(
        f"/api/v1/admin/ratings/batches/{made['batch_id']}/adjudicate",
        json={"adjudicator_id": account_id(m, "GV-01")},
    ).json()
    assert own == {"created": 0, "skipped_own": 2, "skipped_seen": 0}
    third = admin.post(
        f"/api/v1/admin/ratings/batches/{made['batch_id']}/adjudicate",
        json={"adjudicator_id": account_id(m, "GV-03")},
    ).json()
    assert third == {"created": 2, "skipped_own": 0, "skipped_seen": 0}
    mine = sheets(teachers["GV-03"])
    assert len(mine) == 2 and all(i["adjudication"] for i in mine)
    sheet = teachers["GV-03"].get(f"/api/v1/rate/assignments/{mine[0]['assignment_id']}").json()
    assert sheet["adjudication"] is True
    assert "2.5" not in json.dumps(sheet) and "A2" not in json.dumps(sheet)
    assert admin.get("/api/v1/admin/ratings/batches").json()[0]["needs_adjudication"] == 0


def test_an_adjudicator_who_opened_the_machine_result_is_passed_over(m):
    rids, teachers, admin = study(m, students=1, raters=("GV-01", "GV-02", "GV-03"))
    made = new_batch(m, admin, raters=("GV-01", "GV-02"))
    rate_all(teachers["GV-01"], overall=2.5, band="A2")
    rate_all(teachers["GV-02"], overall=3.5, band="B1")
    assert teachers["GV-03"].get(f"/api/v1/responses/{rids[0]}").status_code == 200
    result = admin.post(
        f"/api/v1/admin/ratings/batches/{made['batch_id']}/adjudicate",
        json={"adjudicator_id": account_id(m, "GV-03")},
    ).json()
    assert result == {"created": 0, "skipped_own": 0, "skipped_seen": 1}


# ================================================================= report (FR-64)


def test_the_report_puts_humans_first_and_compares_the_machine_before_any_review(m):
    rids, teachers, admin = study(m, students=3)
    for rid in rids:
        machine_scored(m, rid, 3.0, "B1")
    # A teacher's operational review overwrites the response's score; the
    # report must still compare the humans with what the MACHINE said.
    reviewer = login_as(m, "GV-09", "teacher")
    reviewer.post(
        f"/api/v1/review/{rids[0]}", json={"new_score": 5.5, "reason": "Nghe lại, tốt hơn."}
    )
    made = new_batch(m, admin)
    rate_all(teachers["GV-01"], overall=3.0, band="B1")
    rate_all(teachers["GV-02"], overall=3.5, band="B1")
    d = admin.get(f"/api/v1/admin/ratings/batches/{made['batch_id']}/report").json()
    report = d["report"]
    assert list(report)[:3] == ["counts", "human_human", "machine_human"]
    assert report["counts"]["rated_twice"] == 3
    assert report["human_human"]["n"] == 3
    assert report["human_human"]["mean_abs_diff"] == 0.5
    assert report["machine_human"]["n"] == 3
    # Reference 3.25 everywhere, machine 3.0 everywhere -- the 5.5 was a teacher's.
    assert report["machine_human"]["rmse"]["value"] == 0.25
    assert report["routing"]["flagged"]["n"] == 3
    assert d["plan_targets"] == {"qwk_band": 0.7, "icc_overall": 0.75}
    assert d["time_to_rate"]["n"] == 6 and d["withdrawn"] == 0


def with_features(m, response_id: str, shift: float) -> None:
    """Store features `shift` standard deviations from the training mean on every feature.

    What the pipeline stores next to a scored response; the fake recogniser's
    own features sit outside the model's range, so the test arranges them.
    """
    from conftest import feature_set

    from aicefr.scoring.scorer import load_model

    model = load_model("ridge_resp_v2")
    values = {
        name: mean + shift * scale
        for name, mean, scale in zip(
            model["feature_order"], model["mean"], model["scale"], strict=True
        )
    }
    report = m.repo.get(response_id)
    report.features = feature_set(values, version=model["feature_version"])
    store()["response"].update_one(
        {"response_id": response_id}, {"$set": {"report_json": report.model_dump_json()}}
    )


def test_the_report_rescores_the_batch_with_another_model_on_the_same_ratings(m):
    """D067: two scoring models compared on one set of human ratings."""
    from aicefr.scoring.scorer import RidgeScorer

    rids, teachers, admin = study(m, students=3)
    for rid, shift in zip(rids, (-0.5, 0.0, 0.5), strict=True):
        machine_scored(m, rid, 3.0, "B1")
        with_features(m, rid, shift)
    made = new_batch(m, admin)
    rate_all(teachers["GV-01"], overall=3.0, band="B1")
    rate_all(teachers["GV-02"], overall=3.5, band="B1")
    base = f"/api/v1/admin/ratings/batches/{made['batch_id']}/report"

    graded = admin.get(base).json()
    assert graded["scored_with"] == {"model": None, "rescored": False, "left_out": 0}
    assert {"ridge_resp_v2", "ridge_resp_v2_cal"} <= set(graded["models"])
    assert graded["report"]["machine_human"]["rmse"]["value"] == 0.25

    rmses = {}
    for name in ("ridge_resp_v2", "ridge_resp_v2_cal"):
        d = admin.get(f"{base}?model={name}").json()
        assert d["scored_with"] == {"model": name, "rescored": True, "left_out": 0}
        assert d["report"]["machine_human"]["n"] == 3
        # Each response's machine score is now that model's, from its stored
        # features; the reference is 3.25 everywhere (3.0 and 3.5).
        scorer = RidgeScorer(name)
        scores = [scorer.score(m.repo.get(rid).features).overall_0_6 for rid in rids]
        rmse = (sum((x - 3.25) ** 2 for x in scores) / len(scores)) ** 0.5
        assert d["report"]["machine_human"]["rmse"]["value"] == pytest.approx(rmse, abs=1e-3)
        rmses[name] = rmse
    # The calibrated model spreads the same features further apart (D052).
    assert rmses["ridge_resp_v2"] != rmses["ridge_resp_v2_cal"]
    # The humans' part is the same whichever model the machine is.
    assert d["report"]["human_human"] == graded["report"]["human_human"]


def test_a_response_without_stored_features_is_left_out_of_a_rescore(m):
    rids, teachers, admin = study(m, students=2)
    for rid in rids:
        machine_scored(m, rid, 3.0, "B1")
    with_features(m, rids[0], 0.0)
    made = new_batch(m, admin)
    rate_all(teachers["GV-01"])
    rate_all(teachers["GV-02"])
    base = f"/api/v1/admin/ratings/batches/{made['batch_id']}/report"
    d = admin.get(f"{base}?model=ridge_resp_v2_cal").json()
    assert d["scored_with"]["left_out"] == 1
    assert d["report"]["machine_human"]["n"] == 1
    assert any("không chấm lại được" in note for note in d["report"]["notes"])
    assert admin.get(f"{base}?model=khong-co").status_code == 404
    # ridge_v3 loads but grades whole exam sittings, not one response.
    assert admin.get(f"{base}?model=ridge_v3").status_code == 404


def test_a_review_decision_keeps_the_ratings_and_who_saw_the_machine(m):
    """A teacher's decision updates the response row in place.

    `save` used to write with INSERT OR REPLACE, which deletes the old row
    first; with foreign keys on, the delete cascaded and took every rating
    sheet, every submitted rating and every "saw the machine" record of that
    response with it.
    """
    rids, teachers, admin = study(m, students=2)
    for rid in rids:
        machine_scored(m, rid, 3.0, "B1")
    made = new_batch(m, admin)
    rate_all(teachers["GV-01"])
    rate_all(teachers["GV-02"])
    reviewer = login_as(m, "GV-09", "teacher")
    reviewer.get(f"/api/v1/responses/{rids[0]}")
    before = seen_count()

    r = reviewer.post(
        f"/api/v1/review/{rids[0]}", json={"new_score": 4.0, "reason": "Nghe lại, tốt hơn."}
    )
    assert r.status_code == 200, r.text

    assert len(all_sheets()) == 4
    assert sum(x["submitted_at"] is not None for x in all_sheets()) == 4
    assert seen_count() == before
    d = admin.get(f"/api/v1/admin/ratings/batches/{made['batch_id']}/report").json()
    assert d["report"]["counts"]["rated_twice"] == 2


def test_the_export_lists_every_rating_with_rater_pseudonyms_and_the_machine_score(m):
    rids, teachers, admin = study(m, students=2)
    machine_scored(m, rids[0], 4.0, "B2")
    made = new_batch(m, admin)
    rate_all(teachers["GV-01"])
    rate_all(teachers["GV-02"])
    r = admin.get(f"/api/v1/admin/ratings/batches/{made['batch_id']}/export.csv")
    assert r.headers["content-type"].startswith("text/csv")
    rows = list(csv.DictReader(io.StringIO(r.text.lstrip("﻿"))))
    assert len(rows) == 4
    assert {row["rater_id"] for row in rows} == {"GV-01", "GV-02"}
    scored = [row for row in rows if row["response_id"] == rids[0]]
    assert {row["ai_overall"] for row in scored} == {"4.0"}
    assert all(row["score_fluency"] == "3.5" for row in rows)
    assert m.audit(50)[0].action == "export.ratings"


def test_erasing_a_participant_erases_what_raters_said_about_them(m):
    rids, teachers, admin = study(m, students=2)
    made = new_batch(m, admin)
    rate_all(teachers["GV-01"])
    assert (
        admin.post(
            "/api/v1/admin/erase", json={"speaker_id": "SV-001", "confirm_speaker_id": "SV-001"}
        ).status_code
        == 200
    )
    left = sum(x["response_id"] == rids[0] for x in all_sheets())
    ratings = sum(x["submitted_at"] is not None for x in all_sheets())
    assert left == 0
    assert ratings == 1  # GV-01's rating of SV-002 is all that is left
    batch = admin.get("/api/v1/admin/ratings/batches").json()[0]
    assert batch["batch_id"] == made["batch_id"] and batch["responses"] == 1


def test_only_an_administrator_runs_batches(m):
    _, teachers, admin = study(m, students=1)
    made = new_batch(m, admin)
    teacher = teachers["GV-01"]
    base = f"/api/v1/admin/ratings/batches/{made['batch_id']}"
    assert teacher.get("/api/v1/admin/ratings/setup").status_code == 403
    assert teacher.get(f"{base}/report").status_code == 403
    assert teacher.get(f"{base}/export.csv").status_code == 403
    assert teacher.post(f"{base}/close").status_code == 403
    assert admin.get("/api/v1/admin/ratings/batches/khong-co/report").status_code == 404


def test_the_rater_pages_render(m):
    _, teachers, admin = study(m, students=1)
    new_batch(m, admin)
    teacher = teachers["GV-01"]
    assert 'id="rate-batches"' in teacher.get("/rate").text
    target = sheets(teacher)[0]["assignment_id"]
    page = teacher.get(f"/rate/{target}").text
    assert 'id="sheet-form"' in page and 'data-badge="ratings"' in page


def test_the_command_line_report_gives_the_numbers_of_the_screen(m, tmp_path):
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "agreement_report", Path(__file__).resolve().parents[1] / "tools" / "agreement_report.py"
    )
    tool = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tool)

    rids, teachers, admin = study(m, students=3)
    for rid in rids:
        machine_scored(m, rid, 3.0, "B1")
    made = new_batch(m, admin)
    rate_all(teachers["GV-01"], overall=3.0, band="B1")
    rate_all(teachers["GV-02"], overall=3.5, band="B1")
    screen = admin.get(f"/api/v1/admin/ratings/batches/{made['batch_id']}/report").json()

    out = tmp_path / "dong_thuan.md"
    assert tool.main(["--db", m.repo.db_path, "--batch", made["batch_id"], "--out", str(out)]) == 0
    text = out.read_text(encoding="utf-8")
    assert "## 1. Hai giám khảo với nhau" in text and "## 2. Máy so với" in text
    assert text.index("## 1.") < text.index("## 2.")
    saved = json.loads(out.with_suffix(".json").read_text(encoding="utf-8"))
    assert saved["report"] == screen["report"]
    for rid in rids:
        assert rid not in text
