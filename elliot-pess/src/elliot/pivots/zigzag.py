"""ZigZag pivots from percentage reversals or ATR multiples."""

from __future__ import annotations

from collections.abc import Callable

from elliot.models import Bar, Pivot

Threshold = Callable[[int, float], float]


def zigzag_percent(bars: list[Bar], deviation: float) -> list[Pivot]:
    """Confirm a pivot when price reverses by `deviation` of the extreme price."""
    if deviation <= 0:
        raise ValueError("deviation debe ser mayor que 0")

    def threshold(_index: int, extreme: float) -> float:
        return abs(extreme) * deviation

    return zigzag(bars, threshold)


def zigzag_atr(bars: list[Bar], period: int = 14, multiplier: float = 2.0) -> list[Pivot]:
    """Confirm a pivot when price reverses by `multiplier` times ATR(period)."""
    if period < 1:
        raise ValueError("period debe ser al menos 1")
    if multiplier <= 0:
        raise ValueError("multiplier debe ser mayor que 0")
    atrs = average_true_range(bars, period)

    def threshold(index: int, _extreme: float) -> float:
        return atrs[index] * multiplier

    return zigzag(bars, threshold)


def average_true_range(bars: list[Bar], period: int) -> list[float]:
    if not bars:
        return []
    true_ranges: list[float] = []
    for index, bar in enumerate(bars):
        if index == 0:
            true_ranges.append(bar.high - bar.low)
            continue
        previous_close = bars[index - 1].close
        true_ranges.append(
            max(
                bar.high - bar.low,
                abs(bar.high - previous_close),
                abs(bar.low - previous_close),
            )
        )
    atrs: list[float] = []
    for index in range(len(bars)):
        window = true_ranges[max(0, index - period + 1) : index + 1]
        atrs.append(sum(window) / len(window))
    return atrs


def zigzag(bars: list[Bar], threshold_at: Threshold) -> list[Pivot]:
    """Walk highs and lows. The last extreme is kept even if price has not reversed yet."""
    if not bars:
        return []

    pivots: list[Pivot] = []
    trend: str | None = None
    up_index, up_price = 0, bars[0].high
    down_index, down_price = 0, bars[0].low
    extreme_index = 0
    extreme_price = bars[0].close

    for index in range(1, len(bars)):
        bar = bars[index]
        if trend is None:
            if bar.high >= up_price:
                up_price, up_index = bar.high, index
            if bar.low <= down_price:
                down_price, down_index = bar.low, index
            up_move = up_price - down_price
            if up_index > down_index and up_move >= threshold_at(up_index, down_price):
                pivots.append(_pivot(bars, down_index, down_price, "low"))
                trend = "up"
                extreme_index, extreme_price = up_index, up_price
            elif down_index > up_index and up_move >= threshold_at(down_index, up_price):
                pivots.append(_pivot(bars, up_index, up_price, "high"))
                trend = "down"
                extreme_index, extreme_price = down_index, down_price
            continue

        if trend == "up":
            if bar.high >= extreme_price:
                extreme_price, extreme_index = bar.high, index
            elif extreme_price - bar.low >= threshold_at(index, extreme_price):
                pivots.append(_pivot(bars, extreme_index, extreme_price, "high"))
                trend = "down"
                extreme_price, extreme_index = bar.low, index
        elif bar.low <= extreme_price:
            extreme_price, extreme_index = bar.low, index
        elif bar.high - extreme_price >= threshold_at(index, extreme_price):
            pivots.append(_pivot(bars, extreme_index, extreme_price, "low"))
            trend = "up"
            extreme_price, extreme_index = bar.high, index

    if trend is None:
        if up_index <= down_index:
            pivots.append(_pivot(bars, up_index, up_price, "high"))
            if down_index != up_index:
                pivots.append(_pivot(bars, down_index, down_price, "low"))
        else:
            pivots.append(_pivot(bars, down_index, down_price, "low"))
            if up_index != down_index:
                pivots.append(_pivot(bars, up_index, up_price, "high"))
        return _dedupe(pivots)

    kind = "high" if trend == "up" else "low"
    pivots.append(_pivot(bars, extreme_index, extreme_price, kind))
    return _dedupe(pivots)


def _pivot(bars: list[Bar], index: int, price: float, kind: str) -> Pivot:
    bar = bars[index]
    return Pivot(index=index, price=price, kind=kind, timestamp=bar.timestamp, time=bar.time)  # type: ignore[arg-type]


def _dedupe(pivots: list[Pivot]) -> list[Pivot]:
    unique: list[Pivot] = []
    for pivot in pivots:
        if unique and unique[-1].index == pivot.index and unique[-1].kind == pivot.kind:
            continue
        if unique and unique[-1].kind == pivot.kind:
            continue
        unique.append(pivot)
    return unique
