"""
AEGIS Intent Inference Pipeline - Complete Integration Example

Demonstrates end-to-end flow:
1. MAVLink command received
2. Feature extraction (context-aware)
3. ML intent inference (with SHAP explainability)
4. Decision engine integration
5. Explainable logging

CRITICAL SAFETY REMINDER:
- ML model ADVISES, does NOT control
- Decision engine makes final call
- If ML fails → system continues with rules
- Model output is ONE input among many
"""

import numpy as np
import time
from typing import Dict, Any

# Import AEGIS components
from src.ai_layer.feature_extractor_v2 import (
    FeatureExtractorV2,
    CommandContext,
    mavlink_to_context
)
from src.ai_layer.inference_v2 import get_inference_engine
from src.decision_engine.decision_engine import RiskProportionalDecisionEngine


class AEGISIntentPipeline:
    """
    Complete intent inference + decision pipeline
    
    Integrates:
    - Feature extraction (temporal + context)
    - ML intent inference (with explainability)
    - Risk-proportional decision engine
    - Logging and monitoring
    """
    
    def __init__(self, 
                 model_dir: str = "models/intent_model",
                 enable_ml: bool = True):
        """
        Args:
            model_dir: Path to trained ML models
            enable_ml: Enable ML intent inference (can disable for fallback testing)
        """
        print("🚀 Initializing AEGIS Intent Pipeline...")
        
        # Feature extraction
        self.feature_extractor = FeatureExtractorV2(window_size=7)
        
        # ML inference engine
        self.enable_ml = enable_ml
        if enable_ml:
            try:
                self.ml_engine = get_inference_engine(
                    model_dir=model_dir,
                    confidence_threshold=0.6,
                    enable_shap=True
                )
                print("   ✓ ML inference engine loaded")
            except Exception as e:
                print(f"   ✗ ML engine failed to load: {e}")
                print("   → Operating in rule-based fallback mode")
                self.ml_engine = None
                self.enable_ml = False
        else:
            self.ml_engine = None
        
        # Decision engine (with ML integration)
        self.decision_engine = RiskProportionalDecisionEngine(
            config={'use_ml_intent': self.enable_ml}
        )
        
        print("✅ AEGIS Intent Pipeline ready\n")
    
    def process_command(self,
                       mavlink_msg: Dict[str, Any],
                       vehicle_state: Dict[str, Any],
                       crypto_valid: bool,
                       intent_result,
                       behavior_result,
                       shadow_result) -> Dict[str, Any]:
        """
        Complete command processing pipeline
        
        Args:
            mavlink_msg: MAVLink message dict
            vehicle_state: Current vehicle state
            crypto_valid: Crypto validation result
            intent_result: Rule-based intent check result
            behavior_result: Behavioral anomaly result
            shadow_result: Shadow executor trajectory result
            
        Returns:
            Complete decision result with ML insights
        """
        pipeline_start = time.perf_counter()
        
        # Step 1: Extract features
        command_ctx = mavlink_to_context(mavlink_msg, vehicle_state)
        features = self.feature_extractor.extract(command_ctx)
        
        # Step 2: ML intent inference (if enabled and features available)
        ml_result = None
        if self.enable_ml and features is not None and self.ml_engine is not None:
            try:
                ml_result = self.ml_engine.infer(features)
            except Exception as e:
                print(f"⚠️  ML inference failed: {e}")
                ml_result = None
        
        # Step 3: Decision engine (integrates ML as advisory input)
        decision_result = self.decision_engine.decide(
            crypto_valid=crypto_valid,
            intent_result=intent_result,
            behavior_result=behavior_result,
            shadow_result=shadow_result,
            command_obj=mavlink_msg,
            ml_intent_result=ml_result  # ML advisory input
        )
        
        pipeline_time = (time.perf_counter() - pipeline_start) * 1000
        
        # Build comprehensive result
        result = {
            'decision': decision_result.to_dict(),
            'ml_inference': ml_result.to_dict() if ml_result else None,
            'command': {
                'type': mavlink_msg.get('command_type'),
                'msg_id': mavlink_msg.get('msg_id'),
            },
            'pipeline_time_ms': pipeline_time,
            'timestamp': time.time(),
        }
        
        return result


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

def simulate_normal_navigation():
    """Example 1: Normal navigation command"""
    print("="*70)
    print("EXAMPLE 1: Normal Navigation Command")
    print("="*70)
    
    pipeline = AEGISIntentPipeline(model_dir="models/intent_model", enable_ml=True)
    
    # Simulate MAVLink command
    mavlink_msg = {
        'msg_id': 76,
        'command_type': 'SET_POSITION_TARGET',
        'target_system': 1,
        'target_component': 1,
        'param1': 30.0,  # altitude
        'param2': 0.0,
        'param3': 0.0,
        'param4': 0.0,
        'param5': 0.0,
        'param6': 0.0,
        'param7': 0.0,
    }
    
    # Vehicle state
    vehicle_state = {
        'flight_mode': 'GUIDED',
        'mission_phase': 'CRUISE',
        'armed': True,
        'battery_level': 0.8,
        'altitude': 25.0,
        'velocity': 8.0,
    }
    
    # Mock other layer results (would come from actual layers)
    from dataclasses import dataclass
    
    @dataclass
    class MockIntentResult:
        intent_match: bool = True
        confidence: float = 0.85
        reason: str = "Expected navigation command"
    
    @dataclass
    class MockBehaviorResult:
        behavior_score: float = 0.2
        anomaly_level: str = "LOW"
        anomaly_features: list = None
        explanation: str = "Normal pattern"
    
    @dataclass
    class MockOutcomes:
        geofence_violation: bool = False
        velocity_risk: bool = False
        altitude_risk: bool = False
        time_to_violation: float = 999.0
    
    @dataclass
    class MockShadowResult:
        trajectory_risk: float = 0.15
        predicted_outcomes: MockOutcomes = None
        explanation: str = "Safe trajectory"
        
        def __post_init__(self):
            if self.predicted_outcomes is None:
                self.predicted_outcomes = MockOutcomes()
    
    # Process command
    result = pipeline.process_command(
        mavlink_msg=mavlink_msg,
        vehicle_state=vehicle_state,
        crypto_valid=True,
        intent_result=MockIntentResult(),
        behavior_result=MockBehaviorResult(),
        shadow_result=MockShadowResult()
    )
    
    # Display results
    print("\n📊 Decision Result:")
    print(f"   Decision: {result['decision']['decision']}")
    print(f"   Severity: {result['decision']['severity']}")
    print(f"   Confidence: {result['decision']['confidence']:.2f}")
    print(f"   Risk Score: {result['decision']['contributing_factors']['risk_score']:.2f}")
    print(f"   Explanation: {result['decision']['explanation']}")
    
    if result['ml_inference']:
        ml = result['ml_inference']
        print(f"\n🤖 ML Intent Inference:")
        print(f"   Detected Intent: {ml['intent']}")
        print(f"   ML Confidence: {ml['confidence']:.2f}")
        print(f"   Intent Risk: {ml['intent_risk']:.2f}")
        print(f"   Status: {ml['model_status']}")
        
        if ml['top_features']:
            print(f"   Top Contributing Features:")
            for feat in ml['top_features'][:3]:
                contrib = ml['feature_contributions'].get(feat, 0)
                print(f"      - {feat}: {contrib:.3f}")
    
    print(f"\n⚡ Total Pipeline Time: {result['pipeline_time_ms']:.2f}ms")
    print()


def simulate_high_risk_attack():
    """Example 2: High-risk attack command"""
    print("="*70)
    print("EXAMPLE 2: High-Risk Attack Command (MITM)")
    print("="*70)
    
    pipeline = AEGISIntentPipeline(model_dir="models/intent_model", enable_ml=True)
    
    # Simulate malicious command (disarm at altitude)
    mavlink_msg = {
        'msg_id': 76,
        'command_type': 'ARM_DISARM',
        'target_system': 1,
        'target_component': 1,
        'param1': 0.0,  # DISARM
        'param2': 0.0,
        'param3': 0.0,
        'param4': 0.0,
        'param5': 0.0,
        'param6': 0.0,
        'param7': 0.0,
    }
    
    # Vehicle state (airborne!)
    vehicle_state = {
        'flight_mode': 'AUTO',
        'mission_phase': 'CRUISE',
        'armed': True,  # Currently armed and flying
        'battery_level': 0.75,
        'altitude': 35.0,  # 35 meters altitude
        'velocity': 8.0,
    }
    
    from dataclasses import dataclass
    
    @dataclass
    class MockIntentResult:
        intent_match: bool = False  # Mismatch!
        confidence: float = 0.9
        reason: str = "DISARM at altitude - unsafe"
    
    @dataclass
    class MockBehaviorResult:
        behavior_score: float = 0.85
        anomaly_level: str = "HIGH"
        anomaly_features: list = None
        explanation: str = "Anomalous DISARM command during flight"
    
    @dataclass
    class MockOutcomes:
        geofence_violation: bool = False
        velocity_risk: bool = False
        altitude_risk: bool = True
        time_to_violation: float = 2.0
    
    @dataclass
    class MockShadowResult:
        trajectory_risk: float = 0.95
        predicted_outcomes: MockOutcomes = None
        explanation: str = "CRITICAL: Disarm at altitude will cause crash"
        
        def __post_init__(self):
            if self.predicted_outcomes is None:
                self.predicted_outcomes = MockOutcomes()
    
    # Process command
    result = pipeline.process_command(
        mavlink_msg=mavlink_msg,
        vehicle_state=vehicle_state,
        crypto_valid=False,  # Also crypto failed!
        intent_result=MockIntentResult(),
        behavior_result=MockBehaviorResult(),
        shadow_result=MockShadowResult()
    )
    
    # Display results
    print("\n📊 Decision Result:")
    print(f"   Decision: {result['decision']['decision']}")
    print(f"   Severity: {result['decision']['severity']}")
    print(f"   Confidence: {result['decision']['confidence']:.2f}")
    print(f"   Risk Score: {result['decision']['contributing_factors']['risk_score']:.2f}")
    print(f"   Explanation: {result['decision']['explanation']}")
    
    if result['ml_inference']:
        ml = result['ml_inference']
        print(f"\n🤖 ML Intent Inference:")
        print(f"   Detected Intent: {ml['intent']}")
        print(f"   ML Confidence: {ml['confidence']:.2f}")
        print(f"   Intent Risk: {ml['intent_risk']:.2f}")
        print(f"   Status: {ml['model_status']}")
    
    print(f"\n⚡ Total Pipeline Time: {result['pipeline_time_ms']:.2f}ms")
    print()


def simulate_ml_fallback():
    """Example 3: ML model fallback scenario"""
    print("="*70)
    print("EXAMPLE 3: ML Model Fallback (Low Confidence)")
    print("="*70)
    
    # Initialize with ML disabled to show fallback
    pipeline = AEGISIntentPipeline(model_dir="invalid_path", enable_ml=True)
    
    mavlink_msg = {
        'msg_id': 76,
        'command_type': 'UNKNOWN_CMD',
        'target_system': 1,
        'target_component': 1,
        'param1': 0.0,
        'param2': 0.0,
        'param3': 0.0,
        'param4': 0.0,
        'param5': 0.0,
        'param6': 0.0,
        'param7': 0.0,
    }
    
    vehicle_state = {
        'flight_mode': 'MANUAL',
        'mission_phase': 'NONE',
        'armed': False,
        'battery_level': 0.9,
        'altitude': 0.0,
        'velocity': 0.0,
    }
    
    from dataclasses import dataclass
    
    @dataclass
    class MockIntentResult:
        intent_match: bool = True
        confidence: float = 0.7
        reason: str = "Unknown command type"
    
    @dataclass
    class MockBehaviorResult:
        behavior_score: float = 0.4
        anomaly_level: str = "MEDIUM"
        anomaly_features: list = None
        explanation: str = "Unusual command pattern"
    
    @dataclass
    class MockOutcomes:
        geofence_violation: bool = False
        velocity_risk: bool = False
        altitude_risk: bool = False
        time_to_violation: float = 999.0
    
    @dataclass
    class MockShadowResult:
        trajectory_risk: float = 0.5
        predicted_outcomes: MockOutcomes = None
        explanation: str = "Unknown trajectory"
        
        def __post_init__(self):
            if self.predicted_outcomes is None:
                self.predicted_outcomes = MockOutcomes()
    
    # Process command
    result = pipeline.process_command(
        mavlink_msg=mavlink_msg,
        vehicle_state=vehicle_state,
        crypto_valid=True,
        intent_result=MockIntentResult(),
        behavior_result=MockBehaviorResult(),
        shadow_result=MockShadowResult()
    )
    
    print("\n📊 Decision Result:")
    print(f"   Decision: {result['decision']['decision']}")
    print(f"   Severity: {result['decision']['severity']}")
    print(f"   Note: System continues with rule-based logic when ML unavailable")
    
    print(f"\n⚡ Total Pipeline Time: {result['pipeline_time_ms']:.2f}ms")
    print()


if __name__ == "__main__":
    print("\n" + "="*70)
    print("AEGIS INTENT INFERENCE - INTEGRATION EXAMPLES")
    print("="*70)
    print()
    
    # Run examples
    simulate_normal_navigation()
    simulate_high_risk_attack()
    simulate_ml_fallback()
    
    print("="*70)
    print("✅ Integration examples complete!")
    print("="*70)
    print()
    print("Key Takeaways:")
    print("1. ML model provides ADVISORY input to decision engine")
    print("2. Decision engine makes final decision using ALL layers")
    print("3. If ML fails → system continues with rules (fail-safe)")
    print("4. Explainability via SHAP shows WHY decisions were made")
    print("5. Total latency <50ms end-to-end (well within real-time requirements)")
    print()
