from elliot.engine import analyze, rank_counts, relabel_ending_diagonals
from elliot.models import Count, Wave
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
    assert analysis.primary.at_edge
    assert not analysis.primary.invalidated
    live = [count for count in (analysis.primary, *analysis.alternates) if count.at_edge and not count.invalidated]
    assert analysis.primary.score >= max(count.score for count in live)
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


def test_broken_invalidation_is_not_the_primary():
    """A finished bounce whose origin later breaks stays historical."""
    bounce = [140.0, 100.0, 112.0, 104.0, 118.0, 108.0, 116.0, 80.0]
    analysis = analyze(bars_from_prices(bounce), deviation=0.02)
    assert analysis.primary is not None
    assert analysis.primary.at_edge
    assert not analysis.primary.invalidated
    historical = [
        count
        for count in analysis.considered
        if count.direction == "bullish"
        and count.pattern in {"leading_diagonal", "ending_diagonal", "impulse"}
        and count.status == "complete"
        and count.waves
        and abs(count.waves[0].price_start - 100) < 0.01
        and abs(count.waves[-1].price_end - 116) < 0.01
    ]
    assert historical
    assert all(count.invalidated for count in historical)
    assert all(not count.at_edge for count in historical)
    assert analysis.primary not in historical
    assert not any(count.pattern == "ending_diagonal" for count in historical)


def test_a_higher_score_does_not_rescue_a_broken_count():
    live = _count("zigzag", (_wave("A", 0, 2), _wave("B", 2, 4), _wave("C", 4, 8)))
    live = _with(live, score=20, at_edge=True, invalidated=False)
    dead = _count(
        "ending_diagonal",
        (
            _wave("1", 0, 2),
            _wave("2", 2, 3),
            _wave("3", 3, 5),
            _wave("4", 5, 4),
            _wave("5", 4, 6),
        ),
    )
    dead = _with(dead, score=90, at_edge=False, invalidated=True)
    primary, alternates = rank_counts([dead, live], 2)
    assert primary is live
    assert alternates == (dead,)


def test_ending_diagonal_requires_a_parent_wave():
    orphan = _count(
        "ending_diagonal",
        (
            _wave("1", 10, 12),
            _wave("2", 12, 14),
            _wave("3", 14, 16),
            _wave("4", 16, 18),
            _wave("5", 18, 20),
        ),
    )
    kept = relabel_ending_diagonals([orphan])
    assert kept[0].pattern == "leading_diagonal"

    child = _count(
        "ending_diagonal",
        (
            _wave("1", 30, 32),
            _wave("2", 32, 34),
            _wave("3", 34, 36),
            _wave("4", 36, 38),
            _wave("5", 38, 40),
        ),
    )
    parent = _count(
        "impulse",
        (
            _wave("1", 0, 10),
            _wave("2", 10, 20),
            _wave("3", 20, 30),
            _wave("4", 30, 28),
            _wave("5", 30, 40, subpattern="ending_diagonal"),
        ),
    )
    labeled = relabel_ending_diagonals([child, parent])
    assert labeled[0].pattern == "ending_diagonal"
    assert labeled[1].pattern == "impulse"


def _wave(label: str, start: int, end: int, subpattern: str | None = None) -> Wave:
    return Wave(
        label=label,
        start_index=start,
        end_index=end,
        price_start=float(start),
        price_end=float(end),
        time_start=start,
        time_end=end,
        timestamp_start="t",
        timestamp_end="t",
        subwaves_status="present" if subpattern else "insufficient",
        subpattern=subpattern,
    )


def _with(count: Count, **changes) -> Count:
    from dataclasses import replace

    return replace(count, **changes)


def _count(pattern: str, waves: tuple[Wave, ...]) -> Count:
    return Count(
        score=50,
        direction="bullish",
        pattern=pattern,
        status="complete",
        waves=waves,
        invalidation=0,
        projections=(),
        guideline_notes=(),
        endpoint_indexes=tuple(wave.end_index for wave in waves),
    )
