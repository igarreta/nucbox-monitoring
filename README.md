# NucBox Monitoring System

A comprehensive thermal and system monitoring solution for NucBox G5 (Intel N97) running Proxmox, with Home Assistant integration.

## Features

- 🌡️ **Real-time thermal monitoring** - CPU die and socket temperatures
- 💨 **Fan status monitoring** - Track fan activation and states
- 🚨 **Smart alerting** - Temperature thresholds and state change notifications
- 📊 **Home Assistant integration** - Sensors, history, and mobile notifications
- 🔧 **Throttling detection** - Monitor CPU frequency scaling
- 📈 **Load monitoring** - Track system load and workload completion
- 🏠 **Hybrid architecture** - Host data collection + containerized processing

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Proxmox Host   │    │   LXC Container │    │ Home Assistant  │
│                 │    │                 │    │                 │
│ Data Collector  ├────┤ Monitoring Hub  ├────┤   Dashboard     │
│ (sensors)       │    │ (processing)    │    │ (notifications) │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Requirements

- Proxmox VE host with NucBox G5 (Intel N97)
- LXC container for monitoring service
- Home Assistant instance (VM or external)
- Python 3.8+ with pip

## Quick Start

> **Important**: This system has two parts:
> - **Proxmox Host**: Collects sensor data (run as root)
> - **LXC Container**: Processes data and sends to Home Assistant (run as regular user)

### 1. Clone Repository

```bash
# On your LXC monitoring container
cd /home/rsi
git clone https://github.com/igarreta/nucbox-monitoring.git
cd nucbox-monitoring
```

### 2. Install Dependencies

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip

# Install Python packages
pip3 install -r requirements.txt

# Create necessary directories
mkdir -p ~/etc ~/logs/nucbox-monitoring
```

### 3. Configuration

```bash
# Copy example config and edit
cp config/config.example.json ~/etc/nucbox-monitoring.json

# Create symlink
ln -s ~/etc/nucbox-monitoring.json config/config.json

# Edit configuration
nano ~/etc/nucbox-monitoring.json
```

### 4. Setup Services

#### A. On Proxmox Host (as root)

```bash
# Clone or copy repository to Proxmox host
cd /tmp
git clone https://github.com/igarreta/nucbox-monitoring.git
cd nucbox-monitoring

# Make script executable
chmod +x ./scripts/setup-host.sh

# Run setup (provide your LXC container IP)
./scripts/setup-host.sh 100.96.140.3  # Replace with your container IP
```

#### B. In LXC Container (as regular user)

```bash
# Setup container monitoring service
cd ~/nucbox-monitoring
./scripts/setup-container.sh

# Start services
sudo systemctl enable --now nucbox-monitoring
```

### 5. Home Assistant Integration

Add to your `configuration.yaml`:

```yaml
# Include the provided HA configuration
sensor: !include integrations/homeassistant/sensors.yaml
automation: !include integrations/homeassistant/automations.yaml
```

## Configuration

### Main Configuration File (`~/etc/nucbox-monitoring.json`)

```json
{
  "homeassistant": {
    "url": "http://192.168.1.100:8123",
    "token": "your_long_lived_access_token"
  },
  "thresholds": {
    "cpu_temp": {
      "warning": 90,
      "critical": 95
    },
    "socket_temp": {
      "warning": 35,
      "critical": 45
    }
  },
  "monitoring": {
    "interval": 30,
    "data_file": "/mnt/pve-host/nucbox-thermal.json",
    "http_port": 8080
  },
  "logging": {
    "level": "INFO",
    "file": "/home/rsi/logs/nucbox-monitoring/hub.log",
    "max_size": "10MB",
    "backup_count": 5
  }
}
```

### Temperature Thresholds

| Component | Warning | Critical | Action |
|-----------|---------|----------|--------|
| CPU Die   | 90°C    | 95°C     | Notification + throttling check |
| Socket    | 35°C    | 45°C     | Fan activation expected |

## Usage

### Start/Stop Services

```bash
# Check status
sudo systemctl status nucbox-monitoring

# View logs
journalctl -fu nucbox-monitoring

# Restart service
sudo systemctl restart nucbox-monitoring
```

### Manual Testing

```bash
# Test thermal data collection
cd /home/rsi/nucbox-monitoring
python3 -m src.thermal.monitor --test

# Test Home Assistant connection
python3 -m src.integrations.homeassistant --test
```

### Home Assistant Dashboard

Import the provided dashboard configuration:

1. Go to **Settings** → **Dashboards**
2. Add new dashboard
3. Import `config/homeassistant/dashboard.yaml`

## Monitoring Data

### Sensors Available

- `sensor.nucbox_socket_temp` - Socket temperature (°C)
- `sensor.nucbox_cpu_temp` - CPU die temperature (°C)
- `sensor.nucbox_fan_active` - Fan status (0/1)
- `sensor.nucbox_cpu_throttling` - Throttling status (0/1)
- `sensor.nucbox_load_avg` - System load average

### Notifications

The system sends notifications for:

- 🚨 **Critical temperatures** (immediate)
- ⚠️ **High temperatures** (warning)
- 💨 **Fan activation/deactivation**
- 🐌 **CPU throttling start/stop**
- ✅ **Workload completion** (load drop)

## Troubleshooting

### Common Issues

#### Service won't start
```bash
# Check logs
journalctl -fu nucbox-monitoring

# Verify configuration
python3 -m src.main --check-config
```

#### No thermal data
```bash
# Check host data collector
sudo systemctl status nucbox-data-collector

# Verify sensors on host
cat /sys/class/thermal/thermal_zone*/temp
```

#### Home Assistant not receiving data
```bash
# Test HA connection
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://YOUR_HA_IP:8123/api/states

# Check network connectivity from container
ping YOUR_HA_IP
```

### Log Files

- Main service: `~/logs/nucbox-monitoring/hub.log`
- Thermal module: `~/logs/nucbox-monitoring/thermal.log`
- System service: `journalctl -u nucbox-monitoring`

## Development

### Project Structure

- `src/` - Main Python modules
- `config/` - Configuration files and examples
- `scripts/` - Installation and setup scripts
- `systemd/` - Service definitions
- `docs/` - Additional documentation

### Running Tests

```bash
# Run thermal monitoring test
python3 -m pytest tests/test_thermal.py

# Run integration tests
python3 -m pytest tests/test_integrations.py
```

### Adding New Monitors

1. Create module in `src/monitors/`
2. Add to `src/main.py`
3. Update configuration schema
4. Add tests

## Contributing

1. Fork the repository
2. Create feature branch
3. Add tests for new functionality
4. Submit pull request

## License

MIT License - see LICENSE file for details.

## Support

- **Issues**: GitHub Issues
- **Discussions**: GitHub Discussions
- **Documentation**: [docs/](docs/)

---

**Hardware Tested**: NucBox G5 with Intel N97, Proxmox VE 8.x
**Software Tested**: Python 3.8+, Home Assistant 2024.x
