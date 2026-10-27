"""Plans, licences and quotes: the pure rules of D033 and D034.

Four plans, each step up adding something a school can see:

* **Miễn phí** -- one class to start with (up to 30 students): everything a
  learner does, the teacher's review queue, the sample lesson path.
* **Chuẩn** -- the school's own lesson paths, written by its teachers, and
  class statistics with lesson-by-lesson insights.
* **Nâng cao** -- also blind double rating and the agreement report between
  teachers: evidence that the teachers' own scores are consistent.
* **Dùng thử** -- every feature for 30 days, then back to Miễn phí.

The plan is the institution's, never the student's (BR-29): what a plan opens
or closes is a staff tool -- writing lessons, reading class statistics,
starting a rating batch -- and the number of student accounts. A learner's
lessons, assessments, reports, progress, achievements and data are the same on
every plan. When a paid licence ends, the school falls back to Miễn phí after
14 days of grace: nothing already there is closed (BR-31), only new things
beyond the free plan wait for an upgrade.
"""

from __future__ import annotations

import calendar
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, timedelta
from enum import Enum


class Plan(str, Enum):
    FREE = "free"
    TRIAL = "trial"
    STANDARD = "standard"
    ADVANCED = "advanced"


class PlanFeature(str, Enum):
    # Writing the school's own lesson paths: create, edit, publish, import,
    # record model audio. Paths already published stay open to learners on
    # every plan; the sample path is always there.
    LESSON_AUTHORING = "lesson_authoring"
    # Class statistics and lesson-by-lesson insights for teachers.
    CLASS_INSIGHTS = "class_insights"
    # Starting a blind double-rating batch (D030). A batch already started is
    # always finished: its sheets, report and export stay open.
    BLIND_RATING = "blind_rating"


class LicenseState(str, Enum):
    ACTIVE = "active"
    GRACE = "grace"  # a paid licence ended less than GRACE_DAYS ago
    FREE = "free"  # no licence in force: the free plan


PLAN_NAMES = {
    Plan.FREE: "Miễn phí",
    Plan.TRIAL: "Dùng thử",
    Plan.STANDARD: "Chuẩn",
    Plan.ADVANCED: "Nâng cao",
}
FEATURE_NAMES = {
    PlanFeature.LESSON_AUTHORING: "Soạn lộ trình riêng của trường",
    PlanFeature.CLASS_INSIGHTS: "Thống kê lớp và theo dõi từng bài học",
    PlanFeature.BLIND_RATING: "Chấm mù kép và báo cáo đồng thuận giữa giảng viên",
}
PLAN_FEATURES: dict[Plan, frozenset[PlanFeature]] = {
    Plan.FREE: frozenset(),
    # A trial shows everything, so a school can judge all of it.
    Plan.TRIAL: frozenset(PlanFeature),
    Plan.STANDARD: frozenset({PlanFeature.LESSON_AUTHORING, PlanFeature.CLASS_INSIGHTS}),
    Plan.ADVANCED: frozenset(PlanFeature),
}
# Assessments a student is expected to need a month. A soft figure (BR-30):
# going over warns the administrator, it never refuses a student.
QUOTA_PER_SEAT = {Plan.FREE: 2, Plan.TRIAL: 8, Plan.STANDARD: 4, Plan.ADVANCED: 8}
TIER = {Plan.FREE: 0, Plan.TRIAL: 0, Plan.STANDARD: 1, Plan.ADVANCED: 2}
PURCHASABLE = (Plan.STANDARD, Plan.ADVANCED)
FREE_SEATS = 30  # student accounts on the free plan: one class
TERMS = (6, 12)  # months: a semester, a school year
ANNUAL_DISCOUNT = 15  # percent off a school year paid at once
MIN_SEATS = 10
MAX_SEATS = 5000
GRACE_DAYS = 14
# Credits are whole thousands of dong, and a difference smaller than the least a
# payment gateway takes is waived rather than charged.
ROUND_TO = 1000
MIN_CHARGE = 10_000


@dataclass(frozen=True)
class License:
    license_id: str
    organization: str
    plan: Plan
    seats: int  # student accounts it covers
    valid_from: date
    valid_to: date  # the last day covered
    source: str  # "trial" | "order" | "key"
    order_id: str | None = None
    # What the licence is worth at the price it was bought at: an upgrade is
    # credited the unused part of it. Zero for a trial and for a key, whose
    # price lives in a contract outside the system.
    value_vnd: int = 0
    installed_at: str = ""

    @property
    def paid(self) -> bool:
        return self.source != "trial"

    @property
    def days(self) -> int:
        return (self.valid_to - self.valid_from).days + 1


@dataclass(frozen=True)
class Standing:
    """The plan in force on a day, and what it allows."""

    license: License | None  # None on the free plan
    state: LicenseState
    today: date
    scheduled: tuple[License, ...] = ()
    lapsed: License | None = None  # the licence that ran out, back on the free plan

    @property
    def plan(self) -> Plan:
        return self.license.plan if self.license else Plan.FREE

    @property
    def grace_until(self) -> date | None:
        if self.license is None:
            return None
        return self.license.valid_to + timedelta(days=GRACE_DAYS)

    @property
    def days_left(self) -> int:
        """Days the licence still covers, today included; 0 on the free plan."""
        if self.license is None:
            return 0
        return max(0, (self.license.valid_to - self.today).days + 1)

    @property
    def seat_cap(self) -> int:
        """Student accounts the plan covers."""
        return self.license.seats if self.license else FREE_SEATS

    @property
    def features(self) -> frozenset[PlanFeature]:
        return PLAN_FEATURES[self.plan]

    @property
    def quota(self) -> int:
        """Assessments a month the plan expects, for the whole institution."""
        return self.seat_cap * QUOTA_PER_SEAT[self.plan]


def standing(licenses: Iterable[License], today: date) -> Standing:
    """The plan in force today.

    `licenses` come in the order they were installed. Of those that have
    started, the one that started last is the current one, so a purchase that
    starts today supersedes the licence it upgrades; between two that start the
    same day, the one installed later -- even within the same second. A paid
    licence stays in force for GRACE_DAYS after its last day; a trial does not.
    After that, and before any licence, the plan is Miễn phí.
    """
    every = list(licenses)
    started = [(i, x) for i, x in enumerate(every) if x.valid_from <= today]
    later = tuple(sorted((x for x in every if x.valid_from > today), key=lambda x: x.valid_from))
    if not started:
        return Standing(None, LicenseState.FREE, today, later)
    _, current = max(started, key=lambda ix: (ix[1].valid_from, ix[1].installed_at, ix[0]))
    if today <= current.valid_to:
        return Standing(current, LicenseState.ACTIVE, today, later)
    if current.paid and today <= current.valid_to + timedelta(days=GRACE_DAYS):
        return Standing(current, LicenseState.GRACE, today, later)
    return Standing(None, LicenseState.FREE, today, later, lapsed=current)


def add_months(day: date, months: int) -> date:
    """The same day `months` later, or the month's last day when it is shorter."""
    m = day.month - 1 + months
    year, month = day.year + m // 12, m % 12 + 1
    return date(year, month, min(day.day, calendar.monthrange(year, month)[1]))


class QuoteError(ValueError):
    """A purchase that cannot be quoted; the message says why, in Vietnamese."""


@dataclass(frozen=True)
class Quote:
    plan: Plan
    seats: int
    months: int
    unit_price: int  # VND per student per month
    kind: str  # "new" | "renewal" | "upgrade" | "downgrade"
    starts_on: date
    ends_on: date
    list_price: int  # students x months x unit price
    discount: int  # the school-year discount
    credit: int  # what is left of the paid licence an upgrade replaces

    @property
    def gross(self) -> int:
        """What the licence is worth once discounted: the value an upgrade credits later."""
        return self.list_price - self.discount

    @property
    def amount(self) -> int:
        due = max(0, self.gross - self.credit)
        return 0 if due < MIN_CHARGE else due


def quote(
    current: Standing,
    plan: Plan,
    seats: int,
    months: int,
    unit_price: int,
    today: date,
) -> Quote:
    """What buying `plan` for `seats` students and `months` costs today, and when it runs.

    * On the free plan or a trial: it starts today.
    * Same plan and students as the paid licence in force: a renewal, from the
      day after it ends.
    * A higher plan or more students: an upgrade, from today, credited with the
      unused days of the paid licence it replaces.
    * A lower plan or fewer students: from the day after the current one ends,
      so nobody loses what they paid for.
    """
    if plan not in PURCHASABLE:
        raise QuoteError("chỉ mua được gói Chuẩn hoặc Nâng cao")
    if months not in TERMS:
        raise QuoteError("thời hạn là 6 hoặc 12 tháng")
    if not MIN_SEATS <= seats <= MAX_SEATS:
        raise QuoteError(f"số sinh viên phải từ {MIN_SEATS} đến {MAX_SEATS}")
    if current.scheduled:
        nxt = current.scheduled[0].valid_from.strftime("%d/%m/%Y")
        raise QuoteError(
            f"đã có một gói đặt trước, bắt đầu ngày {nxt}; đợi gói đó bắt đầu rồi mua tiếp"
        )
    list_price = seats * months * unit_price
    discount = list_price * ANNUAL_DISCOUNT // 100 // ROUND_TO * ROUND_TO if months == 12 else 0
    held = current.license
    credit = 0
    if held is None or not held.paid:
        kind, start = "new", today
    elif TIER[plan] > TIER[held.plan] or (plan == held.plan and seats > held.seats):
        kind, start = "upgrade", today
        if current.state is LicenseState.ACTIVE:
            credit = _credit(held, today)
    else:
        down = TIER[plan] < TIER[held.plan] or seats < held.seats
        kind = "downgrade" if down else "renewal"
        start = held.valid_to + timedelta(days=1)
    end = add_months(start, months) - timedelta(days=1)
    worth = list_price - discount
    return Quote(
        plan, seats, months, unit_price, kind, start, end, list_price, discount, min(credit, worth)
    )


def _credit(held: License, today: date) -> int:
    """The unused part of a paid licence an upgrade replaces from today, pro rata by day."""
    left = (held.valid_to - today).days + 1  # the upgrade covers today
    if held.value_vnd <= 0 or left <= 0:
        return 0
    return held.value_vnd * left // held.days // ROUND_TO * ROUND_TO
