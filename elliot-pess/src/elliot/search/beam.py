"""Beam search over pivot spans. A long leg with no legal inner structure is pruned."""

from __future__ import annotations

from dataclasses import dataclass

from elliot.guidelines.fibonacci import fib_quality
from elliot.models import Count, Direction, Pivot, Wave
from elliot.projections import project
from elliot.rules.common import direction_of_start
from elliot.rules.impulse import is_truncated, overlaps_wave1, prefix_impulse_ok
from elliot.rules.triangle import prefix_triangle_ok
from elliot.rules.zigzag import prefix_zigzag_ok
from elliot.rules.flat import prefix_flat_ok
from elliot.score import score_waves
from elliot.search.legs import LegResult, Structure, find_combination, leg_status

LOOKAHEAD = 8
MAX_SPAN = 16
BEAM_WIDTH = 15
MAX_PIVOTS = 40

LABELS = {
    "impulse": ("1", "2", "3", "4", "5"),
    "leading_diagonal": ("1", "2", "3", "4", "5"),
    "ending_diagonal": ("1", "2", "3", "4", "5"),
    "zigzag": ("A", "B", "C"),
    "flat": ("A", "B", "C"),
    "triangle": ("A", "B", "C", "D", "E"),
    "combination": ("W", "X", "Y"),
}

_IMPULSE_ROLES = (
    frozenset({"impulse", "leading_diagonal"}),
    frozenset({"zigzag", "flat"}),
    frozenset({"impulse"}),
    frozenset({"zigzag", "flat", "triangle", "combination"}),
    frozenset({"impulse", "ending_diagonal"}),
)
_DIAGONAL_ROLES = (
    frozenset({"impulse", "leading_diagonal", "zigzag", "flat"}),
    frozenset({"zigzag", "flat"}),
    frozenset({"impulse", "zigzag", "flat"}),
    frozenset({"zigzag", "flat", "triangle", "combination"}),
    frozenset({"impulse", "ending_diagonal", "zigzag", "flat"}),
)
_ZIGZAG_ROLES = (
    frozenset({"impulse", "leading_diagonal"}),
    frozenset({"zigzag", "flat", "triangle"}),
    frozenset({"impulse", "ending_diagonal"}),
)
_FLAT_ROLES = (
    frozenset({"zigzag", "flat"}),
    frozenset({"zigzag", "flat", "triangle"}),
    frozenset({"impulse", "ending_diagonal"}),
)
_TRIANGLE_ROLES = (frozenset({"zigzag", "flat"}),) * 5

_CORRECTIVE = {"zigzag", "flat", "triangle", "combination"}
_MOTIVE = {"impulse", "leading_diagonal", "ending_diagonal"}


@dataclass
class Partial:
    start: int
    ends: tuple[int, ...]
    legs: tuple[LegResult, ...]
    direction: Direction
    family: str
    pattern: str
    variant: str | None = None


def find_counts(pivots: list[Pivot]) -> list[Count]:
    window = pivots[-MAX_PIVOTS:]
    cache: dict[tuple[object, ...], LegResult] = {}
    counts: list[Count] = []
    counts.extend(_search_five(window, cache, family="impulse", roles=_IMPULSE_ROLES, allow_overlap=False, require_overlap=False))
    counts.extend(_search_five(window, cache, family="diagonal", roles=_DIAGONAL_ROLES, allow_overlap=True, require_overlap=True))
    counts.extend(_search_three(window, cache, family="zigzag", roles=_ZIGZAG_ROLES, pattern="zigzag"))
    counts.extend(_search_three(window, cache, family="flat", roles=_FLAT_ROLES, pattern="flat"))
    counts.extend(_search_triangle(window, cache))
    counts.extend(_search_combinations(window, cache))
    return _dedupe(counts)


def _search_five(pivots, cache, *, family, roles, allow_overlap, require_overlap) -> list[Count]:
    partials: list[Partial] = []
    for start in range(len(pivots)):
        direction = direction_of_start(pivots[start].kind)
        beam = [Partial(start, (), (), direction, family, family)]
        for wave_no in range(1, 6):
            expanded: list[Partial] = []
            for partial in beam:
                prev = partial.start if not partial.ends else partial.ends[-1]
                for end in _next_ends(pivots, prev):
                    ends = partial.ends + (end,)
                    prices = _prices(pivots, (partial.start, *ends))
                    if not prefix_impulse_ok(prices, direction, allow_overlap=allow_overlap):
                        continue
                    if not _motive_path_ok(pivots, partial, end, wave_no, allow_overlap):
                        continue
                    if require_overlap and wave_no >= 4 and not overlaps_wave1(prices, direction):
                        continue
                    leg = leg_status(pivots, prev, end, roles[wave_no - 1], cache)
                    if leg.status == "invalid":
                        continue
                    if wave_no == 5 and is_truncated(prices, direction) and family == "impulse":
                        if leg.status != "present" or leg.structure is None or leg.structure.pattern != "impulse":
                            continue
                    expanded.append(
                        Partial(
                            partial.start,
                            ends,
                            partial.legs + (leg,),
                            direction,
                            family,
                            family,
                        )
                    )
            beam = _trim(expanded, pivots)
            partials.extend(partial for partial in beam if len(partial.ends) >= 2)
    classified = [_classify_diagonal(partial) if family == "diagonal" else partial for partial in partials]
    return _emit(pivots, classified, complete_n=5, min_progress=4 if family == "diagonal" else 2)


def _search_three(pivots, cache, *, family, roles, pattern) -> list[Count]:
    partials: list[Partial] = []
    prefix = prefix_zigzag_ok if pattern == "zigzag" else prefix_flat_ok
    for start in range(len(pivots)):
        direction = direction_of_start(pivots[start].kind)
        beam = [Partial(start, (), (), direction, family, pattern)]
        for wave_no in range(1, 4):
            expanded: list[Partial] = []
            for partial in beam:
                prev = partial.start if not partial.ends else partial.ends[-1]
                for end in _next_ends(pivots, prev):
                    ends = partial.ends + (end,)
                    prices = _prices(pivots, (partial.start, *ends))
                    if not prefix(prices, direction):
                        continue
                    if pattern == "zigzag" and wave_no == 2 and not _holds_origin(pivots, partial.start, prev, end, direction):
                        continue
                    leg = leg_status(pivots, prev, end, roles[wave_no - 1], cache)
                    if leg.status == "invalid":
                        continue
                    variant = None
                    if pattern == "flat" and wave_no == 3:
                        from elliot.rules.flat import classify_flat

                        variant = classify_flat(prices, direction)
                        if variant is None:
                            continue
                    expanded.append(
                        Partial(partial.start, ends, partial.legs + (leg,), direction, family, pattern, variant)
                    )
            beam = _trim(expanded, pivots)
            partials.extend(partial for partial in beam if len(partial.ends) >= 2)
    return _emit(pivots, partials, complete_n=3, min_progress=2)


def _search_triangle(pivots, cache) -> list[Count]:
    partials: list[Partial] = []
    for start in range(len(pivots)):
        direction = direction_of_start(pivots[start].kind)
        beam = [Partial(start, (), (), direction, "triangle", "triangle")]
        for wave_no in range(1, 6):
            expanded: list[Partial] = []
            for partial in beam:
                prev = partial.start if not partial.ends else partial.ends[-1]
                for end in _next_ends(pivots, prev):
                    ends = partial.ends + (end,)
                    prices = _prices(pivots, (partial.start, *ends))
                    if not prefix_triangle_ok(prices):
                        continue
                    leg = leg_status(pivots, prev, end, _TRIANGLE_ROLES[wave_no - 1], cache)
                    if leg.status == "invalid":
                        continue
                    expanded.append(
                        Partial(partial.start, ends, partial.legs + (leg,), direction, "triangle", "triangle")
                    )
            beam = _trim(expanded, pivots)
            partials.extend(partial for partial in beam if len(partial.ends) == 5)
    return _emit(pivots, partials, complete_n=5, min_progress=5)


def _search_combinations(pivots, cache) -> list[Count]:
    counts: list[Count] = []
    last = len(pivots)
    for start in range(last):
        for end in range(start + 9, min(last, start + MAX_SPAN + 1)):
            if (end - start) % 2 == 0:
                continue
            structure = find_combination(pivots, start, end, cache)
            if structure is None:
                continue
            legs = tuple(
                LegResult("present", child) for child in structure.children
            )
            partial = Partial(
                start,
                structure.points[1:],
                legs,
                structure.direction,
                "combination",
                "combination",
            )
            counts.append(_to_count(pivots, partial, "complete"))
    return counts


def _emit(pivots, partials: list[Partial], *, complete_n: int, min_progress: int) -> list[Count]:
    counts: list[Count] = []
    for partial in partials:
        size = len(partial.ends)
        if size == complete_n:
            counts.append(_to_count(pivots, partial, "complete"))
        elif _in_progress(partial, partials, complete_n, min_progress, len(pivots)):
            counts.append(_to_count(pivots, partial, "in_progress"))
    return counts


def _in_progress(partial: Partial, partials: list[Partial], complete_n: int, min_progress: int, n_pivots: int) -> bool:
    size = len(partial.ends)
    if size < min_progress or size >= complete_n:
        return False
    if partial.ends[-1] < n_pivots - 8:
        return False
    return not _has_extension(partial, partials)


def _has_extension(partial: Partial, partials: list[Partial]) -> bool:
    for other in partials:
        if other.start != partial.start or len(other.ends) <= len(partial.ends):
            continue
        if other.ends[: len(partial.ends)] != partial.ends:
            continue
        if other.family == partial.family:
            return True
        if partial.family == "impulse" and other.family == "diagonal":
            return True
    return False


def _classify_diagonal(partial: Partial) -> Partial:
    if len(partial.ends) < 4:
        return partial
    corrective = 0
    motive = 0
    for index in (0, 2, 4):
        if index >= len(partial.legs):
            continue
        structure = partial.legs[index].structure
        if structure is None:
            continue
        if structure.pattern in _CORRECTIVE:
            corrective += 1
        if structure.pattern in _MOTIVE:
            motive += 1
    pattern = "ending_diagonal" if corrective > motive else "leading_diagonal"
    return Partial(partial.start, partial.ends, partial.legs, partial.direction, partial.family, pattern, partial.variant)


def _to_count(pivots: list[Pivot], partial: Partial, status: str) -> Count:
    points = (partial.start, *partial.ends)
    labels = LABELS[partial.pattern][: len(partial.ends)]
    waves = tuple(
        _wave(pivots, points[index], points[index + 1], labels[index], partial.legs[index])
        for index in range(len(partial.ends))
    )
    prices = _prices(pivots, points)
    invalidation, projections = project(partial.pattern, partial.direction, prices, partial.variant)
    score, notes = score_waves(partial.pattern, prices, waves, partial.variant)
    if partial.pattern == "impulse" and len(prices) == 6 and is_truncated(prices, partial.direction):
        notes = (*notes, "onda 5 truncada")
    return Count(
        score=score,
        direction=partial.direction,
        pattern=partial.pattern,
        status=status,  # type: ignore[arg-type]
        waves=waves,
        invalidation=invalidation,
        projections=projections,
        guideline_notes=notes,
        variant=partial.variant,
        endpoint_indexes=tuple(pivots[point].index for point in points),
    )


def _wave(pivots: list[Pivot], start: int, end: int, label: str, leg: LegResult) -> Wave:
    left = pivots[start]
    right = pivots[end]
    subwaves: tuple[Wave, ...] = ()
    subpattern = None
    status = "insufficient"
    if leg.status == "present" and leg.structure is not None:
        subwaves = _structure_waves(pivots, leg.structure)
        subpattern = leg.structure.pattern
        status = "present"
    return Wave(
        label=label,
        start_index=left.index,
        end_index=right.index,
        price_start=left.price,
        price_end=right.price,
        time_start=left.time,
        time_end=right.time,
        timestamp_start=left.timestamp,
        timestamp_end=right.timestamp,
        subwaves_status=status,  # type: ignore[arg-type]
        subpattern=subpattern,
        subwaves=subwaves,
    )


def _structure_waves(pivots: list[Pivot], structure: Structure) -> tuple[Wave, ...]:
    labels = LABELS[structure.pattern]
    waves: list[Wave] = []
    for index, label in enumerate(labels):
        child = structure.children[index] if structure.children else None
        leg = LegResult("present", child) if child is not None else LegResult("insufficient", None)
        waves.append(_wave(pivots, structure.points[index], structure.points[index + 1], label, leg))
    return tuple(waves)


def _trim(partials: list[Partial], pivots: list[Pivot]) -> list[Partial]:
    ranked = sorted(partials, key=lambda partial: _partial_quality(partial, pivots), reverse=True)
    kept: list[Partial] = []
    seen: set[tuple[int, tuple[int, ...]]] = set()
    for partial in ranked:
        key = (partial.start, partial.ends)
        if key in seen:
            continue
        seen.add(key)
        kept.append(partial)
        if len(kept) >= BEAM_WIDTH:
            break
    return kept


def _partial_quality(partial: Partial, pivots: list[Pivot]) -> float:
    if not partial.ends:
        return 0.0
    prices = _prices(pivots, (partial.start, *partial.ends))
    return fib_quality(partial.pattern if partial.pattern in LABELS else "impulse", prices)


def _motive_path_ok(pivots: list[Pivot], partial: Partial, end: int, wave_no: int, allow_overlap: bool) -> bool:
    """Wave 2 cannot trade through the origin, and wave 4 cannot trade through wave 1."""
    start = partial.start if not partial.ends else partial.ends[-1]
    if wave_no == 2:
        return _holds_origin(pivots, partial.start, start, end, partial.direction)
    if wave_no == 4 and not allow_overlap:
        bound = pivots[partial.ends[0]].price
        span = [pivots[index].price for index in range(start, end + 1)]
        if partial.direction == "bullish":
            return min(span) > bound
        return max(span) < bound
    return True


def _holds_origin(pivots: list[Pivot], origin: int, start: int, end: int, direction: Direction) -> bool:
    span = [pivots[index].price for index in range(start, end + 1)]
    if direction == "bullish":
        return min(span) > pivots[origin].price
    return max(span) < pivots[origin].price


def _next_ends(pivots: list[Pivot], prev: int):
    found = 0
    last = min(len(pivots) - 1, prev + MAX_SPAN)
    for index in range(prev + 1, last + 1):
        if (index - prev) % 2 == 0:
            continue
        yield index
        found += 1
        if found >= LOOKAHEAD:
            return


def _prices(pivots: list[Pivot], points: tuple[int, ...]) -> list[float]:
    return [pivots[point].price for point in points]


def _dedupe(counts: list[Count]) -> list[Count]:
    unique: list[Count] = []
    seen: set[tuple[object, ...]] = set()
    for count in counts:
        key = (count.pattern, count.status, count.endpoint_indexes, count.variant)
        if key in seen:
            continue
        seen.add(key)
        unique.append(count)
    return unique
