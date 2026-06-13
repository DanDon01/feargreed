#!/usr/bin/env python3
"""Render preview stills and short animation GIFs of every screen.

Runs on any desktop machine (no HAT required). Uses live API data when
available, otherwise canned sample data. Output goes to preview/.
"""

import os
import sys

from market_data import MarketData
from screens import ChartScreen, ConfigScreen, GaugeScreen, PriceScreen

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "preview")
FPS = 20
SECONDS = 6


def sample_data():
    data = MarketData()
    data.fng_value = 12
    data.fng_label = "Extreme Fear"
    data.fng_history = [38, 35, 30, 28, 31, 27, 24, 22, 25, 20,
                        18, 21, 17, 15, 16, 14, 12, 13, 11, 9,
                        10, 12, 14, 11, 9, 8, 10, 12, 12, 12]
    data.price_usd = 63595
    data.price_gbp = 50240
    data.change_24h = 1.52
    data.high_24h = 64285
    data.low_24h = 62320
    data.volume_24h = 31164108275
    base = 61500
    data.chart_7d = [base + 2200 * (i / 168) + 900 * ((i * 7919) % 100 / 100 - 0.5)
                     for i in range(168)]
    data.version = 1
    data.last_update = __import__("time").time()
    return data


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    data = MarketData()
    print("Fetching live data...")
    if data.refresh():
        print(f"Live data: F&G={data.fng_value} BTC=${data.price_usd:,}")
    else:
        print(f"Live fetch failed ({data.error}), using sample data")
        data = sample_data()

    class FakeConfig:
        display_time, brightness, led_brightness = 12, 1.0, 0.3
        led_enabled, flip_display = True, False

    screens = {
        "gauge": GaugeScreen(data),
        "price": PriceScreen(data),
        "chart": ChartScreen(data),
        "config": ConfigScreen(data, FakeConfig()),
    }

    for name, screen in screens.items():
        screen.on_enter()
        frames = []
        dt = 1 / FPS
        for _ in range(FPS * SECONDS):
            screen.update(dt)
            frames.append(screen.render())

        still = os.path.join(OUT_DIR, f"{name}.png")
        frames[-1].save(still)
        gif = os.path.join(OUT_DIR, f"{name}.gif")
        frames[0].save(gif, save_all=True, append_images=frames[1:],
                       duration=int(1000 / FPS), loop=0)
        print(f"Saved {still} and {gif} ({len(frames)} frames)")

    print("Done. Open the preview folder to view.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
