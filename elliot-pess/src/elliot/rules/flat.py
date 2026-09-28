"""Flats 3-3-5: regular, expanded and running."""

from __future__ import annotations

from elliot.models import Direction
from elliot.rules.common import greater, lesser

# B retraces at least 90% of A, or trades beyond the origin of A.
_MIN_B = 0.90


def valid_flat(prices: list[float] | tuple[float, ...], direction: Direction) -> bool:
    return classify_flat(prices, direction) is not None


def prefix_flat_ok(prices: list[float] | tuple[float, ...], direction: Direction) -> bool:
    if len(prices) < 2 or len(prices) > 4:
        return False
    if not _direction_ok_prefix(prices, direction):
        return False
    if len(prices) >= 3:
        length_a = abs(prices[1] - prices[0])
        if length_a == 0:
            return False
        retrace_b = abs(prices[2] - prices[1]) / length_a
        if retrace_b < _MIN_B and not _b_beyond_origin(prices, direction):
            return False
    if len(prices) == 4:
        return classify_flat(prices, direction) is not None
    return True


def _direction_ok_prefix(prices: list[float] | tuple[float, ...], direction: Direction) -> bool:
    for index in range(len(prices) - 1):
        up = (direction == "bullish") == (index % 2 == 0)
        if up and not greater(prices[index + 1], prices[index]):
            return False
        if not up and not lesser(prices[index + 1], prices[index]):
            return False
    return True


def classify_flat(prices: list[float] | tuple[float, ...], direction: Direction) -> str | None:
    if len(prices) != 4 or not _direction_ok(prices, direction):
        return None
    length_a = abs(prices[1] - prices[0])
    if length_a == 0:
        return None
    retrace_b = abs(prices[2] - prices[1]) / length_a
    beyond = _b_beyond_origin(prices, direction)
    if retrace_b < _MIN_B and not beyond:
        return None
    c_beyond = _c_beyond_a(prices, direction)
    if beyond and c_beyond:
        return "expanded"
    if beyond and not c_beyond:
        return "running"
    if not beyond and retrace_b >= _MIN_B:
        return "regular"
    return None


def _direction_ok(prices: list[float] | tuple[float, ...], direction: Direction) -> bool:
    for index in range(3):
        up = (direction == "bullish") == (index % 2 == 0)
        if up and not greater(prices[index + 1], prices[index]):
            return False
        if not up and not lesser(prices[index + 1], prices[index]):
            return False
    return True


def _b_beyond_origin(prices: list[float] | tuple[float, ...], direction: Direction) -> bool:
    if direction == "bullish":
        return not greater(prices[2], prices[0])
    return not lesser(prices[2], prices[0])


def _c_beyond_a(prices: list[float] | tuple[float, ...], direction: Direction) -> bool:
    if direction == "bullish":
        return greater(prices[3], prices[1])
    return lesser(prices[3], prices[1])
