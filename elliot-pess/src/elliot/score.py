"""Weighted score for counts that already passed the cardinal rules."""

from __future__ import annotations

from elliot.guidelines.alternation import alternation_score
from elliot.guidelines.channel import channel_score
from elliot.guidelines.equality import extension_score
from elliot.guidelines.fibonacci import fib_quality, ratio_closeness
from elliot.models import Wave

_MOTIVE = {"impulse", "leading_diagonal", "ending_diagonal"}
_FLAT_NAMES = {
    "regular": "plana regular",
    "expanded": "plana expandida",
    "running": "plana corrida",
}


def score_waves(
    pattern: str,
    prices: list[float] | tuple[float, ...],
    waves: tuple[Wave, ...],
    variant: str | None,
) -> tuple[float, tuple[str, ...]]:
    samples = ratio_closeness(pattern, prices)
    fib_points = 0.0 if not samples else 40.0 * (sum(value for _name, value in samples) / len(samples))
    notes: list[str] = [name for name, value in samples if value >= 0.8]

    sub_points = _subwave_points(waves)
    if pattern in _MOTIVE:
        extension_points, extension_notes = extension_score(waves)
        alternation_points, alternation_notes = alternation_score(waves)
        channel_points, channel_notes = channel_score(waves)
    else:
        extension_points, extension_notes = 0.0, ()
        alternation_points, alternation_notes = 0.0, ()
        channel_points, channel_notes = 0.0, ()

    if variant in _FLAT_NAMES:
        notes.append(_FLAT_NAMES[variant])
    if any(wave.subwaves_status == "insufficient" for wave in waves):
        pass

    total = fib_points + sub_points + extension_points + alternation_points + channel_points
    ordered = (*notes, *extension_notes, *alternation_notes, *channel_notes)
    return round(min(100.0, total), 1), ordered


def _subwave_points(waves: tuple[Wave, ...]) -> float:
    if not waves:
        return 0.0
    qualities: list[float] = []
    for wave in waves:
        if wave.subwaves_status != "present" or not wave.subwaves:
            qualities.append(0.4)
            continue
        inner_prices = [wave.subwaves[0].price_start, *[item.price_end for item in wave.subwaves]]
        inner_pattern = wave.subpattern or "impulse"
        qualities.append(0.75 + 0.25 * fib_quality(inner_pattern, inner_prices))
    return 20.0 * (sum(qualities) / len(qualities))
