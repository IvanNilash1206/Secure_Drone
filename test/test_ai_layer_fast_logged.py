"""
Fast Test Suite for AI Layer Components with Comprehensive Logging
Optimized for quick execution while maintaining full test coverage and detailed logging
"""

import pytest
import time
import numpy as np
import logging
from dataclasses import dataclass
from typing import Dict, Any
from pathlib import Path
import sys
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configure logging
log_dir = Path(__file__).parent.parent / "logs"
log_dir.mkdir(exist_ok=True)
log_file = log_dir / f"test_ai_layer_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

# Setup logging with both file and console output
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(name)s] - %(message)s',
    handlers=[
        logging.FileHandler(log_file, mode='w', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ],
    force=True
)
logger = logging.getLogger('AILayerTest')

# Log test suite start
logger.info("=" * 80)
logger.info("AI LAYER TEST SUITE STARTED")
logger.info(f"Log file: {log_file}")
logger.info(f"Test start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
logger.info("=" * 80)

# Import AI layer components
from src.ai_layer.ml_models.feature_extractor import FeatureExtractorV2, CommandContext
from src.ai_layer.intent_labels import IntentLabeler, IntentClass
from src.ai_layer.attack_detection.dos_detector import DoSDetector
from src.ai_layer.attack_detection.replay_detector import ReplayDetector
from src.ai_layer.attack_detection.injection_detector import InjectionDetector, CommandType, FlightState
from src.ai_layer.intent_firewall import IntentFirewall
from src.ai_layer.normalizer import FeatureNormalizer
from src.ai_layer.trust_model import TrustModel

logger.info("All AI layer modules imported successfully")


class TestFeatureExtractor:
    """Test feature extraction with detailed logging"""
    
    def setup_method(self):
        logger.info("\n" + "=" * 80)
        logger.info("TEST CLASS: TestFeatureExtractor")
        logger.info("=" * 80)
        logger.info("Setting up FeatureExtractorV2...")
        self.extractor = FeatureExtractorV2()
        logger.info("✅ FeatureExtractorV2 initialized successfully")
    
    def test_feature_extraction(self):
        """Test feature extraction with performance metrics"""
        logger.info("\n--- TEST: test_feature_extraction ---")
        logger.info("Creating test command context...")
        
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
        logger.info(f"Command context: type={ctx.command_type}, altitude={ctx.altitude}m, mode={ctx.flight_mode}")
        
        # Build history
        logger.info("Building command history (7 commands)...")
        for i in range(7):
            features = self.extractor.extract(ctx)
            ctx.timestamp += 1.0
        logger.info(f"History built. Feature vector size: {len(features)}")
        
        # Test dimensions
        assert features is not None
        assert len(features) > 0
        logger.info(f"✅ Feature dimension test passed: {len(features)} features")
        
        # Performance test
        logger.info("Running performance test (10 iterations)...")
        latencies = []
        for i in range(10):
            start = time.perf_counter()
            self.extractor.extract(ctx)
            end = time.perf_counter()
            latency_ms = (end - start) * 1000
            latencies.append(latency_ms)
            ctx.timestamp += 0.1
            if i % 3 == 0:
                logger.info(f"  Iteration {i+1}: {latency_ms:.3f}ms")
        
        avg_latency = np.mean(latencies)
        min_latency = np.min(latencies)
        max_latency = np.max(latencies)
        
        logger.info(f"\nPerformance Results:")
        logger.info(f"  Average latency: {avg_latency:.3f}ms")
        logger.info(f"  Min latency: {min_latency:.3f}ms")
        logger.info(f"  Max latency: {max_latency:.3f}ms")
        logger.info(f"  Std deviation: {np.std(latencies):.3f}ms")
        
        assert avg_latency < 2.0
        logger.info("✅ Performance requirement met: avg < 2.0ms")
        logger.info("✅ TEST PASSED: test_feature_extraction\n")


class TestIntentLabeler:
    """Test intent classification with detailed logging"""
    
    def setup_method(self):
        logger.info("\n" + "=" * 80)
        logger.info("TEST CLASS: TestIntentLabeler")
        logger.info("=" * 80)
        logger.info("Setting up IntentLabeler...")
        self.labeler = IntentLabeler()
        logger.info("✅ IntentLabeler initialized successfully")
    
    def test_intent_labeling(self):
        """Test intent labeling for different scenarios"""
        logger.info("\n--- TEST: test_intent_labeling ---")
        
        # Test 1: Navigation command
        logger.info("\n[Test 1] Navigation command labeling:")
        label = self.labeler.label_command(
            command_ctx={'command_type': 'SET_POSITION_TARGET', 'cmd_frequency_1s': 0.1, 'param_magnitude': 0.3},
            vehicle_state={'flight_mode': 'AUTO', 'mission_phase': 'CRUISE', 'armed': True,
                          'battery_level': 0.8, 'altitude': 30.0, 'velocity': 8.0}
        )
        logger.info(f"  Intent: {label.intent}")
        logger.info(f"  Risk score: {label.risk_score:.3f}")
        logger.info(f"  Reasoning: {label.reasoning}")
        assert label.intent == IntentClass.NAVIGATION
        assert 0.0 <= label.risk_score <= 1.0
        logger.info("✅ Navigation intent correctly identified")
        
        # Test 2: ARM on ground (low risk)
        logger.info("\n[Test 2] ARM on ground (low risk):")
        label2 = self.labeler.label_command(
            command_ctx={'command_type': 'ARM_DISARM', 'cmd_frequency_1s': 0.0, 'param_magnitude': 1.0},
            vehicle_state={'flight_mode': 'GUIDED', 'mission_phase': 'NONE', 'armed': False,
                          'battery_level': 0.95, 'altitude': 0.0, 'velocity': 0.0}
        )
        logger.info(f"  Intent: {label2.intent}")
        logger.info(f"  Risk score: {label2.risk_score:.3f}")
        logger.info(f"  Reasoning: {label2.reasoning}")
        assert label2.intent == IntentClass.ARM_DISARM
        assert label2.risk_score < 0.6
        logger.info("✅ ARM intent correctly identified with low risk")
        logger.info("✅ TEST PASSED: test_intent_labeling\n")


class TestDoSDetector:
    """Test DoS attack detection with detailed logging"""
    
    def setup_method(self):
        logger.info("\n" + "=" * 80)
        logger.info("TEST CLASS: TestDoSDetector")
        logger.info("=" * 80)
        logger.info("Setting up DoSDetector...")
        self.detector = DoSDetector(
            normal_threshold=5.0,
            attack_threshold=20.0,
            burst_threshold=50.0
        )
        logger.info("✅ DoSDetector initialized (normal=5.0, attack=20.0, burst=50.0 cmds/sec)")
    
    def test_dos_detection(self):
        """Test DoS detection for normal and attack traffic"""
        logger.info("\n--- TEST: test_dos_detection ---")
        t = time.time()
        
        # Test 1: Normal rate
        logger.info("\n[Test 1] Normal traffic rate (5 commands over 2.5 seconds):")
        for i in range(5):
            metrics = self.detector.record_command(t + i * 0.5)
        logger.info(f"  Commands/sec: {metrics.commands_per_second:.2f}")
        logger.info(f"  DoS detected: {metrics.is_dos_attack}")
        logger.info(f"  Burst score: {metrics.burst_score:.2f}")
        assert metrics.is_dos_attack == False
        logger.info("✅ Normal traffic correctly identified")
        
        # Test 2: Attack rate
        logger.info("\n[Test 2] Attack traffic rate (30 commands in ~1 second):")
        for i in range(30):
            metrics = self.detector.record_command(t + 10 + i * 0.03)
        logger.info(f"  Commands/sec: {metrics.commands_per_second:.2f}")
        logger.info(f"  DoS detected: {metrics.is_dos_attack}")
        logger.info(f"  Confidence: {metrics.confidence:.2f}")
        logger.info(f"  Explanation: {metrics.explanation}")
        assert metrics.is_dos_attack == True
        logger.info("✅ DoS attack correctly detected")
        
        # Test 3: Performance
        logger.info("\n[Test 3] Performance measurement:")
        latencies = []
        for i in range(10):
            start = time.perf_counter()
            self.detector.record_command(t + 20 + i)
            end = time.perf_counter()
            latencies.append((end - start) * 1000)
        
        avg_latency = np.mean(latencies)
        logger.info(f"  Average latency: {avg_latency:.3f}ms")
        logger.info(f"  Min latency: {np.min(latencies):.3f}ms")
        logger.info(f"  Max latency: {np.max(latencies):.3f}ms")
        assert avg_latency < 1.0
        logger.info("✅ Performance requirement met: avg < 1.0ms")
        logger.info("✅ TEST PASSED: test_dos_detection\n")


class TestReplayDetector:
    """Test replay attack detection with detailed logging"""
    
    def setup_method(self):
        logger.info("\n" + "=" * 80)
        logger.info("TEST CLASS: TestReplayDetector")
        logger.info("=" * 80)
        logger.info("Setting up ReplayDetector...")
        self.detector = ReplayDetector()
        logger.info("✅ ReplayDetector initialized successfully")
    
    def test_replay_detection(self):
        """Test replay detection for various scenarios"""
        logger.info("\n--- TEST: test_replay_detection ---")
        t = time.time()
        
        # Test 1: New nonce
        logger.info("\n[Test 1] New nonce acceptance:")
        result = self.detector.check_command(
            nonce=b"nonce_001",
            timestamp=t,
            command_hash=b"hash_001"
        )
        logger.info(f"  Is replay: {result.is_replay}")
        logger.info(f"  Confidence: {result.confidence:.2f}")
        assert result.is_replay == False
        logger.info("✅ New nonce correctly accepted")
        
        # Test 2: Duplicate nonce
        logger.info("\n[Test 2] Duplicate nonce detection:")
        result_dup1 = self.detector.check_command(
            nonce=b"nonce_duplicate",
            timestamp=t + 1,
            command_hash=b"hash_002"
        )
        result_dup2 = self.detector.check_command(
            nonce=b"nonce_duplicate",
            timestamp=t + 2,
            command_hash=b"hash_003"
        )
        logger.info(f"  First occurrence: replay={result_dup1.is_replay}")
        logger.info(f"  Second occurrence: replay={result_dup2.is_replay}")
        logger.info(f"  Detection method: {result_dup2.detection_method}")
        assert result_dup2.is_replay == True
        logger.info("✅ Duplicate nonce correctly detected")
        
        # Test 3: Performance
        logger.info("\n[Test 3] Performance measurement:")
        latencies = []
        for i in range(10):
            start = time.perf_counter()
            self.detector.check_command(
                nonce=f"nonce_{i}".encode(),
                timestamp=t + 10 + i,
                command_hash=f"hash_{i}".encode()
            )
            end = time.perf_counter()
            latencies.append((end - start) * 1000)
        
        avg_latency = np.mean(latencies)
        logger.info(f"  Average latency: {avg_latency:.3f}ms")
        assert avg_latency < 1.0
        logger.info("✅ Performance requirement met: avg < 1.0ms")
        logger.info("✅ TEST PASSED: test_replay_detection\n")


class TestInjectionDetector:
    """Test injection attack detection with detailed logging"""
    
    def setup_method(self):
        logger.info("\n" + "=" * 80)
        logger.info("TEST CLASS: TestInjectionDetector")
        logger.info("=" * 80)
        logger.info("Setting up InjectionDetector...")
        self.detector = InjectionDetector()
        logger.info("✅ InjectionDetector initialized successfully")
    
    def test_injection_detection(self):
        """Test injection detection for various attack patterns"""
        logger.info("\n--- TEST: test_injection_detection ---")
        t = time.time()
        
        # Set state
        logger.info("Setting flight state: IN_FLIGHT, altitude=30m, armed=True")
        self.detector.update_state(
            state=FlightState.IN_FLIGHT,
            altitude=30.0,
            armed=True
        )
        
        # Test 1: Normal command
        logger.info("\n[Test 1] Normal navigation command:")
        result = self.detector.check_command(
            command_type=CommandType.NAVIGATION,
            parameters={'altitude': 30.0, 'velocity': 8.0}
        )
        logger.info(f"  Is injection: {result.is_injection}")
        logger.info(f"  Risk score: {result.risk_score:.3f}")
        assert result.is_injection == False
        logger.info("✅ Normal command correctly accepted")
        
        # Test 2: Dangerous command
        logger.info("\n[Test 2] Dangerous command (disarm in flight):")
        result2 = self.detector.check_command(
            command_type=CommandType.ARM_DISARM,
            parameters={'arm': 0}
        )
        logger.info(f"  Is injection: {result2.is_injection}")
        logger.info(f"  Confidence: {result2.confidence:.2f}")
        logger.info(f"  Detection method: {result2.detection_method}")
        logger.info(f"  Unauthorized: {result2.unauthorized_command}")
        assert result2.is_injection == True or result2.confidence > 0.5
        logger.info("✅ Dangerous command correctly detected")
        
        # Test 3: Parameter violation
        logger.info("\n[Test 3] Parameter violation (altitude too high):")
        result3 = self.detector.check_command(
            command_type=CommandType.NAVIGATION,
            parameters={'altitude': 500.0, 'velocity': 8.0}
        )
        logger.info(f"  Is injection: {result3.is_injection}")
        logger.info(f"  Parameter anomaly: {result3.parameter_anomaly}")
        assert result3.is_injection == True or result3.parameter_anomaly == True
        logger.info("✅ Parameter violation correctly detected")
        
        # Test 4: Performance
        logger.info("\n[Test 4] Performance measurement:")
        latencies = []
        for i in range(10):
            start = time.perf_counter()
            self.detector.check_command(
                command_type=CommandType.NAVIGATION,
                parameters={'altitude': 30.0, 'velocity': 8.0}
            )
            end = time.perf_counter()
            latencies.append((end - start) * 1000)
        
        avg_latency = np.mean(latencies)
        logger.info(f"  Average latency: {avg_latency:.3f}ms")
        assert avg_latency < 1.0
        logger.info("✅ Performance requirement met: avg < 1.0ms")
        logger.info("✅ TEST PASSED: test_injection_detection\n")


class TestIntentFirewall:
    """Test intent firewall with detailed logging"""
    
    def setup_method(self):
        logger.info("\n" + "=" * 80)
        logger.info("TEST CLASS: TestIntentFirewall")
        logger.info("=" * 80)
        logger.info("Setting up IntentFirewall...")
        self.firewall = IntentFirewall()
        logger.info("✅ IntentFirewall initialized successfully")
    
    def test_firewall_basic(self):
        """Test firewall basic functionality"""
        logger.info("\n--- TEST: test_firewall_basic ---")
        logger.info("Testing state update: mode=AUTO, armed=True, altitude=30m")
        self.firewall.update_state(
            mode="AUTO",
            armed=True,
            altitude=30.0
        )
        logger.info(f"  Current mode: {self.firewall.current_mode}")
        logger.info(f"  Armed: {self.firewall.armed}")
        logger.info(f"  Altitude: {self.firewall.altitude}m")
        assert self.firewall.armed == True
        assert self.firewall.altitude == 30.0
        logger.info("✅ State update working correctly")
        logger.info("✅ TEST PASSED: test_firewall_basic\n")


class TestFeatureNormalizer:
    """Test feature normalizer with detailed logging"""
    
    def setup_method(self):
        logger.info("\n" + "=" * 80)
        logger.info("TEST CLASS: TestFeatureNormalizer")
        logger.info("=" * 80)
        logger.info("Setting up FeatureNormalizer...")
        self.normalizer = FeatureNormalizer()
        logger.info("✅ FeatureNormalizer initialized successfully")
    
    def test_normalization(self):
        """Test normalization"""
        logger.info("\n--- TEST: test_normalization ---")
        X = np.array([[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]])
        logger.info(f"Input data shape: {X.shape}")
        logger.info(f"Input data:\n{X}")
        
        self.normalizer.fit(X)
        logger.info(f"Fit complete. Mean: {self.normalizer.mean}, Std: {self.normalizer.std}")
        assert self.normalizer.mean is not None
        assert self.normalizer.std is not None
        logger.info("✅ Normalization fit successful")
        logger.info("✅ TEST PASSED: test_normalization\n")


class TestTrustModel:
    """Test trust model with detailed logging"""
    
    def setup_method(self):
        logger.info("\n" + "=" * 80)
        logger.info("TEST CLASS: TestTrustModel")
        logger.info("=" * 80)
        logger.info("Setting up TrustModel...")
        self.model = TrustModel()
        logger.info("✅ TrustModel initialized successfully")
    
    def test_trust_model(self):
        """Test trust scoring"""
        logger.info("\n--- TEST: test_trust_model ---")
        features = [0.001, 0.001, 1.0, 1.0, 0.5, 0]
        logger.info(f"Test features: {features}")
        score = self.model.trust_score(features)
        logger.info(f"Trust score: {score:.4f}")
        assert isinstance(score, float)
        logger.info("✅ Trust score calculated successfully")
        logger.info("✅ TEST PASSED: test_trust_model\n")


class TestEndToEndPipeline:
    """Test end-to-end pipeline with detailed logging"""
    
    def test_minimal_pipeline(self):
        """Test minimal end-to-end pipeline"""
        logger.info("\n" + "=" * 80)
        logger.info("TEST CLASS: TestEndToEndPipeline")
        logger.info("=" * 80)
        logger.info("\n--- TEST: test_minimal_pipeline ---")
        logger.info("Initializing all pipeline components...")
        
        extractor = FeatureExtractorV2()
        dos_detector = DoSDetector()
        labeler = IntentLabeler()
        logger.info("✅ All components initialized")
        
        # Test command flow
        logger.info("\nTesting complete command flow:")
        t = time.time()
        
        logger.info("Step 1: DoS detection...")
        dos_metrics = dos_detector.record_command(t)
        logger.info(f"  DoS detected: {dos_metrics.is_dos_attack}, rate: {dos_metrics.commands_per_second:.2f} cmds/sec")
        
        logger.info("Step 2: Feature extraction...")
        ctx = CommandContext(
            msg_id=76, command_type='NAVIGATION', target_system=1, target_component=1,
            param1=35.0, flight_mode='AUTO', armed=True, battery_level=0.75,
            altitude=32.0, velocity=8.0, timestamp=t
        )
        # Build minimal history first
        for _ in range(3):
            features = extractor.extract(ctx)
            ctx.timestamp += 1.0
        
        if features is not None:
            feature_count = features.shape[0] if hasattr(features, 'shape') else len(features)
            logger.info(f"  Features extracted: {feature_count} dimensions")
        else:
            logger.info("  Features: None (building history)")
        
        logger.info("Step 3: Intent classification...")
        label = labeler.label_command(
            {'command_type': 'NAVIGATION', 'cmd_frequency_1s': 0.1, 'param_magnitude': 0.3},
            {'flight_mode': 'AUTO', 'mission_phase': 'CRUISE', 'armed': True,
             'battery_level': 0.75, 'altitude': 32.0, 'velocity': 8.0}
        )
        logger.info(f"  Intent: {label.intent}, Risk: {label.risk_score:.3f}")
        
        assert dos_metrics.is_dos_attack == False
        assert features is not None
        assert label.intent == IntentClass.NAVIGATION
        
        logger.info("\n✅ Complete pipeline flow successful")
        logger.info("  - DoS check: PASS")
        logger.info("  - Feature extraction: PASS")
        logger.info(f"  - Intent classification: PASS ({label.intent})")
        logger.info("✅ TEST PASSED: test_minimal_pipeline\n")


# Test suite completion
def pytest_sessionfinish(session, exitstatus):
    """Log test suite completion"""
    logger.info("\n" + "=" * 80)
    logger.info("AI LAYER TEST SUITE COMPLETED")
    logger.info(f"Test end time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Exit status: {exitstatus}")
    logger.info(f"Full log saved to: {log_file}")
    logger.info("=" * 80)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
