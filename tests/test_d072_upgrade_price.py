"""What an upgraded answer costs (D072).

* a cap for everyone together in 24 hours keeps the system under the
  provider's free daily quota;
* on the metered channel an upgrade costs `AICEFR_PRICE_UPGRADE_RUNS` runs:
  held before the model is asked, charged when the upgrade is made, released
  when the model fails, refused when the learner has too few runs;
* the provider's token counts are kept with the upgrade and its ledger entry.
"""

from __future__ import annotations

import io
import json

import pytest
from test_billing import boot
from test_d069_coach import answer, scored
from test_lessons_integration import account_id, login_as, submit_assessment

from aicefr.coach import providers
from aicefr.coach.upgrade import UpgradeError
from aicefr.metering.pricing import PriceList, as_idpoint, upgrade_units

USED = {"input_tokens": 812, "output_tokens": 233}


class Fake:
    name, model = "gemini", "gemini-3.5-flash-lite"
    fail = False

    def complete_with_usage(self, user):
        if self.fail:
            raise UpgradeError("nhà cung cấp mô hình trả lỗi 503")
        return answer(), dict(USED)


@pytest.fixture
def fake(monkeypatch):
    from aicefr.services.core.assessment import coach_api

    model = Fake()
    monkeypatch.setattr(coach_api, "provider_from", lambda settings: model)
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


# ================================================================= the caps


def test_everyone_together_has_a_daily_cap(tmp_path, monkeypatch, fake):
    m = boot(tmp_path, monkeypatch, AICEFR_COACH_GLOBAL_DAILY="1")
    first, rid1 = ready(m, "SV-G01")
    second, rid2 = ready(m, "SV-G02")
    assert first.post(f"/api/v1/responses/{rid1}/upgrade").status_code == 200
    r = second.post(f"/api/v1/responses/{rid2}/upgrade")
    assert r.status_code == 429 and "hệ thống đã dùng hết" in r.json()["detail"]


# ================================================================= the metered channel


def test_metered_an_upgrade_is_charged_with_its_tokens(tmp_path, monkeypatch, fake):
    m = boot(tmp_path, monkeypatch, AICEFR_METERING="on")
    student, rid = ready(m, "SV-M01")
    coach = student.get(f"/api/v1/responses/{rid}/coach").json()
    assert coach["price"] == {"runs": 0.3, "idpoint": 600}
    made = student.post(f"/api/v1/responses/{rid}/upgrade").json()
    assert (made["input_tokens"], made["output_tokens"]) == (812, 233)
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
