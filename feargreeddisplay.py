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

# Clean up any existing GPIO configuration and initialize once
GPIO.cleanup()
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# Display dimensions
width, height = 320, 240

# Create a buffer for the display
buffer = Image.new("RGB", (width, height))

# Initialize DisplayHATMini with the buffer
try:
    display = DisplayHATMini(buffer, backlight_pwm=True)
except Exception as e:
    print(f"Failed to initialize DisplayHATMini: {e}")
    exit(1)

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
        return [create_error_image("GIF Error")]

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
        return f"Fear & Greed: {value}\n{classification}", value
    except Exception as e:
        print(f"Error fetching Fear & Greed Index: {e}")
        return "Error fetching data", None

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

def display_price_ticker(disp):
    """Display BTC price and 24h change"""
    text_image = Image.new('RGB', (width, height), (0, 0, 0))
    draw = ImageDraw.Draw(text_image)
    price = get_btc_price()
    change = get_price_change()
    font = ImageFont.load_default()
    draw.text((10, height//2), price, font=font, fill=(255, 215, 0))
    color = (0, 255, 0) if change.startswith('+') else (255, 0, 0)
    draw.text((10, height//2 + 20), change, font=font, fill=color)
    return text_image

def display_money_flow(disp):
    """Display money flow animation"""
    try:
        frames = load_gif_frames(f"gifs/money_flow/flow_{get_market_direction()}.gif")
        return frames
    except:
        return [create_error_image("Money Flow Error")]

def get_market_direction():
    """Determine market direction based on 24h price change"""
    try:
        response = requests.get("https://api.coindesk.com/v1/bpi/currentprice.json", timeout=5)
        data = response.json()
        current = data["bpi"]["USD"]["rate_float"]
        yesterday = requests.get("https://api.coindesk.com/v1/bpi/historical/close.json?for=yesterday", timeout=5).json()
        yesterday_price = float(list(yesterday["bpi"].values())[0])
        return "up" if current > yesterday_price else "down"
    except Exception as e:
        print(f"Error determining market direction: {e}")
        return "neutral"

def display_volume_chart(disp):
    """Display 24h volume chart"""
    try:
        response = requests.get("https://api.coingecko.com/api/v3/simple/price",
                                params={"ids": "bitcoin", "vs_currencies": "usd", "include_24hr_vol": "true"},
                                timeout=5)
        data = response.json()
        volume = data['bitcoin']['usd_24h_vol']
        image = Image.new('RGB', (width, height), (0, 0, 0))
        draw = ImageDraw.Draw(image)
        font = ImageFont.load_default()
        draw.text((5, 5), f"24h Vol: ${volume/1e9:.1f}B", font=font, fill=(255, 255, 255))
        return [image]
    except Exception as e:
        print(f"Error fetching volume data: {e}")
        return [create_error_image("Volume Error")]

def display_qr_code(disp, address):
    """Display QR code for donation address"""
    qr = qrcode.QRCode(version=1, box_size=2, border=2)
    qr.add_data(address)
    qr.make(fit=True)
    qr_image = qr.make_image(fill_color="white", back_color="black")
    qr_image = qr_image.resize((width, height))
    return [qr_image]

def create_error_image(message="Error"):
    """Create a simple error image"""
    image = Image.new('RGB', (width, height), (0, 0, 0))
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()
    draw.text((10, height//2), message, font=font, fill=(255, 0, 0))
    return image

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

def get_historical_fear_greed():
    """Fetch historical Fear & Greed data"""
    try:
        url = "https://api.alternative.me/fng/?limit=100"
        response = requests.get(url, timeout=5)
        data = response.json()
        values = [(int(entry['value']), datetime.fromtimestamp(int(entry['timestamp']))) for entry in data['data']]
        return values
    except Exception as e:
        print(f"Error fetching historical data: {e}")
        return None

def display_historical_graph(disp):
    """Create and display historical Fear & Greed graph"""
    values = get_historical_fear_greed()
    if not values:
        return [create_error_image("Graph Error")]
    plt.figure(figsize=(1.6, 1.28), dpi=100)
    plt.style.use('dark_background')
    fear_greed_values, dates = zip(*values)
    plt.plot(dates, fear_greed_values, color='white', linewidth=1)
    plt.axhline(y=25, color='red', linestyle='--', alpha=0.3)
    plt.axhline(y=75, color='green', linestyle='--', alpha=0.3)
    plt.fill_between(dates, fear_greed_values, where=[v <= 25 for v in fear_greed_values], color='red', alpha=0.2)
    plt.fill_between(dates, fear_greed_values, where=[v >= 75 for v in fear_greed_values], color='green', alpha=0.2)
    plt.xticks([])
    plt.yticks([0, 25, 50, 75, 100])
    plt.text(0.02, 0.95, f"Current: {fear_greed_values[0]}", transform=plt.gca().transAxes, color='white', fontsize=8)
    buf = BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', transparent=True)
    plt.close()
    buf.seek(0)
    graph_image = Image.open(buf)
    graph_image = graph_image.resize((width, height))
    return [graph_image]

# Define display modes and config
class DisplayMode:
    FEAR_GREED = 'fear_greed'
    PRICE_TICKER = 'price_ticker'
    MONEY_FLOW = 'money_flow'
    VOLUME = 'volume'
    QR_CODE = 'qr_code'
    CONFIG = 'config'
    HISTORICAL_GRAPH = 'historical_graph'

class Config:
    def __init__(self):
        self.display_time = 10
        self.brightness = 1.0  # Adjusted to 0.0-1.0 for PWM backlight
        self.enabled_modes = [DisplayMode.FEAR_GREED, DisplayMode.PRICE_TICKER, DisplayMode.MONEY_FLOW]
        self.donation_address = "YOUR_BTC_ADDRESS"
        self.manual_time = False
        self.time_offset = 0

    def save(self):
        with open('config.json', 'w') as f:
            json.dump(self.__dict__, f)

    @classmethod
    def load(cls):
        try:
            with open('config.json', 'r') as f:
                data = json.load(f)
                config = cls()
                config.__dict__.update(data)
                return config
        except:
            return cls()

class Transitions:
    @staticmethod
    def slide_left(old_frame, new_frame, steps=20):
        for i in range(steps + 1):
            offset = int((width * (steps - i)) / steps)
            combined = Image.new('RGB', (width, height))
            combined.paste(old_frame, (-offset, 0))
            combined.paste(new_frame, (width - offset, 0))
            yield combined

    @staticmethod
    def fade(old_frame, new_frame, steps=20):
        old_array = np.array(old_frame)
        new_array = np.array(new_frame)
        for i in range(steps + 1):
            alpha = i / steps
            blended = Image.fromarray((old_array * (1 - alpha) + new_array * alpha).astype(np.uint8))
            yield blended

    @staticmethod
    def slide_up(old_frame, new_frame, steps=20):
        for i in range(steps + 1):
            offset = int((height * (steps - i)) / steps)
            combined = Image.new('RGB', (width, height))
            combined.paste(old_frame, (0, -offset))
            combined.paste(new_frame, (0, height - offset))
            yield combined

# Button handling (polling)
current_mode_index = 0
current_mode = DisplayMode.FEAR_GREED
modes = [DisplayMode.FEAR_GREED, DisplayMode.PRICE_TICKER, DisplayMode.MONEY_FLOW, DisplayMode.HISTORICAL_GRAPH]
current_config_option = 0
time_setting_option = 0

def check_buttons():
    """Poll buttons and update global state"""
    global current_mode_index, current_mode, current_config_option, time_setting_option
    if display.read_button(display.BUTTON_A):
        if current_mode == DisplayMode.CONFIG:
            current_config_option = (current_config_option - 1) % 5
        elif current_mode == "time_setting":
            time_setting_option = (time_setting_option - 1) % 7
        else:
            current_mode_index = (current_mode_index + 1) % len(modes)
            current_mode = modes[current_mode_index]
        time.sleep(0.2)  # Debounce
    elif display.read_button(display.BUTTON_B):
        if current_mode == DisplayMode.CONFIG:
            current_config_option = (current_config_option + 1) % 5
        elif current_mode == "time_setting":
            time_setting_option = (time_setting_option + 1) % 7
        else:
            current_mode_index = (current_mode_index - 1) % len(modes)
            current_mode = modes[current_mode_index]
        time.sleep(0.2)  # Debounce
    elif display.read_button(display.BUTTON_X):
        if current_mode == DisplayMode.CONFIG:
            handle_config_buttons(display.BUTTON_X)
        elif current_mode == "time_setting":
            result = handle_time_setting(display.BUTTON_X)
            if result == "config":
                current_mode = DisplayMode.CONFIG
        else:
            display.set_led(0.0, 0.0, 0.0)
        time.sleep(0.2)  # Debounce
    elif display.read_button(display.BUTTON_Y):
        if current_mode == DisplayMode.CONFIG:
            handle_config_buttons(display.BUTTON_Y)
        elif current_mode == "time_setting":
            result = handle_time_setting(display.BUTTON_Y)
            if result == "config":
                current_mode = DisplayMode.CONFIG
        else:
            current_mode = DisplayMode.CONFIG
        time.sleep(0.2)  # Debounce

def display_config_menu(disp):
    """Display configuration menu"""
    image = Image.new('RGB', (width, height), (0, 0, 0))
    draw = ImageDraw.Draw(image)
    config = Config.load()
    options = [
        f"Display Time: {config.display_time}s",
        f"Brightness: {int(config.brightness * 100)}%",
        f"Enabled Modes: {len(config.enabled_modes)}",
        "Set System Time",
        "Save & Exit"
    ]
    font = ImageFont.load_default()
    for i, option in enumerate(options):
        color = (0, 255, 0) if i == current_config_option else (255, 255, 255)
        draw.text((10, 10 + i*20), option, font=font, fill=color)
    return [image]

def handle_config_buttons(pin):
    """Handle button presses in config mode"""
    global current_config_option, current_mode
    config = Config.load()
    if pin == display.BUTTON_X:
        if current_config_option == 0:
            config.display_time = (config.display_time % 30) + 5
        elif current_config_option == 1:
            config.brightness = min(1.0, config.brightness + 0.1)
            display.set_backlight(config.brightness)
        elif current_config_option == 3:
            global time_setting_option
            time_setting_option = 0
            current_mode = "time_setting"
        elif current_config_option == 4:
            config.save()
            current_mode = DisplayMode.FEAR_GREED
        config.save()
    elif pin == display.BUTTON_Y:
        current_mode = DisplayMode.FEAR_GREED

def set_system_time(timestamp):
    """Set system time manually"""
    try:
        time_str = timestamp.strftime('%Y-%m-%d %H:%M:%S')
        subprocess.run(['sudo', 'date', '-s', time_str])
        return True
    except Exception as e:
        print(f"Error setting system time: {e}")
        return False

def display_time_setting(disp):
    """Display time setting interface"""
    image = Image.new('RGB', (width, height), (0, 0, 0))
    draw = ImageDraw.Draw(image)
    config = Config.load()
    current_time = datetime.now() + timedelta(seconds=config.time_offset)
    options = [
        f"Year:  {current_time.year}",
        f"Month: {current_time.month:02d}",
        f"Day:   {current_time.day:02d}",
        f"Hour:  {current_time.hour:02d}",
        f"Min:   {current_time.minute:02d}",
        "Set Time",
        "Back"
    ]
    font = ImageFont.load_default()
    for i, option in enumerate(options):
        color = (0, 255, 0) if i == time_setting_option else (255, 255, 255)
        draw.text((10, 10 + i*20), option, font=font, fill=color)
    draw.text((10, height-30), f"New: {current_time.strftime('%Y-%m-%d %H:%M')}", font=font, fill=(255, 165, 0))
    return [image]

def handle_time_setting(pin):
    """Handle button presses in time setting mode"""
    global time_setting_option
    config = Config.load()
    if pin == display.BUTTON_X:
        current_time = datetime.now() + timedelta(seconds=config.time_offset)
        if time_setting_option == 0:
            config.time_offset += timedelta(days=365).total_seconds()
        elif time_setting_option == 1:
            config.time_offset += timedelta(days=30).total_seconds()
        elif time_setting_option == 2:
            config.time_offset += timedelta(days=1).total_seconds()
        elif time_setting_option == 3:
            config.time_offset += timedelta(hours=1).total_seconds()
        elif time_setting_option == 4:
            config.time_offset += timedelta(minutes=1).total_seconds()
        elif time_setting_option == 5:
            new_time = datetime.now() + timedelta(seconds=config.time_offset)
            if set_system_time(new_time):
                config.manual_time = True
                config.time_offset = 0
                config.save()
                return "config"
        elif time_setting_option == 6:
            config.time_offset = 0
            config.save()
            return "config"
    elif pin == display.BUTTON_Y:
        current_time = datetime.now() + timedelta(seconds=config.time_offset)
        if time_setting_option == 0:
            config.time_offset -= timedelta(days=365).total_seconds()
        elif time_setting_option == 1:
            config.time_offset -= timedelta(days=30).total_seconds()
        elif time_setting_option == 2:
            config.time_offset -= timedelta(days=1).total_seconds()
        elif time_setting_option == 3:
            config.time_offset -= timedelta(hours=1).total_seconds()
        elif time_setting_option == 4:
            config.time_offset -= timedelta(minutes=1).total_seconds()
    config.save()

def display_boot_sequence(display):
    """Display an animated boot sequence with real checks"""
    background = Image.new('RGB', (width, height), (0, 0, 0))
    draw = ImageDraw.Draw(background)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
        small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
    except:
        font = small_font = ImageFont.load_default()

    for i in range(20):
        frame = background.copy()
        draw = ImageDraw.Draw(frame)
        draw.text((width//2-50, height//2), "WELCOME", font=font, fill=(0, int(255 * i / 20), 0))
        display.st7789.display(frame)
        time.sleep(0.05)

    frame = background.copy()
    draw = ImageDraw.Draw(frame)
    draw.text((10, 10), "Checking WiFi...", font=small_font, fill=(255, 255, 255))
    display.st7789.display(frame)
    wifi_ok, ssid, signal = check_wifi()
    frame = background.copy()
    draw = ImageDraw.Draw(frame)
    if wifi_ok:
        draw.text((10, 10), f"WiFi: {ssid}", font=small_font, fill=(0, 255, 0))
        draw.text((10, 30), f"Signal: {signal}dBm", font=small_font, fill=(0, 255, 0))
        display.set_led(0.0, 1.0, 0.0)
    else:
        draw.text((10, 10), "WiFi: Not Connected", font=small_font, fill=(255, 0, 0))
        display.set_led(1.0, 0.0, 0.0)
    display.st7789.display(frame)
    time.sleep(1)

def check_wifi():
    """Check WiFi connection and get details"""
    try:
        result = subprocess.run(['iwgetid', '-r'], capture_output=True, text=True)
        ssid = result.stdout.strip()
        strength = subprocess.run(['iwconfig', 'wlan0'], capture_output=True, text=True)
        signal = [line for line in strength.stdout.split('\n') if 'Signal level' in line]
        signal_strength = signal[0].split('=')[1].split(' ')[0] if signal else 'N/A'
        return True, ssid, signal_strength
    except:
        return False, None, None

def main():
    """Main function with improved initialization and boot sequence"""
    global current_mode
    try:
        display.set_backlight(0.0)
        black_screen = Image.new('RGB', (width, height), (0, 0, 0))
        display.st7789.display(black_screen)
        for i in range(101):
            display.set_backlight(i/100)
            time.sleep(0.01)

        display_boot_sequence(display)
        config = Config.load()
        transition_functions = [Transitions.slide_left, Transitions.fade, Transitions.slide_up]

        while True:
            check_buttons()
            if current_mode == DisplayMode.CONFIG:
                current_frames = display_config_menu(display)
            elif current_mode == "time_setting":
                current_frames = display_time_setting(display)
            elif current_mode == DisplayMode.FEAR_GREED:
                index_data, value = get_fear_greed_index()
                set_mood_led(value)
                current_frames = load_gif_frames(get_mood_gif(value))
            elif current_mode == DisplayMode.PRICE_TICKER:
                current_frames = [display_price_ticker(display)]
            elif current_mode == DisplayMode.MONEY_FLOW:
                current_frames = display_money_flow(display)
            elif current_mode == DisplayMode.HISTORICAL_GRAPH:
                current_frames = display_historical_graph(display)

            start_time = time.time()
            frame_index = 0
            while time.time() - start_time < config.display_time:
                frame = current_frames[frame_index % len(current_frames)]
                display.st7789.display(frame)
                frame_index += 1
                check_buttons()
                time.sleep(0.1)

            next_mode_index = (current_mode_index + 1) % len(modes)
            if current_mode in modes:  # Only transition if not in config/time_setting
                if modes[next_mode_index] == DisplayMode.FEAR_GREED:
                    index_data, value = get_fear_greed_index()
                    next_frames = load_gif_frames(get_mood_gif(value))
                elif modes[next_mode_index] == DisplayMode.PRICE_TICKER:
                    next_frames = [display_price_ticker(display)]
                elif modes[next_mode_index] == DisplayMode.MONEY_FLOW:
                    next_frames = display_money_flow(display)
                elif modes[next_mode_index] == DisplayMode.HISTORICAL_GRAPH:
                    next_frames = display_historical_graph(display)
                transition_func = np.random.choice(transition_functions)
                for transition_frame in transition_func(current_frames[0], next_frames[0]):
                    display.st7789.display(transition_frame)
                    time.sleep(0.05)
                current_mode_index = next_mode_index
                current_mode = modes[current_mode_index]

    except Exception as e:
        print(f"Error in main: {e}")
        display.set_led(1.0, 0.0, 0.0)
        time.sleep(5)
    finally:
        cleanup()

if __name__ == "__main__":
    main()
