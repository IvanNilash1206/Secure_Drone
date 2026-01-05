import importlib
import time
from src.logging_config import logger

import pytest
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


@pytest.fixture()
def crypto_stack(monkeypatch):
    # Use an in-memory key so tests do not depend on aes_key.bin on disk.
    key = AESGCM.generate_key(bit_length=256)

    import src.crypto_layer.key_manager as key_manager

    monkeypatch.setattr(key_manager, "load_key", lambda: key)

    encryptor = importlib.reload(importlib.import_module("src.crypto_layer.encryptor"))
    decryptor = importlib.reload(importlib.import_module("src.crypto_layer.decryptor"))

    monkeypatch.setattr(decryptor, "last_seen_counter", 0)
    monkeypatch.setattr(encryptor, "nonce_mgr", encryptor.NonceManager())
    monkeypatch.setattr(decryptor, "nonce_mgr", decryptor.NonceManager())

    return encryptor, decryptor


def test_encrypt_decrypt_round_trip(crypto_stack):
    logger.info("Testing encrypt/decrypt round trip")
    encryptor, decryptor = crypto_stack

    payload = b"ARM_AND_TAKEOFF"
    nonce, ciphertext = encryptor.encrypt_payload(payload)
    plaintext = decryptor.decrypt_payload(nonce, ciphertext)

    assert plaintext == payload
    logger.info("Round trip test passed")


def test_replay_attack_is_rejected(crypto_stack):
    logger.info("Testing replay attack rejection")
    encryptor, decryptor = crypto_stack

    payload = b"RETURN_TO_LAUNCH"
    nonce, ciphertext = encryptor.encrypt_payload(payload)

    decryptor.decrypt_payload(nonce, ciphertext)

    with pytest.raises(ValueError):
        decryptor.decrypt_payload(nonce, ciphertext)
    logger.info("Replay attack correctly rejected")


def test_tamper_attack_fails(crypto_stack):
    logger.info("Testing tamper attack detection")
    encryptor, decryptor = crypto_stack

    payload = b"SET_MODE_GUIDED"
    nonce, ciphertext = encryptor.encrypt_payload(payload)
    tampered = bytearray(ciphertext)
    tampered[0] ^= 0xFF

    with pytest.raises(Exception):
        decryptor.decrypt_payload(nonce, bytes(tampered))
    logger.info("Tamper attack correctly detected")


def test_latency_encrypt_decrypt_budget(crypto_stack):
    logger.info("Testing crypto latency budget")
    encryptor, decryptor = crypto_stack

    payload = b"MISSION_ITEM"
    iterations = 20

    start = time.perf_counter()
    for _ in range(iterations):
        nonce, ciphertext = encryptor.encrypt_payload(payload)
        decryptor.decrypt_payload(nonce, ciphertext)
    avg_duration = (time.perf_counter() - start) / iterations

    assert avg_duration < 0.05, f"Crypto layer avg latency {avg_duration:.4f}s exceeded budget"
    logger.info(f"Crypto latency test passed: {avg_duration:.4f}s average")
