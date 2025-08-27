# Troubleshooting Guide

## Common Issues

### Service Won't Start

**Symptoms:** `systemctl status nucbox-monitoring` shows failed status

**Solutions:**

1. Check configuration:
   ```bash
   cd /home/rsi/nucbox-monitoring
   python3 -m src.main --check-config
   ```

2. Verify Home Assistant connection:
   ```bash
   # Test HA API access
   curl -H "Authorization: Bearer YOUR_TOKEN" \
     http://YOUR_HA_IP:8123/api/states
   ```

3. Check logs for specific errors:
   ```bash
   journalctl -fu nucbox-monitoring
   tail -f /home/rsi/logs/nucbox-monitoring/hub.log
   ```

4. Verify Python dependencies:
   ```bash
   pip3 install -r requirements.txt
   ```

### No Thermal Data

**Symptoms:** Service runs but no temperature data in Home Assistant

**Solutions:**

1. Check Proxmox host data collector:
   ```bash
   # On Proxmox host
   systemctl status nucbox-data-collector.timer
   systemctl status nucbox-data-collector.service
   journalctl -fu nucbox-data-collector.service
   ```

2. Verify sensor files exist on host:
   ```bash
   # On Proxmox host
   ls -la /sys/class/thermal/thermal_zone*/temp
   cat /sys/class/thermal/thermal_zone*/temp
   ```

3. Check data file creation:
   ```bash
   # On Proxmox host
   ls -la /var/lib/vz/nucbox-thermal.json
   cat /var/lib/vz/nucbox-thermal.json
   ```

4. Verify container can access data:
   ```bash
   # In container
   ls -la /mnt/pve-host/nucbox-thermal.json
   ```

### Home Assistant Not Receiving Data

**Symptoms:** Thermal data collected but HA sensors show "unavailable"

**Solutions:**

1. Test HA connection from container:
   ```bash
   # In container
   ping YOUR_HA_IP
   curl -H "Authorization: Bearer YOUR_TOKEN" \
     http://YOUR_HA_IP:8123/api/states
   ```

2. Verify token and URL in config:
   ```bash
   nano ~/etc/nucbox-monitoring.json
   ```

3. Check HA logs for API errors:
   ```bash
   # In Home Assistant
   tail -f /config/home-assistant.log | grep nucbox
   ```

### High CPU Usage

**Symptoms:** Monitoring service consuming too much CPU

**Solutions:**

1. Check monitoring interval:
   ```bash
   # In ~/etc/nucbox-monitoring.json
   "monitoring": {
     "interval": 60  # Increase from 30 to reduce frequency
   }
   ```

2. Disable unnecessary features:
   ```bash
   # In configuration
   "monitoring": {
     "enable_file_monitor": false,  # Use only HTTP
     "enable_http_server": true
   }
   ```

3. Reduce logging level:
   ```bash
   "logging": {
     "level": "WARNING"  # Reduce from INFO
   }
   ```

### Permission Issues

**Symptoms:** File access denied errors

**Solutions:**

1. Fix ownership:
   ```bash
   sudo chown -R rsi:rsi /home/rsi/nucbox-monitoring
   sudo chown -R rsi:rsi /home/rsi/logs
   sudo chown rsi:rsi /home/rsi/etc/nucbox-monitoring.json
   ```

2. Verify mount points in LXC:
   ```bash
   # Check /etc/pve/lxc/YOUR_CONTAINER_ID.conf
   mp0: /var/lib/vz,/mnt/pve-host
   ```

## Sensor-Specific Issues

### Wrong Temperature Readings

**Issue:** Temperature sensors swapped or reading incorrectly

**Solution:** Check and adjust sensor mapping:
```bash
# Test which zone is which
echo "Zone 0: $(cat /sys/class/thermal/thermal_zone0/temp | awk '{print $1/1000}')°C ($(cat /sys/class/thermal/thermal_zone0/type))"
echo "Zone 1: $(cat /sys/class/thermal/thermal_zone1/temp | awk '{print $1/1000}')°C ($(cat /sys/class/thermal/thermal_zone1/type))"

# Update config if needed
"sensors": {
  "thermal_zone_socket": 1,  # Swap if needed
  "thermal_zone_cpu": 0
}
```

### Fan Detection Issues

**Issue:** Fans not detected or wrong count

**Solution:** Check available cooling devices:
```bash
# List all cooling devices
for i in /sys/class/thermal/cooling_device*; do
  echo "$(basename $i): $(cat $i/type) (max: $(cat $i/max_state))"
done

# Update config with correct device IDs
"sensors": {
  "cooling_devices": [0, 1, 2, 3, 4]  # Adjust based on findings
}
```

## Home Assistant Issues

### Sensors Not Appearing

**Solution:** Force sensor creation:
```bash
# In container, test sensor update
cd /home/rsi/nucbox-monitoring
python3 -c "
from src.integrations.homeassistant import HomeAssistantClient
import json

with open('config/config.json') as f:
    config = json.load(f)
    
client = HomeAssistantClient(config['homeassistant'])
print('Testing HA connection:', client.test_connection())

# Create a test sensor
client.update_sensor('nucbox_test', 42, {'test': True})
"
```

### Automation Not Triggering

**Solutions:**

1. Check entity IDs match:
   ```yaml
   # In automations.yaml, ensure entity names match
   entity_id: sensor.nucbox_cpu_temp  # Not sensor.nucbox_cpu_temperature
   ```

2. Test trigger conditions:
   ```bash
   # In HA Developer Tools > States
   # Check current sensor values and states
   ```

## Network Issues

### Container Can't Reach Host

**Symptoms:** HTTP requests from container to Proxmox host fail

**Solutions:**

1. Check LXC network configuration:
   ```bash
   # In /etc/pve/lxc/CONTAINER_ID.conf
   net0: name=eth0,bridge=vmbr0,ip=dhcp
   # Or static IP:
   net0: name=eth0,bridge=vmbr0,ip=192.168.1.100/24,gw=192.168.1.1
   ```

2. Test connectivity:
   ```bash
   # From container
   ping $(hostname -I | awk '{print $1}')  # Ping host
   ```

### Container Can't Reach Home Assistant

**Solutions:**

1. Check firewall rules:
   ```bash
   # On HA system
   sudo ufw status
   sudo ufw allow 8123
   ```

2. Verify HA is listening on correct interface:
   ```yaml
   # In HA configuration.yaml
   http:
     server_host: 0.0.0.0  # Listen on all interfaces
     server_port: 8123
   ```

## Performance Optimization

### Reduce Resource Usage

1. Optimize monitoring frequency:
   ```json
   {
     "monitoring": {
       "interval": 60,  // Increase interval
       "enable_file_monitor": false  // Use only HTTP
     },
     "logging": {
       "level": "WARNING",  // Reduce logging
       "console": false     // Disable console output
     }
   }
   ```

2. Limit systemd resource usage:
   ```ini
   # In service file
   [Service]
   MemoryMax=256M  # Reduce from 512M
   CPUQuota=25%    # Reduce from 50%
   ```

### Improve Reliability

1. Add monitoring redundancy:
   ```json
   {
     "monitoring": {
       "enable_file_monitor": true,   // Keep both enabled
       "enable_http_server": true
     }
   }
   ```

2. Increase restart limits:
   ```ini
   # In service file
   [Service]
   Restart=always
   RestartSec=30          # Wait longer between restarts
   StartLimitBurst=10     # Allow more restart attempts
   ```

## Getting Help

### Collecting Debug Information

```bash
#!/bin/bash
# Debug information collection script

echo "=== NucBox Monitoring Debug Info ==="
echo "Date: $(date)"
echo "User: $(whoami)"
echo "Host: $(hostname)"
echo ""

echo "=== Configuration ==="
echo "Config file exists: $([ -f ~/etc/nucbox-monitoring.json ] && echo 'YES' || echo 'NO')"
echo "Symlink exists: $([ -L /home/rsi/nucbox-monitoring/config/config.json ] && echo 'YES' || echo 'NO')"
echo ""

echo "=== Services ==="
systemctl is-active nucbox-monitoring || echo "Service not active"
systemctl is-enabled nucbox-monitoring || echo "Service not enabled"
echo ""

echo "=== Sensors ==="
if [ -f /sys/class/thermal/thermal_zone0/temp ]; then
    echo "Zone 0: $(($(cat /sys/class/thermal/thermal_zone0/temp)/1000))°C ($(cat /sys/class/thermal/thermal_zone0/type))"
fi
if [ -f /sys/class/thermal/thermal_zone1/temp ]; then
    echo "Zone 1: $(($(cat /sys/class/thermal/thermal_zone1/temp)/1000))°C ($(cat /sys/class/thermal/thermal_zone1/type))"
fi
echo ""

echo "=== Network ==="necho "Container IP: $(hostname -I)"
echo "Can reach HA: $(curl -s -o /dev/null -w '%{http_code}' http://YOUR_HA_IP:8123 || echo 'FAILED')"
echo ""

echo "=== Recent Logs ==="
journalctl -u nucbox-monitoring --no-pager -n 20
```

Run this script and include the output when reporting issues.

### Support Channels

- **GitHub Issues**: [https://github.com/igarreta/nucbox-monitoring/issues](https://github.com/igarreta/nucbox-monitoring/issues)
- **Discussions**: [https://github.com/igarreta/nucbox-monitoring/discussions](https://github.com/igarreta/nucbox-monitoring/discussions)
- **Documentation**: Check README.md and configuration examples