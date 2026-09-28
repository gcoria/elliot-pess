"""Leading and ending diagonals. Wave 4 may overlap wave 1."""

from __future__ import annotations

from elliot.models import Direction
from elliot.rules.impulse import overlaps_wave1, prefix_impulse_ok


def valid_diagonal(prices: list[float] | tuple[float, ...], direction: Direction) -> bool:
    """Same cardinal rules as an impulse, except wave 4 is allowed inside wave 1.

    Wave 5 is not required to exceed wave 3: ending diagonals often throw under.
    A diagonal that does not overlap wave 1 is just an impulse, so overlap is required.
    """
    if len(prices) != 6:
        return False
    if not overlaps_wave1(prices, direction):
        return False
    return prefix_impulse_ok(prices, direction, allow_overlap=True)
