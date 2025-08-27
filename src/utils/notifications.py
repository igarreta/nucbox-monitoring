#!/usr/bin/env python3
"""
Notification management utilities
Handles rate limiting, priority, and notification types
"""

import time
import logging
from datetime import datetime, timedelta


class NotificationManager:
    """Manage notifications with rate limiting and priorities"""
    
    def __init__(self, ha_client, config=None):
        self.ha_client = ha_client
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # Rate limiting configuration (seconds)
        self.rate_limits = self.config.get('rate_limit', {
            'critical': 300,    # 5 minutes
            'warning': 600,     # 10 minutes
            'info': 1800,       # 30 minutes
            'normal': 900       # 15 minutes
        })
        
        # Enabled notification types
        self.enabled_types = set(self.config.get('enabled_types', [
            'temperature_critical',
            'temperature_warning',
            'fan_state_change', 
            'throttling_change',
            'workload_complete'
        ]))
        
        # Track last notification times
        self.last_notifications = {}
        
    def send_notification(self, title, message, priority='normal', notification_type=None):
        """Send notification with rate limiting"""
        
        # Check if notification type is enabled
        if notification_type and notification_type not in self.enabled_types:
            self.logger.debug(f"Notification type {notification_type} is disabled")
            return False
            
        # Check rate limiting
        if not self._check_rate_limit(notification_type, priority):
            self.logger.debug(f"Rate limit hit for {notification_type} ({priority})")
            return False
            
        # Prepare notification data
        notification_data = {
            'priority': priority,
            'tag': 'nucbox-thermal',
            'notification_type': notification_type,
            'timestamp': datetime.now().isoformat()
        }
        
        # Add priority-specific data
        if priority == 'critical':
            notification_data.update({
                'color': 'red',
                'sound': 'alarm',
                'persistent': True
            })
        elif priority == 'high':
            notification_data.update({
                'color': 'orange', 
                'sound': 'default'
            })
        elif priority == 'normal':
            notification_data.update({
                'color': 'blue',
                'sound': 'none'
            })
            
        # Send notification
        success = self.ha_client.send_notification(title, message, notification_data)
        
        if success:
            # Update rate limiting tracker
            key = f"{notification_type}_{priority}"
            self.last_notifications[key] = time.time()
            self.logger.info(f"Notification sent: {title} ({priority})")
        else:
            self.logger.error(f"Failed to send notification: {title}")
            
        return success
        
    def _check_rate_limit(self, notification_type, priority):
        """Check if notification passes rate limiting"""
        if not notification_type:
            return True
            
        key = f"{notification_type}_{priority}"
        last_sent = self.last_notifications.get(key, 0)
        rate_limit = self.rate_limits.get(priority, 900)  # Default 15 minutes
        
        time_since_last = time.time() - last_sent
        
        return time_since_last >= rate_limit
        
    def send_critical_alert(self, title, message, notification_type=None):
        """Send critical priority notification"""
        return self.send_notification(
            title, 
            message, 
            priority='critical',
            notification_type=notification_type
        )
        
    def send_warning(self, title, message, notification_type=None):
        """Send warning priority notification"""
        return self.send_notification(
            title,
            message,
            priority='high', 
            notification_type=notification_type
        )
        
    def send_info(self, title, message, notification_type=None):
        """Send info priority notification"""
        return self.send_notification(
            title,
            message,
            priority='normal',
            notification_type=notification_type
        )
        
    def clear_rate_limits(self):
        """Clear all rate limiting history"""
        self.last_notifications.clear()
        self.logger.info("Rate limiting history cleared")
        
    def get_notification_status(self):
        """Get current notification status"""
        current_time = time.time()
        status = {}
        
        for key, last_sent in self.last_notifications.items():
            notification_type, priority = key.rsplit('_', 1)
            rate_limit = self.rate_limits.get(priority, 900)
            time_since_last = current_time - last_sent
            time_until_next = max(0, rate_limit - time_since_last)
            
            status[key] = {
                'last_sent': datetime.fromtimestamp(last_sent).isoformat(),
                'time_since_last': int(time_since_last),
                'time_until_next': int(time_until_next),
                'can_send': time_until_next == 0
            }
            
        return status
        
    def update_config(self, new_config):
        """Update notification configuration"""
        self.config.update(new_config)
        
        # Update rate limits
        if 'rate_limit' in new_config:
            self.rate_limits.update(new_config['rate_limit'])
            
        # Update enabled types
        if 'enabled_types' in new_config:
            self.enabled_types = set(new_config['enabled_types'])
            
        self.logger.info("Notification configuration updated")
        
    def test_notifications(self):
        """Send test notifications for each priority level"""
        test_notifications = [
            ('normal', '✅ Test Normal Priority', 'This is a normal priority test notification'),
            ('high', '⚠️ Test High Priority', 'This is a high priority test notification'),  
            ('critical', '🚨 Test Critical Priority', 'This is a critical priority test notification')
        ]
        
        results = {}
        for priority, title, message in test_notifications:
            success = self.send_notification(
                title, 
                message,
                priority=priority,
                notification_type='test'
            )
            results[priority] = success
            time.sleep(1)  # Brief delay between tests
            
        return results