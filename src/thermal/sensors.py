#!/usr/bin/env python3
"""
Sensor reading utilities for NucBox thermal monitoring
Handles reading from thermal zones and cooling devices
"""

import logging
from pathlib import Path
from datetime import datetime


class SensorReader:
    """Read thermal sensor data from sysfs"""
    
    def __init__(self, config=None):
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # Default sensor paths
        self.thermal_zone_socket = self.config.get('thermal_zone_socket', 0)
        self.thermal_zone_cpu = self.config.get('thermal_zone_cpu', 1)
        self.cooling_devices = self.config.get('cooling_devices', [0, 1, 2, 3, 4])
        
    def read_temperature(self, zone_id):
        """Read temperature from thermal zone"""
        try:
            temp_file = Path(f'/sys/class/thermal/thermal_zone{zone_id}/temp')
            if temp_file.exists():
                with open(temp_file, 'r') as f:
                    temp_millidegrees = int(f.read().strip())
                return temp_millidegrees // 1000
            else:
                self.logger.warning(f"Temperature file not found: {temp_file}")
                return None
        except Exception as e:
            self.logger.error(f"Error reading temperature from zone {zone_id}: {e}")
            return None
            
    def read_fan_states(self):
        """Read fan states from cooling devices"""
        fan_states = []
        fan_active = False
        
        for device_id in self.cooling_devices:
            try:
                state_file = Path(f'/sys/class/thermal/cooling_device{device_id}/cur_state')
                if state_file.exists():
                    with open(state_file, 'r') as f:
                        state = int(f.read().strip())
                    fan_states.append(state)
                    if state > 0:
                        fan_active = True
                else:
                    self.logger.warning(f"Cooling device file not found: {state_file}")
                    fan_states.append(0)
            except Exception as e:
                self.logger.error(f"Error reading fan state {device_id}: {e}")
                fan_states.append(0)
                
        return fan_states, fan_active
        
    def read_cpu_frequency(self):
        """Read current CPU frequency"""
        try:
            cpuinfo_file = Path('/proc/cpuinfo')
            if cpuinfo_file.exists():
                with open(cpuinfo_file, 'r') as f:
                    for line in f:
                        if line.startswith('cpu MHz'):
                            freq_str = line.split(':')[1].strip()
                            return int(float(freq_str))
            return None
        except Exception as e:
            self.logger.error(f"Error reading CPU frequency: {e}")
            return None
            
    def read_load_average(self):
        """Read system load average"""
        try:
            loadavg_file = Path('/proc/loadavg')
            if loadavg_file.exists():
                with open(loadavg_file, 'r') as f:
                    load_data = f.read().strip().split()
                    return float(load_data[0])  # 1-minute average
            return None
        except Exception as e:
            self.logger.error(f"Error reading load average: {e}")
            return None
            
    def read_all_sensors(self):
        """Read all sensor data and return as dict"""
        # Read temperatures
        socket_temp = self.read_temperature(self.thermal_zone_socket)
        cpu_temp = self.read_temperature(self.thermal_zone_cpu)
        
        # Read fan states
        fan_states, fan_active = self.read_fan_states()
        
        # Read CPU frequency
        cpu_freq = self.read_cpu_frequency()
        
        # Read load average
        load_avg = self.read_load_average()
        
        # Create data dictionary
        sensor_data = {
            'timestamp': int(datetime.now().timestamp()),
            'socket_temp': socket_temp or 0,
            'cpu_temp': cpu_temp or 0,
            'fan_active': int(fan_active),
            'fan_states': ''.join(map(str, fan_states)),
            'cpu_freq': cpu_freq or 0,
            'load_avg': load_avg or 0.0
        }
        
        self.logger.debug(f"Sensor data collected: {sensor_data}")
        return sensor_data
        
    def test_sensors(self):
        """Test sensor availability"""
        results = {}
        
        # Test thermal zones
        socket_temp = self.read_temperature(self.thermal_zone_socket)
        cpu_temp = self.read_temperature(self.thermal_zone_cpu)
        
        results['thermal_zones'] = {
            'socket': socket_temp is not None,
            'cpu': cpu_temp is not None
        }
        
        # Test cooling devices
        fan_states, _ = self.read_fan_states()
        results['cooling_devices'] = {
            'count': len([s for s in fan_states if s is not None]),
            'expected': len(self.cooling_devices)
        }
        
        # Test other sensors
        results['cpu_frequency'] = self.read_cpu_frequency() is not None
        results['load_average'] = self.read_load_average() is not None
        
        self.logger.info(f"Sensor test results: {results}")
        return results
        
    def get_sensor_info(self):
        """Get detailed sensor information"""
        info = {
            'thermal_zones': {},
            'cooling_devices': {},
            'system_info': {}
        }
        
        # Thermal zone information
        for zone_id in [self.thermal_zone_socket, self.thermal_zone_cpu]:
            zone_path = Path(f'/sys/class/thermal/thermal_zone{zone_id}')
            if zone_path.exists():
                try:
                    type_file = zone_path / 'type'
                    zone_type = 'unknown'
                    if type_file.exists():
                        with open(type_file, 'r') as f:
                            zone_type = f.read().strip()
                            
                    info['thermal_zones'][zone_id] = {
                        'type': zone_type,
                        'path': str(zone_path),
                        'available': True
                    }
                except Exception as e:
                    info['thermal_zones'][zone_id] = {
                        'available': False,
                        'error': str(e)
                    }
                    
        # Cooling device information
        for device_id in self.cooling_devices:
            device_path = Path(f'/sys/class/thermal/cooling_device{device_id}')
            if device_path.exists():
                try:
                    type_file = device_path / 'type'
                    device_type = 'unknown'
                    if type_file.exists():
                        with open(type_file, 'r') as f:
                            device_type = f.read().strip()
                            
                    max_state_file = device_path / 'max_state'
                    max_state = 0
                    if max_state_file.exists():
                        with open(max_state_file, 'r') as f:
                            max_state = int(f.read().strip())
                            
                    info['cooling_devices'][device_id] = {
                        'type': device_type,
                        'max_state': max_state,
                        'path': str(device_path),
                        'available': True
                    }
                except Exception as e:
                    info['cooling_devices'][device_id] = {
                        'available': False,
                        'error': str(e)
                    }
                    
        # System information
        info['system_info'] = {
            'cpu_frequency_available': Path('/proc/cpuinfo').exists(),
            'load_average_available': Path('/proc/loadavg').exists(),
            'timestamp': datetime.now().isoformat()
        }
        
        return info