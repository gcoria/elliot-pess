"""Download daily candles from Yahoo Finance and write the CSV the engine reads."""

from __future__ import annotations

import math
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from elliot.models import Bar

_COLUMNS = ("Open", "High", "Low", "Close")


def fetch_daily(ticker: str, start: date, end: date) -> list[Bar]:
    symbol = ticker.strip().upper()
    if not symbol:
        raise ValueError("El ticker está vacío")
    if start > end:
        raise ValueError(f"--from ({start}) es posterior a --to ({end})")

    try:
        import yfinance
    except ImportError as exc:
        raise ValueError(
            "Falta yfinance. Instalá el extra de datos con: pip install -e \".[data]\""
        ) from exc

    # Yahoo treats `end` as exclusive; add one day so the requested last date is included.
    frame = yfinance.download(
        symbol,
        start=start.isoformat(),
        end=(end + timedelta(days=1)).isoformat(),
        interval="1d",
        auto_adjust=False,
        progress=False,
    )
    return frame_to_bars(frame, symbol)


def frame_to_bars(frame, symbol: str) -> list[Bar]:
    if frame is None or len(frame) == 0:
        raise ValueError(f"Yahoo no devolvió velas para {symbol} en ese rango")

    columns = _flatten_columns(frame)
    missing = [name for name in _COLUMNS if name not in columns]
    if missing:
        raise ValueError(f"La respuesta de Yahoo no trae columnas {', '.join(missing)}")

    bars: list[Bar] = []
    for stamp, row in frame.iterrows():
        values = [row[columns[name]] for name in _COLUMNS]
        if any(_is_nan(value) for value in values):
            continue
        # Yahoo serves float32 (187.14999389648438); round to the cent-level precision it means.
        open_, high, low, close = (round(float(value), 6) for value in values)
        day = _as_date(stamp)
        moment = datetime(day.year, day.month, day.day, tzinfo=timezone.utc)
        bars.append(
            Bar(
                timestamp=day.isoformat(),
                open=open_,
                high=max(high, open_, close),
                low=min(low, open_, close),
                close=close,
                index=len(bars),
                time=int(moment.timestamp()),
            )
        )
    if not bars:
        raise ValueError(f"Yahoo devolvió solo filas vacías para {symbol}")
    return bars


def write_ohlc_csv(path: str | Path, bars: list[Bar]) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    lines = ["timestamp,open,high,low,close"]
    for bar in bars:
        lines.append(f"{bar.timestamp},{bar.open!r},{bar.high!r},{bar.low!r},{bar.close!r}")
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return target


def default_output(ticker: str, start: date, end: date) -> Path:
    return Path("data") / f"{ticker.strip().upper()}_{start.isoformat()}_{end.isoformat()}.csv"


def _flatten_columns(frame) -> dict[str, object]:
    """Map 'Open'/'High'/... to the actual column key, whether flat or MultiIndex."""
    mapping: dict[str, object] = {}
    for column in frame.columns:
        name = column[0] if isinstance(column, tuple) else column
        if name in _COLUMNS and name not in mapping:
            mapping[name] = column
    return mapping


def _as_date(stamp) -> date:
    if isinstance(stamp, datetime):
        return stamp.date()
    if isinstance(stamp, date):
        return stamp
    if hasattr(stamp, "to_pydatetime"):
        return stamp.to_pydatetime().date()
    return date.fromisoformat(str(stamp)[:10])


def _is_nan(value) -> bool:
    try:
        return math.isnan(float(value))
    except (TypeError, ValueError):
        return True
