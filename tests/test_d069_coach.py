"""From a result to the next band (D069): targets, the upgraded answer, saying it again.

* `next_band_plan` reads up to three targets off the scoring model, relative
  to the recording and inside the range the model was trained on;
* the upgraded answer is made once by the configured language model -- here a
  stand-in -- kept with the response, grounded in the learner's own words, and
  capped per day;
* "Nói lại đề này" measures three rounds of the same task and compares each
  with the first.
"""

from __future__ import annotations

import json

import pytest
from conftest import feature_set
from dbutil import store
from test_lessons_integration import login_as, m, submit_assessment, wav  # noqa: F401

from aicefr.coach import providers
from aicefr.coach.upgrade import UpgradeError, parse
from aicefr.report.next_band import next_band_plan
from aicefr.scoring.scorer import RidgeScorer, load_model

TRANSCRIPT = (
    "I think online learning is good because students can study at home but "
    "sometimes it is hard to focus and the internet is slow so I prefer the class"
)


def shifted(shift: float):
    model = load_model("ridge_resp_v2")
    values = {
        n: mu + shift * sc
        for n, mu, sc in zip(model["feature_order"], model["mean"], model["scale"], strict=True)
    }
    return model, feature_set(values, version=model["feature_version"])


# ================================================================= targets


def test_targets_point_to_the_next_band_inside_the_trained_range():
    model, features = shifted(-0.6)
    score = RidgeScorer("ridge_resp_v2").score(features).overall_0_6
    plan = next_band_plan(model, features, score)
    assert plan and plan["to_band"] != plan["from_band"]
    assert plan["threshold"] > score and 1 <= len(plan["targets"]) <= 3
    order = model["feature_order"]
    for t in plan["targets"]:
        i = order.index(t["feature"])
        coef = model["coef"][i]
        # Each target moves its feature the way that raises the score.
        assert (t["direction"] == "up") == (coef > 0) or t["feature"] == "vad_pause_per_min"
        assert t["now"] != t["target"]


def test_no_targets_without_a_score_or_above_the_last_threshold():
    model, features = shifted(0.0)
    assert next_band_plan(model, features, None) is None
    assert next_band_plan(model, features, 5.99) is None


# ================================================================= the upgraded answer


def answer(**extra) -> str:
    body = {
        "upgraded": (
            "In my view, online learning is convenient because students can study from home. "
            "However, it can be hard to stay focused, and the connection is often slow, "
            "so on balance I prefer learning in class."
        ),
        "changes": [
            {"from": "but sometimes", "to": "However,", "why_vi": "Từ nối mạch lạc hơn."},
            {"from": "a sentence nobody said", "to": "x", "why_vi": "bịa"},
        ],
        "phrases": [{"phrase": "on balance", "meaning_vi": "cân nhắc mọi mặt"}],
    }
    body.update(extra)
    return json.dumps(body)


def test_a_change_must_point_at_words_the_learner_said():
    made = parse("```json\n" + answer() + "\n```", TRANSCRIPT)
    assert [c["from"] for c in made.changes] == ["but sometimes"]
    assert made.phrases[0]["phrase"] == "on balance"


@pytest.mark.parametrize(
    "raw", ["not json", json.dumps({"upgraded": ""}), answer(upgraded="Too short.")]
)
def test_an_unusable_answer_is_refused(raw):
    with pytest.raises(UpgradeError):
        parse(raw, TRANSCRIPT)


def test_the_provider_is_off_until_a_key_is_set(monkeypatch):
    from aicefr.config import Settings

    monkeypatch.setenv("AICEFR_COACH_PROVIDER", "groq")
    monkeypatch.delenv("AICEFR_GROQ_API_KEY", raising=False)
    assert providers.provider_from(Settings()) is None
    monkeypatch.setenv("AICEFR_GROQ_API_KEY", "x" * 20)
    p = providers.provider_from(Settings())
    assert (p.name, p.model) == ("groq", "llama-3.3-70b-versatile")
    monkeypatch.setenv("AICEFR_COACH_MODEL", "llama-3.1-8b-instant")
    assert providers.provider_from(Settings()).model == "llama-3.1-8b-instant"
    monkeypatch.setenv("AICEFR_COACH_PROVIDER", "off")
    assert providers.provider_from(Settings()) is None


def test_a_free_tier_cap_reads_as_a_sentence(monkeypatch):
    import urllib.error

    def capped(*a, **k):
        raise urllib.error.HTTPError("u", 429, "Too Many Requests", {}, None)

    monkeypatch.setattr(providers.urllib.request, "urlopen", capped)
    p = providers.Provider("groq", "llama-3.3-70b-versatile", "k")
    with pytest.raises(UpgradeError, match="giới hạn lượt"):
        p.complete("{}")


# ================================================================= the application


def scored(m, rid: str, band: str = "B1", score: float = 3.2) -> None:
    """Arrange a scored assessment with a transcript and features, as the pipeline leaves it."""
    from aicefr.contracts import Assessment, Band, ResponseStatus, Transcript

    _, features = shifted(-0.3)
    report = m.repo.get(rid)
    report.status = ResponseStatus.COMPLETED
    report.asr = Transcript(text=TRANSCRIPT, engine="fake", model_version="small")
    report.features = features
    report.assessment = Assessment(
        model_version="ridge_resp_v2", overall_0_6=score, overall_band=Band(band)
    )
    store()["response"].update_one(
        {"response_id": rid},
        {"$set": {"status": "COMPLETED", "overall_0_6": score, "overall_band": band,
                  "report_json": report.model_dump_json()}},
    )  # fmt: skip


@pytest.fixture
def coach_on(monkeypatch):
    calls = []

    class Fake:
        name, model = "groq", "llama-3.3-70b-versatile"

        def complete(self, user):
            calls.append(json.loads(user))
            return answer()

    from aicefr.services.core.assessment import coach_api

    monkeypatch.setattr(coach_api, "provider_from", lambda settings: Fake())
    return calls


def test_the_report_offers_targets_and_an_upgrade_made_once(m, coach_on):
    student = login_as(m, "SV-C01")
    rid = submit_assessment(student)
    scored(m, rid)

    c = student.get(f"/api/v1/responses/{rid}/coach").json()
    assert c["next_band"]["from_band"] == "B1" and c["next_band"]["to_band"] == "B2"
    assert c["can_upgrade"] is True and c["upgrade"] is None

    made = student.post(f"/api/v1/responses/{rid}/upgrade").json()
    assert made["to_band"] == "B2" and made["changes"][0]["from"] == "but sometimes"
    # Only the task and the transcript went out: no pseudonym, no recording.
    sent = coach_on[0]
    assert sent["student_transcript"] == TRANSCRIPT and "SV-C01" not in json.dumps(sent)

    again = student.post(f"/api/v1/responses/{rid}/upgrade").json()
    assert again == made and len(coach_on) == 1  # kept, not paid for twice
    assert student.get(f"/api/v1/responses/{rid}/coach").json()["upgrade"] == made


def test_only_the_owner_upgrades_and_a_day_has_a_cap(m, coach_on, monkeypatch):
    owner = login_as(m, "SV-C02")
    rids = [submit_assessment(owner) for _ in range(2)]
    for rid in rids:
        scored(m, rid)
    other = login_as(m, "SV-C03")
    assert other.post(f"/api/v1/responses/{rids[0]}/upgrade").status_code == 404

    monkeypatch.setenv("AICEFR_COACH_DAILY", "1")
    from aicefr.config import get_settings

    get_settings.cache_clear()
    from aicefr.services.core.assessment.context import svc

    monkeypatch.setattr(svc(), "settings", get_settings())
    assert owner.post(f"/api/v1/responses/{rids[0]}/upgrade").status_code == 200
    assert owner.post(f"/api/v1/responses/{rids[1]}/upgrade").status_code == 429


def test_with_no_provider_the_upgrade_is_not_offered(m):
    student = login_as(m, "SV-C04")
    rid = submit_assessment(student)
    scored(m, rid)
    assert student.get(f"/api/v1/responses/{rid}/coach").json()["can_upgrade"] is False
    assert student.post(f"/api/v1/responses/{rid}/upgrade").status_code == 503


def test_saying_it_again_measures_three_rounds_against_the_first(m):
    student = login_as(m, "SV-C05")
    rid = submit_assessment(student)
    scored(m, rid)

    got = student.get(f"/api/v1/learn/retell/{rid}").json()
    assert got["rounds"] == [60, 45, 30] and got["done"] == []
    for n in (1, 2):
        r = student.post(
            f"/api/v1/learn/retell/{rid}/rounds",
            files={"audio": ("r.wav", wav(8.0), "audio/wav")},
            data={"round": str(n)},
        )
        assert r.status_code == 200, r.text
    second = r.json()["result"]
    assert second["round"] == 2 and isinstance(second["changes"], list)
    assert [a["round"] for a in student.get(f"/api/v1/learn/retell/{rid}").json()["done"]] == [1, 2]
    assert 'data-response-id="' + rid + '"' in student.get(f"/retell/{rid}").text


def test_only_the_owner_says_it_again(m):
    owner = login_as(m, "SV-C06")
    rid = submit_assessment(owner)
    scored(m, rid)
    other = login_as(m, "SV-C07")
    assert other.get(f"/api/v1/learn/retell/{rid}").status_code == 404
    r = other.post(
        f"/api/v1/learn/retell/{rid}/rounds",
        files={"audio": ("r.wav", wav(8.0), "audio/wav")},
    )
    assert r.status_code == 404


def test_a_busy_model_is_asked_once_more(monkeypatch):
    """Gemini's free tier answered 503 for a moment on the production host."""
    import io
    import urllib.error

    calls = []

    class Answer(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def flaky(request, timeout):
        calls.append(1)
        if len(calls) == 1:
            raise urllib.error.HTTPError("u", 503, "Service Unavailable", {}, None)
        body = {"choices": [{"message": {"content": "{}"}}]}
        return Answer(json.dumps(body).encode())

    monkeypatch.setattr(providers.urllib.request, "urlopen", flaky)
    monkeypatch.setattr(providers, "RETRY_WAIT_S", 0)
    p = providers.Provider("gemini", "gemini-3.5-flash-lite", "k")
    assert p.complete("{}") == "{}" and len(calls) == 2
