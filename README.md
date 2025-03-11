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
- Python 3.x
- Required Python packages: `pip install -r requirements.txt`

## Setup

1. Connect the ST7735 display to your Raspberry Pi
2. Install required packages:
   ```bash
   pip install requests pillow ST7735
   ```
3. Create the following GIF file structure in your project directory:

```
feargreed/
├── feargreeddisplay.py
├── README.md
├── pytest.ini
├── PiHatMiniPinout.txt
└── gifs/
    ├── fear_greed/
    │   ├── extreme_fear.gif
    │   ├── fear.gif
    │   ├── neutral.gif
    │   ├── greed.gif
    │   └── extreme_greed.gif
    ├── money_flow/
    │   ├── flow_up.gif
    │   ├── flow_down.gif
    │   └── flow_neutral.gif
    ├── animations/    # Processed animation frames
    ├── incoming/     # Drop new GIFs here
    └── error.gif
```

## GIF Requirements

- GIFs should be sized to match your ST7735 display resolution
- Recommended dimensions: 160x128 pixels (may vary based on display hat mini)
- The ST7735 library requires animated GIFs to be split into individual frames
- You can use tools like ImageMagick to split GIFs:
  ```bash
  convert animated.gif frame_%03d.png
  ```
- Store the frame sequences in their respective sentiment folders
- Frames should follow a consistent naming pattern (e.g., frame_001.png, frame_002.png)
  
- Each GIF represents a different market sentiment:
  - extreme_fear.gif (Index value 0-25)
  - fear.gif (Index value 26-45)
  - neutral.gif (Index value 46-55)
  - greed.gif (Index value 56-75)
  - extreme_greed.gif (Index value 76-100)
  - error.gif (displayed when API fetch fails)

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

The Display HAT Mini features four buttons with the following functions:

- Button A (GPIO 5): Toggle between Fear & Greed Index display and custom animation loop
- Button B (GPIO 6): Cycle through available money flow animations
- Button X (GPIO 16): Cycle through custom animations in the animations folder
- Button Y (GPIO 24): Toggle display backlight on/off

Press and hold any button for 3 seconds to exit the program.

## Running the Display

```bash
python feargreeddisplay.py
```

The display will automatically update with the current Fear & Greed Index and show the corresponding animated GIF.

## Data Source

Fear & Greed Index data is fetched from Alternative.me API: https://alternative.me/crypto/fear-and-greed-index/

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
Run tests with: `pytest`

### Running Tests
Run all tests with:
```bash
pytest -v
```

Run a specific test file:
```bash
pytest -v tests/test_general.py
```

Run a specific test:
```bash
pytest -v tests/test_general.py -k test_display_capabilities
```

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

2.  "GIFs don't animate"

- Verify GIF dimensions (160x128)
- Check frames are numbered correctly
- Make sure GIFs are in correct folders

## Need Help?
Create an issue on GitHub
Check https://thepihut.com/products/display-hat-mini
Check https://thepihut.com/products/raspberry-pi-zero-2


