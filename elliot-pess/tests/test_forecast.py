import json

import pytest

from elliot.cli import main
from elliot.engine import analyze
from elliot.forecast import CountForecast, Target, build_forecast, find_zones

from synthetic import GOLDEN, bars_from_prices, write_csv


def test_closed_impulse_projects_the_retracement_of_the_whole_move():
    bars = bars_from_prices(GOLDEN)
    result = build_forecast(bars, analyze(bars, deviation=0.02))
    primary = result.counts[0]
    assert primary.title == "Primario"
    assert primary.pattern == "impulse"
    assert primary.step == "retracement"
    assert primary.invalidation == 125
    assert [round(target.price, 2) for target in primary.targets] == [115.45, 112.5, 109.55]
    assert primary.central is not None and primary.central.ratio == 0.5
    assert primary.band == pytest.approx((109.55, 115.45))


def test_in_progress_impulse_projects_the_open_wave_five():
    bars = bars_from_prices((100.0, 110.0, 105.0, 121.18, 115.0))
    result = build_forecast(bars, analyze(bars, deviation=0.02))
    fives = [count for count in result.counts if count.pattern == "impulse" and count.step == "wave5"]
    assert fives
    wave5 = fives[0]
    assert wave5.invalidation == 110
    assert wave5.central is not None
    assert wave5.central.ratio == 1.0 and wave5.central.basis == "wave1"
    assert wave5.central.price == pytest.approx(125.0)
    assert wave5.central.reward_risk == pytest.approx(2.0)
    assert all(not target.reached for target in wave5.targets)


def test_invalidated_counts_do_not_forecast():
    bounce = [140.0, 100.0, 112.0, 104.0, 118.0, 108.0, 116.0, 80.0]
    bars = bars_from_prices(bounce)
    analysis = analyze(bars, deviation=0.02, top=8)
    result = build_forecast(bars, analysis)
    assert result.counts
    live = {count.title for count in result.counts}
    titles = ["Primario", "Alternativa 1", "Alternativa 2"]
    for index, count in enumerate(analysis.counts):
        title = titles[index] if index < len(titles) else f"Conteo {index + 1}"
        if count.invalidated or not count.at_edge:
            assert title not in live
    assert abs(sum(count.weight for count in result.counts) - 100) < 0.5


def test_zones_join_central_levels_within_tolerance():
    counts = (
        _forecast("Primario", 100.0, 50.0),
        _forecast("Alternativa 1", 101.0, 30.0),
        _forecast("Alternativa 2", 110.0, 20.0),
    )
    zones = find_zones(counts, close=90.0, tolerance=0.015)
    assert len(zones) == 1
    assert zones[0].titles == ("Primario", "Alternativa 1")
    assert (zones[0].low, zones[0].high) == (100.0, 101.0)
    assert zones[0].weight == 80.0
    assert find_zones(counts, close=90.0, tolerance=0.005) == []


def test_forecast_cli_json(tmp_path, capsys):
    path = tmp_path / "golden.csv"
    write_csv(path, bars_from_prices(GOLDEN))
    assert main(["forecast", str(path), "--deviation", "0.02", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert set(payload) == {"last_close", "last_timestamp", "tolerance", "counts", "zones"}
    assert payload["last_close"] == 125
    first = payload["counts"][0]
    assert first["step"] == "retracement"
    assert {"price", "ratio", "basis", "central", "reached", "distance_pct", "reward_risk"} <= set(first["targets"][0])


def test_forecast_cli_text_and_bad_tolerance(tmp_path, capsys):
    path = tmp_path / "golden.csv"
    write_csv(path, bars_from_prices(GOLDEN))
    assert main(["forecast", str(path), "--deviation", "0.02"]) == 0
    text = capsys.readouterr().out
    assert "Onda abierta por conteo" in text
    assert "Zonas de confluencia" in text
    assert "no una probabilidad de mercado" in text
    assert main(["forecast", str(path), "--tolerance", "0"]) == 1


def _forecast(title: str, price: float, weight: float) -> CountForecast:
    target = Target(
        price=price,
        ratio=1.0,
        basis="wave1",
        central=True,
        reached=False,
        distance_pct=0.0,
        reward_risk=None,
    )
    return CountForecast(
        title=title,
        pattern="impulse",
        direction="bullish",
        status="in_progress",
        score=weight,
        weight=weight,
        step="wave5",
        two_sided=False,
        invalidation=80.0,
        invalidation_pct=0.0,
        band=(price, price),
        targets=(target,),
    )
