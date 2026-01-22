# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- **BREAKING**: Removed alarm and notification functionality from Python monitoring code
- All alerting is now handled by Home Assistant automations
- Python code now only sends sensor data to Home Assistant
- Simplified configuration by removing `thresholds` and `notifications` sections

### Removed
- NotificationManager class and notification handling
- Alert checking methods (temperature, fan, throttling, load alerts)
- Rate limiting functionality (now handled by Home Assistant)
- Threshold configuration in config files

### Migration Guide
If upgrading from v1.0.0:
1. Import the provided Home Assistant automations from `config/homeassistant/automations.yaml`
2. Update your `config.json` to remove `thresholds` and `notifications` sections
3. Restart the monitoring service
4. All existing sensors will continue to work; notifications now come from Home Assistant automations

## [1.0.0] - 2024-12-19

### Added
- Initial release of NucBox G5 thermal monitoring system
- Hybrid architecture with Proxmox host data collection and LXC container processing
- Home Assistant integration with sensors, automations, and dashboard
- Smart notifications with rate limiting and priority levels
- Real-time monitoring of:
  - CPU die temperature (thermal_zone1)
  - Socket temperature (thermal_zone0) 
  - Fan states and activation detection
  - CPU frequency scaling and throttling detection
  - System load average and workload completion detection
- Comprehensive installation scripts:
  - Main installation script (`scripts/install.sh`)
  - Proxmox host setup (`scripts/setup-host.sh`)
  - LXC container setup (`scripts/setup-container.sh`)
- Systemd service integration with proper security settings
- Configurable thresholds and monitoring parameters
- HTTP server for receiving thermal data from host
- File-based monitoring as backup data source
- Comprehensive logging with rotation
- Health check endpoint for monitoring system status
- Example Home Assistant configuration files:
  - Sensor templates and binary sensors
  - Automations for various alert conditions
  - Dashboard configuration with gauges and graphs

### Features
- **Temperature Monitoring**: Separate monitoring of CPU die and socket temperatures
- **Fan Control Awareness**: Detection of fan activation (unusual for NucBox G5 passive cooling)
- **Throttling Detection**: Monitor CPU frequency scaling due to thermal protection
- **Workload Detection**: Smart detection of high-load periods and completion (e.g., Immich indexing)
- **Rate Limited Notifications**: Prevent notification spam with configurable rate limits
- **Multi-Priority Alerts**: Critical, warning, and info level notifications
- **Secure Configuration**: Confidential settings stored in `~/etc/` with symlinks
- **Easy Installation**: One-command setup with automated service configuration
- **Comprehensive Documentation**: Detailed README with troubleshooting guide

### Technical Details
- Written in Python 3.8+ with minimal dependencies
- Uses systemd for service management and automatic startup
- Hybrid data collection: host sensors + containerized processing
- RESTful API integration with Home Assistant
- Configurable JSON-based settings
- Robust error handling and logging
- Resource-efficient design suitable for low-power systems