"""Procedurally rendered, animated screens for the Display HAT Mini.

Each screen keeps a cached static layer (rebuilt only when fresh data
arrives) and draws cheap dynamic elements on a copy every frame, so the
Pi Zero 2 W can sustain a smooth frame rate without pre-baked GIFs.
"""

import math

from PIL import Image, ImageDraw

import fx
import theme
from theme import WIDTH, HEIGHT

BG = fx.vertical_gradient(theme.BG_TOP, theme.BG_BOTTOM)


def _centred(draw, xy, text, fnt, fill):
    box = draw.textbbox((0, 0), text, font=fnt)
    draw.text((xy[0] - (box[2] - box[0]) / 2 - box[0], xy[1]), text, font=fnt, fill=fill)


def _right(draw, xy, text, fnt, fill):
    box = draw.textbbox((0, 0), text, font=fnt)
    draw.text((xy[0] - (box[2] - box[0]), xy[1]), text, font=fnt, fill=fill)


def _stale_badge(draw, data):
    mins = data.stale_minutes()
    if mins is None:
        _right(draw, (WIDTH - 8, 6), "CONNECTING...", theme.font("regular", 11), theme.GREY)
    elif mins > 15:
        _right(draw, (WIDTH - 8, 6), f"OFFLINE {int(mins)}m", theme.font("regular", 11), theme.RED)


class Screen:
    title = ""

    def __init__(self, data):
        self.data = data
        self.t = 0.0
        self._built_version = -1
        self._static = None

    def on_enter(self):
        self.t = 0.0

    def update(self, dt):
        self.t += dt
        if self._built_version != self.data.version:
            self._static = self._build_static()
            self._built_version = self.data.version

    def _build_static(self):
        return BG.copy()

    def render(self):
        return self._static.copy() if self._static else BG.copy()


class GaugeScreen(Screen):
    """Animated fear & greed dial with eased needle and history strip."""

    CX, CY = 160, 168
    R_OUT = 116
    ARC_W = 18

    def __init__(self, data):
        super().__init__(data)
        self.shown = 50.0
        self.particles = fx.Particles(22, theme.GREY, theme.BG_BOTTOM)

    def on_enter(self):
        super().on_enter()
        # Replay the needle sweep from centre each time we rotate in
        self.shown = 50.0

    def update(self, dt):
        super().update(dt)
        target = self.data.fng_value if self.data.fng_value is not None else 50
        self.shown += (target - self.shown) * min(1.0, dt * 3.5)
        self.particles.update(dt)

    def _build_static(self):
        img = BG.copy()
        d = ImageDraw.Draw(img)
        value = self.data.fng_value
        label, colour = theme.zone_for(value)
        self.particles.set_colour(colour, theme.BG_BOTTOM)

        _centred(d, (160, 5), "BITCOIN FEAR & GREED", theme.font("regular", 13), theme.GREY)
        _stale_badge(d, self.data)

        # Gradient arc, one degree at a time
        box = (self.CX - self.R_OUT, self.CY - self.R_OUT,
               self.CX + self.R_OUT, self.CY + self.R_OUT)
        for v in range(100):
            a0 = 180 + v * 1.8
            d.arc(box, a0, a0 + 2.0, fill=theme.gauge_colour(v + 0.5), width=self.ARC_W)

        # Tick marks at the zone boundaries
        for v in (0, 25, 45, 55, 75, 100):
            ang = math.radians(180 + v * 1.8)
            r1, r2 = self.R_OUT - self.ARC_W - 3, self.R_OUT + 2
            d.line((self.CX + r1 * math.cos(ang), self.CY + r1 * math.sin(ang),
                    self.CX + r2 * math.cos(ang), self.CY + r2 * math.sin(ang)),
                   fill=theme.DIM, width=2)
        d.text((self.CX - self.R_OUT - 2, self.CY + 4), "0",
               font=theme.font("regular", 11), fill=theme.GREY)
        _right(d, (self.CX + self.R_OUT + 4, self.CY + 4), "100",
               theme.font("regular", 11), theme.GREY)

        # Big glowing value
        text = "--" if value is None else str(value)
        glow = fx.glow_text(text, theme.font("bold", 58), colour, blur=10)
        img.paste(glow, (160 - glow.width // 2, 130 - glow.height // 2), glow)

        d = ImageDraw.Draw(img)
        _centred(d, (160, 178), label, theme.font("bold", 17), colour)

        # 30-day history strip along the bottom
        hist = self.data.fng_history
        if hist:
            n = len(hist)
            bw = 296 / n
            for i, v in enumerate(hist):
                _, c = theme.zone_for(v)
                x = 12 + i * bw
                h = 4 + v * 0.16
                top = 236 - h
                d.rectangle((x, top, x + bw - 2, 236),
                            fill=fx.lerp_colour(theme.BG_BOTTOM, c, 0.45 + 0.55 * (i / n)))
            d.text((12, 204), "30D", font=theme.font("regular", 10), fill=theme.DIM)
        return img

    def render(self):
        frame = self._static.copy() if self._static else BG.copy()
        d = ImageDraw.Draw(frame)
        _, colour = theme.zone_for(self.data.fng_value)

        self.particles.draw(d)

        # Expanding pulse ring every few seconds
        p = (self.t % 5.0) / 5.0
        if p < 0.5:
            pr = fx.ease_out_cubic(p * 2) * (self.R_OUT - 4)
            ring = fx.lerp_colour(theme.BG_BOTTOM, colour, 0.5 * (1 - p * 2))
            if pr > 12:
                d.arc((self.CX - pr, self.CY - pr, self.CX + pr, self.CY + pr),
                      180, 360, fill=ring, width=2)

        # Needle with a faint breathing wobble
        ang = math.radians(180 + (self.shown + math.sin(self.t * 1.7) * 0.6) * 1.8)
        r_tip = self.R_OUT - self.ARC_W - 10
        tip = (self.CX + r_tip * math.cos(ang), self.CY + r_tip * math.sin(ang))
        base = math.radians(math.degrees(ang) + 90)
        bx, by = 5 * math.cos(base), 5 * math.sin(base)
        d.polygon([(self.CX + bx, self.CY + by), (self.CX - bx, self.CY - by), tip],
                  fill=theme.WHITE)
        d.ellipse((self.CX - 7, self.CY - 7, self.CX + 7, self.CY + 7), fill=colour,
                  outline=theme.WHITE, width=2)
        tipc = fx.lerp_colour(theme.WHITE, colour, 0.5 + 0.5 * fx.pulse(self.t, 1.6))
        d.ellipse((tip[0] - 3, tip[1] - 3, tip[0] + 3, tip[1] + 3), fill=tipc)
        return frame


class PriceScreen(Screen):
    """Big count-up price, 24h change pill and 7-day sparkline."""

    SPARK = (16, 142, 304, 210)  # left, top, right, bottom

    def __init__(self, data):
        super().__init__(data)
        self.shown_price = 0.0
        self.anim_from = 0.0
        self.anim_t = 1.0
        self._last_price = None
        self._pts = []

    def on_enter(self):
        super().on_enter()
        # Re-run the count-up each time the screen comes around
        self.anim_from = 0.0 if self._last_price is None else self._last_price * 0.985
        self.anim_t = 0.0

    def update(self, dt):
        super().update(dt)
        price = self.data.price_usd
        if price is not None and price != self._last_price:
            self.anim_from = self.shown_price if self._last_price else price * 0.985
            self.anim_t = 0.0
            self._last_price = price
        if price is not None:
            self.anim_t = min(1.0, self.anim_t + dt / 1.2)
            self.shown_price = fx.lerp(self.anim_from, price, fx.ease_out_cubic(self.anim_t))

    def _spark_points(self):
        prices = fx.downsample(self.data.chart_7d, 64)
        if len(prices) < 2:
            return []
        x0, y0, x1, y1 = self.SPARK
        lo, hi = min(prices), max(prices)
        span = (hi - lo) or 1
        pts = []
        for i, p in enumerate(prices):
            x = x0 + (x1 - x0) * i / (len(prices) - 1)
            y = y1 - (y1 - y0) * (p - lo) / span
            pts.append((x, y))
        return pts

    def _build_static(self):
        img = BG.copy()
        d = ImageDraw.Draw(img)
        data = self.data

        # Coin badge and title
        d.ellipse((14, 8, 38, 32), fill=theme.GOLD)
        _centred(d, (26, 9), "B", theme.font("bold", 17), (40, 26, 4))
        d.text((46, 12), "BITCOIN", font=theme.font("bold", 14), fill=theme.WHITE)
        _stale_badge(d, data)

        # 24h change pill (price text itself is dynamic)
        chg = data.change_24h
        if chg is not None:
            up = chg >= 0
            pc = theme.GREEN if up else theme.RED
            txt = f"{chg:+.2f}%  24H"
            fnt = theme.font("bold", 15)
            tw = d.textbbox((0, 0), txt, font=fnt)[2]
            x0 = 160 - (tw + 34) / 2
            d.rounded_rectangle((x0, 92, x0 + tw + 34, 116), 12,
                                fill=fx.lerp_colour(theme.BG_BOTTOM, pc, 0.22))
            ay = 104
            if up:
                d.polygon([(x0 + 12, ay + 4), (x0 + 22, ay + 4), (x0 + 17, ay - 5)], fill=pc)
            else:
                d.polygon([(x0 + 12, ay - 4), (x0 + 22, ay - 4), (x0 + 17, ay + 5)], fill=pc)
            d.text((x0 + 28, 95), txt, font=fnt, fill=pc)

        if data.price_gbp:
            _centred(d, (160, 120), f"£{data.price_gbp:,.0f}",
                     theme.font("regular", 13), theme.GREY)

        # Sparkline with soft area fill
        pts = self._spark_points()
        self._pts = pts
        if pts:
            up = data.chart_7d[-1] >= data.chart_7d[0]
            line = theme.GREEN if up else theme.RED
            x0, y0, x1, y1 = self.SPARK
            d.polygon(pts + [(x1, y1), (x0, y1)],
                      fill=fx.lerp_colour(theme.BG_BOTTOM, line, 0.16))
            d.line(pts, fill=line, width=2, joint="curve")
            d.text((x0, y0 - 14), "7D", font=theme.font("regular", 10), fill=theme.DIM)

        if data.high_24h and data.low_24h:
            d.text((16, 218), f"24H HIGH  ${data.high_24h:,.0f}",
                   font=theme.font("regular", 12), fill=theme.GREY)
            _right(d, (304, 218), f"LOW  ${data.low_24h:,.0f}",
                   theme.font("regular", 12), theme.GREY)
        return img

    def render(self):
        frame = self._static.copy() if self._static else BG.copy()
        d = ImageDraw.Draw(frame)

        if self.data.price_usd is None:
            shimmer = fx.lerp_colour(theme.DIM, theme.WHITE, fx.pulse(self.t, 1.4))
            _centred(d, (160, 48), "LOADING...", theme.font("bold", 30), shimmer)
        else:
            _centred(d, (160, 40), f"${self.shown_price:,.0f}",
                     theme.font("bold", 44), theme.WHITE)

        # Bright dot travelling along the sparkline
        if self._pts:
            tt = (self.t % 6.0) / 6.0
            x, y = fx.polyline_at(self._pts, tt)
            up = self.data.chart_7d[-1] >= self.data.chart_7d[0]
            c = theme.GREEN if up else theme.RED
            d.ellipse((x - 5, y - 5, x + 5, y + 5),
                      fill=fx.lerp_colour(theme.BG_BOTTOM, c, 0.35))
            d.ellipse((x - 2.5, y - 2.5, x + 2.5, y + 2.5), fill=theme.WHITE)
        return frame


class ChartScreen(Screen):
    """Full-bleed 7-day chart with an animated draw-in."""

    AREA = (10, 42, 310, 196)
    DRAW_IN_SECS = 1.1

    def __init__(self, data):
        super().__init__(data)
        self._pts = []

    def _build_static(self):
        img = BG.copy()
        d = ImageDraw.Draw(img)
        data = self.data
        x0, y0, x1, y1 = self.AREA

        d.text((12, 6), "BTC / USD", font=theme.font("bold", 14), fill=theme.WHITE)
        d.text((12, 24), "7 DAY CHART", font=theme.font("regular", 11), fill=theme.GREY)
        _stale_badge(d, data)

        prices = fx.downsample(data.chart_7d, 90)
        if len(prices) < 2:
            _centred(d, (160, 110), "NO CHART DATA", theme.font("bold", 18), theme.GREY)
            self._pts = []
            return img

        lo, hi = min(prices), max(prices)
        span = (hi - lo) or 1
        pad = span * 0.08
        lo, hi = lo - pad, hi + pad
        span = hi - lo

        # Dotted gridlines (price labels drawn after the area fill)
        for frac in (0.0, 0.5, 1.0):
            gy = y1 - (y1 - y0) * frac
            for gx in range(x0, x1, 8):
                d.point((gx, gy), fill=theme.DIM)

        pts = []
        for i, p in enumerate(prices):
            x = x0 + (x1 - x0) * i / (len(prices) - 1)
            y = y1 - (y1 - y0) * (p - lo) / span
            pts.append((x, y))
        self._pts = pts

        up = prices[-1] >= prices[0]
        line = theme.GREEN if up else theme.RED
        d.polygon(pts + [(x1, y1), (x0, y1)],
                  fill=fx.lerp_colour(theme.BG_BOTTOM, line, 0.18))
        d.line(pts, fill=line, width=2, joint="curve")

        for frac in (0.0, 0.5, 1.0):
            gy = y1 - (y1 - y0) * frac
            _right(d, (x1, gy - 13), f"${lo + span * frac:,.0f}",
                   theme.font("regular", 10), theme.GREY)

        # Mark the 7-day high and low
        for price, sym in ((max(prices), "H"), (min(prices), "L")):
            i = prices.index(price)
            px, py = pts[i]
            d.ellipse((px - 3, py - 3, px + 3, py + 3), fill=theme.WHITE)
            ty = py - 16 if sym == "H" else py + 5
            _centred(d, (min(max(px, 24), 296), ty), f"{sym} ${price:,.0f}",
                     theme.font("regular", 10), theme.WHITE)

        # Day-of-week labels
        import datetime
        today = datetime.date.today()
        for day in range(7):
            label = (today - datetime.timedelta(days=6 - day)).strftime("%a").upper()
            lx = x0 + (x1 - x0) * (day + 0.5) / 7
            _centred(d, (lx, y1 + 8), label, theme.font("regular", 10), theme.DIM)

        if data.price_usd is not None:
            _right(d, (308, 6), f"${data.price_usd:,.0f}", theme.font("bold", 18), line)
        if data.volume_24h:
            _centred(d, (160, 222), f"24H VOLUME  ${data.volume_24h / 1e9:.1f}B",
                     theme.font("regular", 12), theme.GREY)
        return img

    def render(self):
        static = self._static if self._static else BG
        progress = fx.ease_out_cubic(self.t / self.DRAW_IN_SECS)

        if progress >= 1.0:
            frame = static.copy()
        else:
            # Reveal the chart left to right
            frame = BG.copy()
            w = max(1, int(WIDTH * progress))
            frame.paste(static.crop((0, 0, w, HEIGHT)), (0, 0))

        if self._pts and progress >= 1.0:
            d = ImageDraw.Draw(frame)
            tt = ((self.t - self.DRAW_IN_SECS) % 7.0) / 7.0
            x, y = fx.polyline_at(self._pts, tt)
            x0, y0, x1, y1 = self.AREA
            d.line((x, y0, x, y1), fill=theme.DIM)
            d.ellipse((x - 3, y - 3, x + 3, y + 3), fill=theme.WHITE)
        return frame


class ConfigScreen(Screen):
    """Settings card. Navigation state lives in the main loop."""

    OPTIONS = ("Display time", "Brightness", "LED brightness", "LED",
               "Flip display", "Exit")

    def __init__(self, data, config):
        super().__init__(data)
        self.config = config
        self.selected = 0

    def values(self):
        c = self.config
        return (f"{c.display_time}s",
                f"{int(c.brightness * 100)}%",
                f"{int(c.led_brightness * 100)}%",
                "ON" if c.led_enabled else "OFF",
                "ON" if c.flip_display else "OFF",
                "")

    def update(self, dt):
        self.t += dt

    def render(self):
        frame = BG.copy()
        d = ImageDraw.Draw(frame)
        d.rounded_rectangle((18, 14, 302, 206), 10, fill=(12, 16, 36),
                            outline=(40, 50, 84), width=2)
        d.text((34, 24), "SETTINGS", font=theme.font("bold", 16), fill=theme.GOLD)

        vals = self.values()
        for i, name in enumerate(self.OPTIONS):
            y = 50 + i * 25
            if i == self.selected:
                d.rounded_rectangle((28, y - 4, 292, y + 20), 6, fill=(26, 34, 66))
                d.rectangle((28, y - 4, 31, y + 20), fill=theme.GOLD)
            colour = theme.WHITE if i == self.selected else theme.GREY
            d.text((42, y), name, font=theme.font("regular", 15), fill=colour)
            _right(d, (282, y), vals[i], theme.font("bold", 15),
                   theme.GOLD if i == self.selected else theme.GREY)

        d.text((34, 216), "A up   B down   X +   Y -",
               font=theme.font("regular", 12), fill=theme.DIM)
        return frame
