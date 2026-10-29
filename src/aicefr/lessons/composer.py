"""Compose a lesson path from the lessons that already exist (D046).

A teacher describes the path they want, or a learner says what they want to
practise; this model picks lessons out of the existing paths and puts them in
an order. It never writes a sentence: every lesson it proposes is one a teacher
wrote and published (D025), and every pick carries the reasons it was picked.

Three parts, each readable on its own:

1. **Goal.** The form's fields plus a free wish in Vietnamese or English
   ("luyện kể chuyện du lịch, tập trung trôi chảy"). `parse_wish` turns the
   wish into topics, criteria, pronunciation patterns and bands by a fixed word
   list; English words in it also match the lessons' text (TF-IDF).
2. **Relevance.** Each candidate lesson gets a score from six signals -- band,
   criterion, topic, text, pronunciation and, for a learner, their own
   progress -- weighted by `WEIGHTS`. Similar lessons are spread out (maximal
   marginal relevance), and the same lesson copied into two paths counts once.
3. **Order, learned from the existing paths.** Teachers already put lessons in
   an order in every path they built. `fit_order` reads each pair of
   consecutive lessons as "this one comes before that one" and fits a pairwise
   logistic model on the lessons' features (band, ladder length, text length,
   difficulty measured from learners' attempts). With too few pairs it falls
   back to a fixed order by band and length, and says so.

Deterministic: the same lessons, attempts and goal give the same path.
"""

from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field, replace

import numpy as np

from aicefr.contracts import Band, Criterion
from aicefr.lessons.model import TOPIC_NAMES, Lesson, StepKind, Topic
from aicefr.lessons.text import is_content, tokens
from aicefr.practice.bank import CRITERION_NAMES
from aicefr.pronunciation.vietnamese import PATTERN_NAMES, Pattern, opportunities

COMPOSER_VERSION = "path-composer-v1"

BANDS: tuple[Band, ...] = tuple(Band)
BAND_RANK = {b: i for i, b in enumerate(BANDS)}
MIN_LENGTH, MAX_LENGTH = 3, 30

# How much each signal counts in the relevance score. A signal the goal says
# nothing about scores 0.5 for every lesson, so it changes no ranking.
WEIGHTS = {
    "band": 3.0,
    "criterion": 2.0,
    "topic": 2.5,
    "text": 1.5,
    "pronunciation": 1.5,
    "progress": 1.0,
}
# Maximal marginal relevance: how strongly a lesson like one already picked is
# held back. 0 would pick by relevance alone; 1 would favour variety above fit.
DIVERSITY = 0.25
# Below this many consecutive pairs in the existing paths the order model is
# not fitted; `PRIOR_ORDER` is used instead.
MIN_ORDER_PAIRS = 12
ORDER_FEATURES = ("band", "steps", "text_words", "difficulty")
PRIOR_ORDER = np.array([3.0, -0.5, 0.5, 1.0])  # band first, then harder and longer later
# Difficulty is read from attempts only with this many of them; before that a
# lesson is assumed as hard as its band.
MIN_ATTEMPTS_FOR_DIFFICULTY = 10


# ================================================================= the goal

_TOPIC_WORDS: dict[Topic, tuple[str, ...]] = {
    Topic.DAILY_LIFE: ("doi song", "hang ngay", "gia dinh", "nha cua", "sinh hoat", "daily"),
    Topic.EDUCATION: ("giao duc", "truong", "lop hoc", "hoc tap", "mon hoc", "education", "school"),
    Topic.TRAVEL: ("du lich", "san bay", "khach san", "di choi", "chuyen di", "travel", "trip"),
    Topic.CAREER: ("nghe nghiep", "cong viec", "phong van", "viec lam", "career", "job"),
    Topic.FOOD: ("am thuc", "mon an", "nau an", "nha hang", "do an", "food", "cooking"),
    Topic.HEALTH: ("suc khoe", "the thao", "benh", "tap luyen", "health", "sport"),
    Topic.TECHNOLOGY: ("cong nghe", "may tinh", "dien thoai", "internet", "technology"),
    Topic.ENVIRONMENT: ("moi truong", "khi hau", "o nhiem", "environment", "climate"),
    Topic.PEOPLE: ("con nguoi", "ban be", "tinh cach", "nguoi noi tieng", "people", "friend"),
    Topic.SOCIETY: ("xa hoi", "cong dong", "society", "community"),
}  # fmt: skip
_CRITERION_WORDS: dict[Criterion, tuple[str, ...]] = {
    Criterion.FLUENCY: ("troi chay", "luu loat", "fluency", "fluent"),
    Criterion.COHERENCE: ("mach lac", "lien ket", "coherence"),
    Criterion.RANGE: ("tu vung", "von tu", "range", "vocabulary"),
    Criterion.ACCURACY: ("ngu phap", "chinh xac", "accuracy", "grammar"),
    Criterion.PHONOLOGY: ("phat am", "pronunciation", "phonology"),
}
_PATTERN_WORDS: dict[Pattern, tuple[str, ...]] = {
    Pattern.FINAL_CONSONANT: ("am cuoi", "phu am cuoi", "final consonant"),
    Pattern.ED_ENDING: ("duoi ed", "duoi -ed", "-ed"),
    Pattern.S_ENDING: ("duoi s", "duoi -s", "duoi es", "-s ending"),
    Pattern.TH_SOUND: ("am th", "th sound"),
    Pattern.CLUSTER: ("cum phu am", "cluster"),
}
_BAND_RE = re.compile(r"\b(a1|a2|b1|b2|c1|c2)\b")
# Vietnamese words of a wish that say nothing about content ("luyện ở trường"
# should match on "truong", not on "luyen" or "o"). Without marks, as `plain` gives.
VI_STOPWORDS = frozenset(
    """bai ban cac cach cho chu chuyen cua cung duoc gi hay hon khi khong la lam luyen minh mot
    muon nhieu nhung noi nua roi sao tap the thi toi trong trung tu va ve voi vua""".split()
)


def plain(text: str) -> str:
    """Lower case without Vietnamese marks, so "sức khỏe" and "suc khoe" match."""
    text = text.lower().replace("đ", "d")
    text = "".join(ch for ch in unicodedata.normalize("NFD", text) if not unicodedata.combining(ch))
    text = re.sub(r"[^\w\s-]", " ", text)  # "du lich," is "du lich"
    return f" {' '.join(text.split())} "


def content_words(text: str) -> list[str]:
    """Words worth matching on: English content words and Vietnamese syllables, unmarked."""
    return [
        word
        for word in tokens(plain(text))
        if len(word) >= 3 and is_content(word) and word not in VI_STOPWORDS
    ]


@dataclass(frozen=True)
class Goal:
    """What the path is for. Every field is optional; `wish` fills in the rest."""

    band_from: Band | None = None
    band_to: Band | None = None
    criteria: tuple[Criterion, ...] = ()
    topics: tuple[Topic, ...] = ()
    patterns: tuple[Pattern, ...] = ()
    wish: str = ""
    length: int = 8

    def resolved(self) -> Goal:
        """The goal with what the wish names added, the bands in order, the length bounded."""
        topics, criteria, patterns, bands = parse_wish(self.wish)
        band_from, band_to = self.band_from, self.band_to
        if bands and band_from is None and band_to is None:
            band_from, band_to = min(bands, key=BAND_RANK.get), max(bands, key=BAND_RANK.get)
        if band_from and band_to and BAND_RANK[band_from] > BAND_RANK[band_to]:
            band_from, band_to = band_to, band_from
        return Goal(
            band_from=band_from,
            band_to=band_to,
            criteria=_merge(self.criteria, criteria),
            topics=_merge(self.topics, topics),
            patterns=_merge(self.patterns, patterns),
            wish=self.wish,
            length=min(MAX_LENGTH, max(MIN_LENGTH, int(self.length))),
        )


def _merge(first: Sequence, second: Iterable) -> tuple:
    out = list(first)
    out.extend(x for x in second if x not in out)
    return tuple(out)


def parse_wish(
    wish: str,
) -> tuple[list[Topic], list[Criterion], list[Pattern], list[Band]]:
    """Topics, criteria, pronunciation patterns and bands a free wish names."""
    text = plain(wish)

    def says(word: str) -> bool:
        # Whole words always for phrases ("am th" must not match "am thuc") and
        # short words ("benh"); a long single word may carry an ending.
        word = word.strip()
        return f" {word} " in text or (" " not in word and len(word) > 4 and word in text)

    def named(table: dict) -> list:
        return [key for key, words in table.items() if any(says(w) for w in words)]

    bands = [Band(m.upper()) for m in _BAND_RE.findall(text)]
    return named(_TOPIC_WORDS), named(_CRITERION_WORDS), named(_PATTERN_WORDS), bands


# ================================================================= the candidates


@dataclass(frozen=True)
class Candidate:
    """A published lesson where it sits, with what learners' attempts say of it."""

    lesson: Lesson
    path_id: str
    path_title: str
    unit_title: str
    topic: Topic | None
    criterion: Criterion | None
    position: int  # the lesson's place in its path, from 0
    attempts: int = 0
    passed: int = 0

    @property
    def lesson_id(self) -> str:
        return self.lesson.lesson_id

    @property
    def band(self) -> Band:
        return self.lesson.band

    @property
    def pass_rate(self) -> float | None:
        if self.attempts < MIN_ATTEMPTS_FOR_DIFFICULTY:
            return None
        return self.passed / self.attempts

    def text_words(self) -> list[str]:
        """Content words of the model text and key words: what a reason may quote."""
        return content_words(" ".join([self.lesson.model_text, *self.lesson.keywords]))

    def english_words(self) -> list[str]:
        """Content words of what the learner says: the model text, the steps, the key words."""
        parts = [self.lesson.model_text, *self.lesson.keywords]
        for step in self.lesson.steps:
            parts.append(step.text)
            parts.extend(step.keywords)
        return content_words(" ".join(parts))

    def words(self) -> list[str]:
        """What a wish is matched on: the English words, the Vietnamese title and summary."""
        vietnamese = f"{self.lesson.title} {self.lesson.summary} {self.unit_title}"
        return self.english_words() + content_words(vietnamese)

    def fingerprint(self) -> str:
        """The same lesson copied into another path has the same title and text."""
        return plain(self.lesson.title + " " + self.lesson.model_text).strip()


@dataclass(frozen=True)
class Learner:
    """A learner's own standing, for a path made for them."""

    band: Band | None = None
    weakest: tuple[Criterion, ...] = ()
    weak_patterns: tuple[Pattern, ...] = ()
    completed: frozenset[str] = frozenset()
    started: frozenset[str] = frozenset()


# ================================================================= the order model


def order_features(c: Candidate) -> np.ndarray:
    rate = c.pass_rate
    difficulty = (1.0 - rate) if rate is not None else 0.2 * BAND_RANK[c.band]
    return np.array(
        [
            BAND_RANK[c.band],
            len(c.lesson.steps),
            len(tokens(c.lesson.model_text)) / 50.0,
            difficulty,
        ],
        dtype=float,
    )


@dataclass(frozen=True)
class OrderModel:
    """A linear score; a lesson with a lower score comes earlier in a path."""

    weights: np.ndarray
    pairs: int
    agreement: float | None  # share of the existing pairs the fitted model orders right
    learned: bool

    def score(self, c: Candidate) -> float:
        return float(self.weights @ order_features(c))

    def describe(self) -> dict:
        return {
            "learned": self.learned,
            "pairs": self.pairs,
            "agreement": None if self.agreement is None else round(self.agreement, 3),
            "weights": {
                name: round(float(w), 3)
                for name, w in zip(ORDER_FEATURES, self.weights, strict=True)
            },
        }


def fit_order(paths: Iterable[Sequence[Candidate]], l2: float = 0.1) -> OrderModel:
    """Learn the order teachers use from the consecutive lessons of their paths.

    Pairwise logistic regression without intercept: for consecutive lessons a
    then b, P(a before b) = sigmoid(w . (f(b) - f(a))). Each pair also enters
    reversed with the label flipped, so the model is symmetric. Plain gradient
    descent on a convex loss: no randomness, the same paths give the same w.
    """
    diffs = []
    for lessons in paths:
        feats = [order_features(c) for c in lessons]
        diffs.extend(b - a for a, b in zip(feats, feats[1:], strict=False))
    if len(diffs) < MIN_ORDER_PAIRS:
        return OrderModel(PRIOR_ORDER.copy(), len(diffs), None, learned=False)
    x = np.vstack(diffs + [-d for d in diffs])
    y = np.concatenate([np.ones(len(diffs)), np.zeros(len(diffs))])
    scale = x.std(axis=0)
    scale[scale == 0] = 1.0
    xs = x / scale
    w = np.zeros(xs.shape[1])
    for _ in range(500):
        p = 1.0 / (1.0 + np.exp(-(xs @ w)))
        w -= 0.5 * (xs.T @ (p - y) / len(y) + l2 * w)
    weights = w / scale
    learned = _agreement(diffs, weights)
    prior = _agreement(diffs, PRIOR_ORDER)
    if learned <= prior:
        # The fit did not order the existing paths better than the fixed rule:
        # keep the rule, and say how well it does.
        return OrderModel(PRIOR_ORDER.copy(), len(diffs), prior, learned=False)
    return OrderModel(weights, len(diffs), learned, learned=True)


def _agreement(diffs: list[np.ndarray], weights: np.ndarray) -> float:
    """Share of the existing pairs put in the teachers' order; a tie counts half."""
    margins = np.vstack(diffs) @ weights
    return float(np.mean(np.where(np.isclose(margins, 0.0), 0.5, margins > 0)))


# ================================================================= relevance


def _tfidf(docs: list[list[str]]) -> tuple[list[dict[str, float]], dict[str, float]]:
    df: Counter[str] = Counter()
    for doc in docs:
        df.update(set(doc))
    n = len(docs)
    idf = {t: math.log((1 + n) / (1 + k)) + 1.0 for t, k in df.items()}
    vectors = []
    for doc in docs:
        tf = Counter(doc)
        vec = {t: (1 + math.log(k)) * idf[t] for t, k in tf.items()}
        norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
        vectors.append({t: v / norm for t, v in vec.items()})
    return vectors, idf


def _cosine(a: dict[str, float], b: dict[str, float]) -> float:
    if len(a) > len(b):
        a, b = b, a
    return sum(v * b.get(t, 0.0) for t, v in a.items())


def _band_fit(band: Band, goal: Goal, learner: Learner | None) -> float:
    rank = BAND_RANK[band]
    if goal.band_from or goal.band_to:
        lo = BAND_RANK[goal.band_from or BANDS[0]]
        hi = BAND_RANK[goal.band_to or BANDS[-1]]
        if lo <= rank <= hi:
            return 1.0
        return 0.3 if min(abs(rank - lo), abs(rank - hi)) == 1 else 0.0
    if learner and learner.band:
        gap = rank - BAND_RANK[learner.band]
        return {0: 1.0, 1: 0.75, -1: 0.4}.get(gap, 0.1)
    return 0.5


@dataclass
class Pick:
    candidate: Candidate
    relevance: float
    signals: dict[str, float]
    reasons: list[str] = field(default_factory=list)


def score_candidates(
    candidates: Sequence[Candidate], goal: Goal, learner: Learner | None = None
) -> list[Pick]:
    """Every candidate with its relevance, signals and reasons, best first."""
    criteria = _merge(goal.criteria, learner.weakest if learner else ())
    patterns = _merge(goal.patterns, learner.weak_patterns if learner else ())
    docs = [c.words() for c in candidates]
    wish = content_words(goal.wish)
    vectors, _ = _tfidf(docs + [wish])
    query = vectors[-1]
    content = [c.english_words() for c in candidates]
    pron = [
        sum(1 for w in words if opportunities(w) & set(patterns)) / max(1, len(words))
        for words in content
    ]
    top_pron = max(pron, default=0.0) or 1.0

    picks = []
    for i, c in enumerate(candidates):
        s: dict[str, float] = {"band": _band_fit(c.band, goal, learner)}
        reasons: list[str] = []
        if s["band"] >= 1.0 and (goal.band_from or goal.band_to or (learner and learner.band)):
            reasons.append(f"Đúng trình độ {c.band.value}")

        if criteria:
            s["criterion"] = 1.0 if c.criterion in criteria else 0.0
            if c.criterion in criteria:
                why = (
                    "tiêu chí yếu nhất trong bài đánh giá gần nhất"
                    if learner
                    and c.criterion in learner.weakest
                    and c.criterion not in goal.criteria
                    else "tiêu chí bạn chọn"
                )
                reasons.append(f"Luyện {CRITERION_NAMES[c.criterion]} — {why}")
        else:
            s["criterion"] = 0.5

        if goal.topics:
            s["topic"] = 1.0 if c.topic in goal.topics else 0.0
            if c.topic in goal.topics:
                reasons.append(f"Chủ đề {TOPIC_NAMES[c.topic]}")
        else:
            s["topic"] = 0.5

        if query:
            sim = _cosine(query, vectors[i])
            s["text"] = min(1.0, sim * 2.5)
            shared = sorted(set(wish) & set(candidates[i].text_words()))
            if shared and sim > 0:
                reasons.append("Khớp từ: " + ", ".join(shared[:4]))
        else:
            s["text"] = 0.5

        if patterns:
            s["pronunciation"] = pron[i] / top_pron
            hits = sorted({w for w in content[i] if opportunities(w) & set(patterns)})
            if hits:
                names = ", ".join(PATTERN_NAMES[p].lower() for p in patterns)
                reasons.append(f"{len(hits)} từ để luyện {names}")
        else:
            s["pronunciation"] = 0.5

        if learner:
            if c.lesson_id in learner.completed:
                s["progress"] = 0.0
                reasons.append("Bạn đã hoàn thành — đưa vào để ôn")
            elif c.lesson_id in learner.started:
                s["progress"] = 1.0
                reasons.append("Bạn đang làm dở bài này")
            else:
                s["progress"] = 0.7
        else:
            s["progress"] = 0.5

        relevance = sum(WEIGHTS[k] * v for k, v in s.items()) / sum(WEIGHTS.values())
        picks.append(Pick(c, relevance, s, reasons))
    picks.sort(key=lambda p: (-p.relevance, p.candidate.path_id, p.candidate.position))
    return picks


def _likeness(a: Candidate, b: Candidate) -> float:
    same_topic = 1.0 if a.topic is not None and a.topic == b.topic else 0.0
    wa, wb = set(a.lesson.keywords), set(b.lesson.keywords)
    jaccard = len(wa & wb) / len(wa | wb) if wa | wb else 0.0
    return 0.6 * same_topic + 0.4 * jaccard


def select(picks: Sequence[Pick], length: int, exclude: frozenset[str] = frozenset()) -> list[Pick]:
    """Up to `length` picks: one copy of each lesson, relevant, not all alike."""
    seen: set[str] = set()
    pool = []
    for p in picks:
        key = p.candidate.fingerprint()
        if key in seen or p.candidate.lesson_id in exclude or p.signals["band"] == 0.0:
            continue
        seen.add(key)
        pool.append(p)
    chosen: list[Pick] = []
    while pool and len(chosen) < length:
        best = max(
            pool,
            key=lambda p: (
                p.relevance
                - DIVERSITY * max((_likeness(p.candidate, q.candidate) for q in chosen), default=0)
            ),
        )
        chosen.append(best)
        pool.remove(best)
    return chosen


# ================================================================= the plan


@dataclass
class PlanUnit:
    title: str
    band: Band
    topic: Topic | None
    criterion: Criterion | None
    picks: list[Pick]


@dataclass
class Plan:
    goal: Goal
    units: list[PlanUnit]
    order: OrderModel
    warnings: list[str]
    candidates: int

    @property
    def lesson_ids(self) -> list[str]:
        return [p.candidate.lesson_id for u in self.units for p in u.picks]

    def as_dict(self) -> dict:
        g = self.goal
        return {
            "model_version": COMPOSER_VERSION,
            "goal": goal_dict(g),
            "candidates": self.candidates,
            "order_model": self.order.describe(),
            "warnings": self.warnings,
            "units": [
                {
                    "title": u.title,
                    "band": u.band.value,
                    "topic": u.topic.value if u.topic else None,
                    "criterion": u.criterion.value if u.criterion else None,
                    "lessons": [
                        {
                            "lesson_id": p.candidate.lesson_id,
                            "title": p.candidate.lesson.title,
                            "summary": p.candidate.lesson.summary,
                            "band": p.candidate.band.value,
                            "criterion": p.candidate.criterion.value
                            if p.candidate.criterion
                            else None,
                            "topic": p.candidate.topic.value if p.candidate.topic else None,
                            "from_path": p.candidate.path_title,
                            "steps": len(p.candidate.lesson.steps),
                            "free_steps": sum(
                                1 for s in p.candidate.lesson.steps if s.kind is StepKind.FREE
                            ),
                            "relevance": round(p.relevance, 3),
                            "signals": {k: round(v, 3) for k, v in p.signals.items()},
                            "reasons": p.reasons,
                        }
                        for p in u.picks
                    ],
                }
                for u in self.units
            ],
        }


def goal_dict(g: Goal) -> dict:
    return {
        "band_from": g.band_from.value if g.band_from else None,
        "band_to": g.band_to.value if g.band_to else None,
        "criteria": [c.value for c in g.criteria],
        "topics": [t.value for t in g.topics],
        "patterns": [p.value for p in g.patterns],
        "wish": g.wish,
        "length": g.length,
    }


def _unit_title(band: Band, topics: list[Topic | None], criterion: Criterion | None) -> str:
    """ "B1 · Du lịch, Ẩm thực": the band, then the topics in the order they come."""
    names = []
    for t in topics:
        if t is not None and TOPIC_NAMES[t] not in names:
            names.append(TOPIC_NAMES[t])
    if names:
        shown = ", ".join(names[:3]) + (" và các chủ đề khác" if len(names) > 3 else "")
        return f"{band.value} · {shown}"
    if criterion:
        return f"{band.value} · {CRITERION_NAMES[criterion]}"
    return f"Trình độ {band.value}"


def compose(
    candidates: Sequence[Candidate],
    paths: Iterable[Sequence[Candidate]],
    goal: Goal,
    learner: Learner | None = None,
) -> Plan:
    """The path: relevant lessons, spread out, in the order teachers use, grouped in units.

    `candidates` are the lessons that may be picked; `paths` are the existing
    paths in their teachers' order, to learn that order from.
    """
    goal = goal.resolved()
    if learner and learner.band and not (goal.band_from or goal.band_to):
        # A learner's path starts at the band of their latest assessment and
        # goes one band up (D059: not straight to C2); lower bands only fill a
        # path that would be too short.
        above = BANDS[min(BAND_RANK[learner.band] + 1, len(BANDS) - 1)]
        goal = replace(goal, band_from=learner.band, band_to=above)
    order = fit_order(paths)
    picks = score_candidates(candidates, goal, learner)
    done = learner.completed if learner else frozenset()
    banded = bool(goal.band_from or goal.band_to)
    in_range = [p for p in picks if p.signals["band"] >= 1.0 or not banded]
    fresh = select(in_range, goal.length, exclude=done)
    warnings: list[str] = []
    if len(fresh) < goal.length and banded:
        taken = frozenset(p.candidate.lesson_id for p in fresh)
        near = [p for p in picks if p.signals["band"] < 1.0]
        extra = select(near, goal.length - len(fresh), exclude=done | taken)
        if extra:
            warnings.append(
                f"Thêm {len(extra)} bài ở trình độ liền kề vì trình độ đã chọn không đủ bài."
            )
        fresh.extend(extra)
    if learner and len(fresh) < goal.length:
        # Lessons already done come back as review, but only to fill the path.
        done = [p for p in picks if p.candidate.lesson_id in learner.completed]
        more = select(done, goal.length - len(fresh))
        fresh.extend(more)
    if len(fresh) < goal.length:
        warnings.append(
            f"Chỉ tìm được {len(fresh)} bài phù hợp, ít hơn {goal.length} bài muốn có."
            " Mở rộng trình độ hoặc bỏ bớt điều kiện để có thêm bài."
        )
    for topic in goal.topics:
        if not any(p.candidate.topic == topic for p in fresh):
            warnings.append(f"Chưa có bài đã xuất bản nào về chủ đề {TOPIC_NAMES[topic]}.")
    if not order.learned and order.pairs < MIN_ORDER_PAIRS:
        warnings.append(
            f"Các lộ trình hiện có mới cho {order.pairs} cặp bài liền nhau, chưa đủ"
            f" {MIN_ORDER_PAIRS} để học thứ tự: bài được xếp theo trình độ rồi độ khó."
        )
    elif not order.learned:
        warnings.append(
            "Thứ tự học từ các lộ trình hiện có không tốt hơn quy tắc cố định:"
            " bài được xếp theo trình độ rồi độ khó."
        )

    for p in fresh:
        if not p.reasons:
            topic = f", chủ đề {TOPIC_NAMES[p.candidate.topic]}" if p.candidate.topic else ""
            p.reasons.append(f"Bổ sung cho đủ lộ trình: trình độ {p.candidate.band.value}{topic}")
    fresh.sort(
        key=lambda p: (BAND_RANK[p.candidate.band], order.score(p.candidate), p.candidate.lesson_id)
    )
    units: list[PlanUnit] = []
    for p in fresh:
        c = p.candidate
        if units and units[-1].band == c.band:
            units[-1].picks.append(p)
        else:
            units.append(PlanUnit("", c.band, None, None, [p]))
    for u in units:
        topics = {p.candidate.topic for p in u.picks}
        criteria = {p.candidate.criterion for p in u.picks}
        u.topic = topics.pop() if len(topics) == 1 else None
        u.criterion = criteria.pop() if len(criteria) == 1 else None
        u.title = _unit_title(u.band, [p.candidate.topic for p in u.picks], u.criterion)
    return Plan(goal, units, order, warnings, len(candidates))
