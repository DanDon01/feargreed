#!/usr/bin/env python3
import RPi.GPIO as GPIO
import atexit
import time
import requests
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import qrcode
from datetime import datetime, timedelta
from displayhatmini import DisplayHATMini
import subprocess
import json
import matplotlib.pyplot as plt
from io import BytesIO
import numpy as np

# Initialize GPIO only once at the start
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# Display dimensions
width, height = 320, 240

# Create a buffer for the display
buffer = Image.new("RGB", (width, height))

# Initialize DisplayHATMini with the buffer
display = DisplayHATMini(buffer, backlight_pwm=True)

def cleanup():
    """Cleanup function to ensure GPIO and display resources are released."""
    display.set_led(0.0, 0.0, 0.0)  # Turn off LED
    display.set_backlight(0.0)       # Turn off backlight
    GPIO.cleanup()                   # Clean up GPIO
    print("Cleaned up GPIO resources")

# Register cleanup function
atexit.register(cleanup)

def load_gif_frames(gif_path):
    """Load a GIF and convert frames to format suitable for display"""
    try:
        with Image.open(gif_path) as gif:
            frames = []
            while True:
                frame = gif.copy().convert("RGB")
                if frame.size != (width, height):
                    frame = frame.resize((width, height), Image.Resampling.LANCZOS)
                frames.append(frame)
                try:
                    gif.seek(gif.tell() + 1)
                except EOFError:
                    break
            return frames
    except Exception as e:
        print(f"Error loading GIF: {e}")
        return [Image.new("RGB", (width, height), (255, 0, 0))]

def get_mood_gif(value):
    """Return appropriate GIF path based on fear/greed value"""
    if value is None:
        return "gifs/error.gif"
    value = int(value)
    if value <= 25:
        return "gifs/extreme_fear.gif"
    elif value <= 45:
        return "gifs/fear.gif"
    elif value <= 55:
        return "gifs/neutral.gif"
    elif value <= 75:
        return "gifs/greed.gif"
    else:
        return "gifs/extreme_greed.gif"

def get_fear_greed_index():
    """Fetch the Fear & Greed Index"""
    try:
        url = "https://api.alternative.me/fng/"
        response = requests.get(url, timeout=5)
        data = response.json()
        value = data['data'][0]['value']
        classification = data['data'][0]['value_classification']
        return value, f"Fear & Greed: {value}\n{classification}"
    except Exception as e:
        print(f"Error fetching Fear & Greed Index: {e}")
        return None, "Error fetching data"

def set_mood_led(value):
    """Set RGB LED color based on fear/greed value"""
    if value is None:
        display.set_led(1.0, 0.0, 0.0)  # Red for error
        return
    value = int(value)
    if value <= 25:      # Extreme fear - deep red
        display.set_led(1.0, 0.0, 0.0)
    elif value <= 45:    # Fear - orange
        display.set_led(1.0, 0.65, 0.0)
    elif value <= 55:    # Neutral - yellow
        display.set_led(1.0, 1.0, 0.0)
    elif value <= 75:    # Greed - light green
        display.set_led(0.0, 1.0, 0.0)
    else:                # Extreme greed - deep green
        display.set_led(0.0, 0.5, 0.0)

def get_btc_price():
    """Fetch current BTC price"""
    try:
        response = requests.get("https://api.coindesk.com/v1/bpi/currentprice.json", timeout=5)
        data = response.json()
        price = data["bpi"]["USD"]["rate_float"]
        return f"BTC: ${price:,.2f}"
    except Exception as e:
        print(f"Error fetching BTC price: {e}")
        return "Price Error"

def get_price_change():
    """Fetch 24-hour price change"""
    try:
        response = requests.get("https://api.coingecko.com/api/v3/simple/price",
                               params={"ids": "bitcoin", "vs_currencies": "usd", "include_24hr_change": "true"},
                               timeout=5)
        data = response.json()
        change = data['bitcoin']['usd_24h_change']
        return f"{change:+.2f}%"
    except Exception as e:
        print(f"Error fetching price change: {e}")
        return "N/A"

def display_price_ticker():
    """Display BTC price and 24h change"""
    text_image = Image.new('RGB', (width, height), (0, 0, 0))
    draw = ImageDraw.Draw(text_image)
    price = get_btc_price()
    change = get_price_change()
    font = ImageFont.load_default()
    draw.text((10, height//2 - 10), price, font=font, fill=(255, 215, 0))
    color = (0, 255, 0) if change.startswith('+') else (255, 0, 0)
    draw.text((10, height//2 + 10), change, font=font, fill=color)
    return [text_image]

# Define display modes
class DisplayMode:
    FEAR_GREED = 'fear_greed'
    PRICE_TICKER = 'price_ticker'

# Configuration class
class Config:
    def __init__(self):
        self.display_time = 10  # seconds per mode
        self.brightness = 1.0   # 0.0-1.0 for PWM backlight

# Button handling
current_mode_index = 0
modes = [DisplayMode.FEAR_GREED, DisplayMode.PRICE_TICKER]

def handle_button(pin):
    """Handle button presses"""
    global current_mode_index
    if display.read_button(pin):  # Only handle on button press (not release)
        if pin == display.BUTTON_A:
            current_mode_index = (current_mode_index + 1) % len(modes)
        elif pin == pin == display.BUTTON_B:
            current_mode_index = (current_mode_index - 1) % len(modes)
        elif pin == display.BUTTON_X:
            display.set_led(0.0, 0.0, 0.0)  # Turn off LED
        elif pin == display.BUTTON_Y:
            display.set_led(1.0, 1.0, 1.0)  # White LED for testing

def display_boot_sequence():
    """Simple boot sequence"""
    boot_image = Image.new('RGB', (width, height), (0, 0, 0))
    draw = ImageDraw.Draw(boot_image)
    font = ImageFont.load_default()
    draw.text((10, height//2), "Booting...", font=font, fill=(255, 255, 255))
    display.st7789.display(boot_image)
    time.sleep(1)

def main():
    """Main loop"""
    try:
        # Initial setup
        display.set_backlight(0.0)
        display.set_led(0.0, 0.0, 0.0)
        
        # Fade in backlight
        for i in range(101):
            display.set_backlight(i / 100)
            time.sleep(0.01)

        # Show boot sequence
        display_boot_sequence()

        # Register button handlers
        display.on_button_pressed(handle_button)

        # Main loop
        config = Config()
        while True:
            current_mode = modes[current_mode_index]
            
            if current_mode == DisplayMode.FEAR_GREED:
                value, index_data = get_fear_greed_index()
                set_mood_led(value)
                current_frames = load_gif_frames(get_mood_gif(value))
            elif current_mode == DisplayMode.PRICE_TICKER:
                current_frames = display_price_ticker()

            # Display frames
            start_time = time.time()
            frame_index = 0
            while time.time() - start_time < config.display_time:
                frame = current_frames[frame_index % len(current_frames)]
                display.st7789.display(frame)
                frame_index += 1
                time.sleep(0.1)

    except Exception as e:
        print(f"Error in main: {e}")
        display.set_led(1.0, 0.0, 0.0)  # Red LED for error
        time.sleep(5)
    finally:
        cleanup()

if __name__ == "__main__":
    main()