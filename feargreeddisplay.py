# Version 2.5 15/03/2025 13:16
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
from PIL import ImageEnhance
import math
import random

# Add at top of file after imports
last_button_time = 0
BUTTON_DEBOUNCE_MS = 5  # 10ms debounce window

# Cache to store API results with timestamps
API_CACHE = {
    'fear_greed': {'data': None, 'timestamp': 0},
    'coingecko': {'data': None, 'timestamp': 0}
}
CACHE_DURATION = 300  # Cache data for 5 minutes (300 seconds)

# Font definitions
FONT_PATHS = {
    'regular': "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    'bold': "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    'mono': "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
}

FONT_SIZES = {
    'large': 26,
    'medium': 20,
    'small': 16,
    'tiny': 12
}

def load_fonts():
    """Load and return font dictionary"""
    fonts = {}
    try:
        # Regular fonts
        fonts['regular_large'] = ImageFont.truetype(FONT_PATHS['regular'], FONT_SIZES['large'])
        fonts['regular_medium'] = ImageFont.truetype(FONT_PATHS['regular'], FONT_SIZES['medium'])
        fonts['regular_small'] = ImageFont.truetype(FONT_PATHS['regular'], FONT_SIZES['small'])
        fonts['regular_tiny'] = ImageFont.truetype(FONT_PATHS['regular'], FONT_SIZES['tiny'])
        
        # Bold fonts
        fonts['bold_large'] = ImageFont.truetype(FONT_PATHS['bold'], FONT_SIZES['large'])
        fonts['bold_medium'] = ImageFont.truetype(FONT_PATHS['bold'], FONT_SIZES['medium'])
        fonts['bold_small'] = ImageFont.truetype(FONT_PATHS['bold'], FONT_SIZES['small'])
        
        # Mono fonts (for numbers/data)
        fonts['mono_large'] = ImageFont.truetype(FONT_PATHS['mono'], FONT_SIZES['large'])  # Added
        fonts['mono_medium'] = ImageFont.truetype(FONT_PATHS['mono'], FONT_SIZES['medium'])
        fonts['mono_small'] = ImageFont.truetype(FONT_PATHS['mono'], FONT_SIZES['small'])
    except Exception as e:
        print(f"Warning: Could not load fonts: {e}")
        # Fallback to default font for all
        default = ImageFont.load_default()
        fonts = {key: default for key in [
            'regular_large', 'regular_medium', 'regular_small', 'regular_tiny',
            'bold_large', 'bold_medium', 'bold_small',
            'mono_large', 'mono_medium', 'mono_small'  # Updated keys
        ]}
    return fonts

# Initialize fonts globally
FONTS = load_fonts()

# Initialize GPIO once (no cleanup here to avoid warning)
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

def load_gif_frames(gif_path, max_frames=20):
    """Load a GIF with a frame limit to reduce memory usage"""
    try:
        with Image.open(gif_path) as gif:
            frames = []
            frame_count = 0
            while frame_count < max_frames:
                frame = gif.copy().convert("RGB")
                if frame.size != (width, height):
                    frame = frame.resize((width, height), Image.Resampling.LANCZOS)
                frames.append(frame)
                frame_count += 1
                try:
                    gif.seek(gif.tell() + 1)
                except EOFError:
                    break
            print(f"Loaded {frame_count} frames from {gif_path}")
            return frames
    except Exception as e:
        print(f"Error loading GIF: {e}")
        return [create_error_image("GIF Error")]
    finally:
        if 'gif' in locals():
            gif.close()

def get_mood_gif(value):
    """Return appropriate optimized GIF path based on fear/greed value"""
    if value is None:
        return "gifs/error.gif"  # Assuming this doesn’t need optimization
    value = int(value)
    if value <= 25:
        return "gifs/feargreed/extremefear_opt.gif"
    elif value <= 45:
        return "gifs/feargreed/fear_opt.gif"
    elif value <= 55:
        return "gifs/feargreed/neutral_opt.gif"
    elif value <= 75:
        return "gifs/feargreed/greed_opt.gif"
    else:
        return "gifs/feargreed/extremegreed_opt.gif"

def get_fear_greed_index():
    """Fetch the Fear & Greed Index from Alternative.me with caching"""
    current_time = time.time()
    cache = API_CACHE['fear_greed']
    
    # Return cached data if still valid
    if cache['data'] and (current_time - cache['timestamp']) < CACHE_DURATION:
        return cache['data'], cache['value']
    
    try:
        url = "https://api.alternative.me/fng/"
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        value = data['data'][0]['value']
        classification = data['data'][0]['value_classification']
        result = f"Fear & Greed: {value}\n{classification}"
        
        # Update cache
        API_CACHE['fear_greed']['data'] = result
        API_CACHE['fear_greed']['value'] = value
        API_CACHE['fear_greed']['timestamp'] = current_time
        return result, value
    except requests.exceptions.RequestException as e:
        print(f"Error fetching Fear & Greed Index: {e}")
        if cache['data']:  # Return stale data if available
            return cache['data'], cache['value']
        return "Error fetching data", None

def get_btc_data():
    """Fetch BTC price, 24h change, and volume from CoinGecko with caching"""
    current_time = time.time()
    cache = API_CACHE['coingecko']
    
    # Return cached data if still valid
    if cache['data'] and (current_time - cache['timestamp']) < CACHE_DURATION:
        return cache['data']
    
    try:
        url = "https://api.coingecko.com/api/v3/coins/markets"
        params = {
            "ids": "bitcoin",
            "vs_currency": "usd",
            "order": "market_cap_desc",
            "per_page": 1,
            "page": 1,
            "sparkline": False,
            "price_change_percentage": "24h",
            "locale": "en"
        }
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()[0]
        
        result = {
            'price': data['current_price'],
            'change_24h': data['price_change_percentage_24h'],
            'volume_24h': data['total_volume']
        }
        
        # Update cache
        API_CACHE['coingecko']['data'] = result
        API_CACHE['coingecko']['timestamp'] = current_time
        return result
    except requests.exceptions.RequestException as e:
        print(f"Error fetching BTC data from CoinGecko: {e}")
        if cache['data']:  # Return stale data if available
            return cache['data']
        return {'price': None, 'change_24h': None, 'volume_24h': None}    

def get_btc_price():
    """Format BTC price from CoinGecko data"""
    data = get_btc_data()
    price = data['price']
    return f"BTC: ${price:,.2f}" if price else "Price Error"

def display_price_ticker(disp):
    """Display BTC price ticker with date/time, animated USD, static GBP, and header"""
    # Get BTC data
    data = get_btc_data()
    price_usd = data['price'] if data['price'] else 0
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # Current time as placeholder
    
    # Fixed conversion rate (1 USD = 0.79 GBP, October 2023)
    conversion_rate = 0.79
    price_gbp = price_usd * conversion_rate if price_usd else 0
    
    # Animation parameters
    frames = []
    steps = 10  # 10 frames for counter effect
    step_value = price_usd / steps
    
    # Generate animation frames
    for i in range(steps):
        img = Image.new('RGB', (width, height), (0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Date and time at top (small font)
        draw.text((10, 10), f"Data: {timestamp}", font=FONTS['regular_small'], fill=(255, 255, 255))
        
        # "Current Price" header (medium font)
        header_text = "Current Price"
        header_bbox = draw.textbbox((0, 0), header_text, font=FONTS['mono_medium'])
        header_width = header_bbox[2] - header_bbox[0]
        draw.text((width // 2 - header_width // 2, 40), header_text, 
                  font=FONTS['mono_medium'], fill=(255, 255, 255))
        
        # Animated USD price (large font, gold)
        current_usd = step_value * i
        usd_text = f"BTC: ${current_usd:,.2f}"
        usd_bbox = draw.textbbox((0, 0), usd_text, font=FONTS['mono_large'])
        usd_width = usd_bbox[2] - usd_bbox[0]
        draw.text((width // 2 - usd_width // 2, 90), usd_text, 
                  font=FONTS['mono_large'], fill=(255, 215, 0))
        
        # GBP price below (medium font, gold)
        gbp_text = f"£{price_gbp:,.2f}"
        gbp_bbox = draw.textbbox((0, 0), gbp_text, font=FONTS['mono_medium'])
        gbp_width = gbp_bbox[2] - gbp_bbox[0]
        draw.text((width // 2 - gbp_width // 2, 140), gbp_text, 
                  font=FONTS['mono_medium'], fill=(255, 215, 0))
        
        frames.append(img)
    
    # Final static frame (no animation)
    final_img = Image.new('RGB', (width, height), (0, 0, 0))
    draw = ImageDraw.Draw(final_img)
    
    draw.text((10, 10), f"Data: {timestamp}", font=FONTS['regular_small'], fill=(255, 255, 255))
    header_bbox = draw.textbbox((0, 0), header_text, font=FONTS['mono_medium'])
    header_width = header_bbox[2] - header_bbox[0]
    draw.text((width // 2 - header_width // 2, 40), header_text, 
              font=FONTS['mono_medium'], fill=(255, 255, 255))
    
    usd_text = f"BTC: ${price_usd:,.2f}"
    usd_bbox = draw.textbbox((0, 0), usd_text, font=FONTS['mono_large'])
    usd_width = usd_bbox[2] - usd_bbox[0]
    draw.text((width // 2 - usd_width // 2, 90), usd_text, 
              font=FONTS['mono_large'], fill=(255, 215, 0))
    
    gbp_text = f"£{price_gbp:,.2f}"
    gbp_bbox = draw.textbbox((0, 0), gbp_text, font=FONTS['mono_medium'])
    gbp_width = gbp_bbox[2] - gbp_bbox[0]
    draw.text((width // 2 - gbp_width // 2, 140), gbp_text, 
              font=FONTS['mono_medium'], fill=(255, 215, 0))
    
    # Add animation frames, then repeat final frame
    frames.extend([final_img] * 10)  # 10 pause frames after animation
    
    print(f"Generated {len(frames)} frames for price ticker")
    return frames

def display_money_flow(disp):
    """Display money flow animation based on market direction"""
    direction = get_market_direction()
    gif_path = f"gifs/money_flow/flow_{direction}.gif"
    try:
        frames = load_gif_frames(gif_path, max_frames=20)
        return frames
    except Exception as e:
        print(f"Money Flow GIF error: {e}")
        return [create_error_image("Money Flow Error")]

def get_market_direction():
    """Determine market direction based on 24h price change"""
    data = get_btc_data()
    change = data['change_24h']
    if change is None:
        return "neutral"
    return "up" if change > 0 else "down"

def display_volume_chart(disp):
    """Display 24h volume chart using CoinGecko data"""
    data = get_btc_data()
    volume = data['volume_24h']
    
    if volume is None:
        return [create_error_image("Volume Error")]
    
    image = Image.new('RGB', (width, height), (0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.text((5, 5), f"24h Vol: ${volume/1e9:.1f}B", 
             font=FONTS['mono_medium'], 
             fill=(255, 255, 255))
    return [image]

def display_qr_code(disp, address):
    """Display QR code for donation address"""
    qr = qrcode.QRCode(version=1, box_size=2, border=2)
    qr.add_data(address)
    qr.make(fit=True)
    qr_image = qr.make_image(fill_color="white", back_color="black").convert("RGB")  # Ensure RGB
    qr_image = qr_image.resize((width, height))
    return [qr_image]

def create_error_image(message="Error"):
    """Create a simple error image"""
    image = Image.new('RGB', (width, height), (0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.text((10, height//2), message, 
              font=FONTS['bold_medium'], 
              fill=(255, 0, 0))
    return image

def get_price_change():
    """Format 24-hour price change from CoinGecko data"""
    data = get_btc_data()
    change = data['change_24h']
    return f"{change:+.2f}%" if change is not None else "N/A"

def set_mood_led(value):
    """Set RGB LED color based on fear/greed value with brightness control"""
    config = Config.load()
    if not config.led_enabled:
        display.set_led(0.0, 0.0, 0.0)
        return
        
    brightness = config.led_brightness
    if value is None:
        display.set_led(brightness, 0.0, 0.0)  # Red for error
        return
        
    value = int(value)
    if value <= 25:      # Extreme fear - deep red
        display.set_led(brightness, 0.0, 0.0)
    elif value <= 45:    # Fear - orange
        display.set_led(brightness, brightness*0.65, 0.0)
    elif value <= 55:    # Neutral - yellow
        display.set_led(brightness, brightness, 0.0)
    elif value <= 75:    # Greed - light green
        display.set_led(0.0, brightness, 0.0)
    else:               # Extreme greed - deep green
        display.set_led(0.0, brightness*0.5, 0.0)

def get_historical_fear_greed():
    """Get historical Fear & Greed Index values with caching"""
    global API_CACHE
    cache_key = "fear_greed_historical"
    if cache_key in API_CACHE and time.time() - API_CACHE[cache_key]["timestamp"] < 24 * 60 * 60:
        return API_CACHE[cache_key]["data"]
    
    try:
        url = "https://api.alternative.me/fng/?limit=0"
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()["data"]
        values = [(int(entry["value"]), entry["timestamp"]) for entry in data]
        API_CACHE[cache_key] = {"data": values, "timestamp": time.time()}
        return values
    except Exception as e:
        print(f"Error fetching historical Fear & Greed: {e}")
        return []

def display_historical_graph(disp):
    """Display a 5-day BTC price graph with segmented colors, annotations, and smooth dot"""
    # Get 5 days of BTC price data (mocked daily averages for now)
    values = get_historical_btc_prices()  # Define this function below
    if not values or len(values) < 5:
        return [create_error_image("Graph Data Error")]
    
    # Use last 5 days
    daily_prices = values[-5:]  # [price_day5, price_day4, price_day3, price_day2, price_day1]
    
    # Graph parameters
    graph_width, graph_height = 280, 180
    padding_x, padding_y = 20, 30
    x_step = graph_width // 4  # 5 points = 4 segments
    y_max = max(daily_prices) * 1.05  # 5% above max price
    y_min = min(daily_prices) * 0.95  # 5% below min price
    
    # Normalize prices to graph height
    points = []
    for i, price in enumerate(daily_prices):
        y = padding_y + int(graph_height * (y_max - price) / (y_max - y_min))
        x = padding_x + i * x_step
        points.append((x, y))
    
    # Generate frames with smooth dot movement
    frames = []
    steps_per_segment = 5  # 5 frames per line segment
    for segment in range(4):  # 4 segments between 5 points
        start_x, start_y = points[segment]
        end_x, end_y = points[segment + 1]
        trend_up = daily_prices[segment + 1] > daily_prices[segment]
        line_color = (0, 255, 0) if trend_up else (255, 0, 0)
        
        for step in range(steps_per_segment):
            img = Image.new('RGB', (width, height), (0, 0, 0))
            draw = ImageDraw.Draw(img)
            
            # Draw X/Y axes (white)
            draw.line([(padding_x, padding_y), (padding_x, padding_y + graph_height)], fill=(255, 255, 255), width=2)
            draw.line([(padding_x, padding_y + graph_height), (padding_x + graph_width, padding_y + graph_height)], fill=(255, 255, 255), width=2)
            
            # Draw segmented lines
            for i in range(4):
                p1 = points[i]
                p2 = points[i + 1]
                color = (0, 255, 0) if daily_prices[i + 1] > daily_prices[i] else (255, 0, 0)
                draw.line([p1, p2], fill=color, width=2)
            
            # Draw arrowhead at end
            last_x, last_y = points[-1]
            trend_up = daily_prices[-1] > daily_prices[-2]
            arrow_color = (0, 255, 0) if trend_up else (255, 0, 0)
            if trend_up:
                arrow_points = [(last_x, last_y), (last_x - 10, last_y + 10), (last_x + 10, last_y + 10)]
            else:
                arrow_points = [(last_x, last_y), (last_x - 10, last_y - 10), (last_x + 10, last_y - 10)]
            draw.polygon(arrow_points, fill=arrow_color, outline=arrow_color)
            
            # Interpolate dot position
            t = step / steps_per_segment
            dot_x = int(start_x + (end_x - start_x) * t)
            dot_y = int(start_y + (end_y - start_y) * t)
            dot_color = (0, 255, 0) if trend_up else (255, 0, 0)
            draw.ellipse([(dot_x - 5, dot_y - 5), (dot_x + 5, dot_y + 5)], fill=dot_color, outline=(255, 255, 255))
            
            # X-axis annotations (1 to 5)
            for i in range(5):
                draw.text((padding_x + i * x_step - 5, padding_y + graph_height + 5), str(i + 1), 
                          font=FONTS['regular_small'], fill=(255, 255, 255))
            
            # Y-axis annotations (price range)
            y_steps = 5
            price_step = (y_max - y_min) / (y_steps - 1)
            for i in range(y_steps):
                price = y_min + i * price_step
                y_pos = padding_y + graph_height - int(graph_height * i / (y_steps - 1))
                draw.text((padding_x - 40, y_pos - 5), f"${price:,.0f}", 
                          font=FONTS['regular_small'], fill=(255, 255, 255))
            
            # Title: "5 Day Price Movement"
            title = "5 Day Price Movement"
            title_bbox = draw.textbbox((0, 0), title, font=FONTS['mono_medium'])
            title_width = title_bbox[2] - title_bbox[0]
            draw.text((width // 2 - title_width // 2, 5), title, 
                      font=FONTS['mono_medium'], fill=(255, 255, 255))
            
            frames.append(img)
    
    # Add pause frames
    for _ in range(5):
        frames.append(frames[-1])
    
    print(f"Generated {len(frames)} frames for historical graph")
    return frames

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
        self.led_brightness = 0.5  # Add LED brightness (0.0-1.0)
        self.led_enabled = True    # Add LED enable/disable toggle

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
        old_array = np.array(old_frame.convert("RGB"))  # Ensure RGB
        new_array = np.array(new_frame.convert("RGB"))  # Ensure RGB
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

def check_buttons_main():
    """Handle button presses in main display modes with optimized debouncing"""
    global current_mode, current_mode_index, config, last_button_time, previous_mode
    current_time = time.time() * 1000  # Milliseconds
    
    if (current_time - last_button_time) < BUTTON_DEBOUNCE_MS:
        return False
    
    if display.read_button(display.BUTTON_A):
        print("Button A detected")
        previous_mode = current_mode
        current_mode = DisplayMode.CONFIG
        last_button_time = current_time
        return True
    elif display.read_button(display.BUTTON_B):
        print("Button B detected")
        current_mode_index = (current_mode_index - 1) % len(modes)
        current_mode = modes[current_mode_index]
        last_button_time = current_time
        return True
    elif display.read_button(display.BUTTON_X):
        print("Button X detected")
        config.led_enabled = not config.led_enabled
        if not config.led_enabled:
            display.set_led(0.0, 0.0, 0.0)
        else:
            if current_mode == DisplayMode.FEAR_GREED:
                _, value = get_fear_greed_index()
                set_mood_led(value)
        config.save()
        last_button_time = current_time
        return True
    elif display.read_button(display.BUTTON_Y):
        print("Button Y detected")
        current_mode_index = (current_mode_index + 1) % len(modes)
        current_mode = modes[current_mode_index]
        last_button_time = current_time
        return True
    return False

def check_buttons_config():
    """Handle button presses in config menu with optimized debouncing"""
    global current_config_option, current_mode, last_button_time
    current_time = time.time() * 1000
    
    if (current_time - last_button_time) < BUTTON_DEBOUNCE_MS:
        return False
    
    if display.read_button(display.BUTTON_A):
        print("Button A detected in config")
        current_config_option = (current_config_option - 1) % 7
        last_button_time = current_time
        return True
    elif display.read_button(display.BUTTON_B):
        print("Button B detected in config")
        current_config_option = (current_config_option + 1) % 7
        last_button_time = current_time
        return True
    elif display.read_button(display.BUTTON_X):
        print("Button X detected in config")
        handle_config_buttons(display.BUTTON_X)
        last_button_time = current_time
        return True
    elif display.read_button(display.BUTTON_Y):
        print("Button Y detected in config")
        handle_config_buttons(display.BUTTON_Y)
        last_button_time = current_time
        return True
    return False

def display_config_menu(disp):
    """Display configuration menu with Exit option"""
    image = Image.new('RGB', (width, height), (0, 0, 0))
    draw = ImageDraw.Draw(image)
    config = Config.load()
    options = [
        f"Display Time: {config.display_time}s",
        f"Screen Bright: {int(config.brightness * 100)}%",
        f"LED Bright: {int(config.led_brightness * 100)}%",
        f"LED: {'On' if config.led_enabled else 'Off'}",
        f"Enabled Modes: {len(config.enabled_modes)}",
        "Set System Time",
        "Exit"  # New option
    ]
    
    for i, option in enumerate(options):
        color = (0, 255, 0) if i == current_config_option else (255, 255, 255)
        draw.text((10, 10 + i * 25), option, 
                 font=FONTS['regular_medium'], 
                 fill=color)
    return [image]

def handle_config_buttons(pin):
    """Handle value changes in config mode with Exit option"""
    global current_mode, time_setting_option, previous_mode
    config = Config.load()
    
    if pin == display.BUTTON_X:  # Increase value
        if current_config_option == 0:  # Display Time
            config.display_time = min(30, config.display_time + 5)
        elif current_config_option == 1:  # Screen Brightness
            config.brightness = min(1.0, config.brightness + 0.1)
            display.set_backlight(config.brightness)
        elif current_config_option == 2:  # LED Brightness
            config.led_brightness = min(1.0, config.led_brightness + 0.1)
        elif current_config_option == 3:  # LED On/Off
            config.led_enabled = True
            display.set_led(0.0, 0.0, 0.0)  # Will be updated by mode
        elif current_config_option == 5:  # Set System Time
            time_setting_option = 0
            current_mode = "time_setting"
    elif pin == display.BUTTON_Y:  # Decrease value or exit
        if current_config_option == 0:  # Display Time
            config.display_time = max(5, config.display_time - 5)
        elif current_config_option == 1:  # Screen Brightness
            config.brightness = max(0.0, config.brightness - 0.1)
            display.set_backlight(config.brightness)
        elif current_config_option == 2:  # LED Brightness
            config.led_brightness = max(0.0, config.led_brightness - 0.1)
        elif current_config_option == 3:  # LED On/Off
            config.led_enabled = False
            display.set_led(0.0, 0.0, 0.0)
        elif current_config_option == 4:  # Enabled Modes (no change on Y)
            pass
        elif current_config_option == 6:  # Exit
            current_mode = previous_mode  # Return to previous mode
    config.save()

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
    
    for i, option in enumerate(options):
        color = (0, 255, 0) if i == time_setting_option else (255, 255, 255)
        draw.text((10, 10 + i*25), option, 
                 font=FONTS['mono_medium'] if i < 5 else FONTS['regular_medium'], 
                 fill=color)
    
    draw.text((10, height-30), 
              f"New: {current_time.strftime('%Y-%m-%d %H:%M')}", 
              font=FONTS['mono_medium'], 
              fill=(255, 165, 0))
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
    """Display boot sequence with preloaded Bitcoin spin GIF"""
    import psutil  # Add at top if not present
    
    background = Image.new('RGB', (width, height), (0, 0, 0))
    try:
        font_large = ImageFont.truetype(FONT_PATHS['bold'], 48)
        font_mono = ImageFont.truetype(FONT_PATHS['mono'], 16)
    except Exception as e:
        print(f"Font load error: {e}")
        font_large = font_mono = ImageFont.load_default()

    # Step 1: 3D Welcome Animation
    welcome_text = "WELCOME"
    max_scale_x = 2.0
    max_scale_y = 3.0
    min_scale = 0.5
    frames = 25
    
    for i in range(frames):
        frame = background.copy()
        draw = ImageDraw.Draw(frame)
        
        scale_x = min_scale + (max_scale_x - min_scale) * (math.sin(i * math.pi / frames) + 1) / 2
        scale_y = min_scale + (max_scale_y - min_scale) * (math.sin(i * math.pi / frames) + 1) / 2
        angle = i * 360 / frames
        
        green_to_gold = i / (frames - 1)
        r = int(255 * green_to_gold)
        g = int(255 - 40 * green_to_gold)
        b = 0
        text_color = (r, g, b)
        
        text_img = Image.new('RGB', (width, height), (0, 0, 0))
        text_draw = ImageDraw.Draw(text_img)
        text_bbox = text_draw.textbbox((0, 0), welcome_text, font=font_large)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        
        text_draw.text((width // 2 - text_width // 2, height // 2 - text_height // 2),
                      welcome_text, font=font_large, fill=text_color)
        scaled_size = (int(text_width * scale_x), int(text_height * scale_y))
        text_img = text_img.resize(scaled_size, Image.Resampling.LANCZOS)
        text_img = text_img.rotate(angle, expand=True, fillcolor=(0, 0, 0))
        
        paste_x = (width - text_img.width) // 2
        paste_y = (height - text_img.height) // 2
        frame.paste(text_img, (paste_x, paste_y))
        
        enhancer = ImageEnhance.Brightness(frame)
        frame = enhancer.enhance(1 + math.sin(i * math.pi / frames) * 0.5)
        
        display.st7789.display(frame)
        time.sleep(0.03)

    # Fade to black
    text_bbox = ImageDraw.Draw(background).textbbox((0, 0), welcome_text, font=font_large)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]
    center_x = width // 2 - text_width // 2
    center_y = height // 2 - text_height // 2
    
    for i in range(10):
        frame = background.copy()
        draw = ImageDraw.Draw(frame)
        brightness = 1.0 - (i / 10)
        draw.text((center_x, center_y), welcome_text, font=font_large,
                  fill=(int(255 * brightness), int(215 * brightness), 0))
        display.st7789.display(frame)
        time.sleep(0.03)

    # Step 2: Techy WiFi/Signal Check
    boot_lines = [
        "SYSTEM BOOT v1.1",
        "INITIALIZING HARDWARE...",
        "CHECKING NETWORK INTERFACE",
        "",
    ]
    
    frame = background.copy()
    draw = ImageDraw.Draw(frame)
    for line_idx, line in enumerate(boot_lines):
        for char_idx in range(len(line) + 1):
            frame = background.copy()
            draw = ImageDraw.Draw(frame)
            for prev_idx, prev_line in enumerate(boot_lines[:line_idx]):
                draw.text((10, 10 + prev_idx * 20), prev_line, font=font_mono, fill=(0, 255, 0))
            draw.text((10, 10 + line_idx * 20), line[:char_idx], font=font_mono, fill=(0, 255, 0))
            display.st7789.display(frame)
            time.sleep(0.02)

    wifi_ok, ssid, signal = check_wifi()
    status_lines = [
        f"NETWORK: {'ONLINE' if wifi_ok else 'OFFLINE'}",
        f"SSID: {ssid if ssid else 'N/A'}",
        f"SIGNAL: {signal if signal else 'N/A'} dBm",
        "",
        "BOOT COMPLETE - PRESS ANY KEY"
    ]
    
    for i in range(20):
        frame = background.copy()
        draw = ImageDraw.Draw(frame)
        for idx, line in enumerate(boot_lines + status_lines):
            color = (0, 255, 0) if i % 2 == 0 or idx < len(boot_lines) else (0, 200, 0)
            draw.text((10, 10 + idx * 20), line, font=font_mono, fill=color)
        display.st7789.display(frame)
        time.sleep(0.05 if i < 10 else 0.02)
    
    # Wait for button press with preloading
    gif_path = random.choice(["gifs/animations/bitcoinspin1_opt.gif", "gifs/animations/bitcoinspin2_opt.gif"])
    bitcoin_spin_frames = load_gif_frames(gif_path, max_frames=20)  # Limit to 20 frames
    print(f"Memory before GIF loop: {psutil.virtual_memory().available / 1024 / 1024:.2f} MB")
    
    while not (display.read_button(display.BUTTON_A) or
               display.read_button(display.BUTTON_B) or
               display.read_button(display.BUTTON_X) or
               display.read_button(display.BUTTON_Y)):
        time.sleep(0.005)
    
    # Step 3: Display Random Bitcoin Spin GIF
    global current_mode, current_mode_index
    current_mode = "boot_gif"
    current_mode_index = 0
    frame_index = 0
    
    try:
        while current_mode == "boot_gif":
            frame = bitcoin_spin_frames[frame_index % len(bitcoin_spin_frames)]
            display.st7789.display(frame)
            frame_index += 1
            
            button_pressed = check_buttons_main()
            if button_pressed:
                print(f"Button pressed, exiting GIF. Memory: {psutil.virtual_memory().available / 1024 / 1024:.2f} MB")
                break
            time.sleep(0.02)
    finally:
        del bitcoin_spin_frames  # Free GIF frames
        print(f"Memory after GIF cleanup: {psutil.virtual_memory().available / 1024 / 1024:.2f} MB")
        
def get_historical_btc_prices():
    """Get last 5 days of BTC prices from CoinGecko"""
    global API_CACHE
    cache_key = "btc_historical_prices"
    if cache_key in API_CACHE and time.time() - API_CACHE[cache_key]["timestamp"] < 24 * 60 * 60:
        return API_CACHE[cache_key]["data"]
    
    try:
        url = "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart?vs_currency=usd&days=5&interval=daily"
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()["prices"]
        # Extract daily closing prices (last 5 days)
        prices = [price[1] for price in data[-5:]]  # [price_day5, ..., price_day1]
        API_CACHE[cache_key] = {"data": prices, "timestamp": time.time()}
        return prices
    except Exception as e:
        print(f"Error fetching BTC prices: {e}")
        return []        
        
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
    """Main function with optimized button responsiveness"""
    import psutil
    
    global current_mode, current_mode_index, config
    
    display.set_backlight(0.0)
    black_screen = Image.new('RGB', (width, height), (0, 0, 0))
    display.st7789.display(black_screen)
    for i in range(51):
        display.set_backlight(i / 50)
        time.sleep(0.02)
    display_boot_sequence(display)
    
    config = Config.load()
    last_frame = None
    
    try:
        while True:
            print(f"Current mode: {current_mode}, Memory: {psutil.virtual_memory().available / 1024 / 1024:.2f} MB")
            if current_mode == DisplayMode.CONFIG:
                button_pressed = check_buttons_config()
                current_frames = display_config_menu(display)
            elif current_mode == "time_setting":
                button_pressed = check_buttons_config()
                current_frames = display_time_setting(display)
            elif current_mode == "boot_gif":
                button_pressed = check_buttons_main()
                current_frames = [black_screen]
            else:
                button_pressed = check_buttons_main()
                if psutil.virtual_memory().available < 50 * 1024 * 1024:
                    print("Low memory, skipping complex modes")
                    current_frames = [create_error_image("Low Memory")]
                    current_mode = DisplayMode.PRICE_TICKER
                elif current_mode == DisplayMode.FEAR_GREED:
                    index_data, value = get_fear_greed_index()
                    set_mood_led(value)
                    current_frames = load_gif_frames(get_mood_gif(value), max_frames=20)
                elif current_mode == DisplayMode.PRICE_TICKER:
                    current_frames = display_price_ticker(display)
                elif current_mode == DisplayMode.MONEY_FLOW:
                    current_frames = display_money_flow(display)
                elif current_mode == DisplayMode.HISTORICAL_GRAPH:
                    current_frames = display_historical_graph(display)
                else:
                    current_frames = [create_error_image("Unknown Mode")]

            start_time = time.time()
            frame_index = 0
            while time.time() - start_time < config.display_time:
                # Check buttons first for immediate response
                if current_mode == DisplayMode.CONFIG or current_mode == "time_setting":
                    button_pressed = check_buttons_config()
                else:
                    button_pressed = check_buttons_main()
                
                # Display frame only if needed
                current_frame = current_frames[frame_index % len(current_frames)]
                if current_frame != last_frame or button_pressed:
                    display.st7789.display(current_frame)
                    last_frame = current_frame
                
                # Minimal sleep, skipped if button pressed
                if not button_pressed:
                    time.sleep(0.005)  # Reduced from 0.01 to 0.005
                else:
                    frame_index = 0  # Reset frame index on button press for instant mode switch
                frame_index += 1

            if current_mode in modes:
                next_mode_index = (current_mode_index + 1) % len(modes)
                current_mode = modes[next_mode_index]
                print(f"Transitioning to {current_mode}, Memory: {psutil.virtual_memory().available / 1024 / 1024:.2f} MB")
                if psutil.virtual_memory().available < 50 * 1024 * 1024:
                    current_frames = [create_error_image("Low Memory")]
                elif current_mode == DisplayMode.FEAR_GREED:
                    index_data, value = get_fear_greed_index()
                    current_frames = load_gif_frames(get_mood_gif(value), max_frames=20)
                elif current_mode == DisplayMode.PRICE_TICKER:
                    current_frames = display_price_ticker(display)
                elif current_mode == DisplayMode.MONEY_FLOW:
                    current_frames = display_money_flow(display)
                elif current_mode == DisplayMode.HISTORICAL_GRAPH:
                    current_frames = display_historical_graph(display)
                else:
                    current_frames = [create_error_image("Unknown Mode")]
                display.st7789.display(current_frames[0])

    except Exception as e:
        print(f"Error in main: {e}")
        display.set_led(1.0, 0.0, 0.0)
        time.sleep(5)
    finally:
        cleanup()
        
if __name__ == "__main__":
    main()
