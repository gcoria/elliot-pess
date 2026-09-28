"""Cardinal rules of a five-wave impulse. Frost and Prechter."""

from __future__ import annotations

from elliot.models import Direction
from elliot.rules.common import greater, lesser

# Wave 2 does not retrace 100% of wave 1.
# Wave 3 is never the shortest of waves 1, 3 and 5.
# Wave 4 does not enter the price territory of wave 1.
# Wave 3 exceeds the extreme of wave 1.


def valid_impulse(prices: list[float] | tuple[float, ...], direction: Direction) -> bool:
    return _five(prices, direction, allow_overlap=False, require_wave5_beyond=True)


def valid_truncated_impulse(prices: list[float] | tuple[float, ...], direction: Direction) -> bool:
    """Wave 5 fails to exceed wave 3. The caller must still require five subwaves inside wave 5."""
    return _five(prices, direction, allow_overlap=False, require_wave5_beyond=False) and is_truncated(
        prices, direction
    )


def is_truncated(prices: list[float] | tuple[float, ...], direction: Direction) -> bool:
    if len(prices) < 6:
        return False
    if direction == "bullish":
        return not greater(prices[5], prices[3])
    return not lesser(prices[5], prices[3])


def overlaps_wave1(prices: list[float] | tuple[float, ...], direction: Direction) -> bool:
    """Wave 4 trades in wave 1 territory, including a touch of the wave 1 extreme."""
    if len(prices) < 5:
        return False
    if direction == "bullish":
        return not greater(prices[4], prices[1])
    return not lesser(prices[4], prices[1])


def prefix_impulse_ok(
    prices: list[float] | tuple[float, ...],
    direction: Direction,
    *,
    allow_overlap: bool,
) -> bool:
    """Rules that can already be decided with a prefix of the five waves."""
    if len(prices) < 2 or not _progresses(prices, direction):
        return False
    waves = len(prices) - 1
    if waves >= 2 and not _wave2_holds(prices, direction):
        return False
    if waves >= 3 and not _wave3_progress(prices, direction):
        return False
    if waves >= 4 and not allow_overlap and overlaps_wave1(prices, direction):
        return False
    if waves >= 5 and _wave3_is_shortest(prices):
        return False
    return True


def _five(
    prices: list[float] | tuple[float, ...],
    direction: Direction,
    *,
    allow_overlap: bool,
    require_wave5_beyond: bool,
) -> bool:
    if len(prices) != 6:
        return False
    if not prefix_impulse_ok(prices, direction, allow_overlap=allow_overlap):
        return False
    if require_wave5_beyond and is_truncated(prices, direction):
        return False
    if not require_wave5_beyond and not is_truncated(prices, direction):
        return False
    return True


def _progresses(prices: list[float] | tuple[float, ...], direction: Direction) -> bool:
    for index in range(len(prices) - 1):
        if direction == "bullish":
            expected_up = index % 2 == 0
            if expected_up and not greater(prices[index + 1], prices[index]):
                return False
            if not expected_up and not lesser(prices[index + 1], prices[index]):
                return False
        else:
            expected_down = index % 2 == 0
            if expected_down and not lesser(prices[index + 1], prices[index]):
                return False
            if not expected_down and not greater(prices[index + 1], prices[index]):
                return False
    return True


def _wave2_holds(prices: list[float] | tuple[float, ...], direction: Direction) -> bool:
    # Strict: a full retrace or anything beyond it invalidates the impulse.
    if direction == "bullish":
        return greater(prices[2], prices[0])
    return lesser(prices[2], prices[0])


def _wave3_progress(prices: list[float] | tuple[float, ...], direction: Direction) -> bool:
    if direction == "bullish":
        return greater(prices[3], prices[1])
    return lesser(prices[3], prices[1])


def _wave3_is_shortest(prices: list[float] | tuple[float, ...]) -> bool:
    length1 = abs(prices[1] - prices[0])
    length3 = abs(prices[3] - prices[2])
    length5 = abs(prices[5] - prices[4])
    return length3 < length1 and length3 < length5
