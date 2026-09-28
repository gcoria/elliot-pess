from elliot.rules.flat import classify_flat
from elliot.rules.triangle import valid_triangle
from elliot.rules.zigzag import valid_zigzag
from elliot.rules.combination import x_exceeds_w_origin


def test_zigzag_rejects_b_beyond_origin():
    assert not valid_zigzag([100, 120, 90, 140], "bullish")
    assert valid_zigzag([100, 120, 110, 140], "bullish")


def test_flat_variants():
    assert classify_flat([100, 120, 101, 130], "bullish") == "regular"
    assert classify_flat([100, 120, 95, 150], "bullish") == "expanded"
    assert classify_flat([100, 120, 95, 110], "bullish") == "running"
    assert classify_flat([100, 120, 110, 140], "bullish") is None


def test_contracting_triangle():
    assert valid_triangle([200, 180, 195, 185, 192, 188])
    assert not valid_triangle([200, 180, 190, 160, 170, 150])


def test_x_cannot_pass_the_origin_of_w():
    assert x_exceeds_w_origin(200, 210, "bearish")
    assert not x_exceeds_w_origin(200, 188, "bearish")
