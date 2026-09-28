"""Invalidation levels and Fibonacci targets from the waves already confirmed."""

from __future__ import annotations

from elliot.models import Direction, Projection


def project(
    pattern: str,
    direction: Direction,
    prices: list[float] | tuple[float, ...],
    variant: str | None = None,
) -> tuple[float, tuple[Projection, ...]]:
    del variant
    if pattern in {"impulse", "leading_diagonal", "ending_diagonal"}:
        return _motive(pattern, direction, prices)
    if pattern in {"zigzag", "flat"}:
        return _corrective_three(direction, prices)
    if pattern == "triangle":
        return _triangle(prices)
    if pattern == "combination":
        return _combination(direction, prices)
    return prices[0] if prices else 0.0, ()


def _motive(
    pattern: str,
    direction: Direction,
    prices: list[float] | tuple[float, ...],
) -> tuple[float, tuple[Projection, ...]]:
    sign = 1 if direction == "bullish" else -1
    projections: list[Projection] = []
    invalidation = prices[0]
    if len(prices) >= 3:
        length1 = abs(prices[1] - prices[0])
        for ratio in (1.618, 2.618):
            projections.append(Projection("wave3", ratio, prices[2] + sign * ratio * length1, "wave1"))
    if len(prices) >= 4:
        length3 = abs(prices[3] - prices[2])
        for ratio in (0.236, 0.382):
            projections.append(Projection("wave4", ratio, prices[3] - sign * ratio * length3, "wave3"))
        if pattern == "impulse":
            invalidation = prices[1]
    if len(prices) >= 5:
        length1 = abs(prices[1] - prices[0])
        length3 = abs(prices[3] - prices[2])
        net = abs(prices[3] - prices[0])
        if length1 > 0 and length3 >= length1 * 1.618 * 0.95:
            projections.append(Projection("wave5", 1.0, prices[4] + sign * length1, "wave1"))
        for ratio in (0.618, 1.0):
            projections.append(Projection("wave5", ratio, prices[4] + sign * ratio * net, "net_0_3"))
    return invalidation, tuple(projections)


def _corrective_three(
    direction: Direction,
    prices: list[float] | tuple[float, ...],
) -> tuple[float, tuple[Projection, ...]]:
    sign = 1 if direction == "bullish" else -1
    projections: list[Projection] = []
    if len(prices) >= 3:
        length_a = abs(prices[1] - prices[0])
        for ratio in (1.0, 1.618):
            projections.append(Projection("waveC", ratio, prices[2] + sign * ratio * length_a, "waveA"))
    return prices[0], tuple(projections)


def _triangle(prices: list[float] | tuple[float, ...]) -> tuple[float, tuple[Projection, ...]]:
    if len(prices) < 2:
        return prices[0] if prices else 0.0, ()
    height = max(abs(prices[index + 1] - prices[index]) for index in range(len(prices) - 1))
    last = prices[-1]
    return prices[0], (
        Projection("breakout", 1.0, last + height, ""),
        Projection("breakout", 1.0, last - height, ""),
    )


def _combination(
    direction: Direction,
    prices: list[float] | tuple[float, ...],
) -> tuple[float, tuple[Projection, ...]]:
    sign = 1 if direction == "bullish" else -1
    projections: list[Projection] = []
    if len(prices) >= 3:
        length_w = abs(prices[1] - prices[0])
        for ratio in (1.0, 1.618):
            projections.append(Projection("waveY", ratio, prices[2] + sign * ratio * length_w, "waveW"))
    return prices[0], tuple(projections)
