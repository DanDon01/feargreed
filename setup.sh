#!/bin/bash
echo "Installing system dependencies..."
sudo apt update && sudo apt install -y libopenblas-dev python3-dev python3-pip python3-venv
echo "Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate
echo "Installing Python dependencies..."
pip install --no-cache-dir --prefer-binary -r requirements.txt
echo "Setup complete! Run 'source venv/bin/activate' to start."
