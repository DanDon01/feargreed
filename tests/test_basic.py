"""Tests for theme and fx helpers. Run anywhere, no HAT required."""

import fx
import theme


def test_zone_for():
    cases = [
        (0, "EXTREME FEAR"),
        (25, "EXTREME FEAR"),
        (26, "FEAR"),
        (45, "FEAR"),
        (50, "NEUTRAL"),
        (60, "GREED"),
        (76, "EXTREME GREED"),
        (100, "EXTREME GREED"),
    ]
    for value, expected in cases:
        label, colour = theme.zone_for(value)
        assert label == expected, f"value {value}"
        assert len(colour) == 3


def test_zone_for_none():
    label, _ = theme.zone_for(None)
    assert label == "NO DATA"


def test_gauge_colour_endpoints_and_clamping():
    assert theme.gauge_colour(0) == theme.GAUGE_STOPS[0][1]
    assert theme.gauge_colour(100) == theme.GAUGE_STOPS[-1][1]
    assert theme.gauge_colour(-5) == theme.gauge_colour(0)
    assert theme.gauge_colour(150) == theme.gauge_colour(100)


def test_easing_bounds():
    for f in (fx.ease_out_cubic, fx.ease_in_out):
        assert f(0) == 0
        assert f(1) == 1
        assert f(-1) == 0
        assert f(2) == 1
        assert 0 < f(0.5) < 1


def test_downsample():
    pts = list(range(1000))
    out = fx.downsample(pts, 64)
    assert len(out) == 64
    assert out[0] == 0 and out[-1] == 999
    short = [1, 2, 3]
    assert fx.downsample(short, 64) == short


def test_polyline_at():
    pts = [(0, 0), (10, 10), (20, 0)]
    assert fx.polyline_at(pts, 0) == (0, 0)
    assert fx.polyline_at(pts, 1) == (20, 0)
    assert fx.polyline_at(pts, 0.5) == (10, 10)


def test_vertical_gradient():
    img = fx.vertical_gradient((0, 0, 0), (100, 100, 100), size=(10, 50))
    assert img.size == (10, 50)
    assert img.getpixel((5, 0)) == (0, 0, 0)
    assert img.getpixel((5, 49)) == (100, 100, 100)
