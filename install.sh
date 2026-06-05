#!/bin/bash
set -e

echo "=== Rover Pi Setup ==="

sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-pip python3-venv i2c-tools git

# Enable camera + I2C (requires reboot after)
sudo raspi-config nonint do_camera 0
sudo raspi-config nonint do_i2c 0

python3 -m venv rover-env
source rover-env/bin/activate

pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "=== Hardware checks ==="
echo "I2C devices (expect 0x27 or 0x3F for LCD):"
i2cdetect -y 1 || echo "  [SKIP] I2C not enabled yet — reboot first"

echo "Camera test:"
libcamera-hello --timeout 2000 || echo "  [SKIP] Camera not detected"

echo ""
echo "=== Setup complete ==="
echo "1. Edit config.py — set CLAUDE_API_KEY"
echo "2. Confirm LCD_ADDRESS matches i2cdetect output"
echo "3. Run: source rover-env/bin/activate && python main.py"
