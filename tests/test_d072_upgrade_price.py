"""What an upgraded answer costs (D072).

* a cap for everyone together keeps the system under the provider's free
  daily quota: every request sent, retries and failures included, in the
  provider's day; on a paid tier a daily budget in USD replaces it;
* the administrator sees those counters, today and the last 14 days;
* on the metered channel an upgrade costs `AICEFR_PRICE_UPGRADE_RUNS` runs:
  held before the model is asked, charged when the upgrade is made, released
  when the model fails, refused when the learner has too few runs;
* the provider's token counts are kept with the ledger entry and the day's counters.
"""

from __future__ import annotations

import io
import json
from datetime import UTC, datetime

import pytest
from test_billing import boot
from test_d069_coach import answer, scored
from test_lessons_integration import account_id, login_as, submit_assessment

from aicefr.coach import providers, usage
from aicefr.coach.upgrade import UpgradeError
from aicefr.metering.pricing import PriceList, as_idpoint, upgrade_units

USED = {"input_tokens": 812, "output_tokens": 233}


class Fake:
    name, model = "gemini", "gemini-3.5-flash-lite"
    fail = False

    def complete_with_usage(self, user, calls):
        calls.requests += 1
        if self.fail:
            raise UpgradeError("nhà cung cấp mô hình trả lỗi 503")
        return answer(), dict(USED)


@pytest.fixture
def fake(monkeypatch):
    from aicefr.services.core.assessment import coach_api

    model = Fake()
    monkeypatch.setattr(coach_api, "provider_from", lambda settings, paid=False: model)
    return model


def ready(m, pseudonym: str):
    student = login_as(m, pseudonym)
    rid = submit_assessment(student)
    scored(m, rid)
    return student, rid


def ledger(m, pseudonym: str) -> list[dict]:
    return m.core_parts.state["metering"].history(account_id(m, pseudonym))


# ================================================================= the price itself


def test_an_upgrade_costs_a_third_of_a_run_by_default():
    prices = PriceList()
    assert upgrade_units(prices) == 300 and as_idpoint(prices, upgrade_units(prices)) == 600
    assert upgrade_units(PriceList(upgrade_runs=0)) == 0
    with pytest.raises(ValueError):
        PriceList(upgrade_runs=-0.1)


def test_the_provider_reports_the_tokens_it_used(monkeypatch):
    class Answer(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    body = {
        "choices": [{"message": {"content": "{}"}}],
        "usage": {"prompt_tokens": 700, "completion_tokens": 150},
    }
    monkeypatch.setattr(
        providers.urllib.request, "urlopen", lambda r, timeout: Answer(json.dumps(body).encode())
    )
    p = providers.Provider("gemini", "gemini-3.5-flash-lite", "k")
    assert p.complete_with_usage("{}") == ("{}", {"input_tokens": 700, "output_tokens": 150})


def test_a_retry_is_a_request_the_provider_counts(monkeypatch):
    sent = []

    def urlopen(request, timeout):
        sent.append(request)
        raise providers.urllib.error.HTTPError(request.full_url, 503, "busy", {}, None)

    monkeypatch.setattr(providers.urllib.request, "urlopen", urlopen)
    monkeypatch.setattr(providers, "RETRY_WAIT_S", 0)
    calls = usage.Calls()
    with pytest.raises(UpgradeError):
        providers.Provider("gemini", "m", "k").complete_with_usage("{}", calls)
    assert calls.requests == len(sent) == 2


def test_the_day_is_googles_ending_at_midnight_pacific():
    # 06:30 UTC on 20 Oct is still 19 Oct in California (PDT, UTC-7) ...
    now = datetime(2026, 10, 20, 6, 30, tzinfo=UTC)
    assert usage.provider_day(now) == "2026-10-19"
    assert usage.resets_at(now) == "2026-10-20T07:00:00+00:00"
    # ... and once the clocks have gone back (1 Nov 2026), midnight is 08:00 UTC.
    later = datetime(2026, 11, 10, 7, 30, tzinfo=UTC)
    assert usage.provider_day(later) == "2026-11-09"
    assert usage.resets_at(later) == "2026-11-10T08:00:00+00:00"
    assert usage.last_days(3, now) == ["2026-10-17", "2026-10-18", "2026-10-19"]


# ================================================================= the caps


def test_everyone_together_has_a_daily_cap(tmp_path, monkeypatch, fake):
    m = boot(tmp_path, monkeypatch, AICEFR_COACH_GLOBAL_DAILY="1")
    first, rid1 = ready(m, "SV-G01")
    second, rid2 = ready(m, "SV-G02")
    assert first.post(f"/api/v1/responses/{rid1}/upgrade").status_code == 200
    r = second.post(f"/api/v1/responses/{rid2}/upgrade")
    assert r.status_code == 429 and "hệ thống đã dùng hết" in r.json()["detail"]


def test_a_failed_request_counts_against_the_cap(tmp_path, monkeypatch, fake):
    m = boot(tmp_path, monkeypatch, AICEFR_COACH_GLOBAL_DAILY="1")
    first, rid1 = ready(m, "SV-G03")
    second, rid2 = ready(m, "SV-G04")
    fake.fail = True
    assert first.post(f"/api/v1/responses/{rid1}/upgrade").status_code == 502
    fake.fail = False
    assert second.post(f"/api/v1/responses/{rid2}/upgrade").status_code == 429


def test_on_a_paid_tier_the_cap_is_a_budget(tmp_path, monkeypatch, fake):
    # 812 x 0.30 + 233 x 2.50 per million = 0.00082 USD for the first upgrade.
    m = boot(
        tmp_path,
        monkeypatch,
        AICEFR_COACH_DAILY_BUDGET_USD="0.0005",
        AICEFR_COACH_GLOBAL_DAILY="1000",
    )
    first, rid1 = ready(m, "SV-B01")
    second, rid2 = ready(m, "SV-B02")
    assert first.post(f"/api/v1/responses/{rid1}/upgrade").status_code == 200
    r = second.post(f"/api/v1/responses/{rid2}/upgrade")
    assert r.status_code == 429 and "ngân sách" in r.json()["detail"]


# ================================================================= the dashboard


def test_the_administrator_sees_today_against_the_cap(tmp_path, monkeypatch, fake):
    m = boot(tmp_path, monkeypatch, AICEFR_COACH_GLOBAL_DAILY="2", AICEFR_COACH_DAILY="1")
    student, rid = ready(m, "SV-D01")
    other, rid2 = ready(m, "SV-D02")
    student.post(f"/api/v1/responses/{rid}/upgrade")
    rid3 = submit_assessment(student)
    scored(m, rid3)
    assert student.post(f"/api/v1/responses/{rid3}/upgrade").status_code == 429  # own cap
    fake.fail = True
    other.post(f"/api/v1/responses/{rid2}/upgrade")
    assert other.get("/api/v1/admin/coach").status_code == 403
    d = login_as(m, "QT-D1", "admin").get("/api/v1/admin/coach").json()
    assert (d["tier"], d["daily_requests"], d["per_student_daily"]) == ("free", 2, 1)
    t = d["today"]
    assert t["day"] == usage.provider_day() and len(d["days"]) == 14 and d["days"][-1] == t
    assert (t["requests"], t["upgrades"], t["failed"]) == (2, 1, 1)
    assert (t["refused_user"], t["refused_global"], t["accounts"]) == (1, 0, 2)
    assert (t["input_tokens"], t["output_tokens"]) == (812, 233)
    assert t["cost_usd"] == pytest.approx((812 * 0.30 + 233 * 2.50) / 1e6, abs=1e-6)
    assert t["errors"] == {"nhà cung cấp mô hình trả lỗi 503": 1}
    # The cap is reached: the next one is refused and counted as such.
    third, rid4 = ready(m, "SV-D03")
    assert third.post(f"/api/v1/responses/{rid4}/upgrade").status_code == 429
    again = login_as(m, "QT-D2", "admin").get("/api/v1/admin/coach").json()
    assert again["today"]["refused_global"] == 1


def test_gemini_is_the_deployed_provider_and_its_caps_reach_the_container():
    import yaml

    root = __import__("pathlib").Path(__file__).resolve().parents[1]
    compose = (root / "docker-compose.yml").read_text(encoding="utf-8")
    assert "AICEFR_COACH_PROVIDER: ${AICEFR_COACH_PROVIDER:-gemini}" in compose
    example = (root / ".env.example").read_text(encoding="utf-8")
    for key, default in (
        ("AICEFR_COACH_GLOBAL_DAILY", "475"),
        ("AICEFR_COACH_DAILY_BUDGET_USD", "0"),
        ("AICEFR_COACH_PRICE_INPUT_USD", "0.30"),
        ("AICEFR_COACH_PRICE_OUTPUT_USD", "2.50"),
    ):
        assert f"{key}: ${{{key}:-{default}}}" in compose
        assert f"\n{key}={default}" in example
    assert yaml  # the compose file itself is parsed by test_deploy_config


# ================================================================= the metered channel


def test_metered_an_upgrade_is_charged_with_its_tokens(tmp_path, monkeypatch, fake):
    m = boot(tmp_path, monkeypatch, AICEFR_METERING="on")
    student, rid = ready(m, "SV-M01")
    coach = student.get(f"/api/v1/responses/{rid}/coach").json()
    assert coach["price"] == {"runs": 0.3, "idpoint": 600}
    made = student.post(f"/api/v1/responses/{rid}/upgrade").json()
    # The tokens are the ledger's and the day's, not the upgrade's own.
    assert "input_tokens" not in made
    entry = next(e for e in ledger(m, "SV-M01") if e["action"] == "upgrade")
    assert (entry["state"], entry["charged"]) == ("charged", 300)
    assert (entry["input_tokens"], entry["output_tokens"]) == (812, 233)
    # Made once: asking again returns it and charges nothing more.
    student.post(f"/api/v1/responses/{rid}/upgrade")
    assert sum(e["action"] == "upgrade" for e in ledger(m, "SV-M01")) == 1
    history = student.get("/api/v1/me/credits").json()["history"]
    assert any(h["action"] == "upgrade" for h in history)


def test_metered_a_failed_upgrade_costs_nothing(tmp_path, monkeypatch, fake):
    m = boot(tmp_path, monkeypatch, AICEFR_METERING="on")
    student, rid = ready(m, "SV-M02")
    before = student.get("/api/v1/me/credits").json()["free_runs_left"]
    fake.fail = True
    assert student.post(f"/api/v1/responses/{rid}/upgrade").status_code == 502
    entry = next(e for e in ledger(m, "SV-M02") if e["action"] == "upgrade")
    assert (entry["state"], entry["charged"]) == ("released", 0)
    assert student.get("/api/v1/me/credits").json()["free_runs_left"] == before


def test_metered_too_few_runs_is_refused_before_the_model_is_asked(tmp_path, monkeypatch, fake):
    m = boot(tmp_path, monkeypatch, AICEFR_METERING="on", AICEFR_PRICE_UPGRADE_RUNS="50")
    student, rid = ready(m, "SV-M03")
    fake.fail = True  # would be a 502 if the model were asked
    r = student.post(f"/api/v1/responses/{rid}/upgrade")
    assert r.status_code == 402 and "Nạp thêm IDPoint" in r.json()["detail"]
    assert not any(e["action"] == "upgrade" for e in ledger(m, "SV-M03"))


def test_unmetered_an_upgrade_has_no_price(tmp_path, monkeypatch, fake):
    m = boot(tmp_path, monkeypatch)
    student, rid = ready(m, "SV-M04")
    assert student.get(f"/api/v1/responses/{rid}/coach").json()["price"] is None
    assert student.post(f"/api/v1/responses/{rid}/upgrade").status_code == 200
