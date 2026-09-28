"""One degree of internal structure for a proposed wave."""

from __future__ import annotations

from dataclasses import dataclass

from elliot.guidelines.fibonacci import fib_quality
from elliot.models import Direction, Pivot
from elliot.rules.combination import x_exceeds_w_origin
from elliot.rules.common import direction_of_start
from elliot.rules.diagonal import valid_diagonal
from elliot.rules.flat import classify_flat
from elliot.rules.impulse import valid_impulse
from elliot.rules.triangle import valid_triangle
from elliot.rules.zigzag import valid_zigzag

_MIN_GAP = {
    "impulse": 5,
    "leading_diagonal": 5,
    "ending_diagonal": 5,
    "zigzag": 3,
    "flat": 3,
    "triangle": 5,
    "combination": 9,
}

_MAX_COMBINATIONS = 250


@dataclass(frozen=True)
class Structure:
    pattern: str
    direction: Direction
    variant: str | None
    points: tuple[int, ...]
    children: tuple[Structure, ...] = ()


@dataclass(frozen=True)
class LegResult:
    status: str
    structure: Structure | None


def leg_status(
    pivots: list[Pivot],
    start: int,
    end: int,
    accepted: frozenset[str],
    cache: dict[tuple[object, ...], LegResult],
) -> LegResult:
    gap = end - start
    if gap < 1 or not accepted:
        return LegResult("invalid", None)
    minimum = min(_MIN_GAP[name] for name in accepted)
    if gap < minimum:
        return LegResult("insufficient", None)
    key = (start, end, tuple(sorted(accepted)))
    if key in cache:
        return cache[key]
    found = match_structure(pivots, start, end, accepted, cache)
    result = LegResult("present", found) if found is not None else LegResult("invalid", None)
    cache[key] = result
    return result


def match_structure(
    pivots: list[Pivot],
    start: int,
    end: int,
    accepted: frozenset[str],
    cache: dict[tuple[object, ...], LegResult],
) -> Structure | None:
    found: list[Structure] = []
    direction = direction_of_start(pivots[start].kind)
    if "impulse" in accepted:
        found.extend(_fives(pivots, start, end, direction, "impulse"))
    if "leading_diagonal" in accepted:
        found.extend(_fives(pivots, start, end, direction, "leading_diagonal"))
    if "ending_diagonal" in accepted:
        found.extend(_fives(pivots, start, end, direction, "ending_diagonal"))
    if "zigzag" in accepted:
        found.extend(_threes(pivots, start, end, direction, "zigzag"))
    if "flat" in accepted:
        found.extend(_threes(pivots, start, end, direction, "flat"))
    if "triangle" in accepted:
        found.extend(_fives(pivots, start, end, direction, "triangle"))
    if "combination" in accepted:
        combination = find_combination(pivots, start, end, cache)
        if combination is not None:
            found.append(combination)
    if not found:
        return None
    return max(found, key=lambda structure: _quality(pivots, structure))


def find_combination(
    pivots: list[Pivot],
    start: int,
    end: int,
    cache: dict[tuple[object, ...], LegResult],
) -> Structure | None:
    if end - start < 9:
        return None
    best: Structure | None = None
    best_quality = -1.0
    simple = frozenset({"zigzag", "flat"})
    link = frozenset({"zigzag"})
    tail = frozenset({"zigzag", "flat", "triangle"})
    for wave_end in _split_ends(start, end, min_gap=3, min_after=6):
        wave = match_structure(pivots, start, wave_end, simple, cache)
        if wave is None:
            continue
        for link_end in _split_ends(wave_end, end, min_gap=3, min_after=3):
            connector = match_structure(pivots, wave_end, link_end, link, cache)
            if connector is None or connector.direction == wave.direction:
                continue
            if x_exceeds_w_origin(pivots[start].price, pivots[link_end].price, wave.direction):
                continue
            final = match_structure(pivots, link_end, end, tail, cache)
            if final is None or final.direction != wave.direction:
                continue
            candidate = Structure(
                "combination",
                wave.direction,
                None,
                (start, wave_end, link_end, end),
                (wave, connector, final),
            )
            quality = _quality(pivots, candidate)
            if quality > best_quality:
                best = candidate
                best_quality = quality
    return best


def _fives(
    pivots: list[Pivot],
    start: int,
    end: int,
    direction: Direction,
    pattern: str,
) -> list[Structure]:
    if end - start < 5:
        return []
    found: list[Structure] = []
    for index, points in enumerate(iter_points(start, end, 5)):
        if index >= _MAX_COMBINATIONS:
            break
        prices = [pivots[point].price for point in points]
        if pattern == "impulse" and valid_impulse(prices, direction):
            found.append(Structure(pattern, direction, None, tuple(points)))
        elif pattern in {"leading_diagonal", "ending_diagonal"} and valid_diagonal(prices, direction):
            found.append(Structure(pattern, direction, None, tuple(points)))
        elif pattern == "triangle" and valid_triangle(prices):
            found.append(Structure(pattern, direction, None, tuple(points)))
    return found


def _threes(
    pivots: list[Pivot],
    start: int,
    end: int,
    direction: Direction,
    pattern: str,
) -> list[Structure]:
    if end - start < 3:
        return []
    found: list[Structure] = []
    for index, points in enumerate(iter_points(start, end, 3)):
        if index >= _MAX_COMBINATIONS:
            break
        prices = [pivots[point].price for point in points]
        if pattern == "zigzag" and valid_zigzag(prices, direction):
            found.append(Structure(pattern, direction, None, tuple(points)))
        elif pattern == "flat":
            variant = classify_flat(prices, direction)
            if variant is not None:
                found.append(Structure(pattern, direction, variant, tuple(points)))
    return found


def iter_points(start: int, end: int, n_waves: int):
    if n_waves < 1 or end - start < n_waves:
        return
    if (end - start) % 2 != n_waves % 2:
        return

    def walk(prev: int, waves_left: int, path: list[int]):
        if waves_left == 1:
            if (end - prev) % 2 == 1:
                yield [*path, end]
            return
        last = end - (waves_left - 1)
        for nxt in range(prev + 1, last + 1):
            if (nxt - prev) % 2 == 0:
                continue
            if (end - nxt) < waves_left - 1:
                continue
            if (end - nxt) % 2 != (waves_left - 1) % 2:
                continue
            path.append(nxt)
            yield from walk(nxt, waves_left - 1, path)
            path.pop()

    yield from walk(start, n_waves, [start])


def _split_ends(start: int, end: int, min_gap: int, min_after: int):
    last = end - min_after
    for index in range(start + min_gap, last + 1):
        if (index - start) % 2 == min_gap % 2:
            yield index


def _quality(pivots: list[Pivot], structure: Structure) -> float:
    prices = [pivots[point].price for point in structure.points]
    if structure.pattern == "combination" and structure.children:
        parts = [_quality(pivots, child) for child in structure.children]
        return sum(parts) / len(parts)
    return fib_quality(structure.pattern, prices)
