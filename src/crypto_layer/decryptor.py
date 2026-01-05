from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from src.crypto_layer.key_manager import key_manager
from src.crypto_layer.nonce_manager import NonceManager
from src.logging_config import logger

# Global state for replay protection
last_seen_counter = 0
nonce_mgr = NonceManager()

def decrypt_payload(nonce: bytes, ciphertext: bytes) -> bytes:
    global last_seen_counter
    logger.info("Decrypting payload with session key")

    try:
        counter = nonce_mgr.extract_counter(nonce)
        logger.debug(f"Extracted counter: {counter}, last seen: {last_seen_counter}")

        # 🔁 Replay protection
        if counter <= last_seen_counter:
            logger.warning("Replay attack detected - escalating risk")
            key_manager.update_risk_level("high")
            raise ValueError("Replay attack detected")

        # Get current session key (handles rotation and validation)
        current_key = key_manager.get_active_session_key()
        cipher = AESGCM(current_key)

        plaintext = cipher.decrypt(nonce, ciphertext, None)
        logger.info("Payload decrypted successfully")

        last_seen_counter = counter

        # Increment command counter for rotation tracking
        key_manager.increment_command_counter()

        return plaintext

    except Exception as e:
        logger.error(f"Decryption failed: {e}")

        # Check if this is a key-related failure
        error_msg = str(e).lower()
        if "expired" in error_msg or "revoked" in error_msg:
            logger.critical("Key failure detected - initiating emergency protocols")
            # In a real system, this would trigger failsafe commands only
            raise ValueError("Cryptographic key failure - emergency mode activated")

        raise
