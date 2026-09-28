"""Parallel channel through the ends of waves 1 and 3, projected from wave 2."""

from __future__ import annotations

from elliot.models import Wave


def channel_score(waves: tuple[Wave, ...]) -> tuple[float, tuple[str, ...]]:
    by_label = {wave.label: wave for wave in waves}
    if any(label not in by_label for label in ("1", "2", "3", "4")):
        return 0.0, ()

    origin_x = by_label["1"].start_index
    x1, y1 = by_label["1"].end_index, by_label["1"].price_end
    x2, y2 = by_label["2"].end_index, by_label["2"].price_end
    x3, y3 = by_label["3"].end_index, by_label["3"].price_end
    x4, y4 = by_label["4"].end_index, by_label["4"].price_end
    del origin_x

    if x3 == x1:
        return 0.0, ()
    slope = (y3 - y1) / (x3 - x1)
    projected = y2 + slope * (x4 - x2)
    scale = abs(y3 - y2) or 1.0
    residual = abs(y4 - projected) / scale
    quality = max(0.0, 1.0 - residual / 0.25)
    if quality < 0.4:
        return quality * 10, ()
    return quality * 10, ("la onda 4 respeta el canal 1-3 / 2",)
