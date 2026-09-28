"""Contracting triangle A-B-C-D-E. Each leg is shorter and stays inside the previous one."""

from __future__ import annotations

from elliot.rules.common import alternates, wave_lengths


def prefix_triangle_ok(prices: list[float] | tuple[float, ...]) -> bool:
    if len(prices) < 2 or not alternates(prices):
        return False
    lengths = wave_lengths(prices)
    if any(lengths[index + 1] >= lengths[index] for index in range(len(lengths) - 1)):
        return False
    for index in range(1, len(prices) - 1):
        if not _inside(prices[index + 1], prices[index - 1], prices[index]):
            return False
    return True


def valid_triangle(prices: list[float] | tuple[float, ...]) -> bool:
    if len(prices) != 6 or not alternates(prices):
        return False
    lengths = wave_lengths(prices)
    if not all(lengths[index + 1] < lengths[index] for index in range(4)):
        return False
    for index in range(1, 5):
        if not _inside(prices[index + 1], prices[index - 1], prices[index]):
            return False
    return True


def _inside(price: float, left: float, right: float) -> bool:
    low, high = (left, right) if left < right else (right, left)
    return low < price < high
