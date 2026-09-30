"""Command line: download prices, JSON counts, a local chart, or the forecast of the open wave."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date

from elliot.engine import analyze
from elliot.io.csv_loader import load_ohlc
from elliot.serialize import analysis_to_dict, chart_payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="elliot")
    sub = parser.add_subparsers(dest="command", required=True)

    fetch = sub.add_parser("fetch", help="Baja velas diarias de Yahoo Finance a un CSV")
    fetch.add_argument("ticker")
    fetch.add_argument("--from", dest="start", type=_iso_date, required=True, help="YYYY-MM-DD")
    fetch.add_argument("--to", dest="end", type=_iso_date, default=None, help="YYYY-MM-DD, default hoy")
    fetch.add_argument("--out", default=None, help="Ruta del CSV. Default data/<TICKER>_<from>_<to>.csv")

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

    forecast = sub.add_parser("forecast", help="Objetivo de la onda abierta, zonas de confluencia y riesgo")
    _add_series_args(forecast)
    forecast.add_argument("--top", type=int, default=3)
    forecast.add_argument(
        "--tolerance",
        type=float,
        default=0.015,
        help="Ancho de una zona como fracción del último cierre (default 0.015)",
    )
    forecast.add_argument("--json", action="store_true", help="Escribe el resultado en JSON")

    args = parser.parse_args(argv)
    try:
        if args.command == "fetch":
            return _run_fetch(args)
        if args.command == "forecast":
            return _run_forecast(args)
        return _run_analysis(args)
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


def _run_fetch(args: argparse.Namespace) -> int:
    from elliot.io.fetch import default_output, fetch_daily, write_ohlc_csv

    end = args.end or date.today()
    bars = fetch_daily(args.ticker, args.start, end)
    target = write_ohlc_csv(args.out or default_output(args.ticker, args.start, end), bars)
    print(f"{target} ({len(bars)} velas, {bars[0].timestamp} a {bars[-1].timestamp})")
    return 0


def _run_analysis(args: argparse.Namespace) -> int:
    bars = load_ohlc(args.csv)
    analysis = analyze(
        bars,
        deviation=args.deviation,
        mode=args.mode,
        atr_period=args.atr_period,
        atr_mult=args.atr_mult,
        top=args.top,
    )

    if args.command == "counts":
        print(json.dumps(analysis_to_dict(analysis), ensure_ascii=False, indent=2))
        return 0

    from elliot.web.server import serve

    payload = chart_payload(bars, analysis)
    serve(payload, host=args.host, port=args.port, open_browser=not args.no_browser)
    return 0


def _run_forecast(args: argparse.Namespace) -> int:
    from elliot.forecast import build_forecast, forecast_text, forecast_to_dict

    if args.tolerance <= 0:
        raise ValueError("--tolerance tiene que ser mayor que 0")
    bars = load_ohlc(args.csv)
    analysis = analyze(
        bars,
        deviation=args.deviation,
        mode=args.mode,
        atr_period=args.atr_period,
        atr_mult=args.atr_mult,
        top=args.top,
    )
    result = build_forecast(bars, analysis, tolerance=args.tolerance)
    if args.json:
        print(json.dumps(forecast_to_dict(result), ensure_ascii=False, indent=2))
    else:
        print(forecast_text(result))
    return 0


def _add_series_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("csv")
    parser.add_argument("--deviation", type=float, default=0.03)
    parser.add_argument("--mode", choices=("percent", "atr"), default="percent")
    parser.add_argument("--atr-mult", type=float, default=2.0, dest="atr_mult")
    parser.add_argument("--atr-period", type=int, default=14, dest="atr_period")


def _iso_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"fecha inválida: {value}. Usá YYYY-MM-DD") from exc
