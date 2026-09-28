"""Command line: JSON counts, or a local chart of the projections."""

from __future__ import annotations

import argparse
import json
import sys

from elliot.engine import analyze
from elliot.io.csv_loader import load_ohlc
from elliot.serialize import analysis_to_dict, chart_payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="elliot")
    sub = parser.add_subparsers(dest="command", required=True)

    counts = sub.add_parser("counts", help="Cuenta ondas y escribe JSON")
    _add_series_args(counts)
    counts.add_argument("--top", type=int, default=3)
    counts.add_argument("--json", action="store_true", help="Escribe el resultado en JSON")

    view = sub.add_parser("view", help="Abre el gráfico con conteos y proyecciones")
    _add_series_args(view)
    view.add_argument("--top", type=int, default=3)
    view.add_argument("--host", default="127.0.0.1")
    view.add_argument("--port", type=int, default=8765)
    view.add_argument("--no-browser", action="store_true")

    args = parser.parse_args(argv)
    try:
        bars = load_ohlc(args.csv)
        analysis = analyze(
            bars,
            deviation=args.deviation,
            mode=args.mode,
            atr_period=args.atr_period,
            atr_mult=args.atr_mult,
            top=args.top,
        )
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if args.command == "counts":
        print(json.dumps(analysis_to_dict(analysis), ensure_ascii=False, indent=2))
        return 0

    from elliot.web.server import serve

    payload = chart_payload(bars, analysis)
    serve(payload, host=args.host, port=args.port, open_browser=not args.no_browser)
    return 0


def _add_series_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("csv")
    parser.add_argument("--deviation", type=float, default=0.03)
    parser.add_argument("--mode", choices=("percent", "atr"), default="percent")
    parser.add_argument("--atr-mult", type=float, default=2.0, dest="atr_mult")
    parser.add_argument("--atr-period", type=int, default=14, dest="atr_period")
