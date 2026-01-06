"""
Layer 6: Risk-Proportional Decision Engine

Purpose: Aggregate all layer outputs and make risk-proportional decisions

Decision States (NOT BINARY):
- ACCEPT: Execute command as-is
- CONSTRAIN: Execute with modifications/limits
- HOLD: Delay execution pending clarification
- RTL/ESCAPE: Trigger safe return/landing

High Severity Definition:
Predicted inevitable unsafe outcome + untrusted command + no safe mitigation

NEW: Integrates ML-based intent inference as ADVISORY input
- ML model does NOT control decisions
- ML provides: intent, confidence, risk score, explanations
- Decision engine uses ML as ONE input among many
- If ML confidence low → defer to rule-based logic
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum
import json


class DecisionState(Enum):
    """Four-state decision model"""
    ACCEPT = "ACCEPT"
    CONSTRAIN = "CONSTRAIN"
    HOLD = "HOLD"
    RTL = "RTL"  # Return to launch / emergency escape


class Severity(Enum):
    """Risk severity levels"""
    NONE = "NONE"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass
class DecisionResult:
    """Complete decision output"""
    decision: DecisionState
    severity: Severity
    confidence: float
    explanation: str
    contributing_factors: Dict[str, Any]
    
    def to_dict(self):
        return {
            "decision": self.decision.value,
            "severity": self.severity.value,
            "confidence": self.confidence,
            "explanation": self.explanation,
            "contributing_factors": self.contributing_factors
        }
    
    def to_json(self):
        return json.dumps(self.to_dict(), indent=2)


class RiskProportionalDecisionEngine:
    """
    Converges all layer outputs into final decision
    
    Inputs from all layers:
    1. Command intake: structured command
    2. Crypto: valid/invalid
    3. Intent: match/mismatch + confidence
    4. Behavior: anomaly score
    5. Shadow: trajectory risk
    
    Output: Decision + Severity + Explanation
    """
    
    def __init__(self, config: Optional[Dict] = None):
        config = config or {}
        
        # Decision thresholds
        self.thresholds = {
            "accept_max_risk": config.get("accept_max_risk", 0.3),
            "constrain_max_risk": config.get("constrain_max_risk", 0.6),
            "hold_max_risk": config.get("hold_max_risk", 0.8),
            "rtl_min_risk": config.get("rtl_min_risk", 0.8),
            
            "min_confidence": config.get("min_confidence", 0.7),
            "behavior_anomaly_threshold": config.get("behavior_anomaly_threshold", 0.6),
            "trajectory_risk_threshold": config.get("trajectory_risk_threshold", 0.7),
            
            # NEW: ML model thresholds
            "ml_confidence_threshold": config.get("ml_confidence_threshold", 0.6),
        }
        
        # Risk weights for aggregation
        self.weights = {
            "crypto": config.get("weight_crypto", 0.25),
            "intent": config.get("weight_intent", 0.15),  # Reduced (now supplemented by ML)
            "behavior": config.get("weight_behavior", 0.2),
            "trajectory": config.get("weight_trajectory", 0.2),
            "ml_intent": config.get("weight_ml_intent", 0.2),  # NEW: ML intent risk
        }
        
        # ML integration flag
        self.use_ml_intent = config.get("use_ml_intent", True)
        
        print("✅ Risk-Proportional Decision Engine initialized")
        print(f"   ML Intent Inference: {'Enabled' if self.use_ml_intent else 'Disabled'}")
    
    def aggregate_risk(self, 
                      crypto_valid: bool,
                      intent_result,
                      behavior_result,
                      shadow_result,
                      ml_intent_result=None) -> float:
        """
        Aggregate risk from all layers into single score (0-1)
        
        NOT simple average - weighted by importance
        
        NEW: Includes ML intent inference as advisory input
        """
        risk_components = {}
        
        # 1. Crypto risk
        risk_components["crypto"] = 0.0 if crypto_valid else 1.0
        
        # 2. Intent risk (rule-based)
        intent_risk = 0.0 if intent_result.intent_match else 0.8
        # Boost risk if confidence is low
        if intent_result.confidence < 0.6:
            intent_risk = max(intent_risk, 0.6)
        risk_components["intent"] = intent_risk
        
        # 3. Behavior risk
        risk_components["behavior"] = behavior_result.behavior_score
        
        # 4. Trajectory risk
        risk_components["trajectory"] = shadow_result.trajectory_risk
        
        # 5. ML intent risk (NEW - ADVISORY)
        if self.use_ml_intent and ml_intent_result is not None:
            # Only use ML risk if confidence is sufficient
            if ml_intent_result.confidence >= self.thresholds["ml_confidence_threshold"]:
                risk_components["ml_intent"] = ml_intent_result.intent_risk
            else:
                # Low ML confidence → use conservative estimate
                risk_components["ml_intent"] = 0.5
        else:
            # ML not available → neutral risk
            risk_components["ml_intent"] = 0.5
        
        # Weighted aggregation
        total_risk = (
            self.weights["crypto"] * risk_components["crypto"] +
            self.weights["intent"] * risk_components["intent"] +
            self.weights["behavior"] * risk_components["behavior"] +
            self.weights["trajectory"] * risk_components["trajectory"] +
            self.weights["ml_intent"] * risk_components["ml_intent"]
        )
        
        # Emergency overrides
        # If ANY layer says CRITICAL, overall risk is high
        if shadow_result.predicted_outcomes.geofence_violation:
            total_risk = max(total_risk, 0.85)
        
        if behavior_result.anomaly_level == "HIGH":
            total_risk = max(total_risk, 0.75)
        
        if not crypto_valid:
            total_risk = max(total_risk, 0.7)
        
        # NEW: If ML detects high-risk intent with high confidence
        if (self.use_ml_intent and ml_intent_result is not None and
            ml_intent_result.confidence >= self.thresholds["ml_confidence_threshold"] and
            ml_intent_result.intent_risk > 0.8):
            total_risk = max(total_risk, 0.75)
        
        return round(min(1.0, total_risk), 2)
    
    def determine_severity(self, risk: float, 
                          shadow_result,
                          intent_result) -> Severity:
        """
        Map risk score to severity level
        
        HIGH severity = inevitable unsafe outcome predicted
        """
        if risk < 0.3:
            return Severity.NONE
        elif risk < 0.5:
            return Severity.LOW
        elif risk < 0.7:
            return Severity.MEDIUM
        elif risk < 0.9:
            return Severity.HIGH
        else:
            return Severity.CRITICAL
    
    def decide(self,
              crypto_valid: bool,
              intent_result,
              behavior_result, 
              shadow_result,
              command_obj,
              ml_intent_result=None) -> DecisionResult:
        """
        Main decision function
        
        NEW: Accepts optional ml_intent_result as ADVISORY input
        
        Returns decision state + severity + explanation
        """
        # 1. Aggregate risk from all layers (including ML)
        total_risk = self.aggregate_risk(
            crypto_valid,
            intent_result,
            behavior_result,
            shadow_result,
            ml_intent_result
        )
        
        # 2. Determine severity
        severity = self.determine_severity(
            total_risk,
            shadow_result,
            intent_result
        )
        
        # 3. Make decision based on risk and severity
        decision, explanation = self._make_decision(
            total_risk,
            severity,
            crypto_valid,
            intent_result,
            behavior_result,
            shadow_result,
            command_obj,
            ml_intent_result
        )
        
        # 4. Calculate confidence (include ML if available)
        ml_confidence = ml_intent_result.confidence if ml_intent_result else None
        confidence = self._calculate_confidence(
            intent_result.confidence,
            behavior_result.behavior_score,
            crypto_valid,
            ml_confidence
        )
        
        # 5. Build contributing factors (include ML)
        factors = {
            "risk_score": total_risk,
            "crypto_valid": crypto_valid,
            "intent_match": intent_result.intent_match,
            "intent_confidence": intent_result.confidence,
            "behavior_score": behavior_result.behavior_score,
            "anomaly_level": behavior_result.anomaly_level,
            "trajectory_risk": shadow_result.trajectory_risk,
            "geofence_violation": shadow_result.predicted_outcomes.geofence_violation,
            
            # NEW: ML intent factors
            "ml_intent": ml_intent_result.intent if ml_intent_result else None,
            "ml_confidence": ml_intent_result.confidence if ml_intent_result else None,
            "ml_intent_risk": ml_intent_result.intent_risk if ml_intent_result else None,
            "ml_top_features": ml_intent_result.top_features if ml_intent_result else None,
        }
        
        return DecisionResult(
            decision=decision,
            severity=severity,
            confidence=confidence,
            explanation=explanation,
            contributing_factors=factors
        )
    
    def _make_decision(self, risk, severity, crypto_valid, 
                      intent_result, behavior_result, shadow_result,
                      command_obj, ml_intent_result=None) -> tuple:
        """
        Core decision logic: Map risk to decision state
        
        NEW: Considers ML intent in explanation
        """
        # CRITICAL severity → RTL (emergency escape)
        if severity == Severity.CRITICAL:
            explanation = "CRITICAL RISK: Initiating emergency RTL. "
            reasons = []
            
            if shadow_result.predicted_outcomes.geofence_violation:
                ttv = shadow_result.predicted_outcomes.time_to_violation
                reasons.append(f"Predicted geofence violation in {ttv:.1f}s")
            
            if not crypto_valid:
                reasons.append("Crypto validation failed")
            
            if behavior_result.anomaly_level == "HIGH":
                reasons.append(f"High behavioral anomaly: {', '.join(behavior_result.anomaly_features)}")
            
            explanation += " | ".join(reasons)
            return DecisionState.RTL, explanation
        
        # HIGH severity → HOLD (wait for clarification)
        if severity == Severity.HIGH:
            explanation = "HIGH RISK: Command held for review. "
            reasons = []
            
            if not intent_result.intent_match:
                reasons.append(f"Intent mismatch: {intent_result.reason}")
            
            if shadow_result.trajectory_risk > 0.7:
                reasons.append(f"High trajectory risk: {shadow_result.explanation}")
            
            if behavior_result.behavior_score > 0.6:
                reasons.append(f"Behavioral anomaly: {behavior_result.explanation}")
            
            # NEW: Include ML intent in explanation
            if (ml_intent_result and 
                ml_intent_result.confidence >= self.thresholds["ml_confidence_threshold"] and
                ml_intent_result.intent_risk > 0.7):
                reasons.append(f"ML detected high-risk intent: {ml_intent_result.intent} (risk={ml_intent_result.intent_risk:.2f})")
            
            explanation += " | ".join(reasons)
            return DecisionState.HOLD, explanation
        
        # MEDIUM severity → CONSTRAIN (execute with limits)
        if severity == Severity.MEDIUM:
            explanation = "MEDIUM RISK: Command constrained. "
            reasons = []
            
            if shadow_result.predicted_outcomes.velocity_risk:
                reasons.append("Velocity limited to safe range")
            
            if shadow_result.predicted_outcomes.altitude_risk:
                reasons.append("Altitude clamped to safe bounds")
            
            if behavior_result.behavior_score > 0.4:
                reasons.append("Rate limited due to behavioral pattern")
            
            explanation += " | ".join(reasons)
            return DecisionState.CONSTRAIN, explanation
        
        # LOW/NONE severity → ACCEPT
        explanation = "Command accepted. All layers report acceptable risk."
        return DecisionState.ACCEPT, explanation
    
    def _calculate_confidence(self, intent_conf, behavior_score, 
                            crypto_valid, ml_confidence=None) -> float:
        """
        Confidence in our decision
        High confidence = we're sure about this decision
        
        NEW: Considers ML model confidence
        """
        # Start high
        confidence = 0.9
        
        # Reduce if intent confidence is low
        if intent_conf < 0.6:
            confidence -= 0.2
        
        # Reduce if behavior is borderline
        if 0.4 < behavior_score < 0.6:
            confidence -= 0.1
        
        # Reduce if crypto failed (less data)
        if not crypto_valid:
            confidence -= 0.15
        
        # NEW: Adjust based on ML confidence
        if ml_confidence is not None:
            if ml_confidence < 0.5:
                confidence -= 0.1  # ML uncertain → lower overall confidence
            elif ml_confidence > 0.85:
                confidence += 0.05  # ML very confident → boost confidence
        
        return max(0.5, round(confidence, 2))


# Legacy compatibility
def decision_engine(crypto_valid: bool, trust_score: float, 
                   trust_threshold: float, command: dict):
    """
    Legacy binary decision function
    Kept for backward compatibility
    """
    from src.decision_engine.safe_mode import trigger_safe_mode
    from src.decision_engine.logger import log_event
    
    if crypto_valid and trust_score >= trust_threshold:
        log_event(
            status="ACCEPTED",
            reason="Crypto valid & AI trust high",
            command=command
        )
        return True
    else:
        reason = []
        if not crypto_valid:
            reason.append("Crypto verification failed")
        if trust_score < trust_threshold:
            reason.append("AI trust below threshold")
        
        log_event(
            status="REJECTED",
            reason=" | ".join(reason),
            command=command
        )
        
        trigger_safe_mode()
        return False