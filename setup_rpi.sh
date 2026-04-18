#!/bin/bash
# =============================================================================
# setup_rpi.sh — One-command Raspberry Pi 4 setup for Ly-ion.
# Run as: bash setup_rpi.sh
# Requires: Raspberry Pi OS (64-bit), internet connection.
# =============================================================================

set -e   # Exit immediately on error

echo "=============================="
echo "  Ly-ion RPi Setup Script"
echo "=============================="

# ---------------------------------------------------------------------------
# System packages
# ---------------------------------------------------------------------------
echo "[1/6] Updating system packages..."
sudo apt-get update -y
sudo apt-get install -y python3-pip python3-dev i2c-tools git build-essential \
    libssl-dev libffi-dev python3-setuptools

# ---------------------------------------------------------------------------
# Enable SPI and I2C hardware interfaces
# ---------------------------------------------------------------------------
echo "[2/6] Enabling SPI and I2C interfaces..."
sudo raspi-config nonint do_spi 0   # 0 = enable
sudo raspi-config nonint do_i2c 0

# Verify I2C devices are accessible
echo "Detected I2C devices:"
sudo i2cdetect -y 1 || true

# ---------------------------------------------------------------------------
# Python dependencies
# ---------------------------------------------------------------------------
echo "[3/6] Installing Python libraries..."
pip3 install --upgrade pip
pip3 install \
    mfrc522==0.0.7 \
    rpi_ws281x==5.0.0 \
    adafruit-circuitpython-mcp230xx==2.5.16 \
    requests==2.32.3 \
    python-dotenv==1.0.1

# ---------------------------------------------------------------------------
# Copy project files (assumes script is run from project root)
# ---------------------------------------------------------------------------
echo "[4/6] Installing Ly-ion embedded application..."
INSTALL_DIR="/home/pi/lyion_embedded"
if [ -d "$INSTALL_DIR" ]; then
    echo "Updating existing installation at $INSTALL_DIR"
    cp -r lyion_embedded/* "$INSTALL_DIR/"
else
    cp -r lyion_embedded "$INSTALL_DIR"
fi

# Create .env if it doesn't exist
if [ ! -f "$INSTALL_DIR/.env" ]; then
    cat > "$INSTALL_DIR/.env" <<EOF
BACKEND_URL=http://your-backend-url.com
API_SECRET=your-api-secret-key
STATION_ID=station-001
DB_PATH=/home/pi/lyion_embedded/lyion_local.db
LOG_FILE=/home/pi/lyion_embedded/lyion.log
LOG_LEVEL=INFO
EOF
    echo "Created $INSTALL_DIR/.env — EDIT THIS FILE before starting the service!"
fi

# ---------------------------------------------------------------------------
# systemd service
# ---------------------------------------------------------------------------
echo "[5/6] Installing systemd service..."
sudo tee /etc/systemd/system/lyion_embedded.service > /dev/null <<EOF
[Unit]
Description=Ly-ion Embedded Controller
After=network.target

[Service]
ExecStart=/usr/bin/python3 /home/pi/lyion_embedded/main.py
WorkingDirectory=/home/pi/lyion_embedded
Restart=always
RestartSec=5
User=pi
EnvironmentFile=/home/pi/lyion_embedded/.env

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable lyion_embedded

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------
echo "[6/6] Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Edit /home/pi/lyion_embedded/.env  — set BACKEND_URL, API_SECRET, STATION_ID"
echo "  2. sudo systemctl start lyion_embedded"
echo "  3. sudo journalctl -u lyion_embedded -f  — to follow logs"
echo ""
echo "To test hardware before starting the service:"
echo "  cd /home/pi/lyion_embedded && python3 test_hardware.py"
