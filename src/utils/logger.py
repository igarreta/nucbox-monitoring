#!/usr/bin/env python3
"""
Logging configuration utilities
"""

import logging
import logging.handlers
from pathlib import Path


def setup_logging(config):
    """Setup logging configuration"""
    
    # Default configuration
    log_config = {
        'level': 'INFO',
        'file': '/home/rsi/logs/nucbox-monitoring/hub.log',
        'max_size': '10MB',
        'backup_count': 5,
        'console': True
    }
    
    # Update with provided config
    log_config.update(config)
    
    # Create log directory
    log_file = Path(log_config['file'])
    log_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Setup root logger
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, log_config['level'].upper()))
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # File handler with rotation
    max_bytes = _parse_size(log_config['max_size'])
    file_handler = logging.handlers.RotatingFileHandler(
        log_config['file'],
        maxBytes=max_bytes,
        backupCount=int(log_config['backup_count'])
    )
    
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    # Console handler
    if log_config.get('console', True):
        console_handler = logging.StreamHandler()
        console_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
    
    return logger


def _parse_size(size_str):
    """Parse size string like '10MB' into bytes"""
    size_str = size_str.upper()
    
    multipliers = {
        'B': 1,
        'KB': 1024,
        'MB': 1024 * 1024,
        'GB': 1024 * 1024 * 1024
    }
    
    for suffix, multiplier in multipliers.items():
        if size_str.endswith(suffix):
            number = float(size_str[:-len(suffix)])
            return int(number * multiplier)
    
    # Default to bytes if no suffix
    return int(size_str)