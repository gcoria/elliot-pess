"""Run pivot detection, the count search and the ranking."""

from __future__ import annotations

from dataclasses import replace

from elliot.models import Analysis, Count
from elliot.pivots.zigzag import zigzag_atr, zigzag_percent
from elliot.search.beam import find_counts

_ENDING_PARENT = {"5", "C"}
_BROKEN = "el precio cruzó la invalidación"


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
    found = find_counts(pivots)
    considered = tuple(prepare_counts(found, bars, pivots))
    primary, alternates = rank_counts(considered, top)
    return Analysis(primary=primary, alternates=alternates, pivots=tuple(pivots), considered=considered)


def prepare_counts(counts, bars, pivots) -> list[Count]:
    """Drop a false ending label, then mark broken invalidations and mid-chart counts."""
    labeled = relabel_ending_diagonals(counts)
    return [_annotate(count, bars, pivots) for count in labeled]


def relabel_ending_diagonals(counts) -> list[Count]:
    """An ending diagonal is only the close of a larger wave 5 or C already found."""
    parents = set()
    for count in counts:
        for wave in count.waves:
            if wave.label in _ENDING_PARENT and wave.subpattern == "ending_diagonal":
                parents.add((wave.start_index, wave.end_index, count.direction))
    prepared: list[Count] = []
    seen: dict[tuple, int] = {}
    for count in counts:
        if count.pattern == "ending_diagonal" and count.waves:
            span = (count.waves[0].start_index, count.waves[-1].end_index, count.direction)
            if span not in parents:
                count = replace(count, pattern="leading_diagonal")
        key = (count.pattern, count.status, count.direction, count.endpoint_indexes, count.variant)
        previous = seen.get(key)
        if previous is None:
            seen[key] = len(prepared)
            prepared.append(count)
        elif count.score > prepared[previous].score:
            prepared[previous] = count
    return prepared


def _annotate(count: Count, bars, pivots) -> Count:
    at_edge = _reaches_edge(count, pivots)
    invalidated = _broken_invalidation(count, bars)
    notes = count.guideline_notes
    if invalidated and _BROKEN not in notes:
        notes = (*notes, _BROKEN)
    if at_edge == count.at_edge and invalidated == count.invalidated and notes is count.guideline_notes:
        return count
    return replace(count, at_edge=at_edge, invalidated=invalidated, guideline_notes=notes)


def _reaches_edge(count: Count, pivots) -> bool:
    if not pivots or not count.waves:
        return False
    if count.status == "in_progress":
        return True
    return count.waves[-1].end_index == pivots[-1].index


def _broken_invalidation(count: Count, bars) -> bool:
    if not count.waves:
        return False
    last = count.waves[-1].end_index
    level = count.invalidation
    for bar in bars:
        if bar.index <= last:
            continue
        if count.direction == "bullish" and bar.low <= level:
            return True
        if count.direction == "bearish" and bar.high >= level:
            return True
    return False


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
        count.invalidated,
        not count.at_edge,
        -count.score,
        count.status != "complete",
        count.pattern != "impulse",
        -span,
    )


def _differs(left: Count, right: Count) -> bool:
    if left.pattern != right.pattern or left.status != right.status:
        return True
    return left.endpoint_indexes != right.endpoint_indexes
