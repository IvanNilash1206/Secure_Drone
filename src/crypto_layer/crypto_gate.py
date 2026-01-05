from decryptor import decrypt_payload


def crypto_check(nonce, ciphertext):
    try:
        payload = decrypt_payload(nonce, ciphertext)
        return True, payload
    except Exception as e:
        print(f"❌ Crypto reject: {e}")
        return False, None
