from decryptor import decrypt_payload
from src.logging_config import logger

def crypto_check(nonce, ciphertext):
    logger.info("Performing crypto check on incoming payload")
    try:
        payload = decrypt_payload(nonce, ciphertext)
        logger.info("Crypto check passed: payload decrypted successfully")
        return True, payload
    except Exception as e:
        logger.error(f"Crypto check failed: {e}")
        print(f"❌ Crypto reject: {e}")
        return False, None
