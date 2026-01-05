from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from src.crypto_layer.key_manager import key_manager
from src.crypto_layer.nonce_manager import NonceManager
from src.logging_config import logger

# Initialize AES-GCM with session key from key manager
aesgcm = AESGCM(key_manager.get_active_session_key())
nonce_mgr = NonceManager()

def encrypt_payload(payload: bytes) -> tuple[bytes, bytes]:
    logger.info("Encrypting payload with session key")
    try:
        nonce = nonce_mgr.next_nonce()
        logger.debug(f"Generated nonce with counter: {nonce_mgr.extract_counter(nonce)}")

        # Get fresh session key (handles rotation automatically)
        current_key = key_manager.get_active_session_key()
        cipher = AESGCM(current_key)

        ciphertext = cipher.encrypt(nonce, payload, None)
        logger.info("Payload encrypted successfully")

        # Increment command counter for rotation tracking
        key_manager.increment_command_counter()

        return nonce, ciphertext
    except Exception as e:
        logger.error(f"Encryption failed: {e}")
        raise
