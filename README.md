# Fear & Greed Index Display

A Raspberry Pi project that displays the current Bitcoin Fear & Greed Index on a ST7735 LCD display with animated GIFs representing different market sentiment levels.

## Requirements

- Raspberry Pi
- ST7735 LCD Display
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
    └── error.gif
```

## GIF Requirements

- GIFs should be sized to match your ST7735 display resolution
- Recommended dimensions: 160x128 pixels (may vary based on your display model)
- Each GIF represents a different market sentiment:
  - extreme_fear.gif (Index value 0-25)
  - fear.gif (Index value 26-45)
  - neutral.gif (Index value 46-55)
  - greed.gif (Index value 56-75)
  - extreme_greed.gif (Index value 76-100)
  - error.gif (displayed when API fetch fails)

## Running the Display

```bash
python feargreeddisplay.py
```

The display will automatically update with the current Fear & Greed Index and show the corresponding animated GIF.

## Data Source

Fear & Greed Index data is fetched from Alternative.me API: https://alternative.me/crypto/fear-and-greed-index/