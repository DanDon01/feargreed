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
display = DisplayHATMini()
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

def main():
    display.on()
    display.set_backlight(1.0)
    
    # Setup button handlers
    for button in [display.BUTTON_A, display.BUTTON_B, display.BUTTON_X, display.BUTTON_Y]:
        display.on_button_pressed(button, handle_button)

    config = Config.load()
    
    modes = [DisplayMode.FEAR_GREED, 
             DisplayMode.PRICE_TICKER, 
             DisplayMode.MONEY_FLOW,
             DisplayMode.HISTORICAL_GRAPH]  # Add historical graph mode
    current_mode_index = 0
    transition_functions = [Transitions.slide_left, Transitions.fade, Transitions.slide_up]
    
    while True:
        try:
            if current_mode == DisplayMode.CONFIG:
                # Handle configuration menu
                display_config_menu(display, config)
                continue
                
            current_mode = modes[current_mode_index]
            next_mode_index = (current_mode_index + 1) % len(modes)
            
            # Get current content
            if current_mode == DisplayMode.FEAR_GREED:
                index_data = get_fear_greed_index()
                value = int(index_data.split()[2].split('\n')[0])
                set_mood_led(value)  # Update LED color
                current_frames = load_gif_frames(get_mood_gif(value))
            elif current_mode == DisplayMode.PRICE_TICKER:
                current_frames = [display_price_ticker(display)]
            elif current_mode == DisplayMode.HISTORICAL_GRAPH:
                current_frames = display_historical_graph(display)
            else:  # MONEY_FLOW
                current_frames = display_money_flow(display)
            
            # Display current content for a while
            start_time = time.time()
            frame_index = 0
            while time.time() - start_time < 10:  # Show each mode for 10 seconds
                frame = current_frames[frame_index % len(current_frames)]
                display.display(frame)
                time.sleep(0.1)
                frame_index += 1
            
            # Prepare next content
            if modes[next_mode_index] == DisplayMode.FEAR_GREED:
                index_data = get_fear_greed_index()
                value = int(index_data.split()[2].split('\n')[0])
                next_frames = load_gif_frames(get_mood_gif(value))
            elif modes[next_mode_index] == DisplayMode.PRICE_TICKER:
                next_frames = [display_price_ticker(display)]
            elif modes[next_mode_index] == DisplayMode.HISTORICAL_GRAPH:
                next_frames = display_historical_graph(display)
            else:  # MONEY_FLOW
                next_frames = display_money_flow(display)
            
            # Transition to next content
            transition_func = np.random.choice(transition_functions)
            for transition_frame in transition_func(
                current_frames[0], next_frames[0]
            ):
                display.display(transition_frame)
                time.sleep(0.05)
            
            current_mode_index = next_mode_index
            
        except Exception as e:
            print(f"Error: {e}")
            display.set_led(255, 0, 0)  # Red LED for errors
            time.sleep(5)

if __name__ == "__main__":
    main()