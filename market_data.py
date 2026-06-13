"""Market data layer: Alternative.me Fear & Greed + CoinGecko.

All network IO runs on a background thread so the render loop never
stalls. Screens read the plain attributes; assignment is atomic under
the GIL so no locking is needed for these simple swaps.
"""

import threading
import time

import requests

FNG_URL = "https://api.alternative.me/fng/"
CG_MARKETS = "https://api.coingecko.com/api/v3/coins/markets"
CG_CHART = "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart"
CG_SIMPLE = "https://api.coingecko.com/api/v3/simple/price"

REFRESH_SECS = 300
TIMEOUT = 8


class MarketData:
    def __init__(self):
        self.fng_value = None          # int 0-100
        self.fng_label = None          # classification string
        self.fng_history = []          # last 30 values, oldest first
        self.price_usd = None
        self.price_gbp = None
        self.change_24h = None         # percent
        self.high_24h = None
        self.low_24h = None
        self.volume_24h = None
        self.chart_7d = []             # hourly USD prices, oldest first
        self.last_update = 0           # epoch of last successful refresh
        self.error = None
        self.version = 0               # bumped on every successful refresh
        self._stop = threading.Event()
        self._thread = None

    def start(self):
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()

    def _loop(self):
        while not self._stop.is_set():
            ok = self.refresh()
            # Back off sooner on failure so the display recovers quickly
            self._stop.wait(REFRESH_SECS if ok else 30)

    def refresh(self):
        ok = True
        ok &= self._fetch_fng()
        ok &= self._fetch_markets()
        ok &= self._fetch_chart()
        self._fetch_gbp()  # nice-to-have, failure is not fatal
        if ok:
            self.last_update = time.time()
            self.error = None
            self.version += 1
        return ok

    def _fetch_fng(self):
        try:
            r = requests.get(FNG_URL, params={"limit": 30}, timeout=TIMEOUT)
            r.raise_for_status()
            data = r.json()["data"]
            self.fng_value = int(data[0]["value"])
            self.fng_label = data[0]["value_classification"]
            self.fng_history = [int(d["value"]) for d in reversed(data)]
            return True
        except Exception as e:
            self.error = f"F&G: {e}"
            return False

    def _fetch_markets(self):
        try:
            r = requests.get(CG_MARKETS, params={
                "ids": "bitcoin", "vs_currency": "usd",
                "price_change_percentage": "24h",
            }, timeout=TIMEOUT)
            r.raise_for_status()
            d = r.json()[0]
            self.price_usd = d["current_price"]
            self.change_24h = d["price_change_percentage_24h"]
            self.high_24h = d["high_24h"]
            self.low_24h = d["low_24h"]
            self.volume_24h = d["total_volume"]
            return True
        except Exception as e:
            self.error = f"Price: {e}"
            return False

    def _fetch_chart(self):
        try:
            r = requests.get(CG_CHART, params={
                "vs_currency": "usd", "days": 7,
            }, timeout=TIMEOUT)
            r.raise_for_status()
            self.chart_7d = [p[1] for p in r.json()["prices"]]
            return True
        except Exception as e:
            self.error = f"Chart: {e}"
            return False

    def _fetch_gbp(self):
        try:
            r = requests.get(CG_SIMPLE, params={
                "ids": "bitcoin", "vs_currencies": "gbp",
            }, timeout=TIMEOUT)
            r.raise_for_status()
            self.price_gbp = r.json()["bitcoin"]["gbp"]
        except Exception:
            pass

    def stale_minutes(self):
        if not self.last_update:
            return None
        return (time.time() - self.last_update) / 60
