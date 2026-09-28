"""Synthetic OHLC whose swings are the pivots we intend to count."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from elliot.models import Bar

GOLDEN = (100.0, 110.0, 105.0, 121.18, 115.0, 125.0)


def bars_from_prices(prices: list[float] | tuple[float, ...], bars_per_leg: int = 5) -> list[Bar]:
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    bars: list[Bar] = []

    def add(open_: float, close: float) -> None:
        moment = start + timedelta(hours=len(bars))
        bars.append(
            Bar(
                timestamp=moment.isoformat(),
                open=open_,
                high=max(open_, close),
                low=min(open_, close),
                close=close,
                index=len(bars),
                time=int(moment.timestamp()),
            )
        )

    add(prices[0], prices[0])
    for left, right in zip(prices, prices[1:]):
        for step in range(bars_per_leg):
            open_ = left + (right - left) * step / bars_per_leg
            close = left + (right - left) * (step + 1) / bars_per_leg
            add(open_, close)
    return bars


def write_csv(path, bars: list[Bar]) -> None:
    lines = ["timestamp,open,high,low,close"]
    for bar in bars:
        lines.append(f"{bar.timestamp},{bar.open},{bar.high},{bar.low},{bar.close}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
