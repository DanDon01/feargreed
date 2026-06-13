"""Screens must render valid frames with full, partial and empty data."""

import time

from PIL import Image

from market_data import MarketData
from screens import ChartScreen, ConfigScreen, GaugeScreen, PriceScreen
from theme import WIDTH, HEIGHT


def full_data():
    d = MarketData()
    d.fng_value = 12
    d.fng_label = "Extreme Fear"
    d.fng_history = list(range(10, 40))
    d.price_usd = 63595
    d.price_gbp = 50240
    d.change_24h = -1.52
    d.high_24h = 64285
    d.low_24h = 62320
    d.volume_24h = 31e9
    d.chart_7d = [60000 + (i % 30) * 100 for i in range(168)]
    d.last_update = time.time()
    d.version = 1
    return d


class FakeConfig:
    display_time, brightness, led_brightness = 12, 1.0, 0.3
    led_enabled, flip_display = True, False


def run_screen(screen, seconds=2.0, fps=20):
    screen.on_enter()
    frame = None
    for _ in range(int(seconds * fps)):
        screen.update(1 / fps)
        frame = screen.render()
    return frame


def all_screens(data):
    return [GaugeScreen(data), PriceScreen(data), ChartScreen(data),
            ConfigScreen(data, FakeConfig())]


def check(frame):
    assert isinstance(frame, Image.Image)
    assert frame.size == (WIDTH, HEIGHT)
    assert frame.mode == "RGB"


def test_render_with_full_data():
    for screen in all_screens(full_data()):
        check(run_screen(screen))


def test_render_with_no_data():
    for screen in all_screens(MarketData()):
        check(run_screen(screen, seconds=1.0))


def test_render_with_partial_data():
    d = MarketData()
    d.fng_value = 80
    d.price_usd = 100000
    d.version = 1
    for screen in all_screens(d):
        check(run_screen(screen, seconds=1.0))


def test_static_layer_rebuilds_on_new_data():
    d = full_data()
    screen = GaugeScreen(d)
    run_screen(screen, seconds=0.2)
    first = screen._static
    d.fng_value = 90
    d.version += 1
    run_screen(screen, seconds=0.2)
    assert screen._static is not first
