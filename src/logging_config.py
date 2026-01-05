"""
Logging configuration for Secure Drone project
"""

import logging
import os

# Create logs directory if it doesn't exist
os.makedirs('logs', exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/secure_drone.log'),
        logging.StreamHandler()
    ]
)

# Set up logger for this module
logger = logging.getLogger(__name__)
logger.info("Logging system initialized")