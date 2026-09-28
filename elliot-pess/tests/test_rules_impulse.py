from elliot.rules.diagonal import valid_diagonal
from elliot.rules.impulse import valid_impulse, valid_truncated_impulse

OVERLAP = [100, 120, 110, 130, 115, 135]
SHORTEST = [100, 110, 105, 113, 111, 131]
WAVE2 = [100, 120, 90, 140, 110, 150]
CLEAN = [100, 110, 105, 121.18, 115, 125]


def test_wave2_beyond_origin_is_rejected():
    assert not valid_impulse(WAVE2, "bullish")


def test_wave3_shortest_is_rejected():
    assert not valid_impulse(SHORTEST, "bullish")


def test_overlap_is_rejected_for_impulse_and_allowed_for_diagonal():
    assert not valid_impulse(OVERLAP, "bullish")
    assert valid_diagonal(OVERLAP, "bullish")


def test_clean_impulse_passes():
    assert valid_impulse(CLEAN, "bullish")
    assert not valid_diagonal(CLEAN, "bullish")


def test_truncation_needs_the_explicit_form():
    truncated = [100, 110, 105, 130, 120, 128]
    assert not valid_impulse(truncated, "bullish")
    assert valid_truncated_impulse(truncated, "bullish")
