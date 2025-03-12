import time
import requests
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import numpy as np
import qrcode
from datetime import datetime, timedelta
from displayhatmini import DisplayHATMini
from displayhatmini import ST7789
import colorzero  # For RGB LED colors
import matplotlib.pyplot as plt
from io import BytesIO
import wifi
import subprocess

def load_gif_frames(gif_path):
    """Load a GIF and convert frames to format suitable for display"""
    with Image.open(gif_path) as gif:
        frames = []
        try:
            while True:
                frame = gif.copy()
                if frame.size != (width, height):
                    frame = frame.resize((width, height))
                frames.append(frame)
                gif.seek(gif.tell() + 1)
        except EOFError:
            pass
    return frames

def get_mood_gif(value):
    """Return appropriate gif path based on fear/greed value"""
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
    try:
        url = "https://api.alternative.me/fng/"
        response = requests.get(url)
        data = response.json()
        value = data['data'][0]['value']
        classification = data['data'][0]['value_classification']
        return f"Fear & Greed: {value}\n{classification}"
    except:
        return "Error fetching data"

# Initialize the display
width, height = 320, 240
buffer = Image.new("RGB", (width, height))
display = DisplayHATMini(None)  # Use None if buffer isn't needed

width = display.WIDTH
height = display.HEIGHT



# display = ST7789()
# display.set_backlight(1.0)
# width = LCD_WIDTH
# height = LCD_HEIGHT

# Create a blank image for drawing
image = Image.new('RGB', (width, height), color=(0, 0, 0))

# Get drawing object to draw on image
draw = ImageDraw.Draw(image)

# Load a font
font = ImageFont.load_default()

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
        self.display_time = 10  # seconds per mode
        self.brightness = 100   # 0-100
        self.enabled_modes = [DisplayMode.FEAR_GREED, DisplayMode.PRICE_TICKER, 
                            DisplayMode.MONEY_FLOW]
        self.donation_address = "YOUR_BTC_ADDRESS"

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
            blended = Image.fromarray(
                (old_array * (1 - alpha) + new_array * alpha).astype(np.uint8)
            )
            yield blended

    @staticmethod
    def slide_up(old_frame, new_frame, steps=20):
        for i in range(steps + 1):
            offset = int((height * (steps - i)) / steps)
            combined = Image.new('RGB', (width, height))
            combined.paste(old_frame, (0, -offset))
            combined.paste(new_frame, (0, height - offset))
            yield combined

def get_btc_price():
    try:
        response = requests.get("https://api.coindesk.com/v1/bpi/currentprice.json")
        data = response.json()
        price = data["bpi"]["USD"]["rate_float"]
        return f"BTC: ${price:,.2f}"
    except:
        return "Price Error"

def display_price_ticker(disp):
    text_image = Image.new('RGB', (width, height), color=(0, 0, 0))
    draw = ImageDraw.Draw(text_image)
    price = get_btc_price()
    change = get_price_change()
    draw.text((10, height//2), price, font=font, fill=(255, 215, 0))
    color = (0, 255, 0) if change.startswith('+') else (255, 0, 0)
    draw.text((10, height//2 + 20), change, font=font, fill=color)
    return text_image

def display_money_flow(disp):
    frames = load_gif_frames(f"gifs/money_flow/flow_{get_market_direction()}.gif")
    return frames

def get_market_direction():
    try:
        # Simple 24h price change check
        response = requests.get("https://api.coindesk.com/v1/bpi/currentprice.json")
        data = response.json()
        current = data["bpi"]["USD"]["rate_float"]
        yesterday = requests.get("https://api.coindesk.com/v1/bpi/historical/close.json?for=yesterday").json()
        yesterday_price = float(list(yesterday["bpi"].values())[0])
        return "up" if current > yesterday_price else "down"
    except:
        return "neutral"

def handle_button(pin):
    """Handle button presses"""
    global current_mode_index
    if pin == display.BUTTON_A:
        current_mode_index = (current_mode_index + 1) % len(modes)
    elif pin == display.BUTTON_B:
        current_mode_index = (current_mode_index - 1) % len(modes)
    elif pin == display.BUTTON_X:
        # Toggle LED on/off
        display.set_led(0, 0, 0)
    elif pin == display.BUTTON_Y:
        # Enter config mode
        global current_mode
        current_mode = DisplayMode.CONFIG

def display_volume_chart(disp):
    try:
        response = requests.get("https://api.coingecko.com/api/v3/simple/price",
                              params={"ids": "bitcoin", 
                                     "vs_currencies": "usd",
                                     "include_24hr_vol": "true"})
        data = response.json()
        volume = data['bitcoin']['usd_24h_vol']
        
        image = Image.new('RGB', (width, height), color=(0, 0, 0))
        draw = ImageDraw.Draw(image)
        
        # Draw volume bars
        draw.text((5, 5), f"24h Vol: ${volume/1e9:.1f}B", font=font, fill=(255, 255, 255))
        
        return [image]
    except:
        return [create_error_image()]

def display_qr_code(disp, address):
    qr = qrcode.QRCode(version=1, box_size=2, border=2)
    qr.add_data(address)
    qr.make(fit=True)
    qr_image = qr.make_image(fill_color="white", back_color="black")
    qr_image = qr_image.resize((width, height))
    return [qr_image]

def create_error_image():
    image = Image.new('RGB', (width, height), color=(0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.text((10, height//2), "Error", font=font, fill=(255, 0, 0))
    return image

def get_price_change():
    try:
        response = requests.get("https://api.coingecko.com/api/v3/simple/price",
                              params={"ids": "bitcoin", 
                                     "vs_currencies": "usd",
                                     "include_24hr_change": "true"})
        data = response.json()
        change = data['bitcoin']['usd_24h_change']
        return f"{change:+.2f}%"
    except:
        return "N/A"

def set_mood_led(value):
    """Set RGB LED color based on fear/greed value"""
    if value is None:
        display.set_led(255, 0, 0)  # Red for error
        return
    
    value = int(value)
    if value <= 25:  # Extreme fear - deep red
        display.set_led(255, 0, 0)
    elif value <= 45:  # Fear - orange
        display.set_led(255, 165, 0)
    elif value <= 55:  # Neutral - yellow
        display.set_led(255, 255, 0)
    elif value <= 75:  # Greed - light green
        display.set_led(0, 255, 0)
    else:  # Extreme greed - deep green
        display.set_led(0, 128, 0)

def get_historical_fear_greed():
    """Fetch historical Fear & Greed data"""
    try:
        url = "https://api.alternative.me/fng/?limit=100"
        response = requests.get(url)
        data = response.json()
        values = [(int(entry['value']), 
                  datetime.fromtimestamp(int(entry['timestamp']))) 
                  for entry in data['data']]
        return values
    except:
        return None

def display_historical_graph(disp):
    """Create and display historical Fear & Greed graph"""
    values = get_historical_fear_greed()
    if not values:
        return [create_error_image()]

    # Create figure with transparent background
    plt.figure(figsize=(1.6, 1.28), dpi=100)
    plt.style.use('dark_background')
    
    # Unpack data
    fear_greed_values, dates = zip(*values)
    
    # Create line plot
    plt.plot(dates, fear_greed_values, color='white', linewidth=1)
    
    # Add horizontal lines for fear/greed zones
    plt.axhline(y=25, color='red', linestyle='--', alpha=0.3)    # Extreme Fear
    plt.axhline(y=75, color='green', linestyle='--', alpha=0.3)  # Extreme Greed
    
    # Customize appearance
    plt.fill_between(dates, fear_greed_values, 
                    where=[v <= 25 for v in fear_greed_values], 
                    color='red', alpha=0.2)
    plt.fill_between(dates, fear_greed_values, 
                    where=[v >= 75 for v in fear_greed_values], 
                    color='green', alpha=0.2)
    
    # Remove axes labels and ticks
    plt.xticks([])
    plt.yticks([0, 25, 50, 75, 100])
    
    # Add current value
    current_value = fear_greed_values[0]
    plt.text(0.02, 0.95, f"Current: {current_value}", 
             transform=plt.gca().transAxes, 
             color='white', fontsize=8)
    
    # Convert to image
    buf = BytesIO()
    plt.savefig(buf, format='png', 
                bbox_inches='tight', 
                transparent=True)
    plt.close()
    
    # Convert to PIL Image
    buf.seek(0)
    graph_image = Image.open(buf)
    graph_image = graph_image.resize((width, height))
    
    return [graph_image]

def check_wifi():
    """Check WiFi connection and get details"""
    try:
        # Get WiFi info using iwconfig
        result = subprocess.run(['iwgetid', '-r'], capture_output=True, text=True)
        ssid = result.stdout.strip()
        
        # Get signal strength
        strength = subprocess.run(['iwconfig', 'wlan0'], capture_output=True, text=True)
        signal = [line for line in strength.stdout.split('\n') if 'Signal level' in line]
        signal_strength = signal[0].split('=')[1].split(' ')[0] if signal else 'N/A'
        
        return True, ssid, signal_strength
    except:
        return False, None, None

def check_api_connection():
    """Test API connection and response"""
    try:
        response = requests.get("https://api.alternative.me/fng/", timeout=5)
        if response.status_code == 200:
            data = response.json()
            current_value = data['data'][0]['value']
            return True, current_value
        return False, None
    except:
        return False, None

def display_boot_sequence(display):
    """Display an animated boot sequence with real checks"""
    width = display.WIDTH
    height = display.HEIGHT
    
    # Create a black background
    background = Image.new('RGB', (width, height), color=(0, 0, 0))
    draw = ImageDraw.Draw(background)
    
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20)
        small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
    except:
        font = ImageFont.load_default()
        small_font = ImageFont.load_default()

    # Initial display test
    for i in range(20):
        frame = background.copy()
        draw = ImageDraw.Draw(frame)
        
        draw.text((width//2-50, height//2), "DISPLAY TEST", font=font, 
                 fill=(int(255*i/20), int(255*i/20), int(255*i/20)))
        
        frame = frame.rotate(180)
        display.display(frame)
        time.sleep(0.05)

    # WiFi check
    frame = background.copy()
    draw = ImageDraw.Draw(frame)
    draw.text((10, 10), "Checking WiFi...", font=small_font, fill=(255, 255, 255))
    frame = frame.rotate(180)
    display.display(frame)
    
    wifi_ok, ssid, signal = check_wifi()
    
    frame = background.copy()
    draw = ImageDraw.Draw(frame)
    if wifi_ok:
        draw.text((10, 10), f"WiFi: {ssid}", font=small_font, fill=(0, 255, 0))
        draw.text((10, 30), f"Signal: {signal}dBm", font=small_font, fill=(0, 255, 0))
        display.set_led(0, 255, 0)  # Green LED
    else:
        draw.text((10, 10), "WiFi: Not Connected", font=small_font, fill=(255, 0, 0))
        display.set_led(255, 0, 0)  # Red LED
    
    frame = frame.rotate(180)
    display.display(frame)
    time.sleep(1)

    # API check
    draw.text((10, 50), "Checking API...", font=small_font, fill=(255, 255, 255))
    frame = frame.rotate(180)
    display.display(frame)
    
    api_ok, value = check_api_connection()
    
    if api_ok:
        draw.text((10, 70), f"API: Connected", font=small_font, fill=(0, 255, 0))
        draw.text((10, 90), f"Current Index: {value}", font=small_font, fill=(0, 255, 0))
    else:
        draw.text((10, 70), "API: Error", font=small_font, fill=(255, 0, 0))
    
    frame = frame.rotate(180)
    display.display(frame)
    time.sleep(1)

    # Final boot animation
    for i in range(101):
        frame = background.copy()
        draw = ImageDraw.Draw(frame)
        
        # Progress bar
        bar_width = int((width - 40) * (i / 100))
        draw.rectangle([20, height-30, width-20, height-10], outline=(0, 255, 0))
        draw.rectangle([20, height-30, 20+bar_width, height-10], fill=(0, 255, 0))
        
        # Status info
        if wifi_ok:
            draw.text((10, 10), f"WiFi: {ssid}", font=small_font, fill=(0, 255, 0))
            draw.text((10, 30), f"Signal: {signal}dBm", font=small_font, fill=(0, 255, 0))
        else:
            draw.text((10, 10), "WiFi: Not Connected", font=small_font, fill=(255, 0, 0))
        
        if api_ok:
            draw.text((10, 70), f"API: Connected", font=small_font, fill=(0, 255, 0))
            draw.text((10, 90), f"Current Index: {value}", font=small_font, fill=(0, 255, 0))
        else:
            draw.text((10, 70), "API: Error", font=small_font, fill=(255, 0, 0))
        
        # Loading text
        draw.text((width//2-50, height//2-40), "FEAR & GREED", font=font, fill=(255, 165, 0))
        draw.text((width//2-30, height-50), f"Starting... {i}%", font=small_font, fill=(255, 255, 255))
        
        frame = frame.rotate(180)
        display.display(frame)
        time.sleep(0.02)

def main():
    """Main function with improved initialization and boot sequence"""
    try:
        # Initialize display
        display = DisplayHATMini(None)
        display.set_backlight(0.0)  # Start with backlight off
        
        # Get display dimensions
        width = display.WIDTH
        height = display.HEIGHT
        
        # Clear display
        black_screen = Image.new('RGB', (width, height), color=(0, 0, 0))
        display.display(black_screen.rotate(180))
        
        # Fade in backlight
        for i in range(101):
            display.set_backlight(i/100)
            time.sleep(0.01)
        
        # Show boot sequence
        display_boot_sequence(display)
        
        # Setup button handlers
        display.on_button_pressed(display.BUTTON_A, lambda pin: handle_button(pin))
        display.on_button_pressed(display.BUTTON_B, lambda pin: handle_button(pin))
        display.on_button_pressed(display.BUTTON_X, lambda pin: handle_button(pin))
        display.on_button_pressed(display.BUTTON_Y, lambda pin: handle_button(pin))
        
        # Flash LED to show ready
        for _ in range(3):
            display.set_led(0, 255, 0)  # Green
            time.sleep(0.1)
            display.set_led(0, 0, 0)    # Off
            time.sleep(0.1)
        
        # ...rest of your existing main() code...
        
    except Exception as e:
        print(f"Initialization Error: {e}")
        if 'display' in locals():
            display.set_led(255, 0, 0)  # Red LED for errors
        time.sleep(5)
        raise

if __name__ == "__main__":
    main()