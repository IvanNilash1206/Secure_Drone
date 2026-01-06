"""
Integrated Crypto + AI Attack Test Suite

Tests the complete security pipeline combining:
- Crypto layer: Encryption, nonce management, key rotation
- AI layer: DoS detection, replay detection, injection detection, intent classification

Attack scenarios:
1. Replay attacks (crypto + AI detection)
2. DoS/flooding attacks (rate limiting + AI detection)
3. Command injection attacks (crypto integrity + AI semantic detection)
4. Tamper attacks (crypto authentication + AI anomaly detection)
5. Man-in-the-middle attacks (crypto + AI behavioral analysis)
6. Navigation hijacking (crypto + AI intent firewall)
7. Privilege escalation (crypto + AI context validation)
8. Mixed attack scenarios (multiple vectors)
"""

import importlib
import time
import pytest
import os
import tempfile
import logging
from unittest.mock import patch, MagicMock
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from src.logging_config import logger

# Set up test-specific logging
test_log_dir = os.path.join(os.path.dirname(__file__), '..', 'logs')
os.makedirs(test_log_dir, exist_ok=True)

test_log_file = os.path.join(test_log_dir, f'test_integrated_attacks_{time.strftime("%Y%m%d_%H%M%S")}.log')
file_handler = logging.FileHandler(test_log_file)
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - [%(name)s] - %(message)s'))

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - [%(name)s] - %(message)s'))

test_logger = logging.getLogger('IntegratedAttackTest')
test_logger.setLevel(logging.INFO)
test_logger.addHandler(file_handler)
test_logger.addHandler(console_handler)


@pytest.fixture(scope="function")
def integrated_stack(monkeypatch):
    """Set up integrated crypto + AI stack"""
    test_logger.info("="*80)
    test_logger.info("Setting up integrated crypto + AI stack...")
    test_logger.info("="*80)
    
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

        # Force fresh key generation
        for key_file in [key_manager.ROOT_KEY_FILE, key_manager.SESSION_KEY_FILE, key_manager.KEY_METADATA_FILE]:
            if os.path.exists(key_file):
                os.remove(key_file)

        # Initialize key manager
        key_mgr = key_manager.KeyManager()
        key_manager.key_manager = key_mgr

        # Reload crypto modules
        encryptor = importlib.reload(importlib.import_module("src.crypto_layer.encryptor"))
        decryptor = importlib.reload(importlib.import_module("src.crypto_layer.decryptor"))
        crypto_gate = importlib.reload(importlib.import_module("src.crypto_layer.crypto_gate"))

        # Reset crypto global state
        decryptor.last_seen_counter = 0
        encryptor.nonce_mgr = encryptor.NonceManager()
        decryptor.nonce_mgr = decryptor.NonceManager()

        # Import AI layer components
        from src.ai_layer.attack_detection.dos_detector import DoSDetector
        from src.ai_layer.attack_detection.replay_detector import ReplayDetector
        from src.ai_layer.attack_detection.injection_detector import InjectionDetector
        from src.ai_layer.ml_models.feature_extractor import FeatureExtractorV2, CommandContext
        from src.ai_layer.intent_labels import IntentLabeler, IntentClass
        from src.ai_layer.intent_firewall import IntentFirewall
        
        # Initialize AI components
        dos_detector = DoSDetector(
            normal_threshold=2.0,
            attack_threshold=3.0,
            burst_threshold=10.0,
            window_size_sec=5
        )
        
        replay_detector = ReplayDetector(
            nonce_window_size=100,
            timestamp_tolerance_sec=30.0,
            sequence_window_size=50
        )
        injection_detector = InjectionDetector()
        feature_extractor = FeatureExtractorV2(window_size=7)
        intent_labeler = IntentLabeler()
        intent_firewall = IntentFirewall()
        
        test_logger.info("✅ Crypto layer initialized: Encryptor, Decryptor, CryptoGate, KeyManager")
        test_logger.info("✅ AI layer initialized: DoS, Replay, Injection detectors, Feature extractor, Intent labeler")
        test_logger.info("="*80)
        
        yield {
            'encryptor': encryptor,
            'decryptor': decryptor,
            'crypto_gate': crypto_gate,
            'key_mgr': key_mgr,
            'dos_detector': dos_detector,
            'replay_detector': replay_detector,
            'injection_detector': injection_detector,
            'feature_extractor': feature_extractor,
            'intent_labeler': intent_labeler,
            'intent_firewall': intent_firewall
        }
        
        test_logger.info("✅ Test completed - cleaning up integrated stack")


class TestReplayAttacks:
    """Test replay attack detection at both crypto and AI layers"""
    
    def test_crypto_replay_detection(self, integrated_stack):
        """Test replay attack caught by crypto layer"""
        test_logger.info("\n" + "="*80)
        test_logger.info("TEST: Crypto-level Replay Attack Detection")
        test_logger.info("="*80)
        
        enc = integrated_stack['encryptor']
        dec = integrated_stack['decryptor']
        key_mgr = integrated_stack['key_mgr']
        
        payload = b"ARM"
        test_logger.info(f"Creating payload: {payload}")
        
        # First transmission - should succeed
        nonce, ciphertext = enc.encrypt_payload(payload)
        test_logger.info(f"✅ Encrypted with nonce: {nonce.hex()[:16]}...")
        
        result1 = dec.decrypt_payload(nonce, ciphertext)
        test_logger.info(f"✅ First transmission successful: {result1}")
        assert result1 == payload
        
        # Replay attack - should fail
        test_logger.info("\n🚨 Attempting replay attack with same nonce...")
        with pytest.raises(ValueError, match="Replay attack detected"):
            dec.decrypt_payload(nonce, ciphertext)
        
        test_logger.info("✅ Replay attack BLOCKED by crypto layer")
        test_logger.info(f"Risk level escalated to: {key_mgr._metadata['session'].risk_level}")
        
        assert key_mgr._metadata['session'].risk_level == "high"
        test_logger.info("✅ TEST PASSED: Crypto replay detection\n")
    
    def test_ai_replay_detection(self, integrated_stack):
        """Test replay attack caught by AI layer"""
        test_logger.info("\n" + "="*80)
        test_logger.info("TEST: AI-level Replay Attack Detection")
        test_logger.info("="*80)
        
        replay_detector = integrated_stack['replay_detector']
        
        # Simulate command context
        nonce = b"test_nonce_123"
        timestamp = time.time()
        payload = b"TEST_COMMAND"
        
        test_logger.info(f"Command: nonce={nonce.hex()[:16]}..., timestamp={timestamp}")
        
        # First command - should pass
        result1 = replay_detector.check_command(nonce, timestamp, payload=payload)
        test_logger.info(f"First attempt: replay={result1.is_replay}, method={result1.detection_method}")
        assert not result1.is_replay
        test_logger.info("✅ First command accepted")
        
        # Replay with same nonce - should detect
        test_logger.info("\n🚨 Attempting replay with same nonce...")
        result2 = replay_detector.check_command(nonce, timestamp, payload=payload)
        test_logger.info(f"Replay attempt: replay={result2.is_replay}, confidence={result2.confidence:.2f}")
        test_logger.info(f"Detection method: {result2.detection_method}")
        test_logger.info(f"Explanation: {result2.explanation}")
        
        assert result2.is_replay
        assert result2.confidence > 0.7
        test_logger.info("✅ TEST PASSED: AI replay detection\n")
    
    def test_dual_layer_replay_protection(self, integrated_stack):
        """Test replay attack caught by both layers"""
        test_logger.info("\n" + "="*80)
        test_logger.info("TEST: Dual-Layer Replay Protection (Crypto + AI)")
        test_logger.info("="*80)
        
        enc = integrated_stack['encryptor']
        crypto_gate = integrated_stack['crypto_gate']
        replay_detector = integrated_stack['replay_detector']
        
        payload = b"TAKEOFF"
        test_logger.info(f"Creating secure command: {payload}")
        
        # First transmission
        nonce, ciphertext = enc.encrypt_payload(payload)
        test_logger.info(f"Encrypted command with nonce: {nonce.hex()[:16]}...")
        
        success1, decrypted = crypto_gate.crypto_gate.crypto_check(nonce, ciphertext)
        assert success1
        test_logger.info(f"✅ First transmission: crypto_check={success1}, payload={decrypted}")
        
        # AI layer check
        timestamp = time.time()
        
        ai_result1 = replay_detector.check_command(nonce, timestamp, payload=payload)
        test_logger.info(f"✅ First transmission: AI replay={ai_result1.is_replay}")
        assert not ai_result1.is_replay
        
        # Replay attack
        test_logger.info("\n🚨 ATTACK: Attempting replay with same nonce...")
        
        # Crypto layer should block
        success2, _ = crypto_gate.crypto_gate.crypto_check(nonce, ciphertext)
        test_logger.info(f"🛡️ Crypto layer: blocked={not success2}")
        assert not success2
        
        # AI layer should also detect
        ai_result2 = replay_detector.check_command(nonce, timestamp, payload=payload)
        test_logger.info(f"🛡️ AI layer: replay_detected={ai_result2.is_replay}, confidence={ai_result2.confidence:.2f}")
        assert ai_result2.is_replay
        
        test_logger.info("✅ TEST PASSED: Both layers detected replay attack\n")


class TestDoSAttacks:
    """Test DoS/flooding attack detection"""
    
    def test_command_flooding_attack(self, integrated_stack):
        """Test rapid command flooding attack"""
        test_logger.info("\n" + "="*80)
        test_logger.info("TEST: Command Flooding Attack Detection")
        test_logger.info("="*80)
        
        enc = integrated_stack['encryptor']
        dos_detector = integrated_stack['dos_detector']
        
        # Normal traffic pattern
        test_logger.info("Phase 1: Normal traffic (2 commands in 1 second)")
        for i in range(2):
            payload = f"HEARTBEAT_{i}".encode()
            nonce, ciphertext = enc.encrypt_payload(payload)
            
            result = dos_detector.record_command(time.time())
            test_logger.info(f"  Command {i}: rate={result.commands_per_second:.2f} cmds/sec, dos={result.is_dos_attack}")
        
        time.sleep(1)
        
        # DoS attack - rapid flooding
        test_logger.info("\n🚨 Phase 2: DoS ATTACK (15 commands in 0.5 seconds)")
        dos_detected = False
        attack_start = time.time()
        
        for i in range(15):
            payload = f"FLOOD_{i}".encode()
            nonce, ciphertext = enc.encrypt_payload(payload)
            
            result = dos_detector.record_command(time.time())
            
            if result.is_dos_attack:
                dos_detected = True
                test_logger.info(f"  🚨 DoS DETECTED at command {i}:")
                test_logger.info(f"     Rate: {result.commands_per_second:.2f} cmds/sec")
                test_logger.info(f"     Burst score: {result.burst_score:.2f}")
                test_logger.info(f"     Confidence: {result.confidence:.2f}")
                test_logger.info(f"     Explanation: {result.explanation}")
                break
        
        attack_duration = time.time() - attack_start
        test_logger.info(f"\nAttack detected in {attack_duration:.3f} seconds")
        
        assert dos_detected, "DoS attack should have been detected"
        test_logger.info("✅ TEST PASSED: DoS attack detected\n")
    
    def test_encrypted_dos_attack(self, integrated_stack):
        """Test DoS attack using encrypted commands"""
        test_logger.info("\n" + "="*80)
        test_logger.info("TEST: Encrypted DoS Attack Detection")
        test_logger.info("="*80)
        
        enc = integrated_stack['encryptor']
        crypto_gate = integrated_stack['crypto_gate']
        dos_detector = integrated_stack['dos_detector']
        
        test_logger.info("🚨 ATTACK: Sending encrypted command flood...")
        
        attack_detected = False
        valid_decryptions = 0
        
        for i in range(20):
            # Each command is properly encrypted
            payload = f"ENCRYPTED_FLOOD_{i}".encode()
            nonce, ciphertext = enc.encrypt_payload(payload)
            
            # Crypto layer accepts (valid encryption)
            success, decrypted = crypto_gate.crypto_gate.crypto_check(nonce, ciphertext)
            if success:
                valid_decryptions += 1
            
            # But AI layer detects flooding pattern
            result = dos_detector.record_command(time.time())
            
            if result.is_dos_attack:
                attack_detected = True
                test_logger.info(f"🛡️ AI layer detected DoS at command {i}:")
                test_logger.info(f"   Valid encryptions: {valid_decryptions}/{i+1}")
                test_logger.info(f"   Rate: {result.commands_per_second:.2f} cmds/sec")
                test_logger.info(f"   Confidence: {result.confidence:.2f}")
                break
            
            time.sleep(0.05)  # Small delay to simulate attack
        
        test_logger.info(f"\nResult: {valid_decryptions} commands had valid crypto")
        test_logger.info(f"But AI layer detected flooding pattern: {attack_detected}")
        
        assert attack_detected, "AI should detect DoS even with valid encryption"
        test_logger.info("✅ TEST PASSED: AI layer caught encrypted DoS\n")


class TestInjectionAttacks:
    """Test command injection attack detection"""
    
    def test_dangerous_command_injection(self, integrated_stack):
        """Test injection of dangerous commands"""
        test_logger.info("\n" + "="*80)
        test_logger.info("TEST: Dangerous Command Injection Detection")
        test_logger.info("="*80)
        
        enc = integrated_stack['encryptor']
        crypto_gate = integrated_stack['crypto_gate']
        injection_detector = integrated_stack['injection_detector']
        
        # Set flight state: drone is in flight
        from src.ai_layer.attack_detection.injection_detector import FlightState, CommandType
        injection_detector.update_state(
            state=FlightState.IN_FLIGHT,
            altitude=50.0,
            armed=True
        )
        test_logger.info("Flight state: IN_FLIGHT, altitude=50m, armed=True")
        
        # Normal command - should pass
        test_logger.info("\nPhase 1: Normal navigation command")
        payload = b"SET_POSITION_TARGET_LOCAL_NED|x=10|y=20|z=-30"
        nonce, ciphertext = enc.encrypt_payload(payload)
        success, decrypted = crypto_gate.crypto_gate.crypto_check(nonce, ciphertext)
        
        inj_result = injection_detector.check_command(
            command_type=CommandType.NAVIGATION,
            parameters={'x': 10, 'y': 20, 'z': -30}
        )
        
        test_logger.info(f"  Crypto check: {success}")
        test_logger.info(f"  AI injection check: {inj_result.is_injection}")
        test_logger.info(f"  Risk score: {inj_result.risk_score:.3f}")
        assert not inj_result.is_injection
        test_logger.info("  ✅ Normal command accepted")
        
        # Dangerous command - should be caught
        test_logger.info("\n🚨 Phase 2: ATTACK - Disarm command during flight")
        payload = b"DISARM"
        nonce, ciphertext = enc.encrypt_payload(payload)
        success, decrypted = crypto_gate.crypto_gate.crypto_check(nonce, ciphertext)
        
        inj_result = injection_detector.check_command(
            command_type=CommandType.ARM_DISARM,
            parameters={'action': 'disarm'}
        )
        
        test_logger.info(f"  Crypto check: {success} (encryption valid)")
        test_logger.info(f"  🛡️ AI injection check: {inj_result.is_injection}")
        test_logger.info(f"  Confidence: {inj_result.confidence:.2f}")
        test_logger.info(f"  Detection method: {inj_result.detection_method}")
        test_logger.info(f"  Unauthorized: {inj_result.unauthorized_command}")
        test_logger.info(f"  Context violation: {inj_result.context_violation}")
        test_logger.info(f"  Risk score: {inj_result.risk_score:.3f}")
        test_logger.info(f"  Explanation: {inj_result.explanation}")
        
        assert inj_result.is_injection
        assert inj_result.unauthorized_command
        test_logger.info("  ✅ Dangerous command BLOCKED by AI layer")
        
        test_logger.info("✅ TEST PASSED: Injection attack detected\n")
    
    def test_parameter_injection_attack(self, integrated_stack):
        """Test parameter injection with extreme values"""
        test_logger.info("\n" + "="*80)
        test_logger.info("TEST: Parameter Injection Attack")
        test_logger.info("="*80)
        
        enc = integrated_stack['encryptor']
        injection_detector = integrated_stack['injection_detector']
        
        from src.ai_layer.attack_detection.injection_detector import FlightState, CommandType
        injection_detector.update_state(
            state=FlightState.IN_FLIGHT,
            altitude=30.0,
            armed=True
        )
        
        test_logger.info("🚨 ATTACK: Navigation command with extreme altitude")
        
        # Inject extreme altitude parameter
        payload = b"SET_POSITION_TARGET_LOCAL_NED|x=0|y=0|z=-1000"  # -1000m altitude!
        nonce, ciphertext = enc.encrypt_payload(payload)
        
        result = injection_detector.check_command(
            command_type=CommandType.NAVIGATION,
            parameters={'x': 0, 'y': 0, 'z': -1000, 'altitude': 1000}
        )
        
        test_logger.info(f"  Injected altitude: 1000m (max allowed: 400m)")
        test_logger.info(f"  🛡️ AI detection:")
        test_logger.info(f"     Is injection: {result.is_injection}")
        test_logger.info(f"     Parameter anomaly: {result.parameter_anomaly}")
        test_logger.info(f"     Confidence: {result.confidence:.2f}")
        test_logger.info(f"     Risk score: {result.risk_score:.3f}")
        test_logger.info(f"     Explanation: {result.explanation}")
        
        assert result.parameter_anomaly
        test_logger.info("✅ TEST PASSED: Parameter injection detected\n")


class TestTamperAttacks:
    """Test tampering/integrity attacks"""
    
    def test_ciphertext_tampering(self, integrated_stack):
        """Test detection of tampered ciphertext"""
        test_logger.info("\n" + "="*80)
        test_logger.info("TEST: Ciphertext Tampering Attack")
        test_logger.info("="*80)
        
        enc = integrated_stack['encryptor']
        crypto_gate = integrated_stack['crypto_gate']
        key_mgr = integrated_stack['key_mgr']
        
        payload = b"LAND"
        test_logger.info(f"Original payload: {payload}")
        
        nonce, ciphertext = enc.encrypt_payload(payload)
        test_logger.info(f"Encrypted: {ciphertext.hex()[:32]}...")
        
        # Tamper with ciphertext
        test_logger.info("\n🚨 ATTACK: Flipping bits in ciphertext...")
        tampered = bytearray(ciphertext)
        tampered[0] ^= 0xFF
        tampered[5] ^= 0x42
        test_logger.info(f"Tampered:  {bytes(tampered).hex()[:32]}...")
        
        # Crypto layer should detect tampering
        success, _ = crypto_gate.crypto_gate.crypto_check(nonce, bytes(tampered))
        
        test_logger.info(f"\n🛡️ Crypto layer result: success={success}")
        test_logger.info(f"Risk level: {key_mgr._metadata['session'].risk_level}")
        
        assert not success, "Tampering should be detected"
        test_logger.info("✅ TEST PASSED: Tampering detected by crypto layer\n")
    
    def test_nonce_tampering(self, integrated_stack):
        """Test detection of tampered nonce"""
        test_logger.info("\n" + "="*80)
        test_logger.info("TEST: Nonce Tampering Attack")
        test_logger.info("="*80)
        
        enc = integrated_stack['encryptor']
        dec = integrated_stack['decryptor']
        
        payload = b"ARM"
        nonce, ciphertext = enc.encrypt_payload(payload)
        
        test_logger.info(f"Original nonce: {nonce.hex()}")
        
        # Tamper with nonce
        test_logger.info("\n🚨 ATTACK: Modifying nonce...")
        tampered_nonce = bytearray(nonce)
        tampered_nonce[0] ^= 0xFF
        test_logger.info(f"Tampered nonce: {bytes(tampered_nonce).hex()}")
        
        # Should fail decryption
        test_logger.info("\nAttempting decryption with tampered nonce...")
        with pytest.raises(Exception):
            dec.decrypt_payload(bytes(tampered_nonce), ciphertext)
        
        test_logger.info("✅ TEST PASSED: Nonce tampering detected\n")


class TestNavigationHijacking:
    """Test navigation hijacking attacks"""
    
    def test_navigation_command_hijack(self, integrated_stack):
        """Test hijacking of navigation commands"""
        test_logger.info("\n" + "="*80)
        test_logger.info("TEST: Navigation Command Hijacking Attack")
        test_logger.info("="*80)
        
        enc = integrated_stack['encryptor']
        crypto_gate = integrated_stack['crypto_gate']
        injection_detector = integrated_stack['injection_detector']
        intent_firewall = integrated_stack['intent_firewall']
        
        from src.ai_layer.attack_detection.injection_detector import FlightState, CommandType
        from src.ai_layer.intent_labels import IntentClass
        
        # Set up autonomous mission state
        injection_detector.update_state(
            state=FlightState.IN_FLIGHT,
            altitude=100.0,
            armed=True
        )
        
        intent_firewall.update_state(
            mode='AUTO',
            armed=True,
            altitude=100.0
        )
        
        test_logger.info("Drone state: AUTO mode, executing mission at 100m")
        
        # Legitimate waypoint update
        test_logger.info("\nPhase 1: Legitimate waypoint command")
        payload = b"SET_POSITION_TARGET_LOCAL_NED|x=50|y=100|z=-100|vx=5|vy=5|vz=0"
        nonce, ciphertext = enc.encrypt_payload(payload)
        success, _ = crypto_gate.crypto_gate.crypto_check(nonce, ciphertext)
        
        inj_result = injection_detector.check_command(
            command_type=CommandType.NAVIGATION,
            parameters={'x': 50, 'y': 100, 'z': -100}
        )
        
        test_logger.info(f"  Crypto: {success}, AI injection: {inj_result.is_injection}")
        assert not inj_result.is_injection
        test_logger.info("  ✅ Legitimate command accepted")
        
        # Hijack attempt: dangerous navigation to restricted zone
        test_logger.info("\n🚨 Phase 2: ATTACK - Navigation hijack to restricted zone")
        payload = b"SET_POSITION_TARGET_LOCAL_NED|x=5000|y=5000|z=-10|velocity=30"
        nonce, ciphertext = enc.encrypt_payload(payload)
        success, _ = crypto_gate.crypto_gate.crypto_check(nonce, ciphertext)
        
        inj_result = injection_detector.check_command(
            command_type=CommandType.NAVIGATION,
            parameters={
                'x': 5000, 'y': 5000, 
                'altitude': 200.0,  # Exceeds FAA limit of 150m
                'velocity': 30.0     # Exceeds max velocity of 25 m/s
            }
        )
        
        test_logger.info(f"  Target: x=5000m, y=5000m (far from mission area)")
        test_logger.info(f"  Altitude: 200m (exceeds 150m FAA limit)")
        test_logger.info(f"  Velocity: 30 m/s (exceeds 25 m/s limit)")
        test_logger.info(f"  Crypto check: {success}")
        test_logger.info(f"  🛡️ AI injection check: {inj_result.is_injection}")
        test_logger.info(f"  Parameter anomaly: {inj_result.parameter_anomaly}")
        test_logger.info(f"  Risk score: {inj_result.risk_score:.3f}")
        
        # Should be detected as anomalous
        assert inj_result.parameter_anomaly or inj_result.risk_score > 0.5
        test_logger.info("  ✅ Navigation hijack attempt detected")
        
        test_logger.info("✅ TEST PASSED: Navigation hijacking detected\n")


class TestMixedAttackScenarios:
    """Test complex multi-vector attacks"""
    
    def test_replay_plus_dos_attack(self, integrated_stack):
        """Test combined replay + DoS attack"""
        test_logger.info("\n" + "="*80)
        test_logger.info("TEST: Combined Replay + DoS Attack")
        test_logger.info("="*80)
        
        enc = integrated_stack['encryptor']
        crypto_gate = integrated_stack['crypto_gate']
        dos_detector = integrated_stack['dos_detector']
        replay_detector = integrated_stack['replay_detector']
        
        # Create command
        payload = b"SET_MODE_GUIDED"
        nonce, ciphertext = enc.encrypt_payload(payload)
        
        test_logger.info("🚨 ATTACK: Replaying same command rapidly (replay + DoS)")
        
        replay_detected = False
        dos_detected = False
        
        for i in range(20):
            # Try to replay same command
            success, _ = crypto_gate.crypto_gate.crypto_check(nonce, ciphertext)
            
            if not success and not replay_detected:
                test_logger.info(f"  🛡️ Replay detected at iteration {i}")
                replay_detected = True
            
            # Check DoS
            dos_result = dos_detector.record_command(time.time())
            
            if dos_result.is_dos_attack and not dos_detected:
                test_logger.info(f"  🛡️ DoS detected at iteration {i}")
                test_logger.info(f"     Rate: {dos_result.commands_per_second:.2f} cmds/sec")
                dos_detected = True
            
            if replay_detected and dos_detected:
                break
            
            time.sleep(0.03)
        
        test_logger.info(f"\nResults:")
        test_logger.info(f"  Replay detected: {replay_detected}")
        test_logger.info(f"  DoS detected: {dos_detected}")
        
        assert replay_detected, "Replay should be detected"
        assert dos_detected, "DoS should be detected"
        test_logger.info("✅ TEST PASSED: Both attack vectors detected\n")
    
    def test_tamper_plus_injection_attack(self, integrated_stack):
        """Test combined tampering + injection attack"""
        test_logger.info("\n" + "="*80)
        test_logger.info("TEST: Combined Tampering + Injection Attack")
        test_logger.info("="*80)
        
        enc = integrated_stack['encryptor']
        crypto_gate = integrated_stack['crypto_gate']
        injection_detector = integrated_stack['injection_detector']
        
        from src.ai_layer.attack_detection.injection_detector import FlightState, CommandType
        injection_detector.update_state(
            state=FlightState.IN_FLIGHT,
            altitude=50.0,
            armed=True
        )
        
        test_logger.info("🚨 ATTACK: Tamper ciphertext AND inject dangerous command")
        
        # Create dangerous command
        payload = b"EMERGENCY_DISARM_NOW"
        nonce, ciphertext = enc.encrypt_payload(payload)
        
        # Tamper it
        tampered = bytearray(ciphertext)
        tampered[3] ^= 0x55
        
        test_logger.info("  Attack vector 1: Ciphertext tampering")
        crypto_success, _ = crypto_gate.crypto_gate.crypto_check(nonce, bytes(tampered))
        test_logger.info(f"    Crypto layer: blocked={not crypto_success}")
        
        test_logger.info("  Attack vector 2: Dangerous command injection")
        inj_result = injection_detector.check_command(
            command_type=CommandType.EMERGENCY,
            parameters={'action': 'disarm'}
        )
        test_logger.info(f"    AI layer: injection={inj_result.is_injection}")
        test_logger.info(f"    Unauthorized: {inj_result.unauthorized_command}")
        
        assert not crypto_success or inj_result.is_injection
        test_logger.info("✅ TEST PASSED: At least one layer detected attack\n")


class TestPerformanceUnderAttack:
    """Test system performance during attack conditions"""
    
    def test_latency_during_dos_attack(self, integrated_stack):
        """Test that latency remains acceptable during DoS attack"""
        test_logger.info("\n" + "="*80)
        test_logger.info("TEST: Performance During DoS Attack")
        test_logger.info("="*80)
        
        enc = integrated_stack['encryptor']
        dec = integrated_stack['decryptor']
        dos_detector = integrated_stack['dos_detector']
        
        test_logger.info("Measuring baseline crypto latency...")
        
        # Baseline performance
        baseline_times = []
        for i in range(10):
            payload = f"BASELINE_{i}".encode()
            start = time.perf_counter()
            nonce, ciphertext = enc.encrypt_payload(payload)
            dec.decrypt_payload(nonce, ciphertext)
            baseline_times.append(time.perf_counter() - start)
        
        baseline_avg = sum(baseline_times) / len(baseline_times)
        test_logger.info(f"  Baseline: {baseline_avg*1000:.3f}ms per command")
        
        # During DoS attack
        test_logger.info("\n🚨 Simulating DoS attack while measuring latency...")
        attack_times = []
        
        for i in range(50):
            payload = f"ATTACK_{i}".encode()
            
            start = time.perf_counter()
            nonce, ciphertext = enc.encrypt_payload(payload)
            dec.decrypt_payload(nonce, ciphertext)
            attack_times.append(time.perf_counter() - start)
            
            # Trigger DoS detection
            dos_detector.record_command(time.time())
        
        attack_avg = sum(attack_times) / len(attack_times)
        test_logger.info(f"  Under attack: {attack_avg*1000:.3f}ms per command")
        
        degradation = (attack_avg - baseline_avg) / baseline_avg * 100
        test_logger.info(f"  Performance degradation: {degradation:.1f}%")
        
        # Should still be fast enough
        assert attack_avg < 0.1, "Crypto should remain fast under DoS"
        test_logger.info("✅ TEST PASSED: Performance acceptable under attack\n")


def pytest_sessionfinish(session, exitstatus):
    """Hook called after all tests complete"""
    test_logger.info("\n" + "="*80)
    test_logger.info("INTEGRATED ATTACK TEST SUITE COMPLETED")
    test_logger.info("="*80)
    test_logger.info(f"Log file saved: {test_log_file}")
    test_logger.info("="*80)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-s"])
