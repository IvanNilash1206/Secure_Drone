import importlib
import time
import pytest
import os
import tempfile
from unittest.mock import patch, MagicMock
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

import pytest
from src.logging_config import logger

@pytest.fixture()
def crypto_stack(monkeypatch):
    """Set up crypto stack with hierarchical key management"""
    # Create temporary directory for keys
    with tempfile.TemporaryDirectory() as temp_dir:
        key_dir = os.path.join(temp_dir, "crypto_layer")
        os.makedirs(key_dir, exist_ok=True)

        # Mock the key file paths BEFORE importing
        monkeypatch.setattr("src.crypto_layer.key_manager.ROOT_KEY_FILE", os.path.join(key_dir, "root_key.pem"))
        monkeypatch.setattr("src.crypto_layer.key_manager.SESSION_KEY_FILE", os.path.join(key_dir, "session_key.bin"))
        monkeypatch.setattr("src.crypto_layer.key_manager.KEY_METADATA_FILE", os.path.join(key_dir, "key_metadata.json"))

        # Force reimport of key_manager to get new paths
        import sys
        if "src.crypto_layer.key_manager" in sys.modules:
            del sys.modules["src.crypto_layer.key_manager"]

        import src.crypto_layer.key_manager as key_manager
        importlib.reload(key_manager)

        # Reload dependent modules
        encryptor = importlib.reload(importlib.import_module("src.crypto_layer.encryptor"))
        decryptor = importlib.reload(importlib.import_module("src.crypto_layer.decryptor"))
        crypto_gate = importlib.reload(importlib.import_module("src.crypto_layer.crypto_gate"))

        # Reset global state
        decryptor.last_seen_counter = 0
        encryptor.nonce_mgr = encryptor.NonceManager()
        decryptor.nonce_mgr = decryptor.NonceManager()

        yield encryptor, decryptor, crypto_gate, key_manager.key_manager


def test_key_hierarchy_initialization(crypto_stack):
    """Test that key hierarchy initializes correctly"""
    encryptor, decryptor, crypto_gate, key_mgr = crypto_stack

    logger.info("Testing key hierarchy initialization")

    # Check that keys exist
    assert key_mgr._root_key is not None
    assert key_mgr._session_key is not None
    assert len(key_mgr._session_key) == 32

    # Check metadata
    assert "root" in key_mgr._metadata
    assert "session" in key_mgr._metadata

    # Check key status
    status = key_mgr.get_key_status()
    assert "root" in status
    assert "session" in status
    assert status["session"]["state"] == "active"

    logger.info("Key hierarchy initialization test passed")


def test_encrypt_decrypt_round_trip(crypto_stack):
    """Test encrypt/decrypt round trip with hierarchical keys"""
    encryptor, decryptor, crypto_gate, key_mgr = crypto_stack

    logger.info("Testing encrypt/decrypt round trip with session keys")

    payload = b"ARM_AND_TAKEOFF"
    nonce, ciphertext = encryptor.encrypt_payload(payload)
    plaintext = decryptor.decrypt_payload(nonce, ciphertext)

    assert plaintext == payload

    # Check command counter incremented
    assert key_mgr._metadata["session"].command_count >= 1

    logger.info("Round trip test passed")


def test_crypto_gate_validation(crypto_stack):
    """Test crypto gate with timestamp validation"""
    encryptor, decryptor, crypto_gate, key_mgr = crypto_stack

    logger.info("Testing crypto gate validation")

    # Test valid payload
    payload = f"ARM_AND_TAKEOFF|{time.time()}|test".encode()
    nonce, ciphertext = encryptor.encrypt_payload(payload)

    success, decrypted = crypto_gate.crypto_gate.crypto_check(nonce, ciphertext)
    assert success
    assert decrypted == payload

    logger.info("Crypto gate validation test passed")


def test_replay_attack_is_rejected(crypto_stack):
    """Test replay attack detection and risk escalation"""
    encryptor, decryptor, crypto_gate, key_mgr = crypto_stack

    logger.info("Testing replay attack rejection")

    payload = b"RETURN_TO_LAUNCH"
    nonce, ciphertext = encryptor.encrypt_payload(payload)

    # First decryption should succeed
    decryptor.decrypt_payload(nonce, ciphertext)

    # Second decryption should fail (replay)
    with pytest.raises(ValueError, match="Replay attack detected"):
        decryptor.decrypt_payload(nonce, ciphertext)

    # Check risk level escalated
    assert key_mgr._metadata["session"].risk_level == "high"

    logger.info("Replay attack correctly rejected")


def test_tamper_attack_fails(crypto_stack):
    """Test tamper attack detection"""
    encryptor, decryptor, crypto_gate, key_mgr = crypto_stack

    logger.info("Testing tamper attack detection")

    payload = b"SET_MODE_GUIDED"
    nonce, ciphertext = encryptor.encrypt_payload(payload)
    tampered = bytearray(ciphertext)
    tampered[0] ^= 0xFF

    with pytest.raises(Exception):
        decryptor.decrypt_payload(nonce, bytes(tampered))

    logger.info("Tamper attack correctly detected")


def test_session_key_rotation(crypto_stack):
    """Test automatic session key rotation"""
    encryptor, decryptor, crypto_gate, key_mgr = crypto_stack

    logger.info("Testing session key rotation")

    # Get initial session key info
    initial_session_id = key_mgr._metadata["session"].session_id
    initial_key = key_mgr._session_key

    # Force rotation by setting high command count
    from src.crypto_layer.key_manager import MAX_COMMANDS_PER_SESSION
    key_mgr._metadata["session"].command_count = MAX_COMMANDS_PER_SESSION + 1
    key_mgr.rotate_session_key("test_rotation")

    # Check rotation occurred
    new_session_id = key_mgr._metadata["session"].session_id
    new_key = key_mgr._session_key

    assert initial_session_id != new_session_id
    assert initial_key != new_key
    assert key_mgr._metadata["session"].command_count == 0

    logger.info("Session key rotation test passed")


def test_key_expiry_handling(crypto_stack):
    """Test key expiry handling"""
    encryptor, decryptor, crypto_gate, key_mgr = crypto_stack

    logger.info("Testing key expiry handling")

    # Expire session key
    key_mgr._metadata["session"].expires_at = time.time() - 1

    # Attempt to get key should fail
    with pytest.raises(ValueError, match="Session key expired"):
        key_mgr.get_active_session_key()

    logger.info("Key expiry handling test passed")


def test_emergency_key_revocation(crypto_stack):
    """Test emergency key revocation"""
    encryptor, decryptor, crypto_gate, key_mgr = crypto_stack

    logger.info("Testing emergency key revocation")

    # Revoke session key
    key_mgr.revoke_session_key("test_emergency")

    # Check key is revoked
    assert key_mgr._metadata["session"].state.name == "REVOKED"

    # Attempt to get key should fail
    with pytest.raises(ValueError, match="No active session key"):
        key_mgr.get_active_session_key()

    logger.info("Emergency key revocation test passed")


def test_latency_encrypt_decrypt_budget(crypto_stack):
    """Test crypto latency budget with hierarchical keys"""
    encryptor, decryptor, crypto_gate, key_mgr = crypto_stack

    logger.info("Testing crypto latency budget")

    payload = b"MISSION_ITEM"
    iterations = 20

    start = time.perf_counter()
    for _ in range(iterations):
        nonce, ciphertext = encryptor.encrypt_payload(payload)
        decryptor.decrypt_payload(nonce, ciphertext)
    avg_duration = (time.perf_counter() - start) / iterations

    assert avg_duration < 0.05, f"Crypto layer avg latency {avg_duration:.4f}s exceeded budget"
    logger.info(".4f")


def test_key_hierarchy_validation(crypto_stack):
    """Test key hierarchy validation"""
    encryptor, decryptor, crypto_gate, key_mgr = crypto_stack

    logger.info("Testing key hierarchy validation")

    # Valid hierarchy should pass
    assert key_mgr.validate_key_hierarchy()

    # Corrupt session key
    original_key = key_mgr._session_key
    key_mgr._session_key = b"invalid"
    assert not key_mgr.validate_key_hierarchy()

    # Restore
    key_mgr._session_key = original_key
    assert key_mgr.validate_key_hierarchy()

    logger.info("Key hierarchy validation test passed")


def test_timestamp_validation(crypto_stack):
    """Test timestamp validation in crypto gate"""
    encryptor, decryptor, crypto_gate, key_mgr = crypto_stack

    logger.info("Testing timestamp validation")

    gate = crypto_gate.crypto_gate

    # Valid timestamp
    valid_payload = f"COMMAND|{time.time()}|data".encode()
    assert gate._validate_timestamp(valid_payload)

    # Invalid timestamp (too old)
    invalid_payload = f"COMMAND|{time.time() - 60}|data".encode()
    assert not gate._validate_timestamp(invalid_payload)

    # No timestamp (should pass)
    no_timestamp_payload = b"COMMAND"
    assert gate._validate_timestamp(no_timestamp_payload)

    logger.info("Timestamp validation test passed")
    logger.info("Replay attack correctly rejected")


def test_tamper_attack_fails(crypto_stack):
    logger.info("Testing tamper attack detection")
    encryptor, decryptor, crypto_gate, key_mgr = crypto_stack

    payload = b"SET_MODE_GUIDED"
    nonce, ciphertext = encryptor.encrypt_payload(payload)
    tampered = bytearray(ciphertext)
    tampered[0] ^= 0xFF

    with pytest.raises(Exception):
        decryptor.decrypt_payload(nonce, bytes(tampered))
    logger.info("Tamper attack correctly detected")


def test_latency_encrypt_decrypt_budget(crypto_stack):
    logger.info("Testing crypto latency budget")
    encryptor, decryptor, crypto_gate, key_mgr = crypto_stack

    payload = b"MISSION_ITEM"
    iterations = 20

    start = time.perf_counter()
    for _ in range(iterations):
        nonce, ciphertext = encryptor.encrypt_payload(payload)
        decryptor.decrypt_payload(nonce, ciphertext)
    avg_duration = (time.perf_counter() - start) / iterations

    assert avg_duration < 0.05, f"Crypto layer avg latency {avg_duration:.4f}s exceeded budget"
    logger.info(f"Crypto latency test passed: {avg_duration:.4f}s average")
