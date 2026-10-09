"""Leading and ending diagonals. Wave 4 may overlap wave 1."""

from __future__ import annotations

from elliot.models import Direction
from elliot.rules.common import greater, lesser
from elliot.rules.impulse import overlaps_wave1, prefix_impulse_ok


def valid_diagonal(prices: list[float] | tuple[float, ...], direction: Direction) -> bool:
    """Same cardinal rules as an impulse, except wave 4 is allowed inside wave 1.

    Wave 4 still cannot cross the origin of wave 3. Wave 5 is not required to
    exceed wave 3: ending diagonals often throw under. A diagonal that does not
    overlap wave 1 is just an impulse, so overlap is required.
    """
    if len(prices) != 6:
        return False
    if not overlaps_wave1(prices, direction):
        return False
    if not _wave4_holds_wave3_origin(prices, direction):
        return False
    return prefix_impulse_ok(prices, direction, allow_overlap=True)


def diagonal_shape(prices: list[float] | tuple[float, ...]) -> str | None:
    """Contracting when motive and corrective legs shrink, expanding when they grow."""
    if len(prices) != 6:
        return None
    lengths = [abs(prices[index + 1] - prices[index]) for index in range(5)]
    if lengths[0] > lengths[2] > lengths[4] and lengths[1] > lengths[3]:
        return "contracting"
    if lengths[0] < lengths[2] < lengths[4] and lengths[1] < lengths[3]:
        return "expanding"
    return None


def _wave4_holds_wave3_origin(prices: list[float] | tuple[float, ...], direction: Direction) -> bool:
    if direction == "bullish":
        return greater(prices[4], prices[2])
    return lesser(prices[4], prices[2])
