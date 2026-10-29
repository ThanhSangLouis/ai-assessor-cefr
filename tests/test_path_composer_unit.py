"""Layer 1 for the path model (D046): the goal, the relevance, the learned order.

Pure functions over hand-built lessons; no database, no network, deterministic.
"""

from __future__ import annotations

import pytest

from aicefr.contracts import Band, Criterion
from aicefr.lessons.composer import (
    MIN_ORDER_PAIRS,
    PRIOR_ORDER,
    Candidate,
    Goal,
    Learner,
    compose,
    fit_order,
    parse_wish,
    plain,
)
from aicefr.lessons.model import Lesson, Step, StepKind, Topic
from aicefr.pronunciation.vietnamese import Pattern

pytestmark = pytest.mark.unit


def lesson(
    lesson_id: str,
    band: Band = Band.A2,
    text: str = "I like my small room.",
    title: str | None = None,
    criterion: Criterion | None = None,
    steps: int = 3,
    keywords: tuple[str, ...] = (),
) -> Lesson:
    kinds = [StepKind.READ_ALOUD, StepKind.KEYWORDS, StepKind.FREE, StepKind.GAP, StepKind.REPEAT]
    return Lesson(
        lesson_id=lesson_id,
        title=title or f"Bài {lesson_id}",
        band=band,
        criterion=criterion,
        model_text=text,
        keywords=list(keywords),
        steps=[Step(kind=kinds[i % len(kinds)], text=text) for i in range(steps)],
    )


def cand(
    les: Lesson,
    topic: Topic | None = None,
    path: str = "p1",
    position: int = 0,
    attempts: int = 0,
    passed: int = 0,
) -> Candidate:
    return Candidate(les, path, f"Lộ trình {path}", "Chặng", topic, les.criterion, position,
                     attempts, passed)  # fmt: skip


def ids(plan) -> list[str]:
    return plan.lesson_ids


# ================================================================= the goal


def test_a_wish_in_vietnamese_names_topics_criteria_sounds_and_bands():
    topics, criteria, patterns, bands = parse_wish(
        "Muốn luyện kể chuyện du lịch, tập trung trôi chảy và âm cuối, từ A2 lên B1"
    )
    assert topics == [Topic.TRAVEL]
    assert criteria == [Criterion.FLUENCY]
    assert patterns == [Pattern.FINAL_CONSONANT]
    assert bands == [Band.A2, Band.B1]


def test_marks_do_not_matter_and_short_words_need_a_word_boundary():
    assert plain("Sức Khỏe") == plain("suc khoe")
    assert parse_wish("suc khoe")[0] == [Topic.HEALTH]
    # "benh" is short: it must be a word of its own, not part of another.
    assert parse_wish("benhvien")[0] == []
    # A phrase matches whole words only: "ẩm thực" is food, not the th sound.
    topics, _, patterns, _ = parse_wish("du lịch và ẩm thực")
    assert topics == [Topic.TRAVEL, Topic.FOOD] and patterns == []
    assert parse_wish("luyện âm th")[2] == [Pattern.TH_SOUND]


def test_the_resolved_goal_orders_bands_and_bounds_the_length():
    g = Goal(band_from=Band.B2, band_to=Band.A2, length=99).resolved()
    assert (g.band_from, g.band_to, g.length) == (Band.A2, Band.B2, 30)
    assert Goal(wish="B1", length=1).resolved().band_from is Band.B1
    assert Goal(length=1).resolved().length == 3


# ================================================================= relevance and selection


def test_the_band_asked_for_comes_first_and_others_only_fill_in():
    pool = [cand(lesson(f"a{i}", Band.A2, text=f"Text {i} here.")) for i in range(3)]
    pool += [cand(lesson(f"b{i}", Band.B1, text=f"Words {i} there.")) for i in range(3)]
    plan = compose(pool, [], Goal(band_from=Band.B1, band_to=Band.B1, length=3))
    assert sorted(ids(plan)) == ["b0", "b1", "b2"]
    assert not plan.warnings or all("trình độ liền kề" not in w for w in plan.warnings)

    plan = compose(pool, [], Goal(band_from=Band.B1, band_to=Band.B1, length=5))
    assert set(ids(plan)) >= {"b0", "b1", "b2"} and len(ids(plan)) == 5
    assert any("trình độ liền kề" in w for w in plan.warnings)
    # Two bands away is never offered.
    pool.append(cand(lesson("c0", Band.B2)))
    plan = compose(pool, [], Goal(band_from=Band.A2, band_to=Band.A2, length=10))
    assert "c0" not in ids(plan)


def test_topic_and_criterion_rank_the_matching_lessons_first_with_their_reasons():
    pool = [
        cand(lesson("food", criterion=Criterion.RANGE), Topic.FOOD),
        cand(lesson("trip", criterion=Criterion.FLUENCY), Topic.TRAVEL),
        cand(lesson("home"), Topic.DAILY_LIFE),
    ]
    plan = compose(pool, [], Goal(topics=(Topic.TRAVEL,), criteria=(Criterion.FLUENCY,), length=3))
    first = plan.as_dict()["units"][0]["lessons"]
    best = max(first, key=lambda x: x["relevance"])
    assert best["lesson_id"] == "trip"
    assert "Chủ đề Du lịch" in best["reasons"]
    assert any("Độ trôi chảy" in r for r in best["reasons"])


def test_english_words_of_a_wish_match_the_lesson_text():
    pool = [
        cand(lesson("air", text="I checked in at the airport and waited for my flight.")),
        cand(lesson("cook", text="I cook rice and vegetables for dinner.")),
    ]
    plan = compose(pool, [], Goal(wish="airport flight", length=3))
    top = max(plan.as_dict()["units"][0]["lessons"], key=lambda x: x["relevance"])
    assert top["lesson_id"] == "air"
    assert any("airport" in r for r in top["reasons"])


def test_pronunciation_patterns_favour_lessons_with_more_chances_to_practise_them():
    pool = [
        cand(lesson("many", text="I walked, talked and played, then I worked and cooked.")),
        cand(lesson("few", text="I am happy to see you here today.")),
    ]
    plan = compose(pool, [], Goal(patterns=(Pattern.ED_ENDING,), length=3))
    lessons = {x["lesson_id"]: x for x in plan.as_dict()["units"][0]["lessons"]}
    assert lessons["many"]["relevance"] > lessons["few"]["relevance"]
    assert any("đuôi -ed" in r for r in lessons["many"]["reasons"])


def test_a_lesson_copied_into_two_paths_is_picked_once():
    pool = [cand(lesson("x1", title="Same", text="Same text.")),
            cand(lesson("x2", title="Same", text="Same text."), path="p2"),
            cand(lesson("y", title="Other", text="Other words here."))]  # fmt: skip
    plan = compose(pool, [], Goal(length=3))
    assert len(ids(plan)) == 2 and "y" in ids(plan)


def test_a_learner_gets_new_lessons_first_and_finished_ones_only_to_fill_up():
    pool = [cand(lesson(f"l{i}", text=f"Sentence number {i}.")) for i in range(5)]
    learner = Learner(band=Band.A2, completed=frozenset({"l0", "l1"}), started=frozenset({"l2"}))
    plan = compose(pool, [], Goal(length=3), learner)
    assert set(ids(plan)) == {"l2", "l3", "l4"}
    plan = compose(pool, [], Goal(length=4), learner)
    assert len(ids(plan)) == 4 and {"l2", "l3", "l4"} <= set(ids(plan))


def test_the_learners_weakest_criterion_is_named_as_the_reason():
    pool = [cand(lesson("flu", criterion=Criterion.FLUENCY)), cand(lesson("acc"))]
    learner = Learner(band=Band.A2, weakest=(Criterion.FLUENCY,))
    plan = compose(pool, [], Goal(length=3), learner)
    flu = next(x for u in plan.as_dict()["units"] for x in u["lessons"] if x["lesson_id"] == "flu")
    assert any("yếu nhất" in r for r in flu["reasons"])


def test_too_few_lessons_is_said_not_hidden():
    plan = compose([cand(lesson("only"))], [], Goal(length=5, topics=(Topic.HEALTH,)))
    assert ids(plan) == ["only"]
    assert any("Chỉ tìm được 1 bài" in w for w in plan.warnings)
    assert any("Sức khoẻ" in w for w in plan.warnings)


# ================================================================= the learned order


def _paths_ordered_by_length(n_paths: int = 4) -> list[list[Candidate]]:
    """Paths whose teachers put LONGER texts first, within one band: the opposite
    of the fixed rule, so only a learned order gets them right."""
    paths = []
    for p in range(n_paths):
        seq = []
        for i in range(6):
            words = " ".join(["word"] * (100 - 15 * i))
            seq.append(cand(lesson(f"p{p}l{i}", text=words), path=f"p{p}", position=i))
        paths.append(seq)
    return paths


def test_the_order_teachers_use_is_learned_from_their_paths():
    model = fit_order(_paths_ordered_by_length())
    assert model.learned and model.pairs == 20
    assert model.agreement == 1.0
    assert model.describe()["weights"]["text_words"] < 0


def test_with_few_pairs_the_fixed_order_is_used_and_said():
    model = fit_order(_paths_ordered_by_length(1)[:1])
    assert not model.learned and model.pairs < MIN_ORDER_PAIRS
    assert list(model.weights) == list(PRIOR_ORDER)
    plan = compose([cand(lesson("a"))], [], Goal(length=3))
    assert any("chưa đủ" in w for w in plan.warnings)


def test_the_plan_follows_the_learned_order_and_rises_through_the_bands():
    paths = _paths_ordered_by_length()
    pool = [cand(lesson("long", text=" ".join(["word"] * 90))),
            cand(lesson("short", text="word word word")),
            cand(lesson("b1", Band.B1, text="word word"))]  # fmt: skip
    plan = compose(pool, paths, Goal(length=3))
    assert ids(plan) == ["long", "short", "b1"]
    assert [u.band for u in plan.units] == [Band.A2, Band.B1]


def test_difficulty_comes_from_attempts_once_there_are_enough():
    easy = cand(lesson("e"), attempts=20, passed=18)
    hard = cand(lesson("h"), attempts=20, passed=4)
    unknown = cand(lesson("u"), attempts=3, passed=0)
    assert easy.pass_rate == 0.9 and hard.pass_rate == 0.2 and unknown.pass_rate is None


def test_the_same_input_gives_the_same_plan():
    paths = _paths_ordered_by_length()
    pool = [c for seq in paths for c in seq]
    goal = Goal(wish="word", length=8)
    assert compose(pool, paths, goal).as_dict() == compose(pool, paths, goal).as_dict()
