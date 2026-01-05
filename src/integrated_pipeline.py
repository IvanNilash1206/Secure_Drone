"""
Integrated Security Pipeline

Complete pipeline connecting:
1. Crypto Layer (encryption/decryption)
2. Attack Detection Layer (DoS, Replay, Injection)
3. ML Intent Inference Layer
4. Digital Twin Layer (shadow execution)
5. Decision Engine

This is the main security gateway for all drone commands.
"""

import time
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import json

# Crypto Layer
from src.crypto_layer.crypto_gate import CryptoGate
from src.crypto_layer.decryptor import decrypt_payload

# Attack Detection Layer
from src.ai_layer.attack_detection.dos_detector import DoSDetector, DoSMetrics
from src.ai_layer.attack_detection.replay_detector import ReplayDetector, ReplayMetrics
from src.ai_layer.attack_detection.injection_detector import InjectionDetector, InjectionMetrics, CommandType, FlightState

# AI/ML Layer
from src.ai_layer.intent_firewall import IntentFirewall, IntentResult
from src.ai_layer.ml_models.feature_extractor import FeatureExtractorV2, CommandContext
from src.ai_layer.ml_models.inference import IntentInferenceEngine, IntentInferenceResult

# Digital Twin Layer
from src.digital_twin.shadow_executor import ShadowExecutor, ShadowResult

# Decision Engine
from src.decision_engine.decision_engine import RiskProportionalDecisionEngine, DecisionResult, DecisionState

from src.logging_config import logger


@dataclass
class SecurityCheckResult:
    """Complete security check result for a command"""
    # Input
    command: str
    timestamp: float
    
    # Layer results
    crypto_valid: bool
    dos_metrics: Optional[DoSMetrics]
    replay_metrics: Optional[ReplayMetrics]
    injection_metrics: Optional[InjectionMetrics]
    intent_result: Optional[IntentResult]
    ml_inference: Optional[IntentInferenceResult]
    shadow_result: Optional[ShadowResult]
    
    # Final decision
    decision: DecisionResult
    
    # Timing
    total_time_ms: float
    
    def to_dict(self):
        return {
            "command": self.command,
            "timestamp": self.timestamp,
            "crypto_valid": self.crypto_valid,
            "dos_metrics": self.dos_metrics.to_dict() if self.dos_metrics else None,
            "replay_metrics": self.replay_metrics.to_dict() if self.replay_metrics else None,
            "injection_metrics": self.injection_metrics.to_dict() if self.injection_metrics else None,
            "intent_result": self.intent_result.to_dict() if self.intent_result else None,
            "ml_inference": self.ml_inference.to_dict() if self.ml_inference else None,
            "shadow_result": self.shadow_result.to_dict() if self.shadow_result else None,
            "decision": self.decision.to_dict(),
            "total_time_ms": self.total_time_ms
        }
    
    def to_json(self):
        return json.dumps(self.to_dict(), indent=2)


class IntegratedSecurityPipeline:
    """
    Complete security pipeline for drone commands
    
    Architecture:
    ```
    Encrypted Command
          ↓
    1. Crypto Layer (decrypt & validate)
          ↓
    2. Attack Detection (DoS, Replay, Injection)
          ↓
    3. Intent Analysis (rule-based + ML)
          ↓
    4. Digital Twin (shadow execution)
          ↓
    5. Decision Engine (aggregate all layers)
          ↓
    ACCEPT / REJECT / CONSTRAIN / RTL
    ```
    """
    
    def __init__(self, 
                 enable_ml: bool = True,
                 enable_shadow: bool = True,
                 model_dir: str = "models/intent_model"):
        """
        Args:
            enable_ml: Enable ML-based intent inference
            enable_shadow: Enable shadow execution (digital twin)
            model_dir: Path to trained ML models
        """
        # Initialize all layers
        logger.info("Initializing Integrated Security Pipeline...")
        
        # Layer 1: Crypto
        self.crypto_gate = CryptoGate()
        
        # Layer 2: Attack Detection
        self.dos_detector = DoSDetector()
        self.replay_detector = ReplayDetector()
        self.injection_detector = InjectionDetector()
        
        # Layer 3: Intent Analysis
        self.intent_firewall = IntentFirewall()
        
        # Layer 4: ML Inference (optional)
        self.enable_ml = enable_ml
        self.ml_engine = None
        self.feature_extractor = None
        if enable_ml:
            try:
                self.ml_engine = IntentInferenceEngine(model_dir=model_dir)
                self.feature_extractor = FeatureExtractorV2(window_size=7)
                logger.info("✅ ML inference enabled")
            except Exception as e:
                logger.warning(f"ML inference disabled: {e}")
                self.enable_ml = False
        
        # Layer 5: Digital Twin (optional)
        self.enable_shadow = enable_shadow
        self.shadow_executor = None
        if enable_shadow:
            try:
                self.shadow_executor = ShadowExecutor()
                logger.info("✅ Shadow execution enabled")
            except Exception as e:
                logger.warning(f"Shadow execution disabled: {e}")
                self.enable_shadow = False
        
        # Layer 6: Decision Engine
        self.decision_engine = RiskProportionalDecisionEngine()
        
        # Statistics
        self.total_commands = 0
        self.accepted_commands = 0
        self.rejected_commands = 0
        self.constrained_commands = 0
        self.rtl_commands = 0
        
        logger.info("✅ Integrated Security Pipeline initialized")
    
    def process_encrypted_command(self,
                                  nonce: bytes,
                                  ciphertext: bytes,
                                  source_authenticated: bool = True) -> SecurityCheckResult:
        """
        Process encrypted command through complete security pipeline
        
        Args:
            nonce: Cryptographic nonce
            ciphertext: Encrypted command
            source_authenticated: Whether source is authenticated
            
        Returns:
            SecurityCheckResult with decision
        """
        start_time = time.time()
        self.total_commands += 1
        
        # Layer 1: Crypto validation
        crypto_valid, payload = self.crypto_gate.crypto_check(nonce, ciphertext)
        
        if not crypto_valid:
            # Crypto failed - immediate rejection
            decision = DecisionResult(
                decision=DecisionState.RTL,
                severity="CRITICAL",
                confidence=1.0,
                explanation="Cryptographic validation failed",
                contributing_factors={"crypto_valid": False}
            )
            
            total_time = (time.time() - start_time) * 1000
            
            result = SecurityCheckResult(
                command="UNKNOWN",
                timestamp=time.time(),
                crypto_valid=False,
                dos_metrics=None,
                replay_metrics=None,
                injection_metrics=None,
                intent_result=None,
                ml_inference=None,
                shadow_result=None,
                decision=decision,
                total_time_ms=total_time
            )
            
            self.rejected_commands += 1
            logger.warning(f"Command rejected: Crypto failed (time: {total_time:.2f}ms)")
            return result
        
        # Extract command from payload
        command_str = self._extract_command(payload)
        current_timestamp = time.time()
        
        # Layer 2: Attack Detection
        dos_metrics = self.dos_detector.record_command(current_timestamp)
        replay_metrics = self.replay_detector.check_command(nonce, current_timestamp, payload=payload)
        
        # Determine command type for injection detection
        command_type = self._infer_command_type(command_str)
        parameters = self._extract_parameters(payload)
        injection_metrics = self.injection_detector.check_command(
            command_type,
            parameters,
            source_authenticated=source_authenticated
        )
        
        # Layer 3: Intent Analysis
        intent_result = self.intent_firewall.analyze_command(command_str)
        
        # Layer 4: ML Inference (if enabled)
        ml_inference = None
        if self.enable_ml and self.ml_engine and self.feature_extractor:
            try:
                # Create command context
                context = self._create_command_context(command_str, parameters, current_timestamp)
                
                # Extract features
                features = self.feature_extractor.extract_features(context)
                
                # Run inference
                ml_inference = self.ml_engine.predict(features)
            except Exception as e:
                logger.warning(f"ML inference failed: {e}")
        
        # Layer 5: Shadow Execution (if enabled)
        shadow_result = None
        if self.enable_shadow and self.shadow_executor:
            try:
                shadow_result = self.shadow_executor.predict_outcome(command_str, parameters)
            except Exception as e:
                logger.warning(f"Shadow execution failed: {e}")
        
        # Layer 6: Decision Engine
        decision = self.decision_engine.decide(
            command=command_str,
            crypto_valid=crypto_valid,
            dos_metrics=dos_metrics,
            replay_metrics=replay_metrics,
            injection_metrics=injection_metrics,
            intent_result=intent_result,
            ml_inference=ml_inference,
            shadow_result=shadow_result
        )
        
        # Update statistics
        if decision.decision == DecisionState.ACCEPT:
            self.accepted_commands += 1
        elif decision.decision == DecisionState.REJECT:
            self.rejected_commands += 1
        elif decision.decision == DecisionState.CONSTRAIN:
            self.constrained_commands += 1
        elif decision.decision == DecisionState.RTL:
            self.rtl_commands += 1
        
        total_time = (time.time() - start_time) * 1000
        
        result = SecurityCheckResult(
            command=command_str,
            timestamp=current_timestamp,
            crypto_valid=crypto_valid,
            dos_metrics=dos_metrics,
            replay_metrics=replay_metrics,
            injection_metrics=injection_metrics,
            intent_result=intent_result,
            ml_inference=ml_inference,
            shadow_result=shadow_result,
            decision=decision,
            total_time_ms=total_time
        )
        
        logger.info(f"Command processed: {command_str} -> {decision.decision.value} (time: {total_time:.2f}ms)")
        return result
    
    def update_vehicle_state(self,
                            flight_mode: str = None,
                            flight_state: FlightState = None,
                            armed: bool = None,
                            altitude: float = None,
                            mission_active: bool = None):
        """Update vehicle state for all layers"""
        if flight_mode:
            self.intent_firewall.update_state(mode=flight_mode)
        
        if armed is not None:
            self.intent_firewall.update_state(armed=armed)
        
        if altitude is not None:
            self.intent_firewall.update_state(altitude=altitude)
            if self.shadow_executor:
                self.shadow_executor.current_position["alt"] = altitude
        
        if mission_active is not None:
            self.intent_firewall.mission_active = mission_active
        
        if flight_state:
            self.injection_detector.update_state(state=flight_state)
    
    def _extract_command(self, payload: bytes) -> str:
        """Extract command from payload"""
        try:
            payload_str = payload.decode('utf-8')
            parts = payload_str.split('|')
            return parts[0] if parts else "UNKNOWN"
        except:
            return "UNKNOWN"
    
    def _extract_parameters(self, payload: bytes) -> Dict[str, Any]:
        """Extract parameters from payload"""
        try:
            payload_str = payload.decode('utf-8')
            parts = payload_str.split('|')
            
            # Simple parameter extraction (extend as needed)
            params = {}
            if len(parts) > 3:
                # Assume format: COMMAND|timestamp|source|param1=val1,param2=val2
                param_str = parts[3]
                for param_pair in param_str.split(','):
                    if '=' in param_pair:
                        key, value = param_pair.split('=', 1)
                        try:
                            params[key] = float(value)
                        except ValueError:
                            params[key] = value
            
            return params
        except:
            return {}
    
    def _infer_command_type(self, command: str) -> CommandType:
        """Infer command type from command string"""
        command_upper = command.upper()
        
        if "ARM" in command_upper or "DISARM" in command_upper:
            return CommandType.ARM_DISARM
        elif "TAKEOFF" in command_upper or "LAND" in command_upper:
            return CommandType.TAKEOFF_LAND
        elif "MODE" in command_upper:
            return CommandType.MODE_CHANGE
        elif "RTL" in command_upper or "RETURN" in command_upper:
            return CommandType.EMERGENCY
        elif "WAYPOINT" in command_upper or "GOTO" in command_upper:
            return CommandType.NAVIGATION
        elif "MISSION" in command_upper:
            return CommandType.MISSION_UPLOAD
        elif "PARAM" in command_upper:
            return CommandType.PARAMETER_SET
        else:
            return CommandType.UNKNOWN
    
    def _create_command_context(self, command: str, parameters: Dict, timestamp: float) -> CommandContext:
        """Create CommandContext for feature extraction"""
        # This is a simplified version - extend as needed
        return CommandContext(
            msg_id=76,  # COMMAND_LONG
            command_type=command,
            target_system=1,
            target_component=1,
            param1=parameters.get("param1", 0.0),
            param2=parameters.get("param2", 0.0),
            param3=parameters.get("param3", 0.0),
            param4=parameters.get("param4", 0.0),
            param5=parameters.get("latitude", 0.0),
            param6=parameters.get("longitude", 0.0),
            param7=parameters.get("altitude", 0.0),
            flight_mode=self.intent_firewall.current_mode.value if hasattr(self.intent_firewall, 'current_mode') else 'MANUAL',
            mission_phase='NONE',
            armed=self.intent_firewall.armed,
            battery_level=0.9,
            altitude=self.intent_firewall.altitude,
            velocity=0.0,
            timestamp=timestamp
        )
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get pipeline statistics"""
        return {
            "total_commands": self.total_commands,
            "accepted": self.accepted_commands,
            "rejected": self.rejected_commands,
            "constrained": self.constrained_commands,
            "rtl": self.rtl_commands,
            "acceptance_rate": self.accepted_commands / self.total_commands if self.total_commands > 0 else 0.0,
            "dos_stats": self.dos_detector.get_statistics(),
            "replay_stats": self.replay_detector.get_statistics(),
            "injection_stats": self.injection_detector.get_statistics()
        }


if __name__ == "__main__":
    # Test integrated pipeline
    from src.crypto_layer.encryptor import encrypt_payload
    
    print("Testing Integrated Security Pipeline\n")
    
    # Initialize pipeline
    pipeline = IntegratedSecurityPipeline(enable_ml=False, enable_shadow=True)
    
    # Test 1: Normal command
    print("1. Normal command (ARM_AND_TAKEOFF):")
    payload = b"ARM_AND_TAKEOFF|" + str(time.time()).encode() + b"|GCS"
    nonce, ciphertext = encrypt_payload(payload)
    
    result = pipeline.process_encrypted_command(nonce, ciphertext)
    print(f"   Decision: {result.decision.decision.value}")
    print(f"   Time: {result.total_time_ms:.2f} ms")
    
    # Test 2: DoS attack
    print("\n2. DoS attack (60 commands in 1 sec):")
    base_time = time.time()
    for i in range(60):
        payload = f"COMMAND_{i}|{base_time + i*0.016}|GCS".encode()
        nonce, ciphertext = encrypt_payload(payload)
        result = pipeline.process_encrypted_command(nonce, ciphertext)
    
    print(f"   Last decision: {result.decision.decision.value}")
    print(f"   DoS detected: {result.dos_metrics.is_dos_attack}")
    
    # Test 3: Replay attack
    print("\n3. Replay attack (duplicate nonce):")
    payload = b"TAKEOFF|" + str(time.time()).encode() + b"|GCS"
    nonce, ciphertext = encrypt_payload(payload)
    
    result1 = pipeline.process_encrypted_command(nonce, ciphertext)
    print(f"   First: {result1.decision.decision.value}")
    
    result2 = pipeline.process_encrypted_command(nonce, ciphertext)
    print(f"   Replay: {result2.decision.decision.value}")
    print(f"   Replay detected: {result2.replay_metrics.is_replay}")
    
    # Statistics
    print("\n4. Pipeline Statistics:")
    stats = pipeline.get_statistics()
    print(f"   Total commands: {stats['total_commands']}")
    print(f"   Accepted: {stats['accepted']}")
    print(f"   Rejected: {stats['rejected']}")
    print(f"   Acceptance rate: {stats['acceptance_rate']*100:.1f}%")
