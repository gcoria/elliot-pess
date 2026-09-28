"""Fibonacci proximity used both as a score and to break ties inside a leg."""

from __future__ import annotations

_RETRACE = (0.382, 0.5, 0.618, 0.786)
_EXTEND = (1.618, 2.0, 2.618)
_WAVE4 = (0.236, 0.382, 0.5)
_WAVE5 = (0.618, 1.0, 1.618)
_ZIGZAG_C = (0.618, 1.0, 1.618)
_FLAT_B = (1.0, 1.236, 1.382)
_FLAT_C = (1.0, 1.618)
_CONTRACT = (0.618, 0.786)


def closeness(actual: float, targets: tuple[float, ...]) -> float:
    if actual <= 0:
        return 0.0
    best = min(abs(actual - target) / target for target in targets)
    if best <= 0.05:
        return 1.0
    if best >= 0.25:
        return 0.0
    return 1.0 - (best - 0.05) / 0.20


def fib_quality(pattern: str, prices: list[float] | tuple[float, ...]) -> float:
    samples = ratio_closeness(pattern, prices)
    if not samples:
        return 0.0
    return sum(score for _name, score in samples) / len(samples)


def ratio_closeness(pattern: str, prices: list[float] | tuple[float, ...]) -> list[tuple[str, float]]:
    if pattern in {"impulse", "leading_diagonal", "ending_diagonal"}:
        return _motive(prices)
    if pattern == "zigzag":
        return _zigzag(prices)
    if pattern == "flat":
        return _flat(prices)
    if pattern == "triangle":
        return _triangle(prices)
    if pattern == "combination":
        return []
    return []


def _motive(prices: list[float] | tuple[float, ...]) -> list[tuple[str, float]]:
    samples: list[tuple[str, float]] = []
    if len(prices) >= 3:
        samples.append(("retroceso de la onda 2", closeness(_retrace_of(prices, 0), _RETRACE)))
    if len(prices) >= 4:
        base = abs(prices[1] - prices[0])
        samples.append(("extensión de la onda 3", closeness(abs(prices[3] - prices[2]) / base if base else 0, _EXTEND)))
    if len(prices) >= 5:
        samples.append(("retroceso de la onda 4", closeness(_retrace_of(prices, 2), _WAVE4)))
    if len(prices) >= 6:
        base = abs(prices[1] - prices[0])
        samples.append(("onda 5 respecto de la onda 1", closeness(abs(prices[5] - prices[4]) / base if base else 0, _WAVE5)))
    return samples


def _zigzag(prices: list[float] | tuple[float, ...]) -> list[tuple[str, float]]:
    samples: list[tuple[str, float]] = []
    if len(prices) >= 3:
        samples.append(("retroceso de B", closeness(_retrace_of(prices, 0), _RETRACE)))
    if len(prices) >= 4:
        base = abs(prices[1] - prices[0])
        samples.append(("onda C respecto de A", closeness(abs(prices[3] - prices[2]) / base if base else 0, _ZIGZAG_C)))
    return samples


def _flat(prices: list[float] | tuple[float, ...]) -> list[tuple[str, float]]:
    samples: list[tuple[str, float]] = []
    if len(prices) >= 3:
        samples.append(("retroceso de B", closeness(_retrace_of(prices, 0), _FLAT_B)))
    if len(prices) >= 4:
        base = abs(prices[1] - prices[0])
        samples.append(("onda C respecto de A", closeness(abs(prices[3] - prices[2]) / base if base else 0, _FLAT_C)))
    return samples


def _triangle(prices: list[float] | tuple[float, ...]) -> list[tuple[str, float]]:
    samples: list[tuple[str, float]] = []
    for index in range(len(prices) - 2):
        previous = abs(prices[index + 1] - prices[index])
        current = abs(prices[index + 2] - prices[index + 1])
        samples.append(
            (f"contracción {index + 2}", closeness(current / previous if previous else 0, _CONTRACT))
        )
    return samples


def _retrace_of(prices: list[float] | tuple[float, ...], start: int) -> float:
    span = abs(prices[start + 1] - prices[start])
    if span == 0:
        return 0.0
    return abs(prices[start + 2] - prices[start + 1]) / span
