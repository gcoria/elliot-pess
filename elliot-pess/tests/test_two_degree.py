from elliot.engine import analyze
from elliot.projections import project

from synthetic import bars_from_prices


NESTED = (100, 110, 106, 116, 111, 127.18, 121, 131, 120, 140)
BROKEN_WAVE3 = (100, 115, 106, 130, 100, 140, 135, 160, 120, 170)


def test_wave3_with_internal_impulse_keeps_five_subwaves():
    analysis = analyze(bars_from_prices(NESTED), deviation=0.02)
    found = [
        wave
        for count in analysis.considered
        for wave in count.waves
        if wave.label == "3"
        and wave.subwaves_status == "present"
        and len(wave.subwaves) == 5
        and abs(wave.price_end - 131) < 1e-6
    ]
    assert found
    assert found[0].price_start == 106
    assert [sub.label for sub in found[0].subwaves] == ["1", "2", "3", "4", "5"]


def test_wave3_whose_internals_break_the_rules_is_pruned():
    analysis = analyze(bars_from_prices(BROKEN_WAVE3), deviation=0.02)
    motive = {"impulse", "leading_diagonal", "ending_diagonal"}
    assert not any(
        count.pattern in motive
        and wave.label in {"1", "3", "5"}
        and abs(wave.price_start - 106) < 1e-6
        and abs(wave.price_end - 160) < 1e-6
        for count in analysis.considered
        for wave in count.waves
    )


def test_in_progress_impulse_projects_wave3():
    analysis = analyze(bars_from_prices([100, 110, 105]), deviation=0.02)
    assert analysis.primary is not None
    assert analysis.primary.pattern == "impulse"
    assert analysis.primary.status == "in_progress"
    invalidation, projections = project("impulse", "bullish", [100, 110, 105])
    assert analysis.primary.invalidation == invalidation == 100
    prices = {round(item.price, 2) for item in analysis.primary.projections}
    assert round(105 + 1.618 * 10, 2) in prices
    assert round(105 + 2.618 * 10, 2) in prices
    assert {round(item.price, 2) for item in projections} == prices
