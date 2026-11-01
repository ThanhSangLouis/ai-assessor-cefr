"""The administrator switches the language model to a paid budget (D073).

* nothing switches by itself: the free quota running out is shown on the
  dashboard, and an administrator decides;
* the paid tier asks with its own key; without that key it cannot be chosen;
* the free quota counts the free tier's requests, the budget the paid tier's
  cost, so a day that switched mixes neither;
* who switched and when is kept with the setting and in the audit log.
"""

from __future__ import annotations

import pytest
from test_billing import boot
from test_d069_coach import answer, scored
from test_lessons_integration import login_as, submit_assessment

from aicefr.coach.upgrade import UpgradeError

USED = {"input_tokens": 812, "output_tokens": 233}
COST = (812 * 0.30 + 233 * 2.50) / 1e6


class Fake:
    model = "gemini-3.5-flash-lite"

    def __init__(self, paid: bool, log: list):
        self.name, self.paid, self.log = "gemini", paid, log

    def complete_with_usage(self, user, calls):
        calls.requests += 1
        self.log.append("paid" if self.paid else "free")
        return answer(), dict(USED)


@pytest.fixture
def models(monkeypatch):
    """Which tier answered each upgrade; `ready["paid"]` is whether the paid key is set."""
    from aicefr.services.core.assessment import coach_api

    state = {"log": [], "paid": True}

    def provider_from(settings, paid=False):
        if paid and not state["paid"]:
            return None
        return Fake(paid, state["log"])

    monkeypatch.setattr(coach_api, "provider_from", provider_from)
    return state


def ready(m, pseudonym: str):
    student = login_as(m, pseudonym)
    rid = submit_assessment(student)
    scored(m, rid)
    return student, rid


def switch(admin, **body):
    return admin.put("/api/v1/admin/coach/tier", json=body)


def test_only_an_administrator_switches(tmp_path, monkeypatch, models):
    m = boot(tmp_path, monkeypatch)
    student = login_as(m, "SV-T01")
    assert switch(student, tier="paid", budget_usd=2).status_code == 403


def test_the_paid_tier_needs_its_key_and_a_budget(tmp_path, monkeypatch, models):
    m = boot(tmp_path, monkeypatch)
    admin = login_as(m, "QT-T1", "admin")
    assert switch(admin, tier="paid").status_code == 422
    assert switch(admin, tier="paid", budget_usd=0).status_code == 422
    models["paid"] = False
    r = switch(admin, tier="paid", budget_usd=2)
    assert r.status_code == 409 and "AICEFR_COACH_PAID_API_KEY" in r.json()["detail"]
    d = admin.get("/api/v1/admin/coach").json()
    assert (d["tier"], d["paid_ready"]) == ("free", False)


def test_when_the_free_quota_runs_out_the_administrator_opens_the_paid_tier(
    tmp_path, monkeypatch, models
):
    m = boot(tmp_path, monkeypatch, AICEFR_COACH_GLOBAL_DAILY="1")
    admin = login_as(m, "QT-T2", "admin")
    first, rid1 = ready(m, "SV-T02")
    second, rid2 = ready(m, "SV-T03")
    assert first.post(f"/api/v1/responses/{rid1}/upgrade").status_code == 200
    assert second.post(f"/api/v1/responses/{rid2}/upgrade").status_code == 429
    d = admin.get("/api/v1/admin/coach").json()
    assert (d["tier"], d["free_used_up"]) == ("free", True)  # shown, not switched

    d = switch(admin, tier="paid", budget_usd=2).json()
    assert (d["tier"], d["budget_usd"], d["tier_changed_by"]) == ("paid", 2.0, "QT-T2")
    assert (d["used_today"], d["cap_today"]) == (0, 2.0)
    assert second.post(f"/api/v1/responses/{rid2}/upgrade").status_code == 200
    assert models["log"] == ["free", "paid"]

    t = admin.get("/api/v1/admin/coach").json()["today"]
    assert (t["requests"], t["free_requests"], t["paid_requests"]) == (2, 1, 1)
    assert t["paid_cost_usd"] == pytest.approx(COST, abs=1e-6)
    assert t["cost_usd"] == pytest.approx(2 * COST, abs=1e-6)
    audit = admin.get("/api/v1/audit").json()
    assert any(a["action"] == "coach.tier" and "tier=paid" in (a["detail"] or "") for a in audit)


def test_the_budget_caps_the_paid_tier_and_free_counts_only_free(tmp_path, monkeypatch, models):
    m = boot(tmp_path, monkeypatch, AICEFR_COACH_GLOBAL_DAILY="1")
    admin = login_as(m, "QT-T3", "admin")
    switch(admin, tier="paid", budget_usd=COST / 2)
    a, rid_a = ready(m, "SV-T04")
    b, rid_b = ready(m, "SV-T05")
    c, rid_c = ready(m, "SV-T06")
    assert a.post(f"/api/v1/responses/{rid_a}/upgrade").status_code == 200
    r = b.post(f"/api/v1/responses/{rid_b}/upgrade")
    assert r.status_code == 429 and "ngân sách" in r.json()["detail"]
    # Back on the free tier, the paid requests do not use up the free quota.
    assert switch(admin, tier="free").json()["tier"] == "free"
    assert c.post(f"/api/v1/responses/{rid_c}/upgrade").status_code == 200
    assert models["log"] == ["paid", "free"]


def test_a_failed_paid_request_counts_against_the_budget(tmp_path, monkeypatch, models):
    from aicefr.services.core.assessment import coach_api

    class Broken(Fake):
        def complete_with_usage(self, user, calls):
            calls.requests += 1
            raise UpgradeError("nhà cung cấp mô hình trả lỗi 503")

    monkeypatch.setattr(coach_api, "provider_from", lambda s, paid=False: Broken(paid, []))
    m = boot(tmp_path, monkeypatch)
    admin = login_as(m, "QT-T4", "admin")
    switch(admin, tier="paid", budget_usd=1)
    student, rid = ready(m, "SV-T07")
    assert student.post(f"/api/v1/responses/{rid}/upgrade").status_code == 502
    t = admin.get("/api/v1/admin/coach").json()["today"]
    assert (t["paid_requests"], t["free_requests"], t["failed"]) == (1, 0, 1)
