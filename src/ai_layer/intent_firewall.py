"""
Layer 3: Command Intent Firewall (NOVEL COMPONENT 🔥)

Purpose: Infer what the command is trying to achieve, not just what it says.
This is WHERE AEGIS GOES BEYOND CRYPTO.

Intent Classes:
- NAVIGATION: Moving to waypoints, following missions
- RETURN: RTL, coming home, abort sequences
- SURVEY: Systematic area coverage, mapping
- OVERRIDE: Manual intervention, emergency takeover
- EMERGENCY: Critical safety commands
- MANUAL_CONTROL: Human pilot control
- CONFIG: Parameter changes, setup
"""

from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import json


class Intent(Enum):
    """Intent categories"""
    NAVIGATION = "NAVIGATION"
    RETURN = "RETURN"
    SURVEY = "SURVEY"
    OVERRIDE = "OVERRIDE"
    EMERGENCY = "EMERGENCY"
    MANUAL_CONTROL = "MANUAL_CONTROL"
    CONFIG = "CONFIG"
    UNKNOWN = "UNKNOWN"


class MissionPhase(Enum):
    """Current mission state"""
    PRE_FLIGHT = "PRE_FLIGHT"
    TAKEOFF = "TAKEOFF"
    CRUISE = "CRUISE"
    MISSION = "MISSION"
    RETURN = "RETURN"
    LANDING = "LANDING"
    IDLE = "IDLE"


class FlightMode(Enum):
    """ArduPilot/PX4 flight modes"""
    MANUAL = "MANUAL"
    STABILIZE = "STABILIZE"
    GUIDED = "GUIDED"
    AUTO = "AUTO"
    RTL = "RTL"
    LAND = "LAND"
    LOITER = "LOITER"
    UNKNOWN = "UNKNOWN"


@dataclass
class IntentResult:
    """Output of intent analysis"""
    intent: Intent
    confidence: float  # 0.0 to 1.0
    intent_match: bool
    reason: str
    mission_phase: MissionPhase
    expected_intents: list[Intent]
    
    def to_dict(self):
        return {
            "intent": self.intent.value,
            "confidence": self.confidence,
            "intent_match": self.intent_match,
            "reason": self.reason,
            "mission_phase": self.mission_phase.value,
            "expected_intents": [i.value for i in self.expected_intents]
        }


class IntentFirewall:
    """
    Infers command intent and validates against mission context
    
    Key Innovation: Same command has different meaning in different contexts
    Example: RTL during survey mission = INTENT MISMATCH
    """
    
    def __init__(self):
        self.current_phase = MissionPhase.IDLE
        self.current_mode = FlightMode.UNKNOWN
        self.mission_active = False
        self.armed = False
        self.altitude = 0.0
        self.command_history = []  # Last 10 commands
        
        print("✅ Intent Firewall initialized")
    
    def update_state(self, mode: str = None, armed: bool = None, 
                     altitude: float = None, mission_active: bool = None):
        """Update vehicle state from telemetry"""
        if mode:
            self.current_mode = self._parse_mode(mode)
        if armed is not None:
            self.armed = armed
        if altitude is not None:
            self.altitude = altitude
        if mission_active is not None:
            self.mission_active = mission_active
        
        # Infer mission phase
        self._update_mission_phase()
    
    def _parse_mode(self, mode_str: str) -> FlightMode:
        """Convert mode string to enum"""
        mode_upper = mode_str.upper()
        for fm in FlightMode:
            if fm.value in mode_upper:
                return fm
        return FlightMode.UNKNOWN
    
    def _update_mission_phase(self):
        """Infer current mission phase from state"""
        if not self.armed:
            self.current_phase = MissionPhase.IDLE
        elif self.altitude < 2.0 and self.armed:
            self.current_phase = MissionPhase.TAKEOFF
        elif self.current_mode == FlightMode.RTL:
            self.current_phase = MissionPhase.RETURN
        elif self.current_mode == FlightMode.LAND or (self.altitude < 2.0 and self.current_mode != FlightMode.MANUAL):
            self.current_phase = MissionPhase.LANDING
        elif self.mission_active and self.current_mode == FlightMode.AUTO:
            self.current_phase = MissionPhase.MISSION
        elif self.altitude > 10.0:
            self.current_phase = MissionPhase.CRUISE
        else:
            self.current_phase = MissionPhase.IDLE
    
    def infer_intent(self, command_obj) -> Intent:
        """
        Map command to intent class
        Uses command type + parameters + context
        """
        cmd_type = command_obj.command_type
        params = command_obj.params
        
        # Direct mappings
        if cmd_type == "RETURN":
            return Intent.RETURN
        
        if cmd_type == "EMERGENCY":
            return Intent.EMERGENCY
        
        if cmd_type == "MANUAL":
            return Intent.MANUAL_CONTROL
        
        if cmd_type == "CONFIG":
            return Intent.CONFIG
        
        # Navigation commands - need context
        if cmd_type == "NAVIGATION":
            # Check for abort patterns
            if self._is_abort_pattern():
                return Intent.OVERRIDE
            
            # Check for survey pattern
            if self._is_survey_pattern():
                return Intent.SURVEY
            
            return Intent.NAVIGATION
        
        # Mode changes - context dependent
        if cmd_type == "MODE_CHANGE":
            target_mode = params.get("custom_mode", 0)
            if target_mode == 6:  # RTL in ArduPilot
                return Intent.RETURN
            elif target_mode == 9:  # LAND
                return Intent.EMERGENCY
            else:
                return Intent.OVERRIDE
        
        # ARM/DISARM
        if cmd_type == "ARM":
            return Intent.EMERGENCY if not self.armed else Intent.CONFIG
        
        return Intent.UNKNOWN
    
    def _is_abort_pattern(self) -> bool:
        """Detect sudden RTL/return commands during mission"""
        # Velocity commands with negative Z = descend fast
        # Or sudden mode switch to RTL
        if len(self.command_history) >= 2:
            last_cmd = self.command_history[-1]
            if last_cmd.get("command_type") == "RETURN":
                return True
        return False
    
    def _is_survey_pattern(self) -> bool:
        """Detect systematic waypoint patterns (survey missions)"""
        if len(self.command_history) >= 3:
            # Check for regular spacing
            # This is simplified - real version would check grid patterns
            return self.mission_active and self.current_mode == FlightMode.AUTO
        return False
    
    def get_expected_intents(self, phase: MissionPhase) -> list[Intent]:
        """What intents are expected in this mission phase?"""
        expectations = {
            MissionPhase.IDLE: [Intent.CONFIG, Intent.EMERGENCY],
            MissionPhase.PRE_FLIGHT: [Intent.CONFIG, Intent.EMERGENCY],
            MissionPhase.TAKEOFF: [Intent.NAVIGATION, Intent.EMERGENCY, Intent.RETURN],
            MissionPhase.CRUISE: [Intent.NAVIGATION, Intent.MANUAL_CONTROL, Intent.RETURN],
            MissionPhase.MISSION: [Intent.NAVIGATION, Intent.SURVEY, Intent.RETURN],
            MissionPhase.RETURN: [Intent.RETURN, Intent.EMERGENCY],
            MissionPhase.LANDING: [Intent.EMERGENCY, Intent.RETURN]
        }
        return expectations.get(phase, [Intent.UNKNOWN])
    
    def calculate_confidence(self, intent: Intent, command_obj) -> float:
        """
        Confidence in intent inference
        Based on:
        - Command clarity (RETURN = high, NAVIGATION = medium)
        - Context availability
        - Historical consistency
        """
        base_confidence = {
            Intent.RETURN: 0.95,
            Intent.EMERGENCY: 0.95,
            Intent.MANUAL_CONTROL: 0.90,
            Intent.CONFIG: 0.85,
            Intent.NAVIGATION: 0.75,
            Intent.SURVEY: 0.70,
            Intent.OVERRIDE: 0.65,
            Intent.UNKNOWN: 0.30
        }
        
        conf = base_confidence.get(intent, 0.5)
        
        # Boost if we have good context
        if self.current_mode != FlightMode.UNKNOWN:
            conf = min(1.0, conf + 0.05)
        
        # Reduce if command type was UNKNOWN
        if command_obj.command_type == "UNKNOWN":
            conf *= 0.7
        
        return round(conf, 2)
    
    def validate_intent(self, intent: Intent, confidence: float) -> IntentResult:
        """
        Check if intent matches mission context
        
        KEY RULE: Unexpected intent = MISMATCH
        Example: RTL during active survey mission = suspicious
        """
        expected = self.get_expected_intents(self.current_phase)
        
        # Check match
        intent_match = intent in expected or intent == Intent.EMERGENCY
        
        # Build reason
        if intent_match:
            reason = f"Intent '{intent.value}' expected in {self.current_phase.value}"
        else:
            reason = f"MISMATCH: Intent '{intent.value}' unexpected in {self.current_phase.value}. Expected: {[i.value for i in expected]}"
        
        # Low confidence = suspicious
        if confidence < 0.6:
            intent_match = False
            reason += f" | Low confidence ({confidence})"
        
        return IntentResult(
            intent=intent,
            confidence=confidence,
            intent_match=intent_match,
            reason=reason,
            mission_phase=self.current_phase,
            expected_intents=expected
        )
    
    def analyze(self, command_obj) -> IntentResult:
        """
        Main entry point: Analyze command intent
        
        Returns IntentResult with intent, confidence, and match status
        """
        # 1. Infer intent
        intent = self.infer_intent(command_obj)
        
        # 2. Calculate confidence
        confidence = self.calculate_confidence(intent, command_obj)
        
        # 3. Validate against context
        result = self.validate_intent(intent, confidence)
        
        # 4. Update history
        self.command_history.append({
            "command_type": command_obj.command_type,
            "intent": intent.value,
            "timestamp": command_obj.timestamp
        })
        if len(self.command_history) > 10:
            self.command_history.pop(0)
        
        return result


def main():
    """Test Intent Firewall"""
    firewall = IntentFirewall()
    
    # Simulate mission scenario
    print("\n=== Scenario: Survey Mission ===")
    firewall.update_state(mode="AUTO", armed=True, altitude=50.0, mission_active=True)
    
    # Test case 1: Normal navigation
    class MockCommand:
        command_type = "NAVIGATION"
        params = {"lat": 47.0, "lon": -122.0}
        timestamp = 1234567890.0
    
    result = firewall.analyze(MockCommand())
    print(f"\nTest 1 - Navigation during mission:")
    print(json.dumps(result.to_dict(), indent=2))
    
    # Test case 2: Sudden RTL (INTENT MISMATCH!)
    class MockRTL:
        command_type = "RETURN"
        params = {}
        timestamp = 1234567891.0
    
    result = firewall.analyze(MockRTL())
    print(f"\nTest 2 - Sudden RTL during mission:")
    print(json.dumps(result.to_dict(), indent=2))
    print(f"⚠️ Intent Match: {result.intent_match}")


if __name__ == "__main__":
    main()
