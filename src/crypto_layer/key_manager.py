from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import os
from src.logging_config import logger

KEY_FILE = "crypto_layer/aes_key.bin"

def generate_key():
    logger.info("Generating new AES-256 key")
    key = AESGCM.generate_key(bit_length=256)
    if not os.path.exists(KEY_FILE):
        os.makedirs(os.path.dirname(KEY_FILE), exist_ok=True)
    with open(KEY_FILE, "wb") as f:
        f.write(key)
    logger.info("AES-256 key generated and saved")
    print("✅ AES-256 key generated")

def load_key():
    logger.debug("Loading AES key from file")
    with open(KEY_FILE, "rb") as f:
        return f.read()

if __name__ == "__main__":
    generate_key()
