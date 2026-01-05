from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import os

KEY_FILE = "crypto_layer/aes_key.bin"

def generate_key():
    key = AESGCM.generate_key(bit_length=256)
    if not os.path.exists(KEY_FILE):
        os.makedirs(os.path.dirname(KEY_FILE), exist_ok=True)
    with open(KEY_FILE, "wb") as f:
        f.write(key)
    print("✅ AES-256 key generated")

def load_key():
    with open(KEY_FILE, "rb") as f:
        return f.read()

if __name__ == "__main__":
    generate_key()
