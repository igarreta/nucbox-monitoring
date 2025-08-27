#!/bin/bash
# Setup monitoring service in LXC container

set -e

PROJECT_DIR="/home/rsi/nucbox-monitoring"

echo "=== Setting up Container Monitoring Service ==="

# Check if in LXC container
if [ ! -f "/proc/1/environ" ] || ! grep -q "container=lxc" /proc/1/environ 2>/dev/null; then
    echo "Warning: This doesn't appear to be an LXC container"
fi

# Install systemd service
if [ -f "$PROJECT_DIR/systemd/nucbox-monitoring.service" ]; then
    echo "Installing systemd service..."
    sudo cp "$PROJECT_DIR/systemd/nucbox-monitoring.service" /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl enable nucbox-monitoring
    echo "Service installed and enabled"
else
    echo "Error: Service file not found at $PROJECT_DIR/systemd/nucbox-monitoring.service"
    exit 1
fi

# Test configuration
echo "Testing configuration..."
cd "$PROJECT_DIR"
if python3 -m src.main --check-config; then
    echo "Configuration test passed"
else
    echo "Configuration test failed - please check your config"
    exit 1
fi

# Test sensors (if data file exists)
DATA_FILE="/mnt/pve-host/nucbox-thermal.json"
if [ -f "$DATA_FILE" ]; then
    echo "Testing sensor data availability..."
    echo "Latest sensor data:"
    cat "$DATA_FILE" | python3 -m json.tool
else
    echo "Warning: Sensor data file not found at $DATA_FILE"
    echo "Make sure the Proxmox host data collector is running"
fi

echo ""
echo "=== Container Setup Complete ==="
echo ""
echo "To start monitoring:"
echo "  sudo systemctl start nucbox-monitoring"
echo ""
echo "To check status:"
echo "  systemctl status nucbox-monitoring"
echo ""
echo "To view logs:"
echo "  journalctl -fu nucbox-monitoring"
echo "  tail -f /home/rsi/logs/nucbox-monitoring/hub.log"
echo ""
echo "To test manually:"
echo "  cd $PROJECT_DIR"
echo "  python3 -m src.main --test"
