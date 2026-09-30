import json

from fastapi.testclient import TestClient

from elliot.cli import main
from elliot.serialize import chart_payload
from elliot.engine import analyze
from elliot.web.server import create_app

from synthetic import GOLDEN, bars_from_prices, write_csv


def test_counts_cli_prints_primary_json(tmp_path, capsys):
    path = tmp_path / "golden.csv"
    write_csv(path, bars_from_prices(GOLDEN))
    assert main(["counts", str(path), "--top", "3", "--json", "--deviation", "0.02"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["primary"]["pattern"] == "impulse"
    assert payload["primary"]["projections"]


def test_chart_api_exposes_prices_levels_and_page(tmp_path):
    bars = bars_from_prices(GOLDEN)
    analysis = analyze(bars, deviation=0.02)
    client = TestClient(create_app(chart_payload(bars, analysis)))
    body = client.get("/api/chart").json()
    assert body["candles"]
    primary = body["counts"][0]
    assert primary["pattern"] == "impulse"
    assert primary["invalidation"] == 110
    weights = [count["weight"] for count in body["counts"]]
    assert abs(sum(weights) - 100) < 0.2
    assert weights[0] == max(weights)
    preferred = [item for item in primary["projections"] if item["preferred"]]
    assert [(item["target"], item["ratio"], item["basis"]) for item in preferred] == [
        ("wave3", 1.618, "wave1"),
        ("wave4", 0.382, "wave3"),
        ("wave5", 1.0, "wave1"),
    ]
    assert any(not item["preferred"] for item in primary["projections"])
    page = client.get("/")
    assert page.status_code == 200
    assert "Subondas" in page.text
    assert "Pronóstico" in page.text
    assert body["forecast"]["counts"][0]["step"] == "retracement"
    assert body["forecast"]["last_close"] == 125
    assert "lightweight-charts" in page.text
    assert "count.invalidated" in page.text


def test_invalidated_count_is_not_drawn_as_live():
    bars = bars_from_prices(GOLDEN)
    analysis = analyze(bars, deviation=0.02)
    assert analysis.primary is not None
    from dataclasses import replace

    dead = replace(analysis.primary, invalidated=True, at_edge=False, score=99)
    mixed = replace(analysis, primary=analysis.primary, alternates=(dead,))
    body = chart_payload(bars, mixed)
    assert body["counts"][0]["invalidated"] is False
    assert body["counts"][1]["invalidated"] is True
    assert body["counts"][1]["weight"] == 0.0
    assert abs(body["counts"][0]["weight"] - 100) < 0.2
