"""JSON for the CLI and the payload drawn by the local chart."""

from __future__ import annotations

from elliot.models import Analysis, Bar, Count, Wave

_PATTERN_LABELS = {
    "impulse": "Impulso",
    "leading_diagonal": "Diagonal de inicio",
    "ending_diagonal": "Diagonal de finalización",
    "zigzag": "Zigzag",
    "flat": "Plana",
    "triangle": "Triángulo",
    "combination": "Combinación W-X-Y",
}
_DIRECTION_LABELS = {"bullish": "Alcista", "bearish": "Bajista"}
_STATUS_LABELS = {"complete": "Cerrado", "in_progress": "En curso"}


def analysis_to_dict(analysis: Analysis) -> dict:
    return {
        "primary": None if analysis.primary is None else count_to_dict(analysis.primary),
        "alternates": [count_to_dict(count) for count in analysis.alternates],
        "pivots": len(analysis.pivots),
    }


def count_to_dict(count: Count) -> dict:
    return {
        "score": count.score,
        "direction": count.direction,
        "pattern": count.pattern,
        "status": count.status,
        "invalidated": count.invalidated,
        "variant": count.variant,
        "waves": [_wave_dict(wave) for wave in count.waves],
        "invalidation": count.invalidation,
        "projections": [
            {
                "target": item.target,
                "ratio": item.ratio,
                "price": item.price,
                "basis": item.basis,
                "label": item.label,
            }
            for item in count.projections
        ],
        "guideline_notes": list(count.guideline_notes),
    }


def chart_payload(bars: list[Bar], analysis: Analysis) -> dict:
    counts = []
    titles = ["Primario", "Alternativa 1", "Alternativa 2"]
    for index, count in enumerate(analysis.counts):
        counts.append(_chart_count(count, titles[index] if index < len(titles) else f"Conteo {index + 1}"))
    _assign_weights(counts)
    from elliot.forecast import build_forecast, forecast_to_dict

    return {
        "candles": _candles(bars),
        "counts": counts,
        "pivots": len(analysis.pivots),
        "forecast": forecast_to_dict(build_forecast(bars, analysis)),
    }


def _chart_count(count: Count, title: str) -> dict:
    pattern = _PATTERN_LABELS.get(count.pattern, count.pattern)
    return {
        "id": title.lower().replace(" ", "-"),
        "title": title,
        "score": count.score,
        "weight": 0.0,
        "pattern": count.pattern,
        "pattern_label": pattern,
        "direction": count.direction,
        "direction_label": _DIRECTION_LABELS.get(count.direction, count.direction),
        "status": count.status,
        "status_label": _STATUS_LABELS.get(count.status, count.status),
        "invalidated": count.invalidated,
        "variant": count.variant,
        "notes": list(count.guideline_notes),
        "invalidation": count.invalidation,
        "projections": _projection_rows(count),
        "polyline": _polyline(count),
        "subwaves": _subwaves(count),
    }


def _assign_weights(counts: list[dict]) -> None:
    """Share of the guideline score among live counts, not a market probability."""
    live = [count for count in counts if not count["invalidated"]]
    pool = live or counts
    total = sum(count["score"] for count in pool)
    for count in counts:
        if count["invalidated"] and live:
            count["weight"] = 0.0
        else:
            count["weight"] = round(100.0 * count["score"] / total, 1) if total else 0.0


def _projection_rows(count: Count) -> list[dict]:
    preferred = _preferred_indexes(count.projections)
    return [
        {
            "price": item.price,
            "label": item.label,
            "target": item.target,
            "ratio": item.ratio,
            "basis": item.basis,
            "preferred": index in preferred,
        }
        for index, item in enumerate(count.projections)
    ]


def _preferred_indexes(projections) -> set[int]:
    """One conventional level per wave: 1.618, 0.382, and wave-5 equality or 0.618."""
    groups: dict[str, list[int]] = {}
    for index, item in enumerate(projections):
        groups.setdefault(item.target, []).append(index)
    chosen: set[int] = set()
    for target, indexes in groups.items():
        if target == "breakout":
            chosen.update(indexes)
            continue
        chosen.add(_pick_preferred(projections, indexes, target))
    return chosen


def _pick_preferred(projections, indexes: list[int], target: str) -> int:
    def first(predicate) -> int | None:
        for index in indexes:
            if predicate(projections[index]):
                return index
        return None

    if target == "wave3":
        return first(lambda item: abs(item.ratio - 1.618) < 1e-9) or indexes[0]
    if target == "wave4":
        return first(lambda item: abs(item.ratio - 0.382) < 1e-9) or indexes[0]
    if target == "wave5":
        equality = first(lambda item: item.basis == "wave1" and abs(item.ratio - 1.0) < 1e-9)
        if equality is not None:
            return equality
        net = first(lambda item: item.basis == "net_0_3" and abs(item.ratio - 0.618) < 1e-9)
        return net if net is not None else indexes[0]
    if target in {"waveC", "waveY"}:
        return first(lambda item: abs(item.ratio - 1.0) < 1e-9) or indexes[0]
    return indexes[0]


def _polyline(count: Count) -> list[dict]:
    if not count.waves:
        return []
    origin = count.waves[0]
    points = [
        {
            "time": origin.time_start,
            "price": origin.price_start,
            "label": "0",
        }
    ]
    for wave in count.waves:
        points.append({"time": wave.time_end, "price": wave.price_end, "label": wave.label})
    return points


def _subwaves(count: Count) -> list[list[dict]]:
    paths: list[list[dict]] = []
    for wave in count.waves:
        if wave.subwaves_status != "present" or not wave.subwaves:
            continue
        first = wave.subwaves[0]
        path = [{"time": first.time_start, "price": first.price_start, "label": ""}]
        for sub in wave.subwaves:
            path.append({"time": sub.time_end, "price": sub.price_end, "label": sub.label})
        paths.append(path)
    return paths


def _wave_dict(wave: Wave) -> dict:
    return {
        "label": wave.label,
        "start_index": wave.start_index,
        "end_index": wave.end_index,
        "price_start": wave.price_start,
        "price_end": wave.price_end,
        "timestamp_start": wave.timestamp_start,
        "timestamp_end": wave.timestamp_end,
        "subwaves_status": wave.subwaves_status,
        "subpattern": wave.subpattern,
        "subwaves": [_wave_dict(sub) for sub in wave.subwaves],
    }


def _candles(bars: list[Bar]) -> list[dict]:
    candles = []
    previous = -1
    for bar in bars:
        time = bar.time
        if time <= previous:
            time = previous + 1
        previous = time
        candles.append(
            {
                "time": time,
                "open": bar.open,
                "high": bar.high,
                "low": bar.low,
                "close": bar.close,
            }
        )
    return candles
