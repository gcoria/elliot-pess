"""Where the open wave of each live count could go, where counts agree, and what breaks them."""

from __future__ import annotations

from dataclasses import dataclass

from elliot.models import Analysis, Bar, Count
from elliot.serialize import _pick_preferred

_MOTIVE = {"impulse", "leading_diagonal", "ending_diagonal"}
_THREE = {"zigzag", "flat"}
_OPEN_MOTIVE = {2: "wave3", 3: "wave4", 4: "wave5"}
_RETRACE = (0.382, 0.5, 0.618)
_PATTERN_LABELS = {
    "impulse": "Impulso",
    "leading_diagonal": "Diagonal de inicio",
    "ending_diagonal": "Diagonal de finalización",
    "zigzag": "Zigzag",
    "flat": "Plana",
    "triangle": "Triángulo",
    "combination": "Combinación W-X-Y",
}
_STEP_LABELS = {
    "wave3": "onda 3",
    "wave4": "onda 4",
    "wave5": "onda 5",
    "waveC": "onda C",
    "retracement": "retroceso de 0-5",
    "resumption": "reanudación",
    "breakout": "ruptura",
}
_BASIS_LABELS = {
    "wave1": "onda 1",
    "wave3": "onda 3",
    "net_0_3": "neto 0-3",
    "waveA": "onda A",
    "waveW": "onda W",
}


@dataclass(frozen=True)
class Target:
    price: float
    ratio: float
    basis: str
    central: bool
    reached: bool
    distance_pct: float
    reward_risk: float | None


@dataclass(frozen=True)
class CountForecast:
    title: str
    pattern: str
    direction: str
    status: str
    score: float
    weight: float
    step: str
    two_sided: bool
    invalidation: float
    invalidation_pct: float
    band: tuple[float, float] | None
    targets: tuple[Target, ...]

    @property
    def central(self) -> Target | None:
        for target in self.targets:
            if target.central and not target.reached:
                return target
        return None


@dataclass(frozen=True)
class Zone:
    low: float
    high: float
    titles: tuple[str, ...]
    weight: float


@dataclass(frozen=True)
class Forecast:
    last_close: float
    last_timestamp: str
    tolerance: float
    counts: tuple[CountForecast, ...]
    zones: tuple[Zone, ...]


def build_forecast(bars: list[Bar], analysis: Analysis, tolerance: float = 0.015) -> Forecast:
    if not bars:
        raise ValueError("no hay velas para proyectar")
    close = bars[-1].close
    titles = ["Primario", "Alternativa 1", "Alternativa 2"]
    live = [
        (titles[index] if index < len(titles) else f"Conteo {index + 1}", count)
        for index, count in enumerate(analysis.counts)
        if count.at_edge and not count.invalidated
    ]
    total = sum(count.score for _, count in live)
    forecasts = tuple(
        _count_forecast(title, count, close, round(100.0 * count.score / total, 1) if total else 0.0)
        for title, count in live
    )
    return Forecast(
        last_close=close,
        last_timestamp=bars[-1].timestamp,
        tolerance=tolerance,
        counts=forecasts,
        zones=tuple(find_zones(forecasts, close, tolerance)),
    )


def find_zones(counts, close: float, tolerance: float) -> list[Zone]:
    """Group the central levels of different counts that sit within tolerance of each other."""
    order = {count.title: index for index, count in enumerate(counts)}
    levels = sorted(
        (count.central.price, count.title, count.weight) for count in counts if count.central is not None
    )
    width = tolerance * close
    zones: list[Zone] = []
    group: list[tuple[float, str, float]] = []
    for level in levels:
        if group and level[0] - group[0][0] > width:
            zones.extend(_zone(group, order))
            group = []
        group.append(level)
    zones.extend(_zone(group, order))
    return zones


def _zone(group: list[tuple[float, str, float]], order: dict[str, int]) -> list[Zone]:
    weights: dict[str, float] = {}
    for _, title, weight in group:
        weights.setdefault(title, weight)
    if len(weights) < 2:
        return []
    return [
        Zone(
            low=group[0][0],
            high=group[-1][0],
            titles=tuple(sorted(weights, key=lambda title: order.get(title, len(order)))),
            weight=round(sum(weights.values()), 1),
        )
    ]


def _count_forecast(title: str, count: Count, close: float, weight: float) -> CountForecast:
    step, levels, invalidation, two_sided = _next_move(count)
    sign = _move_sign(count, step)
    targets = tuple(
        _target(price, ratio, basis, central, close, invalidation, sign)
        for price, ratio, basis, central in levels
    )
    prices = [target.price for target in targets]
    return CountForecast(
        title=title,
        pattern=count.pattern,
        direction=count.direction,
        status=count.status,
        score=count.score,
        weight=weight,
        step=step,
        two_sided=two_sided,
        invalidation=invalidation,
        invalidation_pct=_pct(invalidation, close),
        band=(min(prices), max(prices)) if prices else None,
        targets=targets,
    )


def _next_move(count: Count):
    """Levels as (price, ratio, basis, central) for the wave that is still open."""
    size = len(count.waves)
    if count.status == "in_progress":
        if count.pattern in _MOTIVE and size in _OPEN_MOTIVE:
            return _from_projections(count, _OPEN_MOTIVE[size])
        if count.pattern in _THREE and size == 2:
            return _from_projections(count, "waveC")
        return "", [], count.invalidation, False
    if count.pattern in _MOTIVE:
        origin = count.waves[0].price_start
        top = count.waves[-1].price_end
        levels = [(top - ratio * (top - origin), ratio, "0-5", ratio == 0.5) for ratio in _RETRACE]
        return "retracement", levels, top, False
    if count.pattern in _THREE or count.pattern == "combination":
        basis = "origen W" if count.pattern == "combination" else "origen A"
        return "resumption", [(count.waves[0].price_start, 1.0, basis, True)], count.waves[-1].price_end, False
    if count.pattern == "triangle":
        levels = [(item.price, item.ratio, item.basis, True) for item in count.projections if item.target == "breakout"]
        return "breakout", levels, count.invalidation, True
    return "", [], count.invalidation, False


def _from_projections(count: Count, target: str):
    indexes = [index for index, item in enumerate(count.projections) if item.target == target]
    if not indexes:
        return target, [], count.invalidation, False
    central = _pick_preferred(count.projections, indexes, target)
    levels = [
        (count.projections[index].price, count.projections[index].ratio, count.projections[index].basis, index == central)
        for index in indexes
    ]
    return target, levels, count.invalidation, False


def _move_sign(count: Count, step: str) -> int:
    """+1 if the open move goes up, -1 if down, 0 when it can break either way."""
    trend = 1 if count.direction == "bullish" else -1
    if step in {"wave3", "wave5", "waveC"}:
        return trend
    if step in {"wave4", "retracement", "resumption"}:
        return -trend
    return 0


def _target(price, ratio, basis, central, close, invalidation, sign) -> Target:
    reward = price - close
    reached = sign != 0 and reward * sign <= 0
    risk = (close - invalidation) * sign
    return Target(
        price=price,
        ratio=ratio,
        basis=basis,
        central=central,
        reached=reached,
        distance_pct=_pct(price, close),
        reward_risk=None if reached or risk <= 0 else round(abs(reward) / risk, 2),
    )


def _pct(price: float, close: float) -> float:
    return round(100.0 * (price - close) / close, 2) if close else 0.0


def forecast_to_dict(forecast: Forecast) -> dict:
    return {
        "last_close": forecast.last_close,
        "last_timestamp": forecast.last_timestamp,
        "tolerance": forecast.tolerance,
        "counts": [
            {
                "title": count.title,
                "pattern": count.pattern,
                "direction": count.direction,
                "status": count.status,
                "score": count.score,
                "weight": count.weight,
                "step": count.step,
                "step_label": _STEP_LABELS.get(count.step, count.step) or "sin objetivo",
                "two_sided": count.two_sided,
                "invalidation": count.invalidation,
                "invalidation_pct": count.invalidation_pct,
                "band": list(count.band) if count.band else None,
                "targets": [
                    {
                        "price": target.price,
                        "ratio": target.ratio,
                        "basis": target.basis,
                        "central": target.central,
                        "reached": target.reached,
                        "distance_pct": target.distance_pct,
                        "reward_risk": target.reward_risk,
                    }
                    for target in count.targets
                ],
            }
            for count in forecast.counts
        ],
        "zones": [
            {"low": zone.low, "high": zone.high, "titles": list(zone.titles), "weight": zone.weight}
            for zone in forecast.zones
        ],
    }


def forecast_text(forecast: Forecast) -> str:
    lines = [f"Último cierre {forecast.last_close:.2f} ({forecast.last_timestamp})", ""]
    if not forecast.counts:
        lines.append("Ningún conteo vivo llega al borde derecho: no hay objetivo por delante.")
        return "\n".join(lines)
    lines.append("Onda abierta por conteo")
    for count in forecast.counts:
        pattern = _PATTERN_LABELS.get(count.pattern, count.pattern)
        step = _STEP_LABELS.get(count.step, count.step) or "sin objetivo"
        central = count.central
        head = f"  {count.title} · {pattern} · {count.weight}% · próximo: {step}"
        if central is not None:
            head += f" → {central.price:.2f} ({central.distance_pct:+.2f}%)"
            if count.band and count.band[0] != count.band[1]:
                head += f", franja {count.band[0]:.2f}-{count.band[1]:.2f}"
        elif count.targets:
            head += " → objetivo central ya alcanzado"
        lines.append(head)
    lines.append("")
    lines.append(f"Zonas de confluencia (tolerancia {100 * forecast.tolerance:.1f}%)")
    if not forecast.zones:
        lines.append("  Ningún par de conteos apunta a la misma zona.")
    for zone in forecast.zones:
        lines.append(
            f"  {zone.low:.2f}-{zone.high:.2f} · {', '.join(zone.titles)} · peso {zone.weight}%"
        )
    lines.append("")
    lines.append("Riesgo")
    for count in forecast.counts:
        lines.append(f"  {count.title} · invalidación {count.invalidation:.2f} ({count.invalidation_pct:+.2f}%)")
        for target in count.targets:
            mark = "*" if target.central else " "
            if target.reached:
                tail = "alcanzado"
            elif target.reward_risk is None:
                tail = "dos lados" if count.two_sided else "el cierre está en la invalidación"
            else:
                tail = f"recompensa/riesgo {target.reward_risk}"
            ratio = f"{target.ratio:.3f}".rstrip("0").rstrip(".")
            basis_label = _BASIS_LABELS.get(target.basis, target.basis)
            basis = f" {basis_label}" if basis_label else ""
            lines.append(
                f"   {mark} {ratio}{basis} · {target.price:.2f} ({target.distance_pct:+.2f}%) · {tail}"
            )
    lines.append("")
    lines.append("El peso es la parte del puntaje entre los conteos vivos, no una probabilidad de mercado.")
    return "\n".join(lines)
