"""One motive wave extends; the other two tend toward equality or 0.618."""

from __future__ import annotations

from elliot.guidelines.fibonacci import closeness
from elliot.models import Wave


def extension_score(waves: tuple[Wave, ...]) -> tuple[float, tuple[str, ...]]:
    by_label = {wave.label: wave for wave in waves}
    if any(label not in by_label for label in ("1", "3", "5")):
        return 0.0, ()

    lengths = {label: abs(by_label[label].price_end - by_label[label].price_start) for label in ("1", "3", "5")}
    extended = max(lengths, key=lengths.get)
    others = [length for label, length in lengths.items() if label != extended]
    longest_other = max(others) if others else 0.0
    notes: list[str] = []
    points = 0.0

    if longest_other > 0 and lengths[extended] >= 1.618 * longest_other * 0.95:
        points += 8
        notes.append(f"onda {extended} extendida")
    elif longest_other > 0 and lengths[extended] >= 1.382 * longest_other:
        points += 4
        notes.append(f"onda {extended} es la más larga")

    if extended == "3" and lengths["1"] > 0:
        ratio = lengths["5"] / lengths["1"]
        time_ratio = _duration(by_label["5"]) / _duration(by_label["1"])
        equality = max(closeness(ratio, (1.0, 0.618)), closeness(time_ratio, (1.0, 0.618)))
        points += 7 * equality
        if equality >= 0.8:
            notes.append("ondas 1 y 5 cercanas a igualdad o 0.618")
    elif lengths["3"] > 0 and extended in {"1", "5"}:
        left, right = ("3", "5") if extended == "1" else ("1", "3")
        ratio = lengths[right] / lengths[left] if lengths[left] else 0
        equality = closeness(ratio, (1.0, 0.618, 1.618))
        points += 7 * equality

    return min(15.0, points), tuple(notes)


def _duration(wave: Wave) -> float:
    return float(max(wave.end_index - wave.start_index, 1))
