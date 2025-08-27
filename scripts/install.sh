#!/bin/bash
# scripts/install.sh - Main installation script

set -e

PROJECT_DIR="/home/rsi/nucbox-monitoring"
CONFIG_DIR="/home/rsi/etc"
LOG_DIR="/home/rsi/logs/nucbox-monitoring"

echo "=== NucBox Monitoring Installation ==="

# Check if running as correct user
if [ "$USER" != "rsi" ]; then
    echo "Error: This script should be run as user 'rsi'"
    exit 1
fi

# Create directories
echo "Creating directories..."
mkdir -p "$CONFIG_DIR"
mkdir -p "$LOG_DIR"
mkdir -p "$PROJECT_DIR/config"

# Install Python dependencies
echo "Installing Python dependencies..."
pip3 install -r "$PROJECT_DIR/requirements.txt"

# Setup configuration
if [ ! -f "$CONFIG_DIR/nucbox-monitoring.json" ]; then
    echo "Creating configuration file..."
    cp "$PROJECT_DIR/config/config.example.json" "$CONFIG_DIR/nucbox-monitoring.json"
    echo "Configuration file created at $CONFIG_DIR/nucbox-monitoring.json"
    echo "Please edit this file with your Home Assistant details."
else
    echo "Configuration file already exists."
fi

# Create symlink
if [ ! -L "$PROJECT_DIR/config/config.json" ]; then
    ln -s "$CONFIG_DIR/nucbox-monitoring.json" "$PROJECT_DIR/config/config.json"
    echo "Configuration symlink created."
fi

# Install systemd service
echo "Installing systemd service..."
sudo cp "$PROJECT_DIR/systemd/nucbox-monitoring.service" /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable nucbox-monitoring

# Set permissions
chmod +x "$PROJECT_DIR/src/main.py"
chmod +x "$PROJECT_DIR/scripts/"*.sh

echo ""
echo "=== Installation Complete ==="
echo "Next steps:"
echo "1. Edit configuration: nano $CONFIG_DIR/nucbox-monitoring.json"
echo "2. Add your Home Assistant URL and token"
echo "3. Setup Proxmox host data collector: sudo $PROJECT_DIR/scripts/setup-host.sh"
echo "4. Start service: sudo systemctl start nucbox-monitoring"
echo "5. Check logs: journalctl -fu nucbox-monitoring"