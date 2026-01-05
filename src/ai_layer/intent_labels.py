"""
Intent Label Schema and Risk Definitions

Defines:
1. Intent classes for command classification
2. Contextual risk scoring rules
3. Label generation utilities for training data

Design principles:
- Intent is inferred, not declared
- Risk is contextual, not intrinsic
- Human-interpretable categories
- Finite, predefined label space
"""

from enum import Enum
from typing import Dict, Any, Tuple
from dataclasses import dataclass
import numpy as np


class IntentClass(Enum):
    """
    Finite set of operational intents
    
    Each represents a high-level operational goal
    """
    NAVIGATION = "NAVIGATION"              # Waypoint navigation, position commands
    MISSION_UPDATE = "MISSION_UPDATE"      # Mission plan changes, waypoint updates
    MODE_CONTROL = "MODE_CONTROL"          # Flight mode changes (AUTO, GUIDED, RTL, etc.)
    ABORT = "ABORT"                        # Emergency abort, RTL, safe mode
    LANDING = "LANDING"                    # Landing sequence, descent
    MANUAL_OVERRIDE = "MANUAL_OVERRIDE"    # Human taking direct control
    PARAMETER_CHANGE = "PARAMETER_CHANGE"  # System parameter modifications
    ARM_DISARM = "ARM_DISARM"             # Motor arming/disarming
    UNKNOWN = "UNKNOWN"                    # Unrecognized pattern
    
    @classmethod
    def from_string(cls, s: str):
        """Convert string to IntentClass"""
        try:
            return cls[s.upper()]
        except KeyError:
            return cls.UNKNOWN
    
    @classmethod
    def to_index(cls, intent) -> int:
        """Convert intent to numerical index for classification"""
        mapping = {
            cls.NAVIGATION: 0,
            cls.MISSION_UPDATE: 1,
            cls.MODE_CONTROL: 2,
            cls.ABORT: 3,
            cls.LANDING: 4,
            cls.MANUAL_OVERRIDE: 5,
            cls.PARAMETER_CHANGE: 6,
            cls.ARM_DISARM: 7,
            cls.UNKNOWN: 8,
        }
        return mapping.get(intent, 8)
    
    @classmethod
    def from_index(cls, idx: int):
        """Convert numerical index to IntentClass"""
        mapping = [
            cls.NAVIGATION,
            cls.MISSION_UPDATE,
            cls.MODE_CONTROL,
            cls.ABORT,
            cls.LANDING,
            cls.MANUAL_OVERRIDE,
            cls.PARAMETER_CHANGE,
            cls.ARM_DISARM,
            cls.UNKNOWN,
        ]
        if 0 <= idx < len(mapping):
            return mapping[idx]
        return cls.UNKNOWN


class RiskLevel(Enum):
    """
    Risk severity levels
    
    Note: Risk is contextual - same command can be LOW or HIGH
    depending on flight state
    """
    LOW = "LOW"           # Normal operation, safe context
    MEDIUM = "MEDIUM"     # Elevated risk, requires attention
    HIGH = "HIGH"         # Dangerous context, immediate concern
    
    @classmethod
    def from_score(cls, score: float):
        """Convert risk score [0, 1] to RiskLevel"""
        if score < 0.33:
            return cls.LOW
        elif score < 0.67:
            return cls.MEDIUM
        else:
            return cls.HIGH
    
    @classmethod
    def to_score(cls, level) -> float:
        """Convert RiskLevel to numerical score"""
        mapping = {
            cls.LOW: 0.2,
            cls.MEDIUM: 0.5,
            cls.HIGH: 0.85,
        }
        return mapping.get(level, 0.5)


@dataclass
class IntentLabel:
    """
    Complete label for training sample
    
    Contains both intent classification and risk regression targets
    """
    intent: IntentClass
    risk_score: float  # [0, 1]
    
    # Metadata for training
    context_flags: Dict[str, bool]  # What context factors contributed to risk
    reasoning: str  # Human-readable explanation
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'intent': self.intent.value,
            'intent_index': IntentClass.to_index(self.intent),
            'risk_score': self.risk_score,
            'risk_level': RiskLevel.from_score(self.risk_score).value,
            'context_flags': self.context_flags,
            'reasoning': self.reasoning
        }


class ContextualRiskScorer:
    """
    Scores command risk based on context
    
    Risk is NOT intrinsic to command - it depends on:
    - Current flight state
    - Vehicle capabilities
    - Environmental conditions
    - Operational phase
    """
    
    def __init__(self):
        # Risk weights for different context factors
        self.weights = {
            'low_battery': 0.3,
            'high_altitude': 0.25,
            'high_velocity': 0.2,
            'armed_transition': 0.4,
            'mode_mismatch': 0.35,
            'geofence_proximity': 0.5,
            'mission_phase_conflict': 0.3,
            'rapid_command_rate': 0.25,
            'parameter_magnitude': 0.15,
        }
    
    def score(self, 
              intent: IntentClass,
              command_ctx: Dict[str, Any],
              vehicle_state: Dict[str, Any]) -> Tuple[float, Dict[str, bool], str]:
        """
        Compute contextual risk score
        
        Args:
            intent: Inferred intent class
            command_ctx: Command metadata
            vehicle_state: Current vehicle state
            
        Returns:
            (risk_score, context_flags, reasoning)
        """
        risk_factors = []
        context_flags = {}
        
        # Base risk by intent type
        base_risk = self._get_base_risk(intent)
        
        # Context modifiers
        battery = vehicle_state.get('battery_level', 1.0)
        altitude = vehicle_state.get('altitude', 0.0)
        velocity = vehicle_state.get('velocity', 0.0)
        armed = vehicle_state.get('armed', False)
        flight_mode = vehicle_state.get('flight_mode', 'MANUAL')
        mission_phase = vehicle_state.get('mission_phase', 'NONE')
        
        # 1. Low battery risk
        if battery < 0.2:
            risk_factors.append(self.weights['low_battery'])
            context_flags['low_battery'] = True
        
        # 2. High altitude risk (commands at high altitude are riskier)
        if altitude > 80.0:
            risk_factors.append(self.weights['high_altitude'])
            context_flags['high_altitude'] = True
        
        # 3. High velocity risk
        if velocity > 15.0:
            risk_factors.append(self.weights['high_velocity'])
            context_flags['high_velocity'] = True
        
        # 4. Armed state transitions (ARM/DISARM are high risk)
        if intent == IntentClass.ARM_DISARM:
            risk_factors.append(self.weights['armed_transition'])
            context_flags['armed_transition'] = True
        
        # 5. Mode mismatch (command doesn't match current mode)
        if self._check_mode_mismatch(intent, flight_mode):
            risk_factors.append(self.weights['mode_mismatch'])
            context_flags['mode_mismatch'] = True
        
        # 6. Mission phase conflict
        if self._check_phase_conflict(intent, mission_phase):
            risk_factors.append(self.weights['mission_phase_conflict'])
            context_flags['mission_phase_conflict'] = True
        
        # 7. Rapid command rate (from command context)
        cmd_frequency = command_ctx.get('cmd_frequency_1s', 0.0)
        if cmd_frequency > 0.5:  # >5 commands per second
            risk_factors.append(self.weights['rapid_command_rate'])
            context_flags['rapid_command_rate'] = True
        
        # 8. Large parameter magnitude
        param_mag = command_ctx.get('param_magnitude', 0.0)
        if param_mag > 0.8:  # normalized magnitude
            risk_factors.append(self.weights['parameter_magnitude'])
            context_flags['parameter_magnitude'] = True
        
        # Aggregate risk
        if risk_factors:
            context_risk = np.mean(risk_factors)
        else:
            context_risk = 0.0
        
        # Combine base + context risk (weighted average)
        total_risk = 0.4 * base_risk + 0.6 * context_risk
        total_risk = np.clip(total_risk, 0.0, 1.0)
        
        # Generate reasoning
        reasoning = self._generate_reasoning(intent, context_flags, total_risk)
        
        return total_risk, context_flags, reasoning
    
    def _get_base_risk(self, intent: IntentClass) -> float:
        """
        Base risk level for each intent type
        
        This is the intrinsic risk before context modifiers
        """
        risk_map = {
            IntentClass.NAVIGATION: 0.2,        # Low base risk
            IntentClass.MISSION_UPDATE: 0.3,    # Medium-low
            IntentClass.MODE_CONTROL: 0.4,      # Medium
            IntentClass.ABORT: 0.5,             # Medium-high (emergency action)
            IntentClass.LANDING: 0.4,           # Medium (critical phase)
            IntentClass.MANUAL_OVERRIDE: 0.5,   # Medium-high (operator takeover)
            IntentClass.PARAMETER_CHANGE: 0.6,  # High (system modification)
            IntentClass.ARM_DISARM: 0.7,        # High (motor control)
            IntentClass.UNKNOWN: 0.8,           # Very high (unrecognized)
        }
        return risk_map.get(intent, 0.5)
    
    def _check_mode_mismatch(self, intent: IntentClass, flight_mode: str) -> bool:
        """Check if intent conflicts with current flight mode"""
        
        # Manual override in AUTO mode = mismatch
        if intent == IntentClass.MANUAL_OVERRIDE and flight_mode == 'AUTO':
            return True
        
        # Navigation commands in MANUAL mode = mismatch
        if intent == IntentClass.NAVIGATION and flight_mode == 'MANUAL':
            return True
        
        # Mission updates in MANUAL/STABILIZE = mismatch
        if intent == IntentClass.MISSION_UPDATE and flight_mode in ['MANUAL', 'STABILIZE']:
            return True
        
        return False
    
    def _check_phase_conflict(self, intent: IntentClass, mission_phase: str) -> bool:
        """Check if intent conflicts with current mission phase"""
        
        # Navigation commands during landing = conflict
        if intent == IntentClass.NAVIGATION and mission_phase in ['LANDING', 'LANDING_APPROACH']:
            return True
        
        # Mission updates during takeoff/landing = conflict
        if intent == IntentClass.MISSION_UPDATE and mission_phase in ['TAKEOFF', 'LANDING']:
            return True
        
        return False
    
    def _generate_reasoning(self, 
                          intent: IntentClass, 
                          context_flags: Dict[str, bool],
                          risk_score: float) -> str:
        """Generate human-readable risk reasoning"""
        
        risk_level = RiskLevel.from_score(risk_score)
        
        reasoning = f"{risk_level.value} risk for {intent.value} intent"
        
        if context_flags:
            factors = [k.replace('_', ' ') for k, v in context_flags.items() if v]
            reasoning += f" due to: {', '.join(factors)}"
        else:
            reasoning += " (normal operational context)"
        
        return reasoning


# Label generation utilities for training data
class IntentLabeler:
    """
    Automatic labeling of command sequences for training
    
    Uses heuristics + mission context to infer intent
    """
    
    def __init__(self):
        self.risk_scorer = ContextualRiskScorer()
    
    def label_command(self,
                     command_ctx: Dict[str, Any],
                     vehicle_state: Dict[str, Any],
                     sequence_context: Dict[str, Any] = None) -> IntentLabel:
        """
        Generate intent + risk label for a command
        
        Args:
            command_ctx: Command metadata (from feature extractor)
            vehicle_state: Vehicle state at time of command
            sequence_context: Optional sequence-level context
            
        Returns:
            IntentLabel with intent class and risk score
        """
        # Infer intent from command type
        intent = self._infer_intent(command_ctx, vehicle_state)
        
        # Score risk contextually
        risk_score, context_flags, reasoning = self.risk_scorer.score(
            intent, command_ctx, vehicle_state
        )
        
        return IntentLabel(
            intent=intent,
            risk_score=risk_score,
            context_flags=context_flags,
            reasoning=reasoning
        )
    
    def _infer_intent(self, 
                     command_ctx: Dict[str, Any],
                     vehicle_state: Dict[str, Any]) -> IntentClass:
        """
        Infer intent from command type + context
        
        Uses rule-based heuristics (this is what ML will learn to do better)
        """
        cmd_type = command_ctx.get('command_type', '').upper()
        flight_mode = vehicle_state.get('flight_mode', 'MANUAL')
        
        # ARM/DISARM commands
        if 'ARM' in cmd_type or 'DISARM' in cmd_type:
            return IntentClass.ARM_DISARM
        
        # Mode changes
        if 'MODE' in cmd_type or cmd_type in ['SET_MODE', 'DO_SET_MODE']:
            return IntentClass.MODE_CONTROL
        
        # Position/navigation
        if any(x in cmd_type for x in ['POSITION', 'WAYPOINT', 'GOTO', 'NAV']):
            return IntentClass.NAVIGATION
        
        # Mission commands
        if any(x in cmd_type for x in ['MISSION', 'PLAN', 'WAYPOINT_COUNT']):
            return IntentClass.MISSION_UPDATE
        
        # Landing
        if 'LAND' in cmd_type:
            return IntentClass.LANDING
        
        # RTL / Abort
        if any(x in cmd_type for x in ['RTL', 'RETURN', 'ABORT', 'EMERGENCY']):
            return IntentClass.ABORT
        
        # Parameter changes
        if 'PARAM' in cmd_type:
            return IntentClass.PARAMETER_CHANGE
        
        # Manual control
        if 'MANUAL' in cmd_type or flight_mode == 'MANUAL':
            return IntentClass.MANUAL_OVERRIDE
        
        # Default
        return IntentClass.UNKNOWN


# Export key classes
__all__ = [
    'IntentClass',
    'RiskLevel',
    'IntentLabel',
    'ContextualRiskScorer',
    'IntentLabeler',
]


if __name__ == "__main__":
    # Test labeling
    labeler = IntentLabeler()
    
    # Test case 1: Navigation at low altitude, good battery
    label1 = labeler.label_command(
        command_ctx={
            'command_type': 'SET_POSITION_TARGET',
            'cmd_frequency_1s': 0.2,
            'param_magnitude': 0.3,
        },
        vehicle_state={
            'flight_mode': 'GUIDED',
            'battery_level': 0.8,
            'altitude': 25.0,
            'velocity': 5.0,
            'armed': True,
            'mission_phase': 'CRUISE',
        }
    )
    print("Test 1 - Normal navigation:")
    print(f"  Intent: {label1.intent.value}")
    print(f"  Risk: {label1.risk_score:.2f} ({RiskLevel.from_score(label1.risk_score).value})")
    print(f"  Reasoning: {label1.reasoning}\n")
    
    # Test case 2: ARM command at high altitude with low battery
    label2 = labeler.label_command(
        command_ctx={
            'command_type': 'ARM_DISARM',
            'cmd_frequency_1s': 0.1,
            'param_magnitude': 0.5,
        },
        vehicle_state={
            'flight_mode': 'GUIDED',
            'battery_level': 0.15,  # LOW BATTERY
            'altitude': 85.0,  # HIGH ALTITUDE
            'velocity': 3.0,
            'armed': False,
            'mission_phase': 'NONE',
        }
    )
    print("Test 2 - High-risk ARM command:")
    print(f"  Intent: {label2.intent.value}")
    print(f"  Risk: {label2.risk_score:.2f} ({RiskLevel.from_score(label2.risk_score).value})")
    print(f"  Reasoning: {label2.reasoning}\n")
    
    # Test case 3: Navigation during landing phase (conflict)
    label3 = labeler.label_command(
        command_ctx={
            'command_type': 'SET_POSITION_TARGET',
            'cmd_frequency_1s': 0.3,
            'param_magnitude': 0.6,
        },
        vehicle_state={
            'flight_mode': 'AUTO',
            'battery_level': 0.6,
            'altitude': 15.0,
            'velocity': 2.0,
            'armed': True,
            'mission_phase': 'LANDING',  # CONFLICT
        }
    )
    print("Test 3 - Navigation during landing (phase conflict):")
    print(f"  Intent: {label3.intent.value}")
    print(f"  Risk: {label3.risk_score:.2f} ({RiskLevel.from_score(label3.risk_score).value})")
    print(f"  Reasoning: {label3.reasoning}\n")
    
    print("✅ Intent labeling test complete")
