"""Series, pivots, waves and counts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

Direction = Literal["bullish", "bearish"]
SubwaveStatus = Literal["present", "insufficient"]
CountStatus = Literal["complete", "in_progress"]


@dataclass(frozen=True)
class Bar:
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    index: int
    time: int


@dataclass(frozen=True)
class Pivot:
    index: int
    price: float
    kind: Literal["high", "low"]
    timestamp: str
    time: int


@dataclass(frozen=True)
class Projection:
    target: str
    ratio: float
    price: float
    basis: str

    @property
    def label(self) -> str:
        short = {
            "wave3": "3",
            "wave4": "4",
            "wave5": "5",
            "waveC": "C",
            "waveY": "Y",
            "breakout": "ruptura",
        }.get(self.target, self.target)
        ratio = f"{self.ratio:.3f}".rstrip("0").rstrip(".")
        basis = ""
        if self.basis == "wave1":
            basis = " onda 1"
        elif self.basis == "net_0_3":
            basis = " neto 0-3"
        elif self.basis == "waveA":
            basis = " onda A"
        elif self.basis == "waveW":
            basis = " onda W"
        return f"{short} · {ratio}{basis} · {self.price:.2f}"


@dataclass(frozen=True)
class Wave:
    label: str
    start_index: int
    end_index: int
    price_start: float
    price_end: float
    time_start: int
    time_end: int
    timestamp_start: str
    timestamp_end: str
    subwaves_status: SubwaveStatus
    subpattern: str | None = None
    subwaves: tuple[Wave, ...] = ()


@dataclass(frozen=True)
class Count:
    score: float
    direction: Direction
    pattern: str
    status: CountStatus
    waves: tuple[Wave, ...]
    invalidation: float
    projections: tuple[Projection, ...]
    guideline_notes: tuple[str, ...]
    variant: str | None = None
    endpoint_indexes: tuple[int, ...] = field(default_factory=tuple)
    invalidated: bool = False
    at_edge: bool = True

    @property
    def end_prices(self) -> tuple[float, ...]:
        if not self.waves:
            return ()
        return (self.waves[0].price_start, *(wave.price_end for wave in self.waves))


@dataclass(frozen=True)
class Analysis:
    primary: Count | None
    alternates: tuple[Count, ...]
    pivots: tuple[Pivot, ...]
    considered: tuple[Count, ...]

    @property
    def counts(self) -> tuple[Count, ...]:
        if self.primary is None:
            return ()
        return (self.primary, *self.alternates)
