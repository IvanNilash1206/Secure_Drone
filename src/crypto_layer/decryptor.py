from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from src.crypto_layer.key_manager import load_key
from src.crypto_layer.nonce_manager import NonceManager

aesgcm = AESGCM(load_key())
nonce_mgr = NonceManager()

last_seen_counter = 0

def decrypt_payload(nonce: bytes, ciphertext: bytes) -> bytes:
    global last_seen_counter

    counter = nonce_mgr.extract_counter(nonce)

    # 🔁 Replay protection
    if counter <= last_seen_counter:
        raise ValueError("Replay attack detected")

    plaintext = aesgcm.decrypt(nonce, ciphertext, None)

    last_seen_counter = counter
    return plaintext
