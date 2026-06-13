#!/usr/bin/env python3
"""Bitcoin Fear & Greed desk display for the Pimoroni Display HAT Mini.

Procedural real-time rendering (no GIFs): animated gauge, price ticker
and 7-day chart, with eased slide transitions and a mood LED.
"""

import atexit
import json
import math
import os
import signal
import sys
import time

from PIL import Image, ImageDraw

import fx
import theme
from hardware import Buttons, make_display
from market_data import MarketData
from screens import BG, ChartScreen, ConfigScreen, GaugeScreen, PriceScreen, _centred

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
TARGET_FPS = 30
TRANSITION_SECS = 0.4


class Config:
    DEFAULTS = {
        "display_time": 12,
        "brightness": 1.0,
        "led_brightness": 0.3,
        "led_enabled": True,
        "flip_display": False,
    }

    def __init__(self):
        self._extra = {}
        for k, v in self.DEFAULTS.items():
            setattr(self, k, v)
        try:
            with open(CONFIG_PATH) as f:
                data = json.load(f)
            for k, v in data.items():
                if k in self.DEFAULTS:
                    setattr(self, k, v)
                else:
                    self._extra[k] = v
        except Exception:
            pass

    def save(self):
        data = dict(self._extra)
        for k in self.DEFAULTS:
            data[k] = getattr(self, k)
        try:
            with open(CONFIG_PATH, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Could not save config: {e}")


def boot_animation(display):
    """Short coin zoom-in with title fade. Roughly two seconds."""
    duration = 2.0
    start = time.monotonic()
    while True:
        t = (time.monotonic() - start) / duration
        if t >= 1:
            break
        frame = BG.copy()
        d = ImageDraw.Draw(frame)

        coin_t = fx.ease_out_cubic(min(1.0, t / 0.55))
        r = 8 + 42 * coin_t
        wobble = 1 + 0.06 * math.sin(t * 14) * (1 - t)
        rx, ry = r * wobble, r / wobble
        cx, cy = 160, 96
        glow = fx.lerp_colour(theme.BG_TOP, theme.GOLD, 0.25 * coin_t)
        d.ellipse((cx - rx - 10, cy - ry - 10, cx + rx + 10, cy + ry + 10), fill=glow)
        d.ellipse((cx - rx, cy - ry, cx + rx, cy + ry), fill=theme.GOLD)
        d.ellipse((cx - rx * 0.78, cy - ry * 0.78, cx + rx * 0.78, cy + ry * 0.78),
                  outline=(200, 125, 15), width=2)
        if coin_t > 0.5:
            _centred(d, (cx, cy - 17), "B", theme.font("bold", 34), (60, 38, 5))

        if t > 0.45:
            ft = fx.ease_out_cubic((t - 0.45) / 0.4)
            _centred(d, (160, 158), "FEAR & GREED",
                     theme.font("bold", 22), fx.lerp_colour(theme.BG_BOTTOM, theme.WHITE, ft))
            _centred(d, (160, 188), "BITCOIN MARKET SENTIMENT",
                     theme.font("regular", 12), fx.lerp_colour(theme.BG_BOTTOM, theme.GREY, ft))

        display.show(frame)
        time.sleep(1 / TARGET_FPS)


def slide_transition(old_frame, new_frame, progress):
    """Eased horizontal slide between two rendered frames."""
    p = fx.ease_in_out(progress)
    offset = int(theme.WIDTH * p)
    frame = Image.new("RGB", (theme.WIDTH, theme.HEIGHT))
    frame.paste(old_frame, (-offset, 0))
    frame.paste(new_frame, (theme.WIDTH - offset, 0))
    return frame


class ButtonReader:
    """Edge detection so a held button fires once."""

    def __init__(self, display):
        self.display = display
        self.state = {b: False for b in (Buttons.A, Buttons.B, Buttons.X, Buttons.Y)}

    def poll(self):
        fired = []
        for b in self.state:
            now = self.display.pressed(b)
            if now and not self.state[b]:
                fired.append(b)
            self.state[b] = now
        return fired


class App:
    def __init__(self):
        self.display = make_display()
        self.config = Config()
        self.data = MarketData()
        self.screens = [GaugeScreen(self.data), PriceScreen(self.data),
                        ChartScreen(self.data)]
        self.config_screen = ConfigScreen(self.data, self.config)
        self.index = 0
        self.in_config = False
        self.transition = None      # (old_frame, progress) while sliding
        self.mode_timer = 0.0
        self.buttons = ButtonReader(self.display)
        self.led_value = None

    @property
    def screen(self):
        return self.config_screen if self.in_config else self.screens[self.index]

    def switch_to(self, new_index):
        old_frame = self.screen.render()
        self.index = new_index % len(self.screens)
        self.screen.on_enter()
        self.transition = [old_frame, 0.0]
        self.mode_timer = 0.0

    def update_led(self, t):
        if not self.config.led_enabled:
            self.display.set_led(0, 0, 0)
            return
        value = self.data.fng_value
        _, colour = theme.zone_for(value)
        breathe = 0.78 + 0.22 * math.sin(t * 1.5)
        b = self.config.led_brightness * breathe
        self.display.set_led(colour[0] / 255 * b, colour[1] / 255 * b, colour[2] / 255 * b)

    def handle_buttons(self):
        for b in self.buttons.poll():
            if self.in_config:
                self.handle_config_button(b)
            elif b == Buttons.A:
                self.in_config = True
                self.config_screen.selected = 0
            elif b == Buttons.B:
                self.switch_to(self.index - 1)
            elif b == Buttons.Y:
                self.switch_to(self.index + 1)
            elif b == Buttons.X:
                self.config.led_enabled = not self.config.led_enabled
                self.config.save()

    def handle_config_button(self, b):
        cs = self.config_screen
        c = self.config
        n = len(cs.OPTIONS)
        if b == Buttons.A:
            cs.selected = (cs.selected - 1) % n
        elif b == Buttons.B:
            cs.selected = (cs.selected + 1) % n
        elif b in (Buttons.X, Buttons.Y):
            step = 1 if b == Buttons.X else -1
            opt = cs.OPTIONS[cs.selected]
            if opt == "Display time":
                c.display_time = max(5, min(60, c.display_time + 5 * step))
            elif opt == "Brightness":
                c.brightness = max(0.1, min(1.0, round(c.brightness + 0.1 * step, 1)))
                self.display.set_backlight(c.brightness)
            elif opt == "LED brightness":
                c.led_brightness = max(0.0, min(1.0, round(c.led_brightness + 0.1 * step, 1)))
            elif opt == "LED":
                c.led_enabled = step > 0
            elif opt == "Flip display":
                c.flip_display = step > 0
                self.display.set_flip(c.flip_display)
            elif opt == "Exit":
                self.in_config = False
                self.mode_timer = 0.0
            c.save()

    def run(self):
        atexit.register(self.display.close)
        self.display.set_backlight(self.config.brightness)
        self.display.set_flip(self.config.flip_display)
        self.data.start()
        boot_animation(self.display)

        last = time.monotonic()
        while True:
            now = time.monotonic()
            dt = min(0.1, now - last)
            last = now

            self.handle_buttons()
            self.update_led(now)

            if self.transition:
                self.transition[1] += dt / TRANSITION_SECS
                self.screen.update(dt)
                if self.transition[1] >= 1.0:
                    frame = self.screen.render()
                    self.transition = None
                else:
                    frame = slide_transition(self.transition[0],
                                             self.screen.render(),
                                             self.transition[1])
            else:
                self.screen.update(dt)
                frame = self.screen.render()
                if not self.in_config:
                    self.mode_timer += dt
                    if self.mode_timer >= self.config.display_time:
                        self.switch_to(self.index + 1)

            self.display.show(frame)

            elapsed = time.monotonic() - now
            if elapsed < 1 / TARGET_FPS:
                time.sleep(1 / TARGET_FPS - elapsed)


def main():
    # systemd stops the service with SIGTERM; turn it into a clean exit so
    # the finally block runs and the LED/backlight are switched off.
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    app = App()
    try:
        app.run()
    except KeyboardInterrupt:
        pass
    finally:
        app.data.stop()
        app.display.close()


if __name__ == "__main__":
    main()
