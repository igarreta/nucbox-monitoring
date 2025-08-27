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
from ..utils.notifications import NotificationManager


class ThermalMonitor:
    """Main thermal monitoring class"""
    
    def __init__(self, config, ha_client):
        self.config = config
        self.ha_client = ha_client
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self.sensor_reader = SensorReader(config.get('sensors', {}))
        self.notification_manager = NotificationManager(
            ha_client=ha_client,
            config=config.get('notifications', {})
        )
        
        # State tracking
        self.last_state = {
            'fan_active': False,
            'throttling': False,
            'high_load': False,
            'last_notification_times': {}
        }
        
        # Configuration
        self.monitoring_config = config.get('monitoring', {})
        self.thresholds = config.get('thresholds', {})
        
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
            
            # Check for alerts
            self._check_temperature_alerts(socket_temp, cpu_temp)
            self._check_fan_alerts(fan_active, socket_temp, cpu_temp, fan_states)
            self._check_throttling_alerts(cpu_freq)
            self._check_load_alerts(load_avg)
            
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
                
    def _check_temperature_alerts(self, socket_temp, cpu_temp):
        """Check and send temperature alerts"""
        cpu_thresholds = self.thresholds.get('cpu_temp', {})
        socket_thresholds = self.thresholds.get('socket_temp', {})
        
        # CPU temperature alerts
        if cpu_temp >= cpu_thresholds.get('critical', 95):
            self.notification_manager.send_notification(
                "🚨 NucBox Critical Temperature",
                f"CPU temperature is {cpu_temp}°C (Critical: {cpu_thresholds['critical']}°C+)",
                priority="critical",
                notification_type="temperature_critical"
            )
        elif cpu_temp >= cpu_thresholds.get('warning', 90):
            self.notification_manager.send_notification(
                "⚠️ NucBox High Temperature", 
                f"CPU temperature is {cpu_temp}°C (Warning: {cpu_thresholds['warning']}°C+)",
                priority="high",
                notification_type="temperature_warning"
            )
            
        # Socket temperature alerts
        if socket_temp >= socket_thresholds.get('critical', 45):
            self.notification_manager.send_notification(
                "🚨 NucBox Socket Overheating",
                f"Socket temperature is {socket_temp}°C - Fans should activate!",
                priority="critical",
                notification_type="temperature_critical"
            )
        elif socket_temp >= socket_thresholds.get('warning', 35):
            self.notification_manager.send_notification(
                "⚠️ NucBox Socket Warming",
                f"Socket temperature is {socket_temp}°C - Monitor closely",
                priority="high", 
                notification_type="temperature_warning"
            )
            
    def _check_fan_alerts(self, fan_active, socket_temp, cpu_temp, fan_states):
        """Check fan status changes"""
        if fan_active and not self.last_state['fan_active']:
            self.notification_manager.send_notification(
                "💨 NucBox Fans Activated",
                f"Socket: {socket_temp}°C, CPU: {cpu_temp}°C, Fan states: [{fan_states}]",
                priority="normal",
                notification_type="fan_state_change"
            )
        elif not fan_active and self.last_state['fan_active']:
            self.notification_manager.send_notification(
                "✅ NucBox Fans Deactivated", 
                f"Temperatures normalized. Socket: {socket_temp}°C, CPU: {cpu_temp}°C",
                priority="normal",
                notification_type="fan_state_change"
            )
            
        self.last_state['fan_active'] = fan_active
        
    def _check_throttling_alerts(self, cpu_freq):
        """Check CPU throttling status"""
        throttling_threshold = self.thresholds.get('cpu_freq', {}).get('throttling_threshold', 3000)
        throttling = cpu_freq < throttling_threshold
        
        if throttling and not self.last_state['throttling']:
            self.notification_manager.send_notification(
                "🐌 NucBox CPU Throttling",
                f"CPU frequency reduced to {cpu_freq}MHz (thermal protection active)",
                priority="high",
                notification_type="throttling_change"
            )
        elif not throttling and self.last_state['throttling']:
            self.notification_manager.send_notification(
                "🚀 NucBox CPU Throttling Ended",
                f"CPU frequency restored to {cpu_freq}MHz", 
                priority="normal",
                notification_type="throttling_change"
            )
            
        self.last_state['throttling'] = throttling
        
    def _check_load_alerts(self, load_avg):
        """Check system load changes"""
        load_thresholds = self.thresholds.get('load_avg', {})
        high_threshold = load_thresholds.get('high', 3.0)
        normal_threshold = load_thresholds.get('normal', 1.0)
        
        high_load = load_avg > high_threshold
        
        if load_avg < normal_threshold and self.last_state['high_load']:
            self.notification_manager.send_notification(
                "✅ NucBox Workload Complete",
                f"System load normalized ({load_avg}). Likely Immich indexing finished!",
                priority="normal",
                notification_type="workload_complete"
            )
            self.last_state['high_load'] = False
        elif high_load:
            self.last_state['high_load'] = True
            
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
            'thresholds': self.thresholds,
            'ha_connection': self.ha_client.test_connection() if self.ha_client else False
        }