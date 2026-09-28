"""Shared price comparisons for Elliott rules."""

from __future__ import annotations

from elliot.models import Direction

_EPS = 1e-9


def greater(left: float, right: float) -> bool:
    return left > right + _EPS


def lesser(left: float, right: float) -> bool:
    return left < right - _EPS


def direction_of_start(kind: str) -> Direction:
    """A low origin starts a bullish swing; a high origin starts a bearish one."""
    if kind == "low":
        return "bullish"
    if kind == "high":
        return "bearish"
    raise ValueError(f"kind desconocido: {kind}")


def wave_lengths(prices: list[float] | tuple[float, ...]) -> list[float]:
    return [abs(prices[index + 1] - prices[index]) for index in range(len(prices) - 1)]


def alternates(prices: list[float] | tuple[float, ...]) -> bool:
    if len(prices) < 2:
        return False
    moves = [prices[index + 1] - prices[index] for index in range(len(prices) - 1)]
    if any(abs(move) <= _EPS for move in moves):
        return False
    return all(moves[index] * moves[index + 1] < 0 for index in range(len(moves) - 1))


def sign_of(direction: Direction) -> int:
    return 1 if direction == "bullish" else -1
