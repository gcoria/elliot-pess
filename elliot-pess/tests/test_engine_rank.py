from elliot.engine import analyze
from elliot.rules.impulse import valid_impulse

from synthetic import GOLDEN, bars_from_prices


def test_bearish_golden_impulse_ranks_first():
    prices = (200.0, 190.0, 195.0, 178.82, 185.0, 175.0)
    analysis = analyze(bars_from_prices(prices), deviation=0.02)
    assert analysis.primary is not None
    assert analysis.primary.pattern == "impulse"
    assert analysis.primary.direction == "bearish"
    assert analysis.primary.status == "complete"
    assert [round(price, 2) for price in analysis.primary.end_prices] == [round(price, 2) for price in prices]


def test_golden_impulse_ranks_first():
    analysis = analyze(bars_from_prices(GOLDEN), deviation=0.02)
    assert analysis.primary is not None
    assert analysis.primary.pattern == "impulse"
    assert analysis.primary.status == "complete"
    assert analysis.primary.direction == "bullish"
    assert [round(price, 2) for price in analysis.primary.end_prices] == [round(price, 2) for price in GOLDEN]
    assert analysis.primary.score >= 60
    assert all(analysis.primary.score >= alternate.score for alternate in analysis.alternates)
    assert analysis.primary.invalidation == 110
    labels = {item.label for item in analysis.primary.projections}
    assert any(label.startswith("5 ·") for label in labels)


def test_engine_rejects_wave2_beyond_origin():
    analysis = analyze(bars_from_prices([100, 120, 90, 140, 110, 150]), deviation=0.02)
    assert not valid_impulse([100, 120, 90, 140, 110, 150], "bullish")
    assert not any(
        count.pattern == "impulse" and count.status == "complete" for count in analysis.considered
    )
    for count in analysis.considered:
        if count.pattern != "impulse":
            continue
        origin = count.waves[0].price_start
        for wave in count.waves:
            if wave.label != "2":
                continue
            assert wave.price_end > origin
            for sub in wave.subwaves:
                assert min(sub.price_start, sub.price_end) > origin


def test_engine_rejects_shortest_wave3_as_a_complete_impulse():
    prices = [100, 110, 105, 113, 111, 131]
    analysis = analyze(bars_from_prices(prices), deviation=0.02)
    assert not any(
        count.pattern == "impulse" and count.status == "complete" for count in analysis.considered
    )


def test_overlap_is_a_diagonal_not_an_impulse():
    analysis = analyze(bars_from_prices([100, 120, 110, 130, 115, 135]), deviation=0.02)
    assert not any(count.pattern == "impulse" and count.status == "complete" for count in analysis.considered)
    assert any(count.pattern == "leading_diagonal" and count.status == "complete" for count in analysis.considered)


def test_flat_expanded_and_triangle_and_combination_are_found():
    expanded = analyze(bars_from_prices([100, 120, 95, 150]), deviation=0.02)
    assert any(count.pattern == "flat" and count.variant == "expanded" for count in expanded.considered)

    triangle = analyze(bars_from_prices([200, 180, 195, 185, 192, 188]), deviation=0.02)
    assert any(count.pattern == "triangle" and count.status == "complete" for count in triangle.considered)

    combination = analyze(
        bars_from_prices([200, 180, 190, 170, 185, 175, 188, 160, 170, 150]),
        deviation=0.02,
    )
    assert any(count.pattern == "combination" for count in combination.considered)

    broken = analyze(
        bars_from_prices([200, 180, 190, 170, 185, 175, 210, 160, 170, 150]),
        deviation=0.02,
    )
    assert not any(count.pattern == "combination" for count in broken.considered)
