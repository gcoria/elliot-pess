"""Run pivot detection, the count search and the ranking."""

from __future__ import annotations

from elliot.models import Analysis, Count
from elliot.pivots.zigzag import zigzag_atr, zigzag_percent
from elliot.search.beam import find_counts


def analyze(
    bars,
    *,
    deviation: float = 0.03,
    mode: str = "percent",
    atr_period: int = 14,
    atr_mult: float = 2.0,
    top: int = 3,
) -> Analysis:
    if mode == "atr":
        pivots = zigzag_atr(bars, period=atr_period, multiplier=atr_mult)
    elif mode == "percent":
        pivots = zigzag_percent(bars, deviation)
    else:
        raise ValueError("mode debe ser percent o atr")
    considered = tuple(find_counts(pivots))
    primary, alternates = rank_counts(considered, top)
    return Analysis(primary=primary, alternates=alternates, pivots=tuple(pivots), considered=considered)


def rank_counts(counts: tuple[Count, ...] | list[Count], top: int) -> tuple[Count | None, tuple[Count, ...]]:
    ordered = sorted(counts, key=_sort_key)
    chosen: list[Count] = []
    for count in ordered:
        if not chosen:
            chosen.append(count)
        elif len(chosen) >= top:
            break
        elif all(_differs(count, previous) for previous in chosen):
            chosen.append(count)
    if not chosen:
        return None, ()
    return chosen[0], tuple(chosen[1:])


def _sort_key(count: Count):
    span = count.endpoint_indexes[-1] - count.endpoint_indexes[0] if count.endpoint_indexes else 0
    return (
        -count.score,
        count.status != "complete",
        count.pattern != "impulse",
        -span,
    )


def _differs(left: Count, right: Count) -> bool:
    if left.pattern != right.pattern or left.status != right.status:
        return True
    return left.endpoint_indexes != right.endpoint_indexes
