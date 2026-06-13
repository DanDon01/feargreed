"""Colours, fonts and sentiment zones shared by all screens."""

import os
from PIL import ImageFont

WIDTH, HEIGHT = 320, 240

# Background gradient (deep navy, keeps OLED-ish contrast on the LCD)
BG_TOP = (6, 8, 22)
BG_BOTTOM = (18, 24, 52)

WHITE = (240, 244, 255)
GREY = (130, 140, 165)
DIM = (70, 78, 100)
GOLD = (247, 165, 30)
RED = (235, 70, 70)
GREEN = (60, 220, 120)

# Sentiment zones: (upper bound, label, colour)
ZONES = [
    (25, "EXTREME FEAR", (225, 45, 45)),
    (45, "FEAR", (255, 125, 35)),
    (55, "NEUTRAL", (250, 210, 60)),
    (75, "GREED", (130, 225, 80)),
    (100, "EXTREME GREED", (0, 235, 130)),
]

# Colour stops for the smooth gauge gradient
GAUGE_STOPS = [
    (0, (200, 30, 30)),
    (25, (235, 80, 30)),
    (50, (250, 210, 60)),
    (75, (110, 225, 80)),
    (100, (0, 235, 130)),
]


def zone_for(value):
    """Return (label, colour) for a fear/greed value 0-100."""
    if value is None:
        return "NO DATA", GREY
    for bound, label, colour in ZONES:
        if value <= bound:
            return label, colour
    return ZONES[-1][1], ZONES[-1][2]


def gauge_colour(value):
    """Smoothly interpolated colour along the gauge for value 0-100."""
    v = max(0, min(100, value))
    for i in range(len(GAUGE_STOPS) - 1):
        lo, c1 = GAUGE_STOPS[i]
        hi, c2 = GAUGE_STOPS[i + 1]
        if v <= hi:
            t = (v - lo) / (hi - lo)
            return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))
    return GAUGE_STOPS[-1][1]


_FONT_DIRS = [
    "/usr/share/fonts/truetype/dejavu",
    os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts"),
]

_FONT_FILES = {
    "regular": ["DejaVuSans.ttf", "segoeui.ttf", "arial.ttf"],
    "bold": ["DejaVuSans-Bold.ttf", "seguisb.ttf", "arialbd.ttf"],
    "mono": ["DejaVuSansMono.ttf", "consola.ttf", "cour.ttf"],
}


def _find_font(kind):
    for d in _FONT_DIRS:
        for name in _FONT_FILES[kind]:
            path = os.path.join(d, name)
            if os.path.exists(path):
                return path
    return None


_cache = {}


def font(kind, size):
    """Load a font by kind ('regular'|'bold'|'mono') and pixel size, cached."""
    key = (kind, size)
    if key not in _cache:
        path = _find_font(kind)
        if path:
            _cache[key] = ImageFont.truetype(path, size)
        else:
            _cache[key] = ImageFont.load_default()
    return _cache[key]
