"""Zigzag 5-3-5. Wave B does not pass the origin of wave A, and C exceeds A."""

from __future__ import annotations

from elliot.models import Direction
from elliot.rules.common import greater, lesser


def valid_zigzag(prices: list[float] | tuple[float, ...], direction: Direction) -> bool:
    if len(prices) != 4:
        return False
    if not _alternating_three(prices, direction):
        return False
    if not _b_respects_origin(prices, direction):
        return False
    return _c_exceeds_a(prices, direction)


def prefix_zigzag_ok(prices: list[float] | tuple[float, ...], direction: Direction) -> bool:
    if len(prices) < 2 or len(prices) > 4:
        return False
    if not _prefix_direction(prices, direction):
        return False
    if len(prices) >= 3 and not _b_respects_origin(prices, direction):
        return False
    if len(prices) == 4 and not _c_exceeds_a(prices, direction):
        return False
    return True


def _alternating_three(prices: list[float] | tuple[float, ...], direction: Direction) -> bool:
    return _prefix_direction(prices, direction)


def _prefix_direction(prices: list[float] | tuple[float, ...], direction: Direction) -> bool:
    checks = len(prices) - 1
    for index in range(checks):
        up = (direction == "bullish") == (index % 2 == 0)
        if up and not greater(prices[index + 1], prices[index]):
            return False
        if not up and not lesser(prices[index + 1], prices[index]):
            return False
    return True


def _b_respects_origin(prices: list[float] | tuple[float, ...], direction: Direction) -> bool:
    if direction == "bullish":
        return greater(prices[2], prices[0])
    return lesser(prices[2], prices[0])


def _c_exceeds_a(prices: list[float] | tuple[float, ...], direction: Direction) -> bool:
    if direction == "bullish":
        return greater(prices[3], prices[1])
    return lesser(prices[3], prices[1])
