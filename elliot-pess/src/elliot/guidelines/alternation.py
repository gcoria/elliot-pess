"""Alternation between waves 2 and 4: depth, time and corrective character."""

from __future__ import annotations

from elliot.models import Wave

_SHARP = {"zigzag", "simple"}
_SIDEWAYS = {"flat", "triangle", "combination"}


def alternation_score(waves: tuple[Wave, ...]) -> tuple[float, tuple[str, ...]]:
    by_label = {wave.label: wave for wave in waves}
    wave2 = by_label.get("2")
    wave4 = by_label.get("4")
    wave1 = by_label.get("1")
    wave3 = by_label.get("3")
    if wave1 is None or wave2 is None or wave3 is None or wave4 is None:
        return 0.0, ()

    retrace2 = _retrace(wave1, wave2)
    retrace4 = _retrace(wave3, wave4)
    points = 0.0
    notes: list[str] = []

    kind2 = wave2.subpattern or "simple"
    kind4 = wave4.subpattern or "simple"
    if (kind2 in _SHARP and kind4 in _SIDEWAYS) or (kind4 in _SHARP and kind2 in _SIDEWAYS):
        points += 8
        notes.append("alternancia de estructura entre las ondas 2 y 4")

    if (retrace2 >= 0.5 and retrace4 <= 0.4) or (retrace4 >= 0.5 and retrace2 <= 0.4):
        points += 7
        notes.append("alternancia de profundidad entre las ondas 2 y 4")
    elif abs(retrace2 - retrace4) >= 0.12:
        points += 4

    duration2 = max(wave2.end_index - wave2.start_index, 1)
    duration4 = max(wave4.end_index - wave4.start_index, 1)
    if max(duration2, duration4) / min(duration2, duration4) >= 1.6:
        points += 4
        notes.append("alternancia de tiempo entre las ondas 2 y 4")

    return min(15.0, points), tuple(notes)


def _retrace(impulse: Wave, correction: Wave) -> float:
    span = abs(impulse.price_end - impulse.price_start)
    if span == 0:
        return 0.0
    return abs(correction.price_end - correction.price_start) / span
