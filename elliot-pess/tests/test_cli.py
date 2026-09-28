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
    assert body["counts"][0]["pattern"] == "impulse"
    assert body["counts"][0]["projections"]
    assert body["counts"][0]["invalidation"] == 110
    page = client.get("/")
    assert page.status_code == 200
    assert "Subondas" in page.text
    assert "lightweight-charts" in page.text
