"""D090 unit layer: a reading passage written around the words still being said again.

* the request names the band, the words and the length, and nothing else;
* a passage is kept only when every word stands in it as asked;
* the learner's own phrases make a passage without the model;
* a reading passes a word only when every place it stands was heard clearly;
* the passage has its own price, kept in the price list and its versions;
* the provider is asked to write little: a ceiling, and low deliberation;
* passages are kept per learner, found again for the same words, and erased.
"""

from __future__ import annotations

import json

import pytest
from dbutil import store

from aicefr.coach import passage, providers
from aicefr.coach.upgrade import UpgradeError
from aicefr.lessons.drill import judge_passage, passage_step
from aicefr.lessons.model import StepKind, StepResult, WordMark, WordStatus
from aicefr.metering.pricing import PriceList, as_idpoint, passage_units
from aicefr.pronunciation.vietnamese import Pattern
from aicefr.services.core.metering.price_book import PriceBook
from aicefr.storage.drill_repository import DrillPassage, DrillRepository, PassageTake
from aicefr.storage.metering_repository import MeteringRepository

pytestmark = pytest.mark.unit

WORDS = ["worked", "three", "months"]
TEXT = (
    "Last year I worked in a small shop for three months. "
    "The three months went fast, and I worked hard every day."
)


def test_the_request_names_the_band_the_words_and_the_length():
    asked = json.loads(passage.user_message("A2", WORDS))
    assert asked == {"band": "A2", "words": WORDS, "length_words": "50-70"}
    assert json.loads(passage.user_message(None, WORDS))["band"] == "B1"
    assert json.loads(passage.user_message("X9", WORDS))["length_words"] == "60-90"


def test_a_passage_is_kept_only_with_every_word_as_asked():
    made = passage.parse(json.dumps({"text": "  " + TEXT + "  "}), WORDS, "B1")
    assert made.text == TEXT and made.words == WORDS
    with pytest.raises(UpgradeError, match="thiếu từ months"):
        passage.parse(json.dumps({"text": "I worked there for three weeks."}), WORDS, "B1")
    with pytest.raises(UpgradeError, match="thiếu từ worked"):
        passage.parse(json.dumps({"text": "I work for three months."}), WORDS, "B1")
    with pytest.raises(UpgradeError, match="quá dài"):
        passage.parse(json.dumps({"text": TEXT + " word" * 200}), WORDS, "B1")
    for bad in ("không phải json", json.dumps(["x"]), json.dumps({"text": ""})):
        with pytest.raises(UpgradeError):
            passage.parse(bad, WORDS, "B1")


def test_the_places_of_each_word_follow_the_written_words():
    places = passage.places(TEXT, WORDS)
    shown = TEXT.split()
    assert [shown[i] for i in places["worked"]] == ["worked", "worked"]
    assert [shown[i] for i in places["months"]] == ["months.", "months"]
    assert len(places["three"]) == 2


def test_the_learners_own_phrases_make_a_passage_without_the_model():
    made = passage.from_phrases(["I worked very hard", "in three cities,", "for six months"], WORDS)
    assert made.text == "I worked very hard. In three cities. For six months."
    assert all(passage.places(made.text, WORDS).values())


def _result(text: str, statuses: dict[int, tuple[WordStatus, str | None, str | None]]):
    marks = [
        WordMark(
            index=i,
            text=w,
            status=statuses.get(i, (WordStatus.HEARD, None, None))[0],
            said=statuses.get(i, (WordStatus.HEARD, None, None))[1],
            pattern=statuses.get(i, (WordStatus.HEARD, None, None))[2],
        )
        for i, w in enumerate(text.split())
    ]
    return StepResult(step_id="p", kind=StepKind.READ_ALOUD, passed=True, words=marks)


def test_a_word_passes_only_where_every_place_was_heard_clearly():
    places = passage.places(TEXT, WORDS)
    second_worked = places["worked"][1]
    result = _result(TEXT, {second_worked: (WordStatus.UNSURE, "work", "ed_ending")})
    verdicts = judge_passage(result, places)
    assert verdicts["three"].passed and verdicts["months"].passed
    worked = verdicts["worked"]
    assert (worked.measured, worked.passed, worked.said, worked.pattern) == (
        True,
        False,
        "work",
        Pattern.ED_ENDING,
    )
    silent = StepResult(step_id="p", kind=StepKind.READ_ALOUD, passed=False, measured=False)
    assert not any(v.measured or v.passed for v in judge_passage(silent, places).values())


def test_the_passage_is_read_aloud_with_its_words_highlighted():
    step = passage_step(TEXT, WORDS)
    assert (step.kind, step.text, step.hint_words, step.max_seconds) == (
        StepKind.READ_ALOUD,
        TEXT,
        WORDS,
        90,
    )


def test_a_passage_has_its_own_price_kept_in_the_versions():
    prices = PriceList()
    assert passage_units(prices) == 100 and as_idpoint(prices, 100) == 200
    assert prices.as_dict()["passage_runs"] == 0.1
    with pytest.raises(ValueError):
        PriceList(passage_runs=-1)
    book = PriceBook(MeteringRepository(store()), PriceList(passage_runs=0.2))
    # A version saved before D090 has no passage price: the default stands.
    book.store.col("price_list").insert_one(
        {
            "_id": "current",
            "version": "price-admin-1",
            "first_minute_runs": 1.0,
            "extra_minute_runs": 0.7,
            "upgrade_runs": 0.5,
            "idpoint_per_run": 2000,
            "packs": [],
        }
    )
    current = book.current()
    assert (current.version, current.upgrade_runs, current.passage_runs) == (
        "price-admin-1",
        0.5,
        0.2,
    )


class _Answer:
    def __init__(self, body: bytes) -> None:
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def read(self) -> bytes:
        return self.body


def test_the_provider_is_asked_to_write_little(monkeypatch):
    sent: list[dict] = []
    answer = {"choices": [{"message": {"content": "{}"}}], "usage": {}}

    def urlopen(request, timeout):
        sent.append(json.loads(request.data))
        return _Answer(json.dumps(answer).encode())

    monkeypatch.setattr(providers.urllib.request, "urlopen", urlopen)
    providers.Provider("gemini", "m", "k").complete_with_usage("{}", max_tokens=1200)
    providers.Provider("groq", "m", "k").complete_with_usage("{}", max_tokens=1200)
    providers.Provider("gemini", "m", "k").complete_with_usage("{}")
    assert (sent[0]["max_tokens"], sent[0]["reasoning_effort"]) == (1200, "low")
    assert sent[1]["max_tokens"] == 1200 and "reasoning_effort" not in sent[1]
    assert "max_tokens" not in sent[2]  # the upgrade and the lesson draft: unchanged


def test_passages_are_found_again_for_the_same_words_and_erased():
    repo = DrillRepository(store())
    a = repo.save_passage(DrillPassage("p-1", "acc-1", WORDS, ["d1", "d2", "d3"], TEXT, "model"))
    repo.save_passage(DrillPassage("p-2", "acc-1", WORDS[:2], ["d1", "d2"], "x", "phrases"))
    assert repo.passage_for("acc-1", ["d3", "d1", "d2"]).passage_id == a.passage_id
    assert repo.passage_for("acc-1", ["d1", "d2", "d4"]) is None
    assert repo.passage_for("acc-2", ["d1", "d2", "d3"]) is None
    assert repo.model_passages_since("acc-1", "2000-01-01") == 1  # phrases are free
    repo.record_passage_take("acc-1", "p-1", PassageTake(["worked"], ["three"], "2026-11-03"))
    (kept, _) = repo.passages_of("acc-1")
    assert kept["takes"] == [
        {"clear": ["worked"], "unclear": ["three"], "created_at": "2026-11-03"}
    ]
    assert repo.erase_account("acc-1") == 2
    assert repo.passage("acc-1", "p-1") is None
