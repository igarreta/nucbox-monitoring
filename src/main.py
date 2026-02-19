#!/usr/bin/env python3
"""
NucBox Monitoring Hub - Main application
Coordinates thermal monitoring and integrations with Home Assistant
"""

import sys
import json
import time
import signal
import logging
import argparse
import threading
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.thermal.monitor import ThermalMonitor
from src.integrations.homeassistant import HomeAssistantClient
from src.utils.logger import setup_logging


class MonitoringHub:
    """Main monitoring hub that coordinates all monitoring activities"""
    
    def __init__(self, config_path=None):
        self.config_path = config_path or project_root / "config" / "config.json"
        self.config = self.load_config()
        self.logger = setup_logging(self.config.get('logging', {}))
        self.running = False

        # Log config load now that logger is available
        self.logger.info(f"Configuration loaded from {self.config_path}")

        # Initialize components
        self.ha_client = HomeAssistantClient(self.config['homeassistant'])
        self.thermal_monitor = ThermalMonitor(
            config=self.config,
            ha_client=self.ha_client
        )

        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
    def load_config(self):
        """Load configuration from JSON file"""
        try:
            if not self.config_path.exists():
                raise FileNotFoundError(f"Configuration file not found: {self.config_path}")

            with open(self.config_path, 'r') as f:
                config = json.load(f)

            # Note: logger not initialized yet at this point, will log after init
            return config

        except Exception as e:
            print(f"Error loading configuration: {e}")
            sys.exit(1)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        self.logger.info(f"Received signal {signum}, shutting down...")
        self.stop()
        
    def start(self):
        """Start the monitoring hub"""
        self.logger.info("Starting NucBox Monitoring Hub")
        
        try:
            # Test Home Assistant connection
            retry_interval = 30
            while not self.ha_client.test_connection():
                self.logger.warning(
                    f"Cannot reach Home Assistant, retrying in {retry_interval}s..."
                )
                time.sleep(retry_interval)
                
            self.running = True
            
            # Start thermal monitor
            thermal_thread = threading.Thread(
                target=self.thermal_monitor.start,
                daemon=True
            )
            thermal_thread.start()
            
            self.logger.info("Monitoring hub started successfully")
            
            # Main loop
            while self.running:
                time.sleep(1)
                
        except Exception as e:
            self.logger.error(f"Error in monitoring hub: {e}", exc_info=True)
            return False
            
        return True
        
    def stop(self):
        """Stop the monitoring hub"""
        self.logger.info("Stopping monitoring hub")
        self.running = False
        
        # Stop thermal monitor
        if hasattr(self.thermal_monitor, 'stop'):
            self.thermal_monitor.stop()
            
    def check_config(self):
        """Validate configuration"""
        required_keys = [
            'homeassistant',
            'thresholds', 
            'monitoring',
            'sensors'
        ]
        
        missing_keys = []
        for key in required_keys:
            if key not in self.config:
                missing_keys.append(key)
                
        if missing_keys:
            self.logger.error(f"Missing configuration keys: {missing_keys}")
            return False
            
        # Test HA connection
        if not self.ha_client.test_connection():
            self.logger.error("Home Assistant connection test failed")
            return False
            
        self.logger.info("Configuration validation passed")
        return True
        
    def get_status(self):
        """Get current monitoring status"""
        return {
            'running': self.running,
            'thermal_monitor': self.thermal_monitor.get_status(),
            'ha_connection': self.ha_client.test_connection(),
            'config_path': str(self.config_path)
        }


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='NucBox Monitoring Hub')
    parser.add_argument(
        '--config', 
        type=str, 
        help='Path to configuration file'
    )
    parser.add_argument(
        '--check-config',
        action='store_true',
        help='Check configuration and exit'
    )
    parser.add_argument(
        '--test',
        action='store_true',
        help='Run in test mode'
    )
    parser.add_argument(
        '--status',
        action='store_true',
        help='Show status and exit'
    )
    
    args = parser.parse_args()
    
    try:
        hub = MonitoringHub(config_path=args.config)
        
        if args.check_config:
            success = hub.check_config()
            sys.exit(0 if success else 1)
            
        if args.status:
            status = hub.get_status()
            print(json.dumps(status, indent=2))
            sys.exit(0)
            
        if args.test:
            print("Running in test mode...")
            hub.thermal_monitor.test_sensors()
            sys.exit(0)
            
        # Normal operation
        success = hub.start()
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\nShutdown requested by user")
        sys.exit(0)
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()