# NucBox Monitoring System

A comprehensive thermal and system monitoring solution for NucBox G5 (Intel N97) running Proxmox, with Home Assistant integration.

## Features

- 🌡️ **Real-time thermal monitoring** - CPU die and socket temperatures
- 💨 **Fan status monitoring** - Track fan activation and states
- 📊 **Home Assistant integration** - Sensors, history, and automations
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

> **Important**: This system has two parts that must be set up in order:
> 1. **Proxmox Host** (SSH as root) - Collects hardware sensor data
> 2. **LXC Container** (SSH as regular user) - Processes and sends data to Home Assistant

---

### Part A: Setup on Proxmox Host

**⚠️ Run these commands on the Proxmox host itself (SSH as root)**

#### 1. Install Data Collector

```bash
# SSH to your Proxmox host as root
ssh root@your-proxmox-ip

# Clone repository
cd /tmp
git clone https://github.com/igarreta/nucbox-monitoring.git
cd nucbox-monitoring

# Make script executable
chmod +x ./scripts/setup-host.sh

# Run setup script (provide your LXC container IP)
./scripts/setup-host.sh 100.96.140.3  # Replace with your container IP
```

#### 2. Verify Host Data Collection

```bash
# Check the service is running
systemctl status nucbox-data-collector.timer

# Verify data file is being created
cat /var/lib/vz/nucbox-thermal.json
```

---

### Part B: Setup in LXC Container

**⚠️ Run these commands in your LXC container (SSH as regular user)**

> **Prerequisite**: Your LXC container must have the host directory mounted. Add this to your container config on the Proxmox host (`/etc/pve/lxc/YOUR_CONTAINER_ID.conf`):
> ```
> mp0: /var/lib/vz,mp=/mnt/pve-host
> ```
> Then restart the container for the mount to take effect.

#### 1. Clone Repository

```bash
# SSH to your LXC container as regular user (e.g., rsi)
ssh rsi@your-container-ip

# Clone repository
cd /home/rsi
git clone https://github.com/igarreta/nucbox-monitoring.git
cd nucbox-monitoring
```

#### 2. Install Dependencies

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

#### 3. Configure Monitoring

```bash
# Copy example config
cp config/config.example.json ~/etc/nucbox-monitoring.json

# Create symlink
ln -s ~/etc/nucbox-monitoring.json config/config.json

# Edit configuration
nano ~/etc/nucbox-monitoring.json
```

**Important configuration items:**
- `homeassistant.url` - Your Home Assistant URL
- `homeassistant.token` - Your long-lived access token (see instructions below)
- `monitoring.data_file` - Should be `/mnt/pve-host/nucbox-thermal.json`

<details>
<summary><b>📝 How to Create a Home Assistant Long-Lived Access Token</b></summary>

1. Log into your Home Assistant web interface
2. Click on your **username** in the bottom left corner
3. Scroll down to **"Long-Lived Access Tokens"**
4. Click **"Create Token"**
5. Give it a name like `NucBox Monitoring`
6. Click **"OK"** and copy the token immediately (you won't see it again!)
7. Paste the token into your `~/etc/nucbox-monitoring.json` configuration

**Test the token:**
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://YOUR_HA_IP:8123/api/states
```

If successful, you should see a JSON response with your entities.
</details>

#### 4. Setup and Start Service

```bash
# Run container setup
./scripts/setup-container.sh

# Start monitoring service
sudo systemctl enable --now nucbox-monitoring

# Check status
systemctl status nucbox-monitoring
```

---

### Part C: Home Assistant Integration

Add to your `configuration.yaml`:

```yaml
# Include the provided HA configuration
sensor: !include nucbox-monitoring/sensors.yaml
automation: !include nucbox-monitoring/automations.yaml
```

Copy the files from the repository to your Home Assistant config directory:
- `config/homeassistant/sensors.yaml` → Your HA config directory
- `config/homeassistant/automations.yaml` → Your HA config directory

## Configuration

### Main Configuration File (`~/etc/nucbox-monitoring.json`)

```json
{
  "homeassistant": {
    "url": "http://192.168.1.100:8123",
    "token": "your_long_lived_access_token"
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

Notifications are handled by Home Assistant automations (see `config/homeassistant/automations.yaml`). The provided automations include alerts for:

- 🚨 **Sustained high temperatures** - CPU temp > 90°C for 5+ minutes
- 📈 **Temperature spikes** - Rapid temperature increases (> 10°C)
- 💨 **Fan activation** - Unusual for passive cooling systems
- ⚡ **High system load** - Load average > 3.0
- ✅ **Workload completion** - Load normalizes after high usage

You can customize these automations or add your own in Home Assistant.

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
