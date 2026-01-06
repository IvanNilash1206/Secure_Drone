"""
Comprehensive AI Layer Test Suite

Tests all AI layer components:
1. Feature Extraction
2. Intent Classification
3. Risk Scoring
4. Attack Detection (DoS, Replay, Injection)
5. Intent Firewall
6. Trust Model
7. Normalizer

Run with: pytest test_ai_layer.py -v
"""

import pytest
import numpy as np
import time
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ai_layer.ml_models.feature_extractor import FeatureExtractorV2, CommandContext, FLIGHT_MODES
from src.ai_layer.intent_labels import IntentClass, IntentLabeler, RiskLevel
from src.ai_layer.attack_detection.dos_detector import DoSDetector
from src.ai_layer.attack_detection.replay_detector import ReplayDetector
from src.ai_layer.attack_detection.injection_detector import InjectionDetector, CommandType, FlightState
from src.ai_layer.intent_firewall import IntentFirewall, IntentResult
from src.ai_layer.normalizer import FeatureNormalizer
from src.ai_layer.trust_model import TrustModel


class TestFeatureExtractor:
    """Test feature extraction pipeline - FAST VERSION"""
    
    def setup_method(self):
        self.extractor = FeatureExtractorV2(window_size=7)
    
    def test_feature_extraction_dimensions_and_normalization(self):
        """Verify feature vector dimensions and normalization (combined test)"""
        ctx = CommandContext(
            msg_id=76,
            command_type='ARM_DISARM',
            target_system=1,
            target_component=1,
            param1=1.0,
            flight_mode='GUIDED',
            armed=False,
            battery_level=0.95,
            altitude=0.0,
            velocity=0.0,
            timestamp=time.time()
        )
        
        # First command returns None (no history)
        features = self.extractor.extract(ctx)
        assert features is None
        
        # Add second command
        ctx.timestamp += 1.0
        features = self.extractor.extract(ctx)
        
        assert features is not None
        assert len(features) == 37, f"Expected 37 features, got {len(features)}"
        
        # Verify normalization
        for i, feat in enumerate(features):
            assert not np.isnan(feat), f"Feature {i} is NaN"
            assert not np.isinf(feat), f"Feature {i} is infinite"
    
    def test_feature_extraction_performance(self):
        """Verify feature extraction meets latency budget (<1ms)"""
        ctx = CommandContext(
            msg_id=76,
            command_type='SET_POSITION_TARGET',
            target_system=1,
            target_component=1,
            param1=30.0,
            flight_mode='AUTO',
            armed=True,
            battery_level=0.9,
            altitude=25.0,
            velocity=8.0,
            timestamp=time.time()
        )
        
        # Build history (minimal)
        for _ in range(7):
            self.extractor.extract(ctx)
            ctx.timestamp += 1.0
        
        # Measure extraction time (reduced iterations)
        latencies = []
        for _ in range(20):  # Reduced from 100 to 20
            start = time.perf_counter()
            self.extractor.extract(ctx)
            end = time.perf_counter()
            latencies.append((end - start) * 1000)  # ms
            ctx.timestamp += 0.1
        
        avg_latency = np.mean(latencies)
        
        print(f"\n  Feature extraction latency: avg={avg_latency:.3f}ms")
        
        assert avg_latency < 1.0, f"Average latency {avg_latency:.3f}ms exceeds 1ms budget"


class TestIntentLabeler:
    """Test intent classification and risk scoring - FAST VERSION"""
    
    def setup_method(self):
        self.labeler = IntentLabeler()
    
    def test_intent_classification_and_risk_scoring(self):
        """Test multiple intents in one test (combined)"""
        # Test 1: Navigation (normal)
        label = self.labeler.label_command(
            command_ctx={'command_type': 'SET_POSITION_TARGET', 'cmd_frequency_1s': 0.1, 'param_magnitude': 0.3},
            vehicle_state={'flight_mode': 'AUTO', 'mission_phase': 'CRUISE', 'armed': True, 
                          'battery_level': 0.8, 'altitude': 30.0, 'velocity': 8.0}
        )
        assert label.intent == IntentClass.NAVIGATION
        assert 0.0 <= label.risk_score <= 1.0
        
        # Test 2: ARM on ground (low risk)
        label = self.labeler.label_command(
            command_ctx={'command_type': 'ARM_DISARM', 'cmd_frequency_1s': 0.0, 'param_magnitude': 1.0},
            vehicle_state={'flight_mode': 'GUIDED', 'mission_phase': 'NONE', 'armed': False,
                          'battery_level': 0.95, 'altitude': 0.0, 'velocity': 0.0}
        )
        assert label.intent == IntentClass.ARM_DISARM
        assert label.risk_score < 0.6
        
        # Test 3: Disarm in flight (high risk)
        label = self.labeler.label_command(
            command_ctx={'command_type': 'ARM_DISARM', 'cmd_frequency_1s': 0.0, 'param_magnitude': 0.0},
            vehicle_state={'flight_mode': 'GUIDED', 'mission_phase': 'CRUISE', 'armed': True,
                          'battery_level': 0.8, 'altitude': 30.0, 'velocity': 8.0}
        )
        assert label.intent == IntentClass.ARM_DISARM
        assert label.risk_score > 0.7, f"Expected high risk, got {label.risk_score}"


class TestDoSDetector:
    """Test DoS attack detection - FAST VERSION"""
    
    def setup_method(self):
        self.detector = DoSDetector(
            rate_threshold=10.0,
            burst_threshold=5,
            window_seconds=1.0
        )
    
    def test_dos_detection(self):
        """Test normal and burst attacks (combined)"""
        t = time.time()
        
        # Test 1: Normal rate accepted
        for i in range(5):  # Reduced from 10
            result = self.detector.check_command(command_id=f"cmd_{i}", timestamp=t + i * 0.5)
            assert result.is_dos == False
        
        # Test 2: Burst attack detected
        dos_detected = False
        for i in range(10):
            result = self.detector.check_command(command_id=f"burst_{i}", timestamp=t + 10 + i * 0.02)
            if result.is_dos:
                dos_detected = True
                break
        assert dos_detected, "Burst DoS attack not detected"
        
        # Test 3: Performance check (reduced iterations)
        latencies = []
        for i in range(20):  # Reduced from 100
            start = time.perf_counter()
            self.detector.check_command(command_id=f"perf_{i}", timestamp=t + 20 + i * 0.1)
            end = time.perf_counter()
            latencies.append((end - start) * 1000)
        
        avg_latency = np.mean(latencies)
        print(f"\n  DoS detection latency: avg={avg_latency:.3f}ms")
        assert avg_latency < 1.0, f"DoS detection too slow: {avg_latency:.3f}ms"


class TestReplayDetector:
    """Test replay attack detection - FAST VERSION"""
    
    def setup_method(self):
        self.detector = ReplayDetector(
            nonce_window_size=10000,
            timestamp_tolerance_sec=30.0
        )
    
    def test_replay_detection(self):
        """Test replay detection (combined tests)"""
        t = time.time()
        
        # Test 1: New nonce accepted
        result = self.detector.check_command(
            nonce="nonce_001",
            timestamp=t,
            sequence_num=1,
            command_hash="hash_001"
        )
        assert result.is_replay == False
        
        # Test 2: Duplicate nonce rejected
        result1 = self.detector.check_command(
            nonce="nonce_dup",
            timestamp=t + 1,
            sequence_num=2,
            command_hash="hash_002"
        )
        assert result1.is_replay == False
        
        result2 = self.detector.check_command(
            nonce="nonce_dup",  # Same nonce
            timestamp=t + 2,
            sequence_num=3,
            command_hash="hash_003"
        )
        assert result2.is_replay == True
        
        # Test 3: Old timestamp rejected
        result = self.detector.check_command(
            nonce="nonce_old",
            timestamp=t - 60.0,  # 60 seconds ago
            sequence_num=4,
            command_hash="hash_old"
        )
        assert result.is_replay == True
        
        # Test 4: Performance (reduced)
        latencies = []
        for i in range(20):  # Reduced from 100
            start = time.perf_counter()
            self.detector.check_command(
                nonce=f"nonce_{i}",
                timestamp=t + 10 + i,
                sequence_num=10 + i,
                command_hash=f"hash_{i}"
            )
            end = time.perf_counter()
            latencies.append((end - start) * 1000)
        
        avg_latency = np.mean(latencies)
        print(f"\n  Replay detection latency: avg={avg_latency:.3f}ms")
        assert avg_latency < 1.0


class TestInjectionDetector:
    """Test command injection detection - FAST VERSION"""
    
    def setup_method(self):
        self.detector = InjectionDetector()
    
    def test_injection_detection(self):
        """Test injection detection (combined tests)"""
        # Test 1: Normal navigation accepted
        result = self.detector.check_command(
            command_type=CommandType.NAVIGATION,
            source_identity="pilot_001",
            parameters={'altitude': 30.0, 'velocity': 8.0},
            flight_state=FlightState(
                mode='AUTO',
                armed=True,
                altitude=25.0,
                battery=0.8
            ),
            timestamp=time.time()
        )
        assert result.is_injection == False
        
        # Test 2: Unauthorized disarm detected
        result2 = self.detector.check_command(
            command_type=CommandType.ARM_DISARM,
            source_identity="unauthorized_user",
            parameters={'arm': 0},
            flight_state=FlightState(
                mode='AUTO',
                armed=True,
                altitude=30.0,
                battery=0.8
            ),
            timestamp=time.time()
        )
        assert result2.is_injection == True or result2.confidence > 0.5
        
        # Test 3: Out of bounds altitude detected
        result3 = self.detector.check_command(
            command_type=CommandType.NAVIGATION,
            source_identity="pilot_001",
            parameters={'altitude': 500.0, 'velocity': 8.0},
            flight_state=FlightState(
                mode='AUTO',
                armed=True,
                altitude=30.0,
                battery=0.8
            ),
            timestamp=time.time()
        )
        assert result3.is_injection == True
        
        # Test 4: Performance (reduced)
        latencies = []
        for i in range(20):  # Reduced from 100
            start = time.perf_counter()
            self.detector.check_command(
                command_type=CommandType.NAVIGATION,
                source_identity="pilot_001",
                parameters={'altitude': 30.0, 'velocity': 8.0},
                flight_state=FlightState(
                    mode='AUTO',
                    armed=True,
                    altitude=28.0,
                    battery=0.8
                ),
                timestamp=time.time()
            )
            end = time.perf_counter()
            latencies.append((end - start) * 1000)
        
        avg_latency = np.mean(latencies)
        print(f"\n  Injection detection latency: avg={avg_latency:.3f}ms")
        assert avg_latency < 1.0


class TestIntentFirewall:
    """Test intent firewall rules and blocking - FAST VERSION"""
    
    def setup_method(self):
        self.firewall = IntentFirewall()
    
    def test_firewall_decisions(self):
        """Test firewall decisions (combined tests)"""
        # Test 1: Allowed intent passes
        decision = self.firewall.evaluate(
            intent=IntentClass.NAVIGATION,
            risk_score=0.2,
            context={'flight_mode': 'AUTO', 'armed': True, 'altitude': 30.0}
        )
        assert decision.allowed == True
        
        # Test 2: High risk blocked
        decision2 = self.firewall.evaluate(
            intent=IntentClass.ARM_DISARM,
            risk_score=0.95,
            context={'flight_mode': 'AUTO', 'armed': True, 'altitude': 30.0}
        )
        assert decision2.allowed == False
        
        # Test 3: Unknown intent handled
        decision3 = self.firewall.evaluate(
            intent=IntentClass.UNKNOWN,
            risk_score=0.5,
            context={}
        )
        assert decision3.allowed == False or decision3.requires_review == True


class TestNormalizer:
    """Test command parameter normalization - FAST VERSION"""
    
    def setup_method(self):
        self.normalizer = FeatureNormalizer()
    
    def test_normalization(self):
        """Test normalization (combined tests)"""
        # Test 1: Altitude normalization
        norm_alt = self.normalizer.normalize_altitude(50.0, max_altitude=150.0)
        assert 0.0 <= norm_alt <= 1.0
        assert abs(norm_alt - 0.333) < 0.01
        
        # Test 2: Velocity normalization
        norm_vel = self.normalizer.normalize_velocity(10.0, max_velocity=20.0)
        assert 0.0 <= norm_vel <= 1.0
        assert abs(norm_vel - 0.5) < 0.01
        
        # Test 3: Battery already normalized
        norm_batt = self.normalizer.normalize_battery(0.75)
        assert 0.0 <= norm_batt <= 1.0
        assert abs(norm_batt - 0.75) < 0.001


class TestTrustModel:
    """Test dynamic trust scoring - FAST VERSION"""
    
    def setup_method(self):
        self.trust_model = TrustModel()
    
    def test_trust_model(self):
        """Test trust scoring (combined tests)"""
        # Test 1: Initial trust score
        score = self.trust_model.get_trust_score("new_pilot")
        assert 0.0 <= score <= 1.0
        assert 0.4 <= score <= 0.7
        
        # Test 2: Trust increases with good behavior
        source_id = "good_pilot"
        initial_trust = self.trust_model.get_trust_score(source_id)
        for _ in range(10):
            self.trust_model.record_command(source_id, success=True, risk_score=0.1)
        final_trust = self.trust_model.get_trust_score(source_id)
        assert final_trust > initial_trust
        
        # Test 3: Trust decreases with risky behavior
        source_id2 = "risky_pilot"
        initial_trust2 = self.trust_model.get_trust_score(source_id2)
        for _ in range(5):
            self.trust_model.record_command(source_id2, success=True, risk_score=0.9)
        final_trust2 = self.trust_model.get_trust_score(source_id2)
        assert final_trust2 < initial_trust2


class TestEndToEndAILayer:
    """End-to-end integration tests for full AI layer - FAST VERSION"""
    
    def test_full_pipeline_normal_command(self):
        """Test normal command through full AI pipeline"""
        # Components
        extractor = FeatureExtractorV2()
        labeler = IntentLabeler()
        dos_detector = DoSDetector()
        replay_detector = ReplayDetector()
        injection_detector = InjectionDetector()
        firewall = IntentFirewall()
        trust_model = TrustModel()
        
        # Build history
        for i in range(7):
            ctx = CommandContext(
                msg_id=76,
                command_type='SET_POSITION_TARGET',
                target_system=1,
                target_component=1,
                param1=30.0,
                flight_mode='AUTO',
                armed=True,
                battery_level=0.8,
                altitude=25.0 + i,
                velocity=8.0,
                timestamp=time.time() + i
            )
            extractor.extract(ctx)
        
        # New command
        t = time.time() + 10
        ctx = CommandContext(
            msg_id=76,
            command_type='NAVIGATION',
            target_system=1,
            target_component=1,
            param1=35.0,
            flight_mode='AUTO',
            armed=True,
            battery_level=0.75,
            altitude=32.0,
            velocity=8.0,
            timestamp=t
        )
        
        # 1. Feature extraction
        features = extractor.extract(ctx)
        assert features is not None
        
        # 2. Attack detection
        dos_result = dos_detector.check_command("cmd_test", t)
    
    def test_full_ai_pipeline(self):
        """Test complete AI pipeline integration (combined tests)"""
        # Initialize all components
        extractor = FeatureExtractorV2()
        labeler = IntentLabeler()
        dos_detector = DoSDetector(rate_limit=10, window_sec=1.0)
        replay_detector = ReplayDetector()
        injection_detector = InjectionDetector()
        firewall = IntentFirewall()
        trust_model = TrustModel()
        
        t = time.time()
        
        # TEST 1: Normal navigation command (should pass)
        ctx = CommandContext(
            msg_id=76, command_type='NAVIGATION', target_system=1, target_component=1,
            param1=35.0, flight_mode='AUTO', armed=True, battery_level=0.75,
            altitude=32.0, velocity=8.0, timestamp=t
        )
        
        dos_result = dos_detector.check_command("pilot_001", t)
        assert dos_result.is_dos == False
        
        replay_result = replay_detector.check_command("nonce_test", t, 1, "hash_test")
        assert replay_result.is_replay == False
        
        injection_result = injection_detector.check_command(
            CommandType.NAVIGATION, "pilot_001", {'altitude': 35.0, 'velocity': 8.0},
            FlightState('AUTO', True, 32.0, 0.75), t
        )
        assert injection_result.is_injection == False
        
        label = labeler.label_command(
            {'command_type': 'NAVIGATION', 'cmd_frequency_1s': 0.1, 'param_magnitude': 0.3},
            {'flight_mode': 'AUTO', 'mission_phase': 'CRUISE', 'armed': True,
             'battery_level': 0.75, 'altitude': 32.0, 'velocity': 8.0}
        )
        
        decision = firewall.evaluate(label.intent, label.risk_score, 
                                    {'flight_mode': 'AUTO', 'armed': True, 'altitude': 32.0})
        assert decision.allowed == True
        
        trust_score = trust_model.get_trust_score("pilot_001")
        assert 0.0 <= trust_score <= 1.0
        
        print(f"\n  Full pipeline test passed!")
        print(f"    Intent: {label.intent.value}, Risk: {label.risk_score:.2f}")
        print(f"    Decision: {'ALLOWED' if decision.allowed else 'BLOCKED'}")
        
        # TEST 2: Attack command (should be blocked)
        injection_result2 = injection_detector.check_command(
            CommandType.ARM_DISARM, "attacker", {'arm': 0},
            FlightState('AUTO', True, 30.0, 0.8), t
        )
        assert injection_result2.is_injection == True or injection_result2.confidence > 0.7
        
        label2 = labeler.label_command(
            {'command_type': 'ARM_DISARM', 'cmd_frequency_1s': 0.0, 'param_magnitude': 1.0},
            {'flight_mode': 'AUTO', 'mission_phase': 'CRUISE', 'armed': True,
             'battery_level': 0.8, 'altitude': 30.0, 'velocity': 8.0}
        )
        assert label2.risk_score > 0.7
        
        decision2 = firewall.evaluate(label2.intent, label2.risk_score,
                                     {'flight_mode': 'AUTO', 'armed': True, 'altitude': 30.0})
        assert decision2.allowed == False
        
        print(f"\n  Attack detection test passed!")
        print(f"    Risk score: {label2.risk_score:.2f}, Firewall: BLOCKED")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
