"""
Attack Testing Orchestrator

Comprehensive attack testing framework for:
1. DoS (Denial of Service) attacks
2. Replay attacks
3. Message injection attacks

Tests detection accuracy, response time, and system resilience.
"""

import time
import os
import json
import random
import sys
from typing import Dict, Any, List, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import attack detectors
from src.ai_layer.attack_detection.dos_detector import DoSDetector
from src.ai_layer.attack_detection.replay_detector import ReplayDetector
from src.ai_layer.attack_detection.injection_detector import (
    InjectionDetector,
    CommandType,
    FlightState
)


@dataclass
class AttackTestResult:
    """Result of a single attack test"""
    attack_type: str
    attack_variant: str
    detected: bool
    confidence: float
    detection_time_ms: float
    false_positives: int
    false_negatives: int
    explanation: str
    details: Dict[str, Any]
    
    def to_dict(self):
        return asdict(self)


@dataclass
class AttackTestSummary:
    """Summary of all attack tests"""
    total_tests: int
    successful_detections: int
    failed_detections: int
    false_positives: int
    false_negatives: int
    avg_detection_time_ms: float
    detection_rate: float
    results_by_attack: Dict[str, Dict[str, Any]]
    
    def to_dict(self):
        return asdict(self)


class AttackTestOrchestrator:
    """
    Orchestrates comprehensive attack testing
    
    Test scenarios:
    - DoS: Command flooding, burst attacks, slow DoS
    - Replay: Nonce reuse, old timestamps, session replay
    - Injection: Unauthorized commands, parameter manipulation, privilege escalation
    """
    
    def __init__(self, output_dir: str = "attack_tests/results"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize detectors
        self.dos_detector = DoSDetector()
        self.replay_detector = ReplayDetector()
        self.injection_detector = InjectionDetector()
        
        # Test results
        self.results: List[AttackTestResult] = []
        
        print("🚀 Attack Test Orchestrator initialized")
        print(f"   Output directory: {self.output_dir}")
    
    def run_all_tests(self) -> AttackTestSummary:
        """Run complete attack test suite"""
        print("\n" + "="*80)
        print("STARTING COMPREHENSIVE ATTACK TESTING")
        print("="*80 + "\n")
        
        # Run DoS tests
        print("📊 Testing DoS (Denial of Service) Attacks...")
        self._test_dos_attacks()
        
        # Run Replay tests
        print("\n📊 Testing Replay Attacks...")
        self._test_replay_attacks()
        
        # Run Injection tests
        print("\n📊 Testing Message Injection Attacks...")
        self._test_injection_attacks()
        
        # Generate summary
        summary = self._generate_summary()
        
        # Save results
        self._save_results(summary)
        
        # Print summary
        self._print_summary(summary)
        
        return summary
    
    def _test_dos_attacks(self):
        """Test DoS attack detection"""
        print("\n1. DoS Attack Tests:")
        
        # Test 1: Normal traffic (baseline - should NOT detect)
        print("   ├─ Test 1.1: Normal traffic (2 cmds/sec)")
        result = self._run_dos_test_normal_traffic()
        self.results.append(result)
        print(f"   │  └─ {'✅ PASS' if not result.detected else '❌ FAIL'}: {result.explanation}")
        
        # Test 2: Burst attack (should detect)
        print("   ├─ Test 1.2: Burst attack (60 cmds in 1 sec)")
        result = self._run_dos_test_burst()
        self.results.append(result)
        print(f"   │  └─ {'✅ PASS' if result.detected else '❌ FAIL'}: {result.explanation}")
        
        # Test 3: Sustained flooding (should detect)
        print("   ├─ Test 1.3: Sustained flooding (25 cmds/sec for 5 sec)")
        result = self._run_dos_test_sustained()
        self.results.append(result)
        print(f"   │  └─ {'✅ PASS' if result.detected else '❌ FAIL'}: {result.explanation}")
        
        # Test 4: Slow DoS (should detect)
        print("   └─ Test 1.4: Slow DoS (15 cmds/sec for 10 sec)")
        result = self._run_dos_test_slow()
        self.results.append(result)
        print(f"      └─ {'✅ PASS' if result.detected else '❌ FAIL'}: {result.explanation}")
    
    def _test_replay_attacks(self):
        """Test replay attack detection"""
        print("\n2. Replay Attack Tests:")
        
        # Test 1: Normal commands (baseline - should NOT detect)
        print("   ├─ Test 2.1: Normal commands (unique nonces)")
        result = self._run_replay_test_normal()
        self.results.append(result)
        print(f"   │  └─ {'✅ PASS' if not result.detected else '❌ FAIL'}: {result.explanation}")
        
        # Test 2: Nonce reuse (should detect)
        print("   ├─ Test 2.2: Nonce reuse (exact replay)")
        result = self._run_replay_test_nonce_reuse()
        self.results.append(result)
        print(f"   │  └─ {'✅ PASS' if result.detected else '❌ FAIL'}: {result.explanation}")
        
        # Test 3: Old timestamp (should detect)
        print("   ├─ Test 2.3: Old timestamp (60 sec old)")
        result = self._run_replay_test_old_timestamp()
        self.results.append(result)
        print(f"   │  └─ {'✅ PASS' if result.detected else '❌ FAIL'}: {result.explanation}")
        
        # Test 4: Command sequence replay (should detect)
        print("   └─ Test 2.4: Duplicate command in short window")
        result = self._run_replay_test_sequence()
        self.results.append(result)
        print(f"      └─ {'✅ PASS' if result.detected else '❌ FAIL'}: {result.explanation}")
    
    def _test_injection_attacks(self):
        """Test injection attack detection"""
        print("\n3. Message Injection Attack Tests:")
        
        # Test 1: Normal command (baseline - should NOT detect)
        print("   ├─ Test 3.1: Normal ARM command")
        result = self._run_injection_test_normal()
        self.results.append(result)
        print(f"   │  └─ {'✅ PASS' if not result.detected else '❌ FAIL'}: {result.explanation}")
        
        # Test 2: Disarm in flight (should detect)
        print("   ├─ Test 3.2: Disarm while in flight")
        result = self._run_injection_test_disarm_in_flight()
        self.results.append(result)
        print(f"   │  └─ {'✅ PASS' if result.detected else '❌ FAIL'}: {result.explanation}")
        
        # Test 3: Parameter injection (should detect)
        print("   ├─ Test 3.3: Extreme altitude parameter (500m)")
        result = self._run_injection_test_parameter()
        self.results.append(result)
        print(f"   │  └─ {'✅ PASS' if result.detected else '❌ FAIL'}: {result.explanation}")
        
        # Test 4: Privilege escalation (should detect)
        print("   ├─ Test 3.4: Unauthenticated mode change")
        result = self._run_injection_test_privilege()
        self.results.append(result)
        print(f"   │  └─ {'✅ PASS' if result.detected else '❌ FAIL'}: {result.explanation}")
        
        # Test 5: Mode change during landing (should detect)
        print("   └─ Test 3.5: Mode change during landing")
        result = self._run_injection_test_landing()
        self.results.append(result)
        print(f"      └─ {'✅ PASS' if result.detected else '❌ FAIL'}: {result.explanation}")
    
    # DoS Test Implementations
    def _run_dos_test_normal_traffic(self) -> AttackTestResult:
        """Test normal traffic (should NOT trigger DoS detection)"""
        self.dos_detector.reset()
        start_time = time.time()
        base_time = start_time
        
        detected = False
        for i in range(20):
            timestamp = base_time + (i * 0.5)  # 2 commands/sec
            metrics = self.dos_detector.record_command(timestamp)
            if metrics.is_dos_attack:
                detected = True
        
        detection_time = (time.time() - start_time) * 1000
        
        # Should NOT detect (false positive if detected)
        return AttackTestResult(
            attack_type="DoS",
            attack_variant="Normal Traffic (Baseline)",
            detected=detected,
            confidence=0.0,
            detection_time_ms=detection_time,
            false_positives=1 if detected else 0,
            false_negatives=0,
            explanation="Normal traffic should not trigger DoS detection",
            details={"commands_sent": 20, "rate": 2.0}
        )
    
    def _run_dos_test_burst(self) -> AttackTestResult:
        """Test burst attack (should detect)"""
        self.dos_detector.reset()
        start_time = time.time()
        base_time = start_time
        
        detected = False
        detection_time_ms = 0
        confidence = 0.0
        
        for i in range(60):
            timestamp = base_time + (i * 0.016)  # 60 commands in 1 second
            metrics = self.dos_detector.record_command(timestamp)
            if metrics.is_dos_attack and not detected:
                detected = True
                detection_time_ms = (time.time() - start_time) * 1000
                confidence = metrics.confidence
        
        # Should detect (false negative if not detected)
        return AttackTestResult(
            attack_type="DoS",
            attack_variant="Burst Attack",
            detected=detected,
            confidence=confidence,
            detection_time_ms=detection_time_ms,
            false_positives=0,
            false_negatives=0 if detected else 1,
            explanation=f"Burst attack {'detected' if detected else 'NOT detected'}",
            details={"commands_sent": 60, "rate": 60.0}
        )
    
    def _run_dos_test_sustained(self) -> AttackTestResult:
        """Test sustained flooding (should detect)"""
        self.dos_detector.reset()
        start_time = time.time()
        base_time = start_time
        
        detected = False
        detection_time_ms = 0
        confidence = 0.0
        
        for i in range(125):
            timestamp = base_time + (i * 0.04)  # 25 commands/sec for 5 sec
            metrics = self.dos_detector.record_command(timestamp)
            if metrics.is_dos_attack and not detected:
                detected = True
                detection_time_ms = (time.time() - start_time) * 1000
                confidence = metrics.confidence
        
        return AttackTestResult(
            attack_type="DoS",
            attack_variant="Sustained Flooding",
            detected=detected,
            confidence=confidence,
            detection_time_ms=detection_time_ms,
            false_positives=0,
            false_negatives=0 if detected else 1,
            explanation=f"Sustained attack {'detected' if detected else 'NOT detected'}",
            details={"commands_sent": 125, "rate": 25.0, "duration_sec": 5.0}
        )
    
    def _run_dos_test_slow(self) -> AttackTestResult:
        """Test slow DoS (should detect)"""
        self.dos_detector.reset()
        start_time = time.time()
        base_time = start_time
        
        detected = False
        detection_time_ms = 0
        confidence = 0.0
        
        for i in range(150):
            timestamp = base_time + (i * 0.067)  # 15 commands/sec for 10 sec
            metrics = self.dos_detector.record_command(timestamp)
            if metrics.is_dos_attack and not detected:
                detected = True
                detection_time_ms = (time.time() - start_time) * 1000
                confidence = metrics.confidence
        
        return AttackTestResult(
            attack_type="DoS",
            attack_variant="Slow DoS",
            detected=detected,
            confidence=confidence,
            detection_time_ms=detection_time_ms,
            false_positives=0,
            false_negatives=0 if detected else 1,
            explanation=f"Slow DoS {'detected' if detected else 'NOT detected'}",
            details={"commands_sent": 150, "rate": 15.0, "duration_sec": 10.0}
        )
    
    # Replay Test Implementations
    def _run_replay_test_normal(self) -> AttackTestResult:
        """Test normal commands (should NOT detect)"""
        self.replay_detector.reset()
        start_time = time.time()
        base_time = start_time
        
        detected = False
        for i in range(10):
            nonce = os.urandom(16)
            timestamp = base_time + i
            payload = f"COMMAND_{i}".encode()
            metrics = self.replay_detector.check_command(nonce, timestamp, payload=payload)
            if metrics.is_replay:
                detected = True
        
        detection_time = (time.time() - start_time) * 1000
        
        return AttackTestResult(
            attack_type="Replay",
            attack_variant="Normal Commands (Baseline)",
            detected=detected,
            confidence=0.0,
            detection_time_ms=detection_time,
            false_positives=1 if detected else 0,
            false_negatives=0,
            explanation="Normal commands should not trigger replay detection",
            details={"commands_sent": 10}
        )
    
    def _run_replay_test_nonce_reuse(self) -> AttackTestResult:
        """Test nonce reuse (should detect)"""
        self.replay_detector.reset()
        start_time = time.time()
        base_time = start_time
        
        # Send normal command first
        nonce = os.urandom(16)
        metrics = self.replay_detector.check_command(nonce, base_time, payload=b"CMD_1")
        
        # Replay with same nonce
        start_detection = time.time()
        metrics = self.replay_detector.check_command(nonce, base_time + 1, payload=b"CMD_1")
        detection_time = (time.time() - start_detection) * 1000
        
        return AttackTestResult(
            attack_type="Replay",
            attack_variant="Nonce Reuse",
            detected=metrics.is_replay,
            confidence=metrics.confidence,
            detection_time_ms=detection_time,
            false_positives=0,
            false_negatives=0 if metrics.is_replay else 1,
            explanation=f"Nonce reuse {'detected' if metrics.is_replay else 'NOT detected'}",
            details={"detection_method": metrics.detection_method}
        )
    
    def _run_replay_test_old_timestamp(self) -> AttackTestResult:
        """Test old timestamp (should detect)"""
        self.replay_detector.reset()
        start_time = time.time()
        
        nonce = os.urandom(16)
        old_timestamp = start_time - 60  # 60 seconds ago
        
        start_detection = time.time()
        metrics = self.replay_detector.check_command(nonce, old_timestamp, payload=b"OLD_CMD")
        detection_time = (time.time() - start_detection) * 1000
        
        return AttackTestResult(
            attack_type="Replay",
            attack_variant="Old Timestamp",
            detected=metrics.is_replay,
            confidence=metrics.confidence,
            detection_time_ms=detection_time,
            false_positives=0,
            false_negatives=0 if metrics.is_replay else 1,
            explanation=f"Old timestamp {'detected' if metrics.is_replay else 'NOT detected'}",
            details={"timestamp_age_sec": 60, "detection_method": metrics.detection_method}
        )
    
    def _run_replay_test_sequence(self) -> AttackTestResult:
        """Test duplicate command sequence (should detect)"""
        self.replay_detector.reset()
        start_time = time.time()
        base_time = start_time
        
        # Send command
        payload = b"TAKEOFF"
        nonce1 = os.urandom(16)
        metrics = self.replay_detector.check_command(nonce1, base_time, payload=payload)
        
        # Send duplicate command with different nonce
        nonce2 = os.urandom(16)
        start_detection = time.time()
        metrics = self.replay_detector.check_command(nonce2, base_time + 1, payload=payload)
        detection_time = (time.time() - start_detection) * 1000
        
        return AttackTestResult(
            attack_type="Replay",
            attack_variant="Sequence Replay",
            detected=metrics.is_replay,
            confidence=metrics.confidence,
            detection_time_ms=detection_time,
            false_positives=0,
            false_negatives=0 if metrics.is_replay else 1,
            explanation=f"Sequence replay {'detected' if metrics.is_replay else 'NOT detected'}",
            details={"detection_method": metrics.detection_method}
        )
    
    # Injection Test Implementations
    def _run_injection_test_normal(self) -> AttackTestResult:
        """Test normal command (should NOT detect)"""
        self.injection_detector.reset()
        self.injection_detector.update_state(state=FlightState.DISARMED)
        
        start_time = time.time()
        metrics = self.injection_detector.check_command(
            CommandType.ARM_DISARM,
            {"arm": 1},
            source_authenticated=True
        )
        detection_time = (time.time() - start_time) * 1000
        
        return AttackTestResult(
            attack_type="Injection",
            attack_variant="Normal Command (Baseline)",
            detected=metrics.is_injection,
            confidence=metrics.confidence,
            detection_time_ms=detection_time,
            false_positives=1 if metrics.is_injection else 0,
            false_negatives=0,
            explanation="Normal ARM command should not trigger injection detection",
            details={"risk_score": metrics.risk_score}
        )
    
    def _run_injection_test_disarm_in_flight(self) -> AttackTestResult:
        """Test disarm while in flight (should detect)"""
        self.injection_detector.reset()
        self.injection_detector.update_state(
            state=FlightState.IN_FLIGHT,
            altitude=50.0,
            armed=True
        )
        
        start_time = time.time()
        metrics = self.injection_detector.check_command(
            CommandType.ARM_DISARM,
            {"arm": 0},  # Disarm
            source_authenticated=True
        )
        detection_time = (time.time() - start_time) * 1000
        
        return AttackTestResult(
            attack_type="Injection",
            attack_variant="Disarm in Flight",
            detected=metrics.is_injection,
            confidence=metrics.confidence,
            detection_time_ms=detection_time,
            false_positives=0,
            false_negatives=0 if metrics.is_injection else 1,
            explanation=f"Disarm in flight {'detected' if metrics.is_injection else 'NOT detected'}",
            details={"risk_score": metrics.risk_score, "detection_method": metrics.detection_method}
        )
    
    def _run_injection_test_parameter(self) -> AttackTestResult:
        """Test parameter injection (should detect)"""
        self.injection_detector.reset()
        self.injection_detector.update_state(state=FlightState.IN_FLIGHT)
        
        start_time = time.time()
        metrics = self.injection_detector.check_command(
            CommandType.NAVIGATION,
            {"altitude": 500.0, "latitude": 47.0, "longitude": -122.0},  # Extreme altitude
            source_authenticated=True
        )
        detection_time = (time.time() - start_time) * 1000
        
        return AttackTestResult(
            attack_type="Injection",
            attack_variant="Parameter Injection",
            detected=metrics.is_injection,
            confidence=metrics.confidence,
            detection_time_ms=detection_time,
            false_positives=0,
            false_negatives=0 if metrics.is_injection else 1,
            explanation=f"Parameter injection {'detected' if metrics.is_injection else 'NOT detected'}",
            details={"risk_score": metrics.risk_score, "parameter": "altitude=500m"}
        )
    
    def _run_injection_test_privilege(self) -> AttackTestResult:
        """Test privilege escalation (should detect)"""
        self.injection_detector.reset()
        self.injection_detector.update_state(state=FlightState.IN_FLIGHT)
        
        start_time = time.time()
        metrics = self.injection_detector.check_command(
            CommandType.MODE_CHANGE,
            {"mode": "MANUAL"},
            source_authenticated=False  # NOT authenticated
        )
        detection_time = (time.time() - start_time) * 1000
        
        return AttackTestResult(
            attack_type="Injection",
            attack_variant="Privilege Escalation",
            detected=metrics.is_injection,
            confidence=metrics.confidence,
            detection_time_ms=detection_time,
            false_positives=0,
            false_negatives=0 if metrics.is_injection else 1,
            explanation=f"Privilege escalation {'detected' if metrics.is_injection else 'NOT detected'}",
            details={"risk_score": metrics.risk_score, "detection_method": metrics.detection_method}
        )
    
    def _run_injection_test_landing(self) -> AttackTestResult:
        """Test mode change during landing (should detect)"""
        self.injection_detector.reset()
        self.injection_detector.update_state(
            state=FlightState.LANDING,
            altitude=5.0,
            armed=True
        )
        
        start_time = time.time()
        metrics = self.injection_detector.check_command(
            CommandType.MODE_CHANGE,
            {"mode": "GUIDED"},
            source_authenticated=True
        )
        detection_time = (time.time() - start_time) * 1000
        
        return AttackTestResult(
            attack_type="Injection",
            attack_variant="Mode Change During Landing",
            detected=metrics.is_injection,
            confidence=metrics.confidence,
            detection_time_ms=detection_time,
            false_positives=0,
            false_negatives=0 if metrics.is_injection else 1,
            explanation=f"Mode change during landing {'detected' if metrics.is_injection else 'NOT detected'}",
            details={"risk_score": metrics.risk_score, "detection_method": metrics.detection_method}
        )
    
    def _generate_summary(self) -> AttackTestSummary:
        """Generate test summary"""
        total_tests = len(self.results)
        successful_detections = sum(1 for r in self.results if r.detected and r.false_positives == 0)
        failed_detections = sum(1 for r in self.results if r.false_negatives > 0)
        total_false_positives = sum(r.false_positives for r in self.results)
        total_false_negatives = sum(r.false_negatives for r in self.results)
        
        avg_detection_time = sum(r.detection_time_ms for r in self.results) / total_tests if total_tests > 0 else 0.0
        detection_rate = successful_detections / total_tests if total_tests > 0 else 0.0
        
        # Group by attack type
        results_by_attack = {}
        for result in self.results:
            attack_type = result.attack_type
            if attack_type not in results_by_attack:
                results_by_attack[attack_type] = {
                    "total": 0,
                    "detected": 0,
                    "false_positives": 0,
                    "false_negatives": 0,
                    "variants": []
                }
            
            results_by_attack[attack_type]["total"] += 1
            if result.detected:
                results_by_attack[attack_type]["detected"] += 1
            results_by_attack[attack_type]["false_positives"] += result.false_positives
            results_by_attack[attack_type]["false_negatives"] += result.false_negatives
            results_by_attack[attack_type]["variants"].append({
                "variant": result.attack_variant,
                "detected": result.detected,
                "confidence": result.confidence
            })
        
        return AttackTestSummary(
            total_tests=total_tests,
            successful_detections=successful_detections,
            failed_detections=failed_detections,
            false_positives=total_false_positives,
            false_negatives=total_false_negatives,
            avg_detection_time_ms=avg_detection_time,
            detection_rate=detection_rate,
            results_by_attack=results_by_attack
        )
    
    def _save_results(self, summary: AttackTestSummary):
        """Save test results to files"""
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        
        # Save detailed results
        results_file = self.output_dir / f"attack_test_results_{timestamp}.json"
        with open(results_file, 'w') as f:
            json.dump([r.to_dict() for r in self.results], f, indent=2)
        
        # Save summary
        summary_file = self.output_dir / f"attack_test_summary_{timestamp}.json"
        with open(summary_file, 'w') as f:
            json.dump(summary.to_dict(), f, indent=2)
        
        print(f"\n💾 Results saved:")
        print(f"   - {results_file}")
        print(f"   - {summary_file}")
    
    def _print_summary(self, summary: AttackTestSummary):
        """Print test summary"""
        print("\n" + "="*80)
        print("ATTACK TEST SUMMARY")
        print("="*80)
        print(f"\n📊 Overall Results:")
        print(f"   Total Tests: {summary.total_tests}")
        print(f"   Successful Detections: {summary.successful_detections} ({summary.detection_rate*100:.1f}%)")
        print(f"   Failed Detections: {summary.failed_detections}")
        print(f"   False Positives: {summary.false_positives}")
        print(f"   False Negatives: {summary.false_negatives}")
        print(f"   Avg Detection Time: {summary.avg_detection_time_ms:.2f} ms")
        
        print(f"\n📈 Results by Attack Type:")
        for attack_type, stats in summary.results_by_attack.items():
            detection_rate = stats["detected"] / stats["total"] * 100 if stats["total"] > 0 else 0.0
            print(f"\n   {attack_type}:")
            print(f"      Total: {stats['total']}")
            print(f"      Detected: {stats['detected']} ({detection_rate:.1f}%)")
            print(f"      False Positives: {stats['false_positives']}")
            print(f"      False Negatives: {stats['false_negatives']}")
            print(f"      Variants:")
            for variant in stats["variants"]:
                status = "✅" if variant["detected"] else "❌"
                print(f"         {status} {variant['variant']}: Conf={variant['confidence']:.2f}")
        
        print("\n" + "="*80)


if __name__ == "__main__":
    # Run comprehensive attack tests
    orchestrator = AttackTestOrchestrator()
    summary = orchestrator.run_all_tests()
    
    print(f"\n✅ Testing complete!")
    print(f"   Detection rate: {summary.detection_rate*100:.1f}%")
    print(f"   Average detection time: {summary.avg_detection_time_ms:.2f} ms")
