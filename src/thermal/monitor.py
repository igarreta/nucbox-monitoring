#!/usr/bin/env python3
"""
Thermal monitoring module for NucBox G5
Handles temperature sensors, fan states, and thermal events
"""

import json
import time
import logging
import threading
from datetime import datetime, timedelta
from pathlib import Path
from http.server import BaseHTTPRequestHandler, HTTPServer

from .sensors import SensorReader


class ThermalMonitor:
    """Main thermal monitoring class"""
    
    def __init__(self, config, ha_client):
        self.config = config
        self.ha_client = ha_client
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self.sensor_reader = SensorReader(config.get('sensors', {}))
        
        # State tracking
        self.last_state = {}

        # Configuration
        self.monitoring_config = config.get('monitoring', {})
        
        # Threading
        self.running = False
        self.http_server = None
        
    def start(self):
        """Start thermal monitoring"""
        self.logger.info("Starting thermal monitoring")
        self.running = True
        
        # Start file monitor if enabled
        if self.monitoring_config.get('enable_file_monitor', True):
            file_thread = threading.Thread(target=self._file_monitor, daemon=True)
            file_thread.start()
            
        # Start HTTP server if enabled
        if self.monitoring_config.get('enable_http_server', True):
            http_thread = threading.Thread(target=self._start_http_server, daemon=True)
            http_thread.start()
            
        self.logger.info("Thermal monitoring started")
        
    def stop(self):
        """Stop thermal monitoring"""
        self.logger.info("Stopping thermal monitoring")
        self.running = False
        
        if self.http_server:
            self.http_server.shutdown()
            
    def _file_monitor(self):
        """Monitor thermal data file for changes"""
        data_file = Path(self.monitoring_config.get('data_file', '/tmp/nucbox-thermal.json'))
        last_modified = 0
        
        self.logger.info(f"Starting file monitor for {data_file}")
        
        while self.running:
            try:
                if data_file.exists():
                    current_modified = data_file.stat().st_mtime
                    
                    if current_modified > last_modified:
                        with open(data_file, 'r') as f:
                            thermal_data = json.load(f)
                            
                        self.process_thermal_data(thermal_data)
                        last_modified = current_modified
                        
            except Exception as e:
                self.logger.error(f"File monitoring error: {e}")
                
            time.sleep(self.monitoring_config.get('interval', 30))
            
    def _start_http_server(self):
        """Start HTTP server for receiving thermal data"""
        port = self.monitoring_config.get('http_port', 8080)
        
        class ThermalHandler(BaseHTTPRequestHandler):
            def __init__(self, thermal_monitor):
                self.thermal_monitor = thermal_monitor
                
            def __call__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                
            def do_POST(self):
                if self.path == '/thermal-data':
                    try:
                        content_length = int(self.headers['Content-Length'])
                        thermal_data = json.loads(self.rfile.read(content_length))
                        
                        self.thermal_monitor.process_thermal_data(thermal_data)
                        
                        self.send_response(200)
                        self.end_headers()
                        self.wfile.write(b'OK')
                    except Exception as e:
                        self.thermal_monitor.logger.error(f"HTTP handler error: {e}")
                        self.send_response(500)
                        self.end_headers()
                else:
                    self.send_response(404)
                    self.end_headers()
                    
            def do_GET(self):
                if self.path == '/health':
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    health_data = {
                        'status': 'healthy',
                        'timestamp': datetime.now().isoformat(),
                        'monitoring': self.thermal_monitor.get_status()
                    }
                    self.wfile.write(json.dumps(health_data).encode())
                else:
                    self.send_response(404)
                    self.end_headers()
                    
            def log_message(self, format, *args):
                # Suppress HTTP logs
                pass
                
        try:
            handler = lambda *args, **kwargs: ThermalHandler(self)(*args, **kwargs)
            self.http_server = HTTPServer(('0.0.0.0', port), handler)
            self.logger.info(f"HTTP server started on port {port}")
            self.http_server.serve_forever()
        except Exception as e:
            self.logger.error(f"HTTP server error: {e}")
            
    def process_thermal_data(self, data):
        """Process thermal data and handle events"""
        try:
            # Extract data
            socket_temp = int(data.get('socket_temp', 0))
            cpu_temp = int(data.get('cpu_temp', 0))
            fan_active = bool(data.get('fan_active', False))
            cpu_freq = int(data.get('cpu_freq', 0))
            load_avg = float(data.get('load_avg', 0.0))
            fan_states = data.get('fan_states', '')
            
            # Log current status
            self.logger.debug(
                f"Thermal data: Socket={socket_temp}°C, CPU={cpu_temp}°C, "
                f"Fans={fan_active}, Freq={cpu_freq}MHz, Load={load_avg}"
            )
            
            # Update Home Assistant sensors
            self._update_ha_sensors(data)
            
        except Exception as e:
            self.logger.error(f"Error processing thermal data: {e}", exc_info=True)
            
    def _update_ha_sensors(self, data):
        """Update Home Assistant sensors with current data"""
        sensors = [
            ('nucbox_socket_temp', data['socket_temp'], {
                'unit_of_measurement': '°C',
                'device_class': 'temperature',
                'friendly_name': 'NucBox Socket Temperature'
            }),
            ('nucbox_cpu_temp', data['cpu_temp'], {
                'unit_of_measurement': '°C',
                'device_class': 'temperature',
                'friendly_name': 'NucBox CPU Temperature'
            }),
            ('nucbox_cpu_freq', data['cpu_freq'], {
                'unit_of_measurement': 'MHz',
                'device_class': 'frequency',
                'friendly_name': 'NucBox CPU Frequency',
                'icon': 'mdi:chip'
            }),
            ('nucbox_fan_active', int(data['fan_active']), {
                'device_class': 'running',
                'friendly_name': 'NucBox Fans Active',
                'fan_states': data.get('fan_states', '')
            }),
            ('nucbox_cpu_throttling', int(data['cpu_freq'] < 3000), {
                'device_class': 'problem',
                'friendly_name': 'NucBox CPU Throttling',
                'cpu_frequency': f"{data['cpu_freq']}MHz"
            }),
            ('nucbox_load_avg', data['load_avg'], {
                'friendly_name': 'NucBox Load Average',
                'unit_of_measurement': 'load'
            })
        ]
        
        for entity_id, state, attributes in sensors:
            try:
                self.ha_client.update_sensor(entity_id, state, attributes)
            except Exception as e:
                self.logger.error(f"Failed to update sensor {entity_id}: {e}")

    def test_sensors(self):
        """Test sensor reading functionality"""
        self.logger.info("Testing sensor functionality...")
        
        try:
            test_data = self.sensor_reader.read_all_sensors()
            self.logger.info(f"Sensor test data: {test_data}")
            
            # Test processing
            self.process_thermal_data(test_data)
            self.logger.info("Sensor test completed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Sensor test failed: {e}")
            return False
            
    def get_status(self):
        """Get current monitoring status"""
        return {
            'running': self.running,
            'last_state': self.last_state.copy(),
            'ha_connection': self.ha_client.test_connection() if self.ha_client else False
        }