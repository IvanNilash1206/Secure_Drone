from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from src.crypto_layer.key_manager import load_key
from src.crypto_layer.nonce_manager import NonceManager

aesgcm = AESGCM(load_key())
nonce_mgr = NonceManager()

def encrypt_payload(payload: bytes) -> tuple[bytes, bytes]:
    nonce = nonce_mgr.next_nonce()
    ciphertext = aesgcm.encrypt(nonce, payload, None)
    return nonce, ciphertext
