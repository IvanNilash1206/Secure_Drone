import os
import struct
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.logging_config import logger

NONCE_SIZE = 12  # AES-GCM standard

class NonceManager:
    def __init__(self):
        logger.debug("Initializing NonceManager")
        self.counter = 0

    def next_nonce(self):
        self.counter += 1
        nonce = struct.pack(">Q", self.counter).rjust(NONCE_SIZE, b'\x00')
        logger.debug(f"Generated nonce for counter: {self.counter}")
        return nonce

    def extract_counter(self, nonce):
        counter = struct.unpack(">Q", nonce[-8:])[0]
        logger.debug(f"Extracted counter: {counter}")
        return counter
