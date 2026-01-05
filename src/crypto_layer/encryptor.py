from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from src.crypto_layer.key_manager import load_key
from src.crypto_layer.nonce_manager import NonceManager
from src.logging_config import logger

aesgcm = AESGCM(load_key())
nonce_mgr = NonceManager()

def encrypt_payload(payload: bytes) -> tuple[bytes, bytes]:
    logger.info("Encrypting payload")
    nonce = nonce_mgr.next_nonce()
    logger.debug(f"Generated nonce with counter: {nonce_mgr.extract_counter(nonce)}")
    ciphertext = aesgcm.encrypt(nonce, payload, None)
    logger.info("Payload encrypted successfully")
    return nonce, ciphertext
