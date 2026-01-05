from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from src.crypto_layer.key_manager import load_key
from src.crypto_layer.nonce_manager import NonceManager
from src.logging_config import logger

aesgcm = AESGCM(load_key())
nonce_mgr = NonceManager()

last_seen_counter = 0

def decrypt_payload(nonce: bytes, ciphertext: bytes) -> bytes:
    global last_seen_counter
    logger.info("Decrypting payload")

    counter = nonce_mgr.extract_counter(nonce)
    logger.debug(f"Extracted counter: {counter}, last seen: {last_seen_counter}")

    # 🔁 Replay protection
    if counter <= last_seen_counter:
        logger.warning("Replay attack detected")
        raise ValueError("Replay attack detected")

    plaintext = aesgcm.decrypt(nonce, ciphertext, None)
    logger.info("Payload decrypted successfully")

    last_seen_counter = counter
    return plaintext
