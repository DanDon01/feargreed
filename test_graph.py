import time
from PIL import Image, ImageDraw, ImageFont # Ensure Pillow is installed
import numpy as np # Ensure NumPy is installed
import sys

# --- Mock RPi.GPIO ---
class MockGPIO:
    BCM = "BCM"
    OUT = "OUT"
    IN = "IN"
    PUD_UP = "PUD_UP"
    LOW = 0
    HIGH = 1
    def setmode(self, mode): pass
    def setwarnings(self, flag): pass
    def setup(self, channel, mode, pull_up_down=None): pass
    def output(self, channel, state): pass
    def input(self, channel): return self.LOW
    def cleanup(self): pass

sys.modules['RPi'] = type('RPi', (), {'GPIO': MockGPIO()})
sys.modules['RPi.GPIO'] = MockGPIO()

# --- Mock displayhatmini ---
class MockST7789:
    def display(self, image):
        # print(f"MockST7789.display called with image of size {image.size}")
        pass

class MockDisplayHATMini:
    def __init__(self, buffer, backlight_pwm=True):
        self.buffer = buffer
        self.backlight_pwm = backlight_pwm
        self.st7789 = MockST7789()
    def set_led(self, r, g, b): pass
    def set_backlight(self, value): pass
    def read_button(self, button_pin): return False
    BUTTON_A, BUTTON_B, BUTTON_X, BUTTON_Y = "A", "B", "X", "Y"

sys.modules['displayhatmini'] = type('displayhatmini', (), {'DisplayHATMini': MockDisplayHATMini})


# --- Now import from feargreeddisplay ---
# Temporarily add /app to sys.path if feargreeddisplay is not discoverable
# sys.path.insert(0, '/app') 
# No, this is not needed if the tool runs from /app context

from feargreeddisplay import (
    display_historical_graph,
    FONTS, # Relies on load_fonts() which relies on FONT_PATHS, FONT_SIZES
    FONT_PATHS, FONT_SIZES, # Need to define these for load_fonts to work
    load_fonts, # Need to call this to populate FONTS
    create_error_image,
    get_historical_fear_greed, # This function makes API calls
    width, height, # Globals from feargreeddisplay
    API_CACHE # get_historical_fear_greed uses this
)
# Note: calculate_sma and get_y_coord are local to display_historical_graph

# --- Test Script Setup ---
print("INFO: Test script starting.")

# Define necessary globals that are expected by imported functions
# FONT_PATHS and FONT_SIZES are imported, so FONTS can be loaded
if not FONTS['regular_tiny']: # Check if fonts were loaded (they are by default in feargreeddisplay)
    print("INFO: Manually loading fonts for test script.")
    # This is tricky because load_fonts() is already called in feargreeddisplay.py
    # We might need to re-initialize or ensure it's properly populated.
    # For simplicity, assume FONTS is populated when feargreeddisplay is imported.
    # If not, we'd redefine load_fonts here or ensure paths are correct.
    # Let's verify if FONTS has been populated
    if not FONTS.get('regular_small') or not FONTS.get('mono_medium'):
         print("ERROR: Fonts not loaded correctly from feargreeddisplay.py. Attempting to load manually.")
         # Redefine necessary globals for load_fonts, if they weren't set by importing feargreeddisplay
         FONT_PATHS = FONT_PATHS if 'FONT_PATHS' in globals() else {
            'regular': "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            'bold': "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            'mono': "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
         }
         FONT_SIZES = FONT_SIZES if 'FONT_SIZES' in globals() else {
            'large': 26, 'medium': 20, 'small': 16, 'tiny': 12
         }
         FONTS.update(load_fonts()) # Populate FONTS dict

# Mock the API call within get_historical_fear_greed to return predictable data
def mock_get_historical_fear_greed():
    print("INFO: Using mock_get_historical_fear_greed()")
    # Return 30 data points: (value, timestamp_str)
    # Values from 0 to 96 in steps of approx 3.3, then a few more
    mock_data = []
    for i in range(30):
        val = min(100, int(i * 3.33))
        # Timestamp can be simple strings for this test, as only value is used by graph
        mock_data.append((val, f"2023-10-{30-i:02d}")) 
    # API returns newest first, graph function reverses it. So provide newest first.
    return mock_data[::-1] # Ensure it's newest first, as per original API

# Replace the real get_historical_fear_greed with our mock
original_get_historical_fear_greed = get_historical_fear_greed
sys.modules['feargreeddisplay'].get_historical_fear_greed = mock_get_historical_fear_greed

# Create a mock display object
mock_buffer = Image.new("RGB", (width, height))
mock_disp = MockDisplayHATMini(mock_buffer)

print("INFO: Calling display_historical_graph with mock display and data...")
frames = []
try:
    frames = display_historical_graph(mock_disp)
except Exception as e:
    print(f"ERROR: Exception during display_historical_graph: {e}")
    import traceback
    traceback.print_exc()

if frames:
    print(f"INFO: display_historical_graph generated {len(frames)} frames.")
    # You could save frames here for visual inspection if desired, e.g., frames[0].save("frame_0.png")
    for i, frame in enumerate(frames):
        if i < 5: # Limit printing for brevity
            print(f"  Simulating display of frame {i+1} (size: {frame.size}, mode: {frame.mode})")
        # frame.save(f"test_frame_{i}.png") # Optional: save frames
    if len(frames) > 5:
        print(f"  ... (skipped displaying info for remaining {len(frames)-5} frames)")
else:
    print("WARNING: display_historical_graph returned no frames.")

# Restore original function if necessary (though test is ending)
sys.modules['feargreeddisplay'].get_historical_fear_greed = original_get_historical_fear_greed

print("INFO: Test script finished.")

# To run this: python test_graph.py
# Ensure feargreeddisplay.py is in the same directory or Python path.
# Ensure Pillow and NumPy are installed: pip install Pillow numpy
