"""Small animation/render helpers: easing, gradients, glow text, particles."""

import math
import random

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from theme import WIDTH, HEIGHT


def ease_out_cubic(t):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def ease_in_out(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def lerp(a, b, t):
    return a + (b - a) * t


def lerp_colour(c1, c2, t):
    return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))


def vertical_gradient(top, bottom, size=(WIDTH, HEIGHT)):
    """Pre-rendered vertical gradient image (build once, reuse)."""
    w, h = size
    ramp = np.linspace(0, 1, h)[:, None]
    top_a = np.array(top, dtype=np.float32)
    bot_a = np.array(bottom, dtype=np.float32)
    rows = top_a[None, :] + (bot_a - top_a)[None, :] * ramp
    arr = np.repeat(rows[:, None, :], w, axis=1).astype(np.uint8)
    return Image.fromarray(arr, "RGB")


def glow_text(text, fnt, colour, blur=8, expand=24):
    """Render text with a soft glow. Returns an RGBA image to paste."""
    dummy = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    box = dummy.textbbox((0, 0), text, font=fnt)
    w = box[2] - box[0] + expand * 2
    h = box[3] - box[1] + expand * 2
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.text((expand - box[0], expand - box[1]), text, font=fnt, fill=colour + (255,))
    halo = img.filter(ImageFilter.GaussianBlur(blur))
    return Image.alpha_composite(halo, img)


class Particles:
    """Slow upward-drifting embers, drawn straight on the frame.

    Colours are pre-faded toward the background so no alpha compositing
    is needed per frame (cheap on the Pi Zero).
    """

    def __init__(self, count, colour, bg, area=(WIDTH, HEIGHT)):
        self.w, self.h = area
        self.dots = []
        for _ in range(count):
            self.dots.append(self._spawn(random.uniform(0, self.h)))
        self.set_colour(colour, bg)

    def _spawn(self, y=None):
        return {
            "x": random.uniform(0, self.w),
            "y": self.h + 4 if y is None else y,
            "vy": random.uniform(8, 26),
            "drift": random.uniform(-6, 6),
            "r": random.choice((1, 1, 2)),
            "tone": random.uniform(0.15, 0.55),
        }

    def set_colour(self, colour, bg):
        self.shades = [lerp_colour(bg, colour, t / 10) for t in range(2, 8)]

    def update(self, dt):
        for d in self.dots:
            d["y"] -= d["vy"] * dt
            d["x"] += d["drift"] * dt
            if d["y"] < -4:
                d.update(self._spawn())

    def draw(self, draw):
        n = len(self.shades)
        for d in self.dots:
            shade = self.shades[min(n - 1, int(d["tone"] * n))]
            r = d["r"]
            x, y = d["x"], d["y"]
            draw.ellipse((x - r, y - r, x + r, y + r), fill=shade)


def downsample(points, target):
    """Reduce a list of floats to roughly `target` evenly spaced samples."""
    if len(points) <= target:
        return list(points)
    step = (len(points) - 1) / (target - 1)
    return [points[round(i * step)] for i in range(target)]


def polyline_at(pts, t):
    """Point at parameter t (0-1) along a polyline of (x, y) tuples."""
    if not pts:
        return 0, 0
    if len(pts) == 1 or t <= 0:
        return pts[0]
    if t >= 1:
        return pts[-1]
    pos = t * (len(pts) - 1)
    i = int(pos)
    f = pos - i
    x = lerp(pts[i][0], pts[i + 1][0], f)
    y = lerp(pts[i][1], pts[i + 1][1], f)
    return x, y


def pulse(t, period):
    """0..1..0 triangle-ish pulse over the given period, from time t."""
    p = (t % period) / period
    return math.sin(p * math.pi)
