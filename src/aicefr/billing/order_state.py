"""The life of a run-pack order, as the State pattern (D098).

An order is in one of five states. Each state is an object that knows the
moves it allows, so the rules live in one place instead of in a set of
statuses read in three:

    pending  --gateway: paid / failed / cancelled-->  paid | failed | cancelled
    pending  --nobody paid in time----------------->  expired
    expired  --gateway: paid / failed / cancelled-->  paid | failed | cancelled

An expired order still takes its gateway's word: the money may have moved
after the wait ended, and a payment that arrives is honoured. Paid, failed and
cancelled are final: any later word about such an order changes nothing,
which is what makes the browser's return and the gateway's notification safe
in either order.

The service asks the state before it settles; the store guards its atomic
update with the same table (`sources`), so two messages racing for one order
still move it once. `docs/sdd/diagrams/10_state_don_hang.mmd` draws this
module, and a test keeps the drawing and `transitions()` the same.
"""

from __future__ import annotations

from aicefr.billing.payments import OrderStatus

# What a gateway may say for good: the outcomes that settle an order.
OUTCOMES = frozenset({OrderStatus.PAID, OrderStatus.FAILED, OrderStatus.CANCELLED})


class TransitionRefused(ValueError):
    """A move this order's state does not allow; nothing was changed."""

    def __init__(self, state: OrderStatus, wanted: OrderStatus) -> None:
        super().__init__(f"đơn {state.value} không chuyển sang {wanted.value} được")
        self.state = state
        self.wanted = wanted


class OrderState:
    """A state of an order: its status, the name a buyer reads, the moves it allows."""

    status: OrderStatus
    name: str
    # True while a gateway's final word may still move the order.
    settleable = False

    def settle(self, outcome: OrderStatus) -> OrderStatus:
        """The state a gateway's final `outcome` moves this order to."""
        raise TransitionRefused(self.status, outcome)

    def expire(self) -> OrderStatus:
        """The state an order waits in once nobody paid in time."""
        raise TransitionRefused(self.status, OrderStatus.EXPIRED)

    @property
    def final(self) -> bool:
        return not self.settleable


class _Open(OrderState):
    """Pending or expired: still waiting for, or still taking, the gateway's word."""

    settleable = True

    def settle(self, outcome: OrderStatus) -> OrderStatus:
        if outcome not in OUTCOMES:
            raise TransitionRefused(self.status, outcome)
        return outcome


class Pending(_Open):
    status = OrderStatus.PENDING
    name = "Chờ thanh toán"

    def expire(self) -> OrderStatus:
        return OrderStatus.EXPIRED


class Expired(_Open):
    status = OrderStatus.EXPIRED
    name = "Hết hạn chờ"


class Paid(OrderState):
    status = OrderStatus.PAID
    name = "Đã thanh toán"


class Failed(OrderState):
    status = OrderStatus.FAILED
    name = "Không thành công"


class Cancelled(OrderState):
    status = OrderStatus.CANCELLED
    name = "Đã huỷ"


STATES: dict[OrderStatus, OrderState] = {
    s.status: s for s in (Pending(), Expired(), Paid(), Failed(), Cancelled())
}


def state_of(status: OrderStatus | str) -> OrderState:
    """The state object of a status, as kept on an order ("pending") or as the enum."""
    return STATES[OrderStatus(status)]


def sources(target: OrderStatus) -> frozenset[OrderStatus]:
    """The states a move into `target` may start from: the guard of the store's update."""
    found = set()
    for state in STATES.values():
        try:
            reached = state.expire() if target is OrderStatus.EXPIRED else state.settle(target)
        except TransitionRefused:
            continue
        if reached is target:
            found.add(state.status)
    return frozenset(found)


def transitions() -> list[tuple[OrderStatus, OrderStatus]]:
    """Every move the states allow, (from, to): what the state diagram draws."""
    moves = []
    for state in STATES.values():
        for target in OrderStatus:
            if state.status in sources(target):
                moves.append((state.status, target))
    return moves


# The open states, and the names a buyer reads: kept for the readers of before.
SETTLEABLE = frozenset(s.status for s in STATES.values() if s.settleable)
ORDER_STATUS_NAMES = {s.status: s.name for s in STATES.values()}
