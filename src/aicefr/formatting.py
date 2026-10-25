"""How numbers are written for a Vietnamese reader."""

from __future__ import annotations


def vi_decimal(x: float, digits: int = 1) -> str:
    """A decimal with a comma, as Vietnamese writes it: 2.5 -> "2,5"."""
    return f"{x:.{digits}f}".replace(".", ",")
