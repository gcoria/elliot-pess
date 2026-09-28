from datetime import date

import pytest

pd = pytest.importorskip("pandas")
yfinance = pytest.importorskip("yfinance")

from elliot.cli import main
from elliot.io.csv_loader import load_ohlc
from elliot.io.fetch import default_output, fetch_daily, frame_to_bars, write_ohlc_csv


def _flat_frame():
    index = pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-04"])
    return pd.DataFrame(
        {
            "Open": [100.0, 102.0, float("nan")],
            "High": [105.0, 106.0, 110.0],
            "Low": [99.0, 101.0, 105.0],
            "Close": [102.0, 104.0, 108.0],
            "Adj Close": [102.0, 104.0, 108.0],
            "Volume": [1000, 1100, 1200],
        },
        index=index,
    )


def _multi_frame():
    flat = _flat_frame().drop(columns=["Adj Close", "Volume"])
    flat.columns = pd.MultiIndex.from_product([flat.columns, ["AAPL"]], names=["Price", "Ticker"])
    return flat


def test_flat_frame_becomes_bars_and_drops_nan_rows():
    bars = frame_to_bars(_flat_frame(), "AAPL")
    assert [bar.timestamp for bar in bars] == ["2024-01-02", "2024-01-03"]
    assert bars[0].open == 100.0
    assert bars[1].close == 104.0


def test_multiindex_columns_are_flattened():
    bars = frame_to_bars(_multi_frame(), "AAPL")
    assert len(bars) == 2
    assert bars[0].high == 105.0


def test_empty_frame_raises():
    with pytest.raises(ValueError, match="no devolvió velas"):
        frame_to_bars(pd.DataFrame(), "NOPE")


def test_fetch_passes_inclusive_end_and_roundtrips_csv(tmp_path, monkeypatch):
    calls = {}

    def fake_download(symbol, **kwargs):
        calls["symbol"] = symbol
        calls.update(kwargs)
        return _multi_frame()

    monkeypatch.setattr(yfinance, "download", fake_download)
    bars = fetch_daily("aapl", date(2024, 1, 1), date(2024, 1, 4))
    assert calls["symbol"] == "AAPL"
    assert calls["start"] == "2024-01-01"
    assert calls["end"] == "2024-01-05"
    assert calls["interval"] == "1d"

    target = write_ohlc_csv(tmp_path / "data" / "AAPL.csv", bars)
    loaded = load_ohlc(target)
    assert [(bar.timestamp, bar.open, bar.close) for bar in loaded] == [
        (bar.timestamp, bar.open, bar.close) for bar in bars
    ]


def test_start_after_end_is_rejected():
    with pytest.raises(ValueError, match="posterior"):
        fetch_daily("AAPL", date(2024, 2, 1), date(2024, 1, 1))


def test_default_output_path():
    assert str(default_output("msft", date(2024, 1, 1), date(2024, 6, 30))) == "data/MSFT_2024-01-01_2024-06-30.csv"


def test_cli_fetch_writes_csv_and_reports(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(yfinance, "download", lambda symbol, **kwargs: _flat_frame())
    out = tmp_path / "prices.csv"
    assert main(["fetch", "AAPL", "--from", "2024-01-01", "--to", "2024-01-04", "--out", str(out)]) == 0
    assert out.is_file()
    assert "2 velas" in capsys.readouterr().out
    assert len(load_ohlc(out)) == 2


def test_cli_fetch_rejects_bad_range(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(yfinance, "download", lambda symbol, **kwargs: _flat_frame())
    code = main(["fetch", "AAPL", "--from", "2024-02-01", "--to", "2024-01-01", "--out", str(tmp_path / "x.csv")])
    assert code == 1
    assert "posterior" in capsys.readouterr().err
