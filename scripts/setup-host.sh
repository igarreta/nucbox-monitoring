#!/bin/bash
# Setup data collector on Proxmox host

set -e

CONTAINER_IP="${1:-10.0.0.202}"  # Default container IP
HOST_SCRIPT_PATH="/usr/local/bin/nucbox-data-collector.sh"
SERVICE_PATH="/etc/systemd/system/nucbox-data-collector"

echo "=== Setting up Proxmox Host Data Collector ==="

# Check if running on Proxmox host
if [ ! -f "/etc/pve/storage.cfg" ]; then
    echo "Warning: This doesn't appear to be a Proxmox host"
    read -p "Continue anyway? (y/N): " -n 1 -r
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Install required packages
echo "Installing required packages..."
apt update
apt install -y bc curl

# Create data collector script
echo "Creating data collector script..."
cat > "$HOST_SCRIPT_PATH" << 'HOSTEOF'
#!/bin/bash
# NucBox thermal data collector for Proxmox host

# Read thermal data
SOCKET_TEMP=$(($(cat /sys/class/thermal/thermal_zone0/temp)/1000))
CPU_TEMP=$(($(cat /sys/class/thermal/thermal_zone1/temp)/1000))

# Read fan states
FAN_STATES=""
FAN_ACTIVE=0
for i in {0..4}; do
    if [ -f "/sys/class/thermal/cooling_device$i/cur_state" ]; then
        STATE=$(cat /sys/class/thermal/cooling_device$i/cur_state)
        FAN_STATES="${FAN_STATES}${STATE}"
        if [ "$STATE" -gt 0 ]; then
            FAN_ACTIVE=1
        fi
    else
        FAN_STATES="${FAN_STATES}0"
    fi
done

# Read CPU frequency
CPU_FREQ=$(grep MHz /proc/cpuinfo | head -1 | awk '{print $4}' | cut -d'.' -f1)

# Read system load
LOAD_1MIN=$(cat /proc/loadavg | awk '{print $1}')

# Create JSON data
JSON_DATA=$(cat <<JSONEOF
{
  "timestamp": $(date +%s),
  "socket_temp": $SOCKET_TEMP,
  "cpu_temp": $CPU_TEMP,
  "fan_active": $FAN_ACTIVE,
  "fan_states": "$FAN_STATES",
  "cpu_freq": $CPU_FREQ,
  "load_avg": "$LOAD_1MIN"
}
JSONEOF
)

# Write to shared file (accessible by containers/VMs)
mkdir -p /var/lib/vz
echo "$JSON_DATA" > /var/lib/vz/nucbox-thermal.json

# Also send directly to container via HTTP (if monitoring container is running)
MONITOR_CONTAINER_IP="CONTAINER_IP_PLACEHOLDER"
curl -s -X POST -H "Content-Type: application/json" -d "$JSON_DATA" \
  "http://$MONITOR_CONTAINER_IP:8080/thermal-data" > /dev/null 2>&1 || true

exit 0
HOSTEOF

# Replace placeholder with actual container IP
sed -i "s/CONTAINER_IP_PLACEHOLDER/$CONTAINER_IP/g" "$HOST_SCRIPT_PATH"

chmod +x "$HOST_SCRIPT_PATH"

# Create systemd service
echo "Creating systemd service..."
cat > "${SERVICE_PATH}.service" << 'SERVICEEOF'
[Unit]
Description=NucBox Thermal Data Collector
After=network.target

[Service]
Type=oneshot
ExecStart=/usr/local/bin/nucbox-data-collector.sh
User=root

[Install]
WantedBy=multi-user.target
SERVICEEOF

# Create systemd timer
cat > "${SERVICE_PATH}.timer" << 'TIMEREOF'
[Unit]
Description=Run NucBox Data Collector every 30 seconds
Requires=nucbox-data-collector.service

[Timer]
OnBootSec=30
OnUnitActiveSec=30

[Install]
WantedBy=timers.target
TIMEREOF

# Enable and start services
echo "Enabling and starting services..."
systemctl daemon-reload
systemctl enable nucbox-data-collector.timer
systemctl start nucbox-data-collector.timer

echo ""
echo "=== Host Setup Complete ==="
echo "Data collector installed and started"
echo "Container IP configured: $CONTAINER_IP"
echo ""
echo "Check status with:"
echo "  systemctl status nucbox-data-collector.timer"
echo "  systemctl status nucbox-data-collector.service"
echo ""
echo "View logs with:"
echo "  journalctl -fu nucbox-data-collector.service"