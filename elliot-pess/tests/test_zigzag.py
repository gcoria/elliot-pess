from elliot.io.csv_loader import load_ohlc
from elliot.pivots.zigzag import average_true_range, zigzag_atr, zigzag_percent

from synthetic import bars_from_prices, write_csv


def test_percent_zigzag_keeps_the_swings():
    prices = [100, 110, 105, 120, 112, 130]
    bars = bars_from_prices(prices)
    pivots = zigzag_percent(bars, 0.02)
    assert [round(pivot.price, 2) for pivot in pivots] == prices
    assert [pivot.kind for pivot in pivots] == ["low", "high", "low", "high", "low", "high"]


def test_small_reversal_is_ignored():
    bars = bars_from_prices([100, 110, 109, 120], bars_per_leg=4)
    pivots = zigzag_percent(bars, 0.02)
    assert [round(pivot.price, 2) for pivot in pivots] == [100, 120]


def test_atr_threshold_uses_a_multiple_of_range():
    bars = bars_from_prices([100, 130, 110, 140], bars_per_leg=6)
    atrs = average_true_range(bars, 14)
    assert max(atrs) < 8
    pivots = zigzag_atr(bars, period=14, multiplier=3)
    assert [round(pivot.price, 2) for pivot in pivots] == [100, 130, 110, 140]

    noisy = bars_from_prices([100, 110, 108, 120], bars_per_leg=6)
    assert [round(pivot.price, 2) for pivot in zigzag_atr(noisy, period=14, multiplier=3)] == [100, 120]


def test_csv_roundtrip(tmp_path):
    path = tmp_path / "prices.csv"
    write_csv(path, bars_from_prices([100, 110, 105]))
    loaded = load_ohlc(path)
    assert len(loaded) == len(bars_from_prices([100, 110, 105]))
    assert loaded[0].open == 100
    assert loaded[-1].close == 105
