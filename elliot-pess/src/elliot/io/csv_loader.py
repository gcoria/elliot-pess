"""Load an OHLC series from CSV."""

from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path

from elliot.models import Bar

_REQUIRED = ("timestamp", "open", "high", "low", "close")
_TIME_FORMATS = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y/%m/%d %H:%M:%S", "%Y/%m/%d")


def load_ohlc(path: str | Path) -> list[Bar]:
    file_path = Path(path)
    if not file_path.is_file():
        raise FileNotFoundError(f"No existe el archivo: {file_path}")

    with file_path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError("El CSV no tiene encabezado")
        columns = {_normal(name): name for name in reader.fieldnames if name}
        missing = [name for name in _REQUIRED if name not in columns]
        if missing:
            raise ValueError(
                "Faltan columnas: " + ", ".join(missing) + ". Se esperan timestamp,open,high,low,close"
            )
        bars: list[Bar] = []
        for line_no, row in enumerate(reader, start=2):
            if row is None or not any((value or "").strip() for value in row.values()):
                continue
            bars.append(_bar(row, columns, line_no, len(bars)))

    if not bars:
        raise ValueError("El CSV no tiene velas")
    return bars


def _normal(name: str) -> str:
    return name.strip().lower().replace(" ", "")


def _bar(row: dict[str, str | None], columns: dict[str, str], line_no: int, index: int) -> Bar:
    try:
        timestamp = (row[columns["timestamp"]] or "").strip()
        open_ = float(row[columns["open"]] or "")
        high = float(row[columns["high"]] or "")
        low = float(row[columns["low"]] or "")
        close = float(row[columns["close"]] or "")
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Fila {line_no}: no se pudo leer OHLC") from exc

    if not timestamp:
        raise ValueError(f"Fila {line_no}: timestamp vacío")
    if high < low:
        raise ValueError(f"Fila {line_no}: high es menor que low")
    if high < max(open_, close) or low > min(open_, close):
        raise ValueError(f"Fila {line_no}: open/close fuera del rango high-low")

    return Bar(
        timestamp=timestamp,
        open=open_,
        high=high,
        low=low,
        close=close,
        index=index,
        time=_epoch(timestamp, line_no),
    )


def _epoch(value: str, line_no: int) -> int:
    if value.isdigit():
        return int(value)
    text = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        parsed = None
        for fmt in _TIME_FORMATS:
            try:
                parsed = datetime.strptime(value, fmt)
                break
            except ValueError:
                continue
        if parsed is None:
            raise ValueError(f"Fila {line_no}: timestamp no reconocido: {value}")
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return int(parsed.timestamp())
