"""The life of a run-pack order as the State pattern (D098).

Each state of `aicefr.billing.order_state` decides the moves it allows; the
service asks it before settling and the store guards its atomic update with the
same table. These tests pin the table, the drawing of it in the SDD, and the
store's behaviour when messages about one order arrive in any order.

Test case ids (TC-OS-xx) are listed in `docs/test/TEST_PLAN_D098.md`.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from test_billing import PACKS, boot
from test_lessons_integration import login_as

from aicefr.billing.order_state import (
    STATES,
    TransitionRefused,
    sources,
    state_of,
    transitions,
)
from aicefr.billing.payments import OrderStatus as S

DIAGRAM = Path(__file__).resolve().parents[1] / "docs/sdd/diagrams/10_state_don_hang.mmd"
ALLOWED = {
    (S.PENDING, S.PAID),
    (S.PENDING, S.FAILED),
    (S.PENDING, S.CANCELLED),
    (S.PENDING, S.EXPIRED),
    (S.EXPIRED, S.PAID),
    (S.EXPIRED, S.FAILED),
    (S.EXPIRED, S.CANCELLED),
}


@pytest.mark.unit
def test_each_state_allows_only_its_own_moves():
    for state in STATES.values():
        for target in S:
            move = (state.status, target)
            try:
                reached = state.expire() if target is S.EXPIRED else state.settle(target)
            except TransitionRefused as refused:
                assert move not in ALLOWED, move
                assert refused.state is state.status and refused.wanted is target
                continue
            assert move in ALLOWED and reached is target, move
    assert set(transitions()) == ALLOWED


@pytest.mark.unit
def test_a_settled_order_is_final_and_an_expired_one_still_takes_the_money():
    for status in (S.PAID, S.FAILED, S.CANCELLED):
        assert state_of(status).final and not state_of(status).settleable
    assert state_of("expired").settle(S.PAID) is S.PAID  # the money moved after the wait
    with pytest.raises(TransitionRefused):
        state_of("pending").settle(S.PENDING)  # "not yet" is no move
    assert sources(S.PAID) == {S.PENDING, S.EXPIRED} and sources(S.EXPIRED) == {S.PENDING}
    assert [state_of(s).name for s in ("pending", "paid")] == ["Chờ thanh toán", "Đã thanh toán"]


@pytest.mark.unit
def test_the_state_diagram_draws_exactly_the_moves_the_code_allows():
    text = DIAGRAM.read_text(encoding="utf-8")
    drawn = {(S(a), S(b)) for a, b in re.findall(r"^\s*([a-z]+) --> ([a-z]+)\b", text, re.M)}
    assert drawn == set(transitions())


@pytest.mark.integration
def test_the_store_moves_an_order_once_whatever_arrives_after(tmp_path, monkeypatch):
    m = boot(
        tmp_path, monkeypatch, AICEFR_BILLING="on", AICEFR_METERING="on", AICEFR_CREDIT_PACKS=PACKS
    )
    buyer = login_as(m, "SV-001")
    order_id = buyer.post("/api/v1/me/credit-orders", json={"runs": 10}).json()["order"]["order_id"]
    store = m.billing_store

    assert store.settle(order_id, S.PAID, "REF1") is True
    # Paid is final: a late "failed", an expiry run, a second "paid" change nothing.
    assert store.settle(order_id, S.FAILED, "REF2") is False
    assert store.settle(order_id, S.PAID, "REF3") is False
    store.expire_pending("9999-12-31T00:00:00+00:00")
    order = store.order(order_id)
    assert (order["status"], order["reference"]) == ("paid", "REF1")
    # An expired order still takes a payment that arrives late.
    other = buyer.post("/api/v1/me/credit-orders", json={"runs": 10}).json()["order"]["order_id"]
    assert store.expire_pending("9999-12-31T00:00:00+00:00") == [other]
    assert store.settle(other, S.PAID, "LATE") is True
