import atexit
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

# Register cleanup function
def cleanup():
    display.set_led(0.0, 0.0, 0.0)  # Turn off LED
    print("Cleaned up GPIO resources")

atexit.register(cleanup)

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
        self.manual_time = False  # Add this flag
        self.time_offset = 0      # Add time offset in seconds

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
        display.set_led(0.0, 0.0, 0.0)
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
        display.set_led(1.0, 0.0, 0.0)  # Red for error
        return
    
    value = int(value)
    if value <= 25:  # Extreme fear - deep red
        display.set_led(1.0, 0.0, 0.0)
    elif value <= 45:  # Fear - orange
        display.set_led(1.0, 0.65, 0.0)
    elif value <= 55:  # Neutral - yellow
        display.set_led(1.0, 1.0, 0.0)
    elif value <= 75:  # Greed - light green
        display.set_led(0.0, 1.0, 0.0)
    else:  # Extreme greed - deep green
        display.set_led(0.0, 0.5, 0.0)

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

def check_time_sync():
    """Check if system time is synchronized"""
    try:
        # Check if timesyncd is running and synchronized
        result = subprocess.run(['timedatectl', 'status'], 
                              capture_output=True, text=True)
        return "System clock synchronized: yes" in result.stdout
    except:
        return False

def sync_time():
    """Force NTP time sync"""
    try:
        subprocess.run(['sudo', 'timedatectl', 'set-ntp', 'true'])
        # Wait for sync (max 10 seconds)
        for _ in range(10):
            if check_time_sync():
                return True
            time.sleep(1)
        return False
    except:
        return False

def check_ntp_sync():
    """Check if system time is synchronized via NTP"""
    try:
        # Check timesyncd status
        result = subprocess.run(['timedatectl', 'status'], 
                              capture_output=True, text=True)
        return "System clock synchronized: yes" in result.stdout
    except:
        return False

def force_ntp_sync():
    """Force NTP synchronization"""
    try:
        # Enable NTP sync
        subprocess.run(['sudo', 'timedatectl', 'set-ntp', 'true'])
        # Wait for sync (max 5 seconds)
        for _ in range(5):
            if check_ntp_sync():
                return True
            time.sleep(1)
        return False
    except:
        return False

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
        
        draw.text((width//2-50, height//2), "WELCOME", font=font, 
                 fill=(int(255*i/20), int(255*i/20), int(255*i/20)))
        
        frame = frame.rotate(180)
        display.st7789.display(frame)
        time.sleep(0.05)

    # WiFi check
    frame = background.copy()
    draw = ImageDraw.Draw(frame)
    draw.text((10, 10), "Checking WiFi...", font=small_font, fill=(255, 255, 255))
    frame = frame.rotate(180)
    display.st7789.display(frame)
    
    wifi_ok, ssid, signal = check_wifi()
    
    frame = background.copy()
    draw = ImageDraw.Draw(frame)
    if wifi_ok:
        draw.text((10, 10), f"WiFi: {ssid}", font=small_font, fill=(0, 255, 0))
        draw.text((10, 30), f"Signal: {signal}dBm", font=small_font, fill=(0, 255, 0))
        display.set_led(0.0, 1.0, 0.0)  # Green LED
    else:
        draw.text((10, 10), "WiFi: Not Connected", font=small_font, fill=(255, 0, 0))
        display.set_led(1.0, 0.0, 0.0)  # Red LED
    
    frame = frame.rotate(180)
    display.st7789.display(frame)
    time.sleep(1)

    # Time sync check
    draw.text((10, 50), "Checking Time Sync...", font=small_font, fill=(255, 255, 255))
    frame = frame.rotate(180)
    display.st7789.display(frame)

    time_ok = check_ntp_sync()
    if not time_ok:
        draw.text((10, 50), "Syncing Time...", font=small_font, fill=(255, 165, 0))
        frame = frame.rotate(180)
        display.st7789.display(frame)
        time_ok = force_ntp_sync()

    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    if time_ok:
        draw.text((10, 50), f"Time: {current_time}", font=small_font, fill=(0, 255, 0))
    else:
        draw.text((10, 50), "Time Sync Failed", font=small_font, fill=(255, 0, 0))
        draw.text((10, 70), f"Using: {current_time}", font=small_font, fill=(255, 165, 0))

    # API check
    draw.text((10, 70), "Checking API...", font=small_font, fill=(255, 255, 255))
    frame = frame.rotate(180)
    display.st7789.display(frame)
    
    api_ok, value = check_api_connection()
    
    if api_ok:
        draw.text((10, 90), f"API: Connected", font=small_font, fill=(0, 255, 0))
        draw.text((10, 110), f"Current Index: {value}", font=small_font, fill=(0, 255, 0))
    else:
        draw.text((10, 90), "API: Error", font=small_font, fill=(255, 0, 0))
    
    frame = frame.rotate(180)
    display.st7789.display(frame)
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
        display.st7789.display(frame)
        time.sleep(0.02)

def display_config_menu(disp):
    """Display configuration menu"""
    image = Image.new('RGB', (width, height), color=(0, 0, 0))
    draw = ImageDraw.Draw(image)
    
    config = Config.load()
    options = [
        f"Display Time: {config.display_time}s",
        f"Brightness: {config.brightness}%",
        f"Enabled Modes: {len(config.enabled_modes)}",
        "Set System Time",  # Add this option
        "Save & Exit"
    ]
    
    for i, option in enumerate(options):
        color = (0, 255, 0) if i == current_config_option else (255, 255, 255)
        draw.text((10, 10 + i*20), option, font=font, fill=color)
    
    return [image.rotate(180)]

def handle_config_buttons(pin):
    """Handle button presses in config mode"""
    global current_config_option, config, current_mode
    
    if pin == display.BUTTON_A:  # Up
        current_config_option = (current_config_option - 1) % 5
    elif pin == display.BUTTON_B:  # Down
        current_config_option = (current_config_option + 1) % 5
    elif pin == display.BUTTON_X:  # Modify
        if current_config_option == 0:
            config.display_time = (config.display_time % 30) + 5
        elif current_config_option == 1:
            config.brightness = (config.brightness + 10) % 110
            display.set_backlight(config.brightness / 100)
        elif current_config_option == 2:
            # Toggle modes
            pass
        elif current_config_option == 3:  # Set System Time
            global time_setting_option
            time_setting_option = 0
            current_mode = "time_setting"
        elif current_config_option == 4:  # Save & Exit
            config.save()
            current_mode = DisplayMode.FEAR_GREED
    elif pin == display.BUTTON_Y:  # Exit without saving
        current_mode = DisplayMode.FEAR_GREED

def set_system_time(timestamp):
    """Set system time manually"""
    try:
        # Format datetime for system
        time_str = timestamp.strftime('%Y-%m-%d %H:%M:%S')
        subprocess.run(['sudo', 'date', '-s', time_str])
        return True
    except:
        return False

def display_time_setting(disp):
    """Display time setting interface"""
    image = Image.new('RGB', (width, height), color=(0, 0, 0))
    draw = ImageDraw.Draw(image)
    
    current_time = datetime.now()
    if config.time_offset:
        current_time += timedelta(seconds=config.time_offset)
    
    options = [
        "Year:  " + str(current_time.year),
        "Month: " + str(current_time.month).zfill(2),
        "Day:   " + str(current_time.day).zfill(2),
        "Hour:  " + str(current_time.hour).zfill(2),
        "Min:   " + str(current_time.minute).zfill(2),
        "Set Time",
        "Back"
    ]
    
    for i, option in enumerate(options):
        color = (0, 255, 0) if i == time_setting_option else (255, 255, 255)
        draw.text((10, 10 + i*20), option, font=font, fill=color)
    
    # Show preview of new time
    draw.text((10, height-30), 
              f"New: {current_time.strftime('%Y-%m-%d %H:%M')}",
              font=font, fill=(255, 165, 0))
    
    return [image.rotate(180)]

def handle_time_setting(pin):
    """Handle button presses in time setting mode"""
    global time_setting_option, config
    
    if pin == display.BUTTON_A:  # Up
        time_setting_option = (time_setting_option - 1) % 7
    elif pin == display.BUTTON_B:  # Down
        time_setting_option = (time_setting_option + 1) % 7
    elif pin == display.BUTTON_X:  # Modify
        current_time = datetime.now() + timedelta(seconds=config.time_offset)
        
        if time_setting_option == 0:   # Year
            config.time_offset += timedelta(days=365).total_seconds()
        elif time_setting_option == 1: # Month
            config.time_offset += timedelta(days=30).total_seconds()
        elif time_setting_option == 2: # Day
            config.time_offset += timedelta(days=1).total_seconds()
        elif time_setting_option == 3: # Hour
            config.time_offset += timedelta(hours=1).total_seconds()
        elif time_setting_option == 4: # Minute
            config.time_offset += timedelta(minutes=1).total_seconds()
        elif time_setting_option == 5: # Set Time
            new_time = datetime.now() + timedelta(seconds=config.time_offset)
            if set_system_time(new_time):
                config.manual_time = True
                config.time_offset = 0
                return "config"  # Return to main config
        elif time_setting_option == 6: # Back
            config.time_offset = 0
            return "config"
    elif pin == display.BUTTON_Y:  # Decrease value
        current_time = datetime.now() + timedelta(seconds=config.time_offset)
        
        if time_setting_option == 0:   # Year
            config.time_offset -= timedelta(days=365).total_seconds()
        elif time_setting_option == 1: # Month
            config.time_offset -= timedelta(days=30).total_seconds()
        elif time_setting_option == 2: # Day
            config.time_offset -= timedelta(days=1).total_seconds()
        elif time_setting_option == 3: # Hour
            config.time_offset -= timedelta(hours=1).total_seconds()
        elif time_setting_option == 4: # Minute
            config.time_offset -= timedelta(minutes=1).total_seconds()

def main():
    """Main function with improved initialization and boot sequence"""
    try:
        # Initialize display
        display.set_backlight(0.0)  # Start with backlight off
        
        # Get display dimensions
        width = display.WIDTH
        height = display.HEIGHT
        
        # Clear display
        black_screen = Image.new('RGB', (width, height), color=(0, 0, 0))
        display.st7789.display(black_screen.rotate(180))
        
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
            display.set_led(0.0, 1.0, 0.0)  # Green LED
            time.sleep(0.1)
            display.set_led(0, 0, 0)    # Off
            time.sleep(0.1)
        
        # Load configuration
        config = Config.load()
        
        modes = [DisplayMode.FEAR_GREED, 
                 DisplayMode.PRICE_TICKER, 
                 DisplayMode.MONEY_FLOW,
                 DisplayMode.HISTORICAL_GRAPH]  # Add historical graph mode
        current_mode_index = 0
        transition_functions = [Transitions.slide_left, Transitions.fade, Transitions.slide_up]
        
        try:
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
                        display.st7789.display(frame)
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
                    display.set_led(1.0, 0.0, 0.0)  # Correct Red LED
                    time.sleep(5)
        finally:
            cleanup()
        
    except Exception as e:
        print(f"Initialization Error: {e}")
        display.set_led(1.0, 0.0, 0.0)  # Correct Red LED
        time.sleep(5)
        raise

if __name__ == "__main__":
    main()
