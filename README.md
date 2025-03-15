# Fear & Greed Index Display

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.7+](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![Raspberry Pi](https://img.shields.io/badge/Raspberry%20Pi-Compatible-green.svg)](https://www.raspberrypi.org/)
[![Bitcoin](https://img.shields.io/badge/Bitcoin-Fear%20%26%20Greed-orange.svg)](https://alternative.me/crypto/fear-and-greed-index/)
[![Python Application](https://github.com/yourusername/feargreed/actions/workflows/python-app.yml/badge.svg)](https://github.com/yourusername/feargreed/actions/workflows/python-app.yml)
[![codecov](https://codecov.io/gh/yourusername/feargreed/branch/main/graph/badge.svg)](https://codecov.io/gh/yourusername/feargreed)

A Raspberry Pi project that displays the current Bitcoin Fear & Greed Index on a ST7735 LCD display with animated GIFs representing different market sentiment levels.

## Requirements

- Raspberry Pi (Zero 2W)
- ST7735 LCD Display (Display Hat Mini)
- Python 3.7+
- Minimum 512MB RAM (1GB swap recommended)
- Memory monitoring (psutil)
- Required Python packages: `pip install -r requirements.txt`

## Setup

1. Connect the ST7735 display to your Raspberry Pi
2. This automates everything:
```bash
./setup.sh
```
✅ Installs system dependencies✅ Sets up the virtual environment✅ Installs Python dependencies
3. Install required packages:
   ```bash
   pip install requests pillow ST7735
   ```
4. Create the following GIF file structure in your project directory:

```
feargreed/
├── feargreeddisplay.py
├── config.json        # New: Persistent settings
├── README.md
└── gifs/
    ├── fear_greed/
    │   └── *_opt.gif  # Memory-optimized GIFs
    ├── money_flow/
    │   └── flow_*.gif # Market direction animations
    ├── animations/    
    │   └── bitcoinspin*_opt.gif # Boot animations
    └── error.gif      # Error state display
```

## Boot Sequence

1. Welcome Screen
   - 3D rotating text animation
   - Color transition effects
   - Interactive welcome message

2. System Check
   - Hardware initialization
   - Network interface check
   - WiFi connection status
   - Signal strength display

3. Exit Options
   - Press any button to continue
   - Displays random Bitcoin spin animation
   - Memory-optimized transition

## GIF Requirements

- Dimensions: 320x240 pixels
- Frame limit: Maximum 20 frames
- Optimized versions with '_opt' suffix
- Memory-efficient loading
- Cached frame storage

## GIF Processing

The project includes a GIF processor that monitors an incoming folder for new animations:

1. Install additional required package:
   ```bash
   pip install watchdog
   ```

2. Run the GIF processor:
   ```bash
   python gif_processor.py
   ```

3. Drop any animated GIF into the `gifs/incoming` folder
   
4. The processor will:
   - Split the GIF into individual frames
   - Save frames to a timestamped folder in `gifs/animations`
   - Move the original GIF to `gifs/incoming/processed`

5. Use the Display HAT Mini button to cycle through animations

## Button Controls

### Main Display
- Button A (GPIO 5): Enter config menu
- Button B (GPIO 6): Previous display mode
- Button X (GPIO 16): Toggle LED
- Button Y (GPIO 24): Next display mode

### Config Menu
- Button A: Move up
- Button B: Move down
- Button X: Increase value
- Button Y: Decrease value / Back

### Features
- 5ms debounce protection
- Memory-aware transitions
- Cached frame storage
- Button state logging

### Display Modes

1. **Fear & Greed Index**
   - Shows current sentiment (0-100)
   - Memory-optimized GIF animations
   - Auto-updates every 5 minutes
   - LED color matches sentiment
   - Frame limit: 20 frames per GIF

2. **Price Ticker**
   - Animated USD counter effect
   - Static GBP conversion (0.79 rate)
   - Current timestamp display
   - Smooth animation transitions

3. **Money Flow**
   - Market momentum visualization
   - Up/Down/Neutral states
   - Memory-efficient animations
   - Auto-direction based on 24h change

4. **Historical Graph**
   - 5-day BTC price history
   - Animated dot movement
   - Color-coded segments
   - Price range indicators
   - Auto-scaling display

## Memory Management

- Frame limit: 20 frames per GIF
- Auto memory monitoring
- Low memory detection (<50MB)
- Fallback to simple modes
- Cache cleanup on transition
- Memory usage logging

## Running the Display

```bash
python feargreeddisplay.py
```

The display will automatically update with the current Fear & Greed Index and show the corresponding animated GIF.

## API Setup & Usage

### Data Sources
- Fear & Greed Index: Alternative.me API
- Price Data: CoinGecko API v3
- Cache Duration: 5 minutes
- Automatic retry with fallback to cached data

### API Cache System
```python
API_CACHE = {
    'fear_greed': {'data': None, 'timestamp': 0},
    'coingecko': {'data': None, 'timestamp': 0},
    'btc_historical': {'data': None, 'timestamp': 0}
}
CACHE_DURATION = 300  # 5 minutes
```

### Error States
- Network Error: Shows error.gif with LED flash
- Rate Limit: Uses cached data
- Low Memory: Falls back to simple display
- API Timeout: 5 second limit

## Configuration System

### config.json Settings
```json
{
    "display_time": 10,
    "brightness": 1.0,
    "led_brightness": 0.5,
    "led_enabled": true,
    "enabled_modes": ["fear_greed", "price_ticker", "money_flow"],
    "manual_time": false,
    "time_offset": 0
}
```

### Performance Settings
- Frame Limit: 20 frames per GIF
- Button Debounce: 5ms
- Memory Threshold: 50MB
- Cache Cleanup: Auto

## Display Settings

### Screen Configuration
- Resolution: 320x240 pixels
- PWM Backlight: 0.0-1.0
- Rotation: 0 degrees
- Default Theme: Dark

### Font System
```python
FONT_PATHS = {
    'regular': "DejaVuSans.ttf",
    'bold': "DejaVuSans-Bold.ttf",
    'mono': "DejaVuSansMono.ttf"
}

FONT_SIZES = {
    'large': 26,
    'medium': 20,
    'small': 16,
    'tiny': 12
}
```

## Troubleshooting

### Memory Issues
- Monitor usage: Check psutil stats
- Clear cache: Remove .pyc files
- Increase swap: Follow swap setup
- Limit frames: Max 20 per GIF

### Display Problems
- Black screen: Check backlight PWM
- No animations: Verify frame limits
- LED off: Check config.json
- Slow response: Monitor CPU usage

## Data Source

Fear & Greed Index data is fetched from Alternative.me API: https://alternative.me/crypto/fear-and-greed-index/

### Example API Response
```json
{
    "name": "Fear and Greed Index",
    "data": [
        {
            "value": "25",
            "value_classification": "extreme fear",
            "timestamp": "1648790400",
            "time_until_update": "3600"
        }
    ],
    "metadata": {
        "error": null
    }
}
```

### Error Handling
- The display shows `error.gif` if:
  - API is unreachable
  - Rate limit exceeded
  - Invalid response received
- Retries after 60 seconds
- Logs errors to `error.log`

### Configuration
You can adjust API settings in `config.py`:
```python
API_URL = "https://api.alternative.me/fng/"
UPDATE_INTERVAL = 300  # Update every 5 minutes
MAX_RETRIES = 3       # Number of retry attempts
```

### Local Development
For testing without API calls, use the `--mock` flag:
```bash
python feargreeddisplay.py --mock
```

# Contributing to Fear & Greed Index Display

## Getting Started
1. Fork the repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## Development Setup
[To come: development environment setup instructions]

## Testing

### Setting Up Tests

1. Install test requirements:
   ```bash
   pip install pytest pytest-cov
   ```

### Running Tests

You can run tests in several ways:

#### 1. Using Visual Studio Code (Recommended for Development)
1. Open the project in VS Code
2. Install the Python extension if not already installed
3. Click the beaker icon in the left sidebar or press `Ctrl+Shift+P` and type "Python: Configure Tests"
4. Select "pytest" as your test framework
5. Click the play button next to any test to run it
6. Use the Test Explorer to see all tests organized by file

#### 2. Running on Raspberry Pi Directly
If you're working directly on the Pi:
```bash
# Open terminal on Pi
cd ~/feargreed
pytest -v
```

#### 3. Running via SSH
If you're connecting to Pi remotely:
```bash
# From your development machine
ssh pi@raspberrypi
cd ~/feargreed
pytest -v
```

### Available Test Commands

Run all tests with verbose output:
```bash
pytest -v
```

Run a specific test file:
```bash
pytest -v tests/test_general.py
```

Run the display capability demo test:
```bash
pytest -v tests/test_general.py -k test_display_capabilities
```

View test coverage report:
```bash
pytest --cov=. --cov-report=term-missing
```

### What the Tests Check

1. **Basic Tests** (`test_general.py`)
   - Fear & Greed index range validation
   - Display initialization checks
   - Folder structure verification
   - Display capabilities demo (shows rainbow animation)

2. **Display Tests**
   - Verifies 160x128 resolution
   - Tests color rendering
   - Checks animation performance
   - Validates button inputs

### Automated Testing
This project uses GitHub Actions to automatically run tests when you push code.
You can view test results:
1. Go to your repository on GitHub
2. Click the "Actions" tab
3. Look for the latest workflow run

### Test Coverage
View test coverage report:
```bash
pytest --cov=. --cov-report=term-missing
```
### Available Tests

1. **Basic Tests** (`test_general.py`)
   - Fear & Greed index range validation
   - Display initialization checks
   - Folder structure verification
   - Display capabilities demo

2. **Display Tests**
   - Resolution verification (160x128)
   - Color rendering tests
   - Animation performance checks
   - Button input validation

### Test Requirements
- pytest: `pip install pytest`
- pytest-cov: `pip install pytest-cov`
- Test files location: `tests/` directory

### Continuous Integration
This project uses GitHub Actions for automated testing. Every push and pull request triggers:
- Code style checks (flake8)
- Unit tests (pytest)
- Coverage reporting (codecov)

View the latest test results in the [Actions tab](https://github.com/DanDon01/feargreed/actions) of the repository.

## Code Style
Follow PEP 8 guidelines

## Quick Start Guide

1. Download project:
   ```bash
   git clone https://github.com/DanDon01/feargreed.git
   cd feargreed
   ```

2. Install everything needed:
  ```bash
  pip install -r requirements.txt
  ```
3. Connect your Display HAT Mini (with pictures showing correct orientation)

4. Run the display:
   ```bash
   python feargreeddisplay.py
   ```

## Common Problems & Solutions

1. "Display shows nothing"

- Check power connection
- Verify display orientation
- Run sudo raspi-config and enable SPI
- Run test_display_capabilities

2.  "GIFs don't animate"

- Verify GIF dimensions (160x128)
- Check frames are numbered correctly
- Make sure GIFs are in correct folders
- Run test_general

3. API Error Handling
- The display shows `error.gif` if:
- API is unreachable
- Rate limit exceeded
- Invalid response received
- Retries after 60 seconds
- Logs errors to `error.log`

## Display Modes

### 1. Fear & Greed Index
- Shows current market sentiment (0-100)
- Updates every 5 minutes
- Displays corresponding animated GIF

### 2. Historical Graph
- Real-time Fear & Greed trend visualization
- Last 100 data points plotted
- Color zones:
  - Red: Extreme Fear (<25)
  - Yellow: Fear (26-45)
  - White: Neutral (46-55)
  - Light Green: Greed (56-75)
  - Dark Green: Extreme Greed (>75)
- Features:
  - Auto-scaling display
  - Current value indicator
  - Trend line visualization
  - Zone highlighting
  - Dark theme optimized for LCD

### 3. Price Ticker
- Current BTC price
- 24h change percentage
- Directional indicators

### 4. Money Flow
- Market momentum visualization
- Buy/Sell pressure indicators
- Volume analysis

## Display Controls

### Button Functions
- A (GPIO 5): Cycle display modes
- B (GPIO 6): Toggle historical view (1D/7D/30D)
- X (GPIO 16): Adjust brightness
- Y (GPIO 24): Toggle backlight

### Display Settings
```python
# Adjust in config.py
GRAPH_UPDATE_INTERVAL = 300  # 5 minutes
DISPLAY_ROTATION = 0        # 0/90/180/270 degrees
BRIGHTNESS = 100            # 0-100%
COLOR_THEME = "dark"        # dark/light
```

### Graph Customization
- Resolution: 160x128 pixels
- Update frequency: Every 5 minutes
- Historical data: 100 points
- Visualization options:
  - Line graph
  - Candlestick view
  - Heat map mode

## Troubleshooting Python Package Installation on Raspberry Pi Zero 2 W

### Common Installation Issue: `` Hanging or Failing

Error Message: When running:
```bash
pip install -r requirements.txt
```

- You may encounter an issue where contourpy hangs for a long time at:
```bash
Installing backend dependencies ... done
Preparing metadata (pyproject.toml) ... /
```
- Or it fails with an error similar to:
```bash
ERROR: Python dependency not found
../src/meson.build:5:10: ERROR: Python dependency not found
```
## Why This Happens:

 1. Low RAM (512MB) – The Pi Zero 2 W doesn’t have enough memory to compile large packages.

 2. Missing system dependencies – Some Python packages require additional libraries like python3-dev and meson.

 3. Pip tries to build from source – Some versions of contourpy don’t have prebuilt wheels for ARM, causing slow compilation.

## 🚀 Fix: Increase Swap Memory to Prevent Crashes

### Since the Pi Zero 2 W has limited RAM, increasing swap space helps prevent system freezes.

1️⃣ Enable a 1GB Swap File

Run these commands:
```bash
sudo fallocate -l 1G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```
Verify swap is active:
```bash
free -h
```
Expected output:
```bash
            total        used        free      shared  buff/cache   available
Mem:         480Mi       300Mi        50Mi        20Mi       130Mi       180Mi
Swap:        1.5Gi       0.0Gi       1.0Gi
```
2️⃣ Make Swap Permanent (Optional, but Recommended)

If you want swap to persist after reboot, run:
```bash 
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```
This ensures swap is enabled on startup.

## Install System Requirements (if errors with requirements installing)
```bash
xargs sudo apt install -y < requirements-system.txt
```

## Time Synchronization

The Raspberry Pi Zero 2 W doesn't have a real-time clock. Time is synchronized via NTP when connected to the internet.

### Automatic Time Sync
- Time syncs automatically when WiFi is connected
- Uses Network Time Protocol (NTP)
- Updates every few minutes
- No configuration needed

### Manual Time Setting
Access the manual time setting through the configuration menu:
1. Press Button Y to enter config mode
2. Select "Set System Time"
3. Use buttons to adjust:
   - Button A: Move up
   - Button B: Move down
   - Button X: Increase value
   - Button Y: Decrease value
4. Available settings:
   - Year
   - Month
   - Day
   - Hour
   - Minute
5. Select "Set Time" to apply changes
6. Select "Back" to cancel

### Optional: Add RTC Module
For offline time keeping, you can add an RTC module:

1. Install I2C RTC module (e.g., DS3231)
2. Enable I2C:
   ```bash
   sudo raspi-config
   # Interface Options -> I2C -> Enable
   ```
3. Install required packages:
   ```bash
   sudo apt-get update
   sudo apt-get install i2c-tools python3-smbus
   ```
4. Add to /boot/config.txt:
   ```
   dtoverlay=i2c-rtc,ds3231
   ```
5. Reboot:
   ```bash
   sudo reboot
   ```

## LED Controls & Configuration

### LED Brightness
The onboard RGB LED brightness can be configured:
1. Press Button Y to enter config mode
2. Select "LED Bright" option
3. Use buttons to adjust:
   - Button X: Increase brightness (0-100%)
   - Button Y: Decrease brightness (0-100%)
4. LED brightness settings persist after reboot

### LED Color Mapping
The RGB LED indicates market sentiment:
- Extreme Fear (0-25): Deep Red
- Fear (26-45): Orange
- Neutral (46-55): Yellow
- Greed (56-75): Light Green
- Extreme Greed (76-100): Deep Green
- Error State: Flashing Red

### LED Settings in Config
```python
# In config.py
LED_ENABLED = True     # Toggle LED on/off
LED_BRIGHTNESS = 0.5   # Default brightness (0.0-1.0)
```

### LED Controls in Menu
The config menu allows you to:
- Adjust LED brightness
- Toggle LED on/off
- Save preferences
- Test different brightness levels

### Power Saving
- LED can be disabled completely
- Brightness can be set very low
- Settings persist through reboots

## Need Help?
Create an issue on GitHub
Check https://thepihut.com/products/display-hat-mini
Check https://thepihut.com/products/raspberry-pi-zero-2


