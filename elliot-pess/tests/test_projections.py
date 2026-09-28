from elliot.engine import analyze
from elliot.projections import project

from synthetic import GOLDEN, bars_from_prices


def test_wave5_targets_and_invalidation_from_a_completed_impulse():
    invalidation, projections = project("impulse", "bullish", GOLDEN)
    assert invalidation == 110
    by_basis = {(item.target, item.ratio, item.basis): item.price for item in projections}
    assert by_basis[("wave5", 1.0, "wave1")] == 125
    assert abs(by_basis[("wave5", 0.618, "net_0_3")] - (115 + 0.618 * (121.18 - 100))) < 1e-9
    assert abs(by_basis[("wave5", 1.0, "net_0_3")] - (115 + (121.18 - 100))) < 1e-9


def test_wave4_retracement_and_wave1_invalidation():
    invalidation, projections = project("impulse", "bullish", [100, 110, 105, 121.18])
    assert invalidation == 110
    prices = [item.price for item in projections if item.target == "wave4"]
    assert abs(prices[0] - (121.18 - 0.236 * 16.18)) < 1e-9
    assert abs(prices[1] - (121.18 - 0.382 * 16.18)) < 1e-9


def test_diagonal_invalidation_stays_at_the_origin():
    invalidation, _projections = project("leading_diagonal", "bullish", [100, 120, 110, 130, 115])
    assert invalidation == 100


def test_zigzag_c_targets():
    _invalidation, projections = project("zigzag", "bullish", [100, 120, 110])
    prices = {round(item.price, 2) for item in projections}
    assert prices == {130.0, round(110 + 1.618 * 20, 2)}
