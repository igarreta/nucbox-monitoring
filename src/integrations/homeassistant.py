#!/usr/bin/env python3
"""
Home Assistant integration for NucBox monitoring
Handles sensor updates and notifications
"""

import json
import logging
import requests
from datetime import datetime, timedelta


class HomeAssistantClient:
    """Client for Home Assistant API integration"""
    
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        self.base_url = config['url'].rstrip('/')
        self.token = config['token']
        self.timeout = config.get('timeout', 10)
        
        self.headers = {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json'
        }
        
    def test_connection(self):
        """Test connection to Home Assistant"""
        try:
            response = requests.get(
                f'{self.base_url}/api/',
                headers=self.headers,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                self.logger.debug("Home Assistant connection test successful")
                return True
            else:
                self.logger.error(f"HA connection test failed: {response.status_code}")
                return False
                
        except Exception as e:
            self.logger.error(f"HA connection test error: {e}")
            return False
            
    def update_sensor(self, entity_id, state, attributes=None):
        """Update sensor state in Home Assistant"""
        try:
            url = f'{self.base_url}/api/states/sensor.{entity_id}'
            
            data = {
                'state': str(state),
                'attributes': attributes or {}
            }
            
            # Add default attributes
            data['attributes'].update({
                'last_updated': datetime.now().isoformat(),
                'source': 'nucbox-monitoring'
            })
            
            response = requests.post(
                url,
                headers=self.headers,
                json=data,
                timeout=self.timeout
            )
            
            if response.status_code in [200, 201]:
                self.logger.debug(f"Updated sensor {entity_id}: {state}")
                return True
            else:
                self.logger.error(
                    f"Failed to update sensor {entity_id}: {response.status_code} - {response.text}"
                )
                return False
                
        except Exception as e:
            self.logger.error(f"Error updating sensor {entity_id}: {e}")
            return False
            
    def send_notification(self, title, message, data=None):
        """Send notification through Home Assistant"""
        try:
            url = f'{self.base_url}/api/services/notify/notify'
            
            payload = {
                'message': message,
                'title': title,
                'data': data or {}
            }
            
            # Add default notification data
            payload['data'].update({
                'timestamp': datetime.now().isoformat(),
                'source': 'nucbox-monitoring'
            })
            
            response = requests.post(
                url,
                headers=self.headers,
                json=payload,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                self.logger.debug(f"Notification sent: {title}")
                return True
            else:
                self.logger.error(
                    f"Failed to send notification: {response.status_code} - {response.text}"
                )
                return False
                
        except Exception as e:
            self.logger.error(f"Error sending notification: {e}")
            return False
            
    def call_service(self, domain, service, service_data=None):
        """Call Home Assistant service"""
        try:
            url = f'{self.base_url}/api/services/{domain}/{service}'
            
            response = requests.post(
                url,
                headers=self.headers,
                json=service_data or {},
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                self.logger.debug(f"Service called: {domain}.{service}")
                return True
            else:
                self.logger.error(
                    f"Failed to call service {domain}.{service}: "
                    f"{response.status_code} - {response.text}"
                )
                return False
                
        except Exception as e:
            self.logger.error(f"Error calling service {domain}.{service}: {e}")
            return False
            
    def get_sensor_state(self, entity_id):
        """Get current state of a sensor"""
        try:
            url = f'{self.base_url}/api/states/sensor.{entity_id}'
            
            response = requests.get(
                url,
                headers=self.headers,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'state': data.get('state'),
                    'attributes': data.get('attributes', {}),
                    'last_changed': data.get('last_changed'),
                    'last_updated': data.get('last_updated')
                }
            else:
                self.logger.error(f"Failed to get sensor state {entity_id}: {response.status_code}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error getting sensor state {entity_id}: {e}")
            return None
            
    def create_sensor_config(self, entity_id, name, config):
        """Create sensor configuration (for MQTT discovery-like behavior)"""
        # This would be used if we implemented MQTT auto-discovery
        # For REST API, sensors are created when first updated
        pass
        
    def get_system_info(self):
        """Get Home Assistant system information"""
        try:
            url = f'{self.base_url}/api/config'
            
            response = requests.get(
                url,
                headers=self.headers,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                self.logger.error(f"Failed to get system info: {response.status_code}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error getting system info: {e}")
            return None