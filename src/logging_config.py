"""
Logging configuration for AEGIS security system
"""
import logging
import sys
from pathlib import Path

# Create logs directory if it doesn't exist
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_dir / "aegis.log")
    ]
)

# Create logger instance
logger = logging.getLogger("AEGIS")
logger.setLevel(logging.INFO)
