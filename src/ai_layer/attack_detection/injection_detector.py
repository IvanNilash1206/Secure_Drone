"""
Message Injection Attack Detector

Detects malicious command injection:
1. Unauthorized commands (unexpected command types)
2. Parameter anomalies (out-of-bounds values)
3. Context violations (command doesn't match flight state)
4. Privilege escalation attempts
5. Semantic anomalies (ML-based)
"""

import time
from typing import Dict, Any, Optional, List, Tuple, Set
from dataclasses import dataclass
from enum import Enum


class CommandType(Enum):
    """Command categories"""
    NAVIGATION = "NAVIGATION"
    MODE_CHANGE = "MODE_CHANGE"
    ARM_DISARM = "ARM_DISARM"
    TAKEOFF_LAND = "TAKEOFF_LAND"
    MISSION_UPLOAD = "MISSION_UPLOAD"
    PARAMETER_SET = "PARAMETER_SET"
    EMERGENCY = "EMERGENCY"
    TELEMETRY_REQUEST = "TELEMETRY_REQUEST"
    UNKNOWN = "UNKNOWN"


class FlightState(Enum):
    """Vehicle flight states"""
    DISARMED = "DISARMED"
    ARMED_GROUND = "ARMED_GROUND"
    TAKING_OFF = "TAKING_OFF"
    IN_FLIGHT = "IN_FLIGHT"
    LANDING = "LANDING"
    EMERGENCY = "EMERGENCY"


@dataclass
class InjectionMetrics:
    """Injection attack detection metrics"""
    is_injection: bool
    confidence: float
    detection_method: str
    explanation: str
    unauthorized_command: bool
    parameter_anomaly: bool
    context_violation: bool
    privilege_escalation: bool
    semantic_anomaly: bool
    risk_score: float  # 0.0 to 1.0
    
    def to_dict(self):
        return {
            "is_injection": self.is_injection,
            "confidence": self.confidence,
            "detection_method": self.detection_method,
            "explanation": self.explanation,
            "unauthorized_command": self.unauthorized_command,
            "parameter_anomaly": self.parameter_anomaly,
            "context_violation": self.context_violation,
            "privilege_escalation": self.privilege_escalation,
            "semantic_anomaly": self.semantic_anomaly,
            "risk_score": self.risk_score
        }


class InjectionDetector:
    """
    Multi-layer injection attack detection
    
    Detection layers:
    1. Command whitelist/blacklist
    2. Parameter bounds checking
    3. State-based command authorization
    4. Privilege level validation
    5. Semantic anomaly detection (ML-based)
    
    Attack patterns:
    - Unauthorized disarm during critical phase
    - Parameter injection (extreme values)
    - Mode change during autonomous mission
    - Emergency command injection
    - Geofence override attempts
    """
    
    def __init__(self):
        # Command authorization by flight state
        self.authorized_commands = {
            FlightState.DISARMED: {
                CommandType.ARM_DISARM,
                CommandType.MODE_CHANGE,
                CommandType.PARAMETER_SET,
                CommandType.MISSION_UPLOAD,
                CommandType.TELEMETRY_REQUEST
            },
            FlightState.ARMED_GROUND: {
                CommandType.ARM_DISARM,
                CommandType.TAKEOFF_LAND,
                CommandType.MODE_CHANGE,
                CommandType.EMERGENCY,
                CommandType.TELEMETRY_REQUEST
            },
            FlightState.TAKING_OFF: {
                CommandType.NAVIGATION,
                CommandType.MODE_CHANGE,
                CommandType.EMERGENCY,
                CommandType.TELEMETRY_REQUEST
            },
            FlightState.IN_FLIGHT: {
                CommandType.NAVIGATION,
                CommandType.MODE_CHANGE,
                CommandType.TAKEOFF_LAND,
                CommandType.EMERGENCY,
                CommandType.MISSION_UPLOAD,
                CommandType.TELEMETRY_REQUEST
            },
            FlightState.LANDING: {
                CommandType.NAVIGATION,
                CommandType.TAKEOFF_LAND,
                CommandType.EMERGENCY,
                CommandType.TELEMETRY_REQUEST
            },
            FlightState.EMERGENCY: {
                CommandType.EMERGENCY,
                CommandType.TAKEOFF_LAND,
                CommandType.ARM_DISARM,
                CommandType.TELEMETRY_REQUEST
            }
        }
        
        # Parameter bounds (example for common MAVLink commands)
        self.parameter_bounds = {
            "altitude": (0.0, 150.0),  # meters (FAA limit ~120m)
            "velocity": (0.0, 25.0),    # m/s
            "latitude": (-90.0, 90.0),
            "longitude": (-180.0, 180.0),
            "yaw": (-180.0, 180.0),     # degrees
            "pitch": (-90.0, 90.0),     # degrees
            "roll": (-45.0, 45.0),      # degrees
            "throttle": (0.0, 1.0),
        }
        
        # Dangerous command patterns
        self.dangerous_patterns = {
            "disarm_in_flight": {"command": CommandType.ARM_DISARM, "state": FlightState.IN_FLIGHT},
            "mode_change_during_landing": {"command": CommandType.MODE_CHANGE, "state": FlightState.LANDING},
            "extreme_altitude": {"param": "altitude", "min": 0.0, "max": 150.0},
            "extreme_velocity": {"param": "velocity", "min": 0.0, "max": 25.0},
        }
        
        # Current state
        self.current_state = FlightState.DISARMED
        self.mission_active = False
        self.altitude = 0.0
        self.armed = False
        
        # Statistics
        self.total_commands = 0
        self.detected_injections = 0
        self.unauthorized_count = 0
        self.parameter_violations = 0
        self.context_violations = 0
        self.privilege_violations = 0
        
        print("✅ Injection Detector initialized")
    
    def update_state(self, 
                    state: FlightState = None,
                    altitude: float = None,
                    armed: bool = None,
                    mission_active: bool = None):
        """Update vehicle state"""
        if state is not None:
            self.current_state = state
        if altitude is not None:
            self.altitude = altitude
        if armed is not None:
            self.armed = armed
        if mission_active is not None:
            self.mission_active = mission_active
    
    def check_command(self,
                     command_type: CommandType,
                     parameters: Dict[str, Any],
                     source_authenticated: bool = True,
                     ml_risk_score: float = 0.0) -> InjectionMetrics:
        """
        Check if command is malicious injection
        
        Args:
            command_type: Type of command
            parameters: Command parameters to validate
            source_authenticated: Whether source is authenticated
            ml_risk_score: ML-based anomaly score (0.0 to 1.0)
            
        Returns:
            InjectionMetrics with detection results
        """
        self.total_commands += 1
        
        # Layer 1: Command authorization check
        unauthorized = self._check_authorization(command_type)
        
        # Layer 2: Parameter bounds check
        param_anomaly, param_violations = self._check_parameters(parameters)
        
        # Layer 3: Context violation check
        context_violation, context_reason = self._check_context(command_type, parameters)
        
        # Layer 4: Privilege escalation check
        privilege_esc = self._check_privilege_escalation(command_type, source_authenticated)
        
        # Layer 5: Semantic anomaly (ML-based)
        semantic_anomaly = ml_risk_score > 0.7
        
        # Aggregate detection
        is_injection, confidence, method, explanation, risk_score = self._aggregate_detection(
            unauthorized, param_anomaly, context_violation, privilege_esc, semantic_anomaly,
            command_type, param_violations, context_reason, ml_risk_score
        )
        
        if is_injection:
            self.detected_injections += 1
        
        return InjectionMetrics(
            is_injection=is_injection,
            confidence=confidence,
            detection_method=method,
            explanation=explanation,
            unauthorized_command=unauthorized,
            parameter_anomaly=param_anomaly,
            context_violation=context_violation,
            privilege_escalation=privilege_esc,
            semantic_anomaly=semantic_anomaly,
            risk_score=risk_score
        )
    
    def _check_authorization(self, command_type: CommandType) -> bool:
        """Check if command is authorized in current state"""
        authorized_set = self.authorized_commands.get(self.current_state, set())
        
        if command_type not in authorized_set and command_type != CommandType.UNKNOWN:
            self.unauthorized_count += 1
            return True
        
        return False
    
    def _check_parameters(self, parameters: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Check if parameters are within valid bounds
        
        Returns: (has_anomaly, list_of_violations)
        """
        violations = []
        
        for param_name, value in parameters.items():
            if param_name in self.parameter_bounds:
                min_val, max_val = self.parameter_bounds[param_name]
                
                try:
                    numeric_value = float(value)
                    if numeric_value < min_val or numeric_value > max_val:
                        violations.append(f"{param_name}={numeric_value} out of bounds [{min_val}, {max_val}]")
                        self.parameter_violations += 1
                except (ValueError, TypeError):
                    violations.append(f"{param_name} has invalid type: {type(value)}")
        
        return len(violations) > 0, violations
    
    def _check_context(self, command_type: CommandType, parameters: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Check for dangerous context-command combinations
        
        Returns: (is_violation, reason)
        """
        # Disarm in flight
        if command_type == CommandType.ARM_DISARM and self.current_state == FlightState.IN_FLIGHT:
            if parameters.get("arm", 1) == 0:  # Disarm command
                self.context_violations += 1
                return True, "Attempting to disarm while in flight (crash risk)"
        
        # Mode change during landing
        if command_type == CommandType.MODE_CHANGE and self.current_state == FlightState.LANDING:
            self.context_violations += 1
            return True, "Mode change during landing (unsafe)"
        
        # Takeoff while already in flight
        if command_type == CommandType.TAKEOFF_LAND and self.current_state == FlightState.IN_FLIGHT:
            if parameters.get("command", "").upper() == "TAKEOFF":
                self.context_violations += 1
                return True, "Takeoff command while already airborne"
        
        # Mission upload during active mission
        if command_type == CommandType.MISSION_UPLOAD and self.mission_active:
            return True, "Mission upload during active mission (risky)"
        
        return False, "Context valid"
    
    def _check_privilege_escalation(self, command_type: CommandType, authenticated: bool) -> bool:
        """Check for privilege escalation attempts"""
        # Critical commands require authentication
        critical_commands = {
            CommandType.ARM_DISARM,
            CommandType.MODE_CHANGE,
            CommandType.PARAMETER_SET,
            CommandType.EMERGENCY
        }
        
        if command_type in critical_commands and not authenticated:
            self.privilege_violations += 1
            return True
        
        return False
    
    def _aggregate_detection(self,
                            unauthorized: bool,
                            param_anomaly: bool,
                            context_violation: bool,
                            privilege_esc: bool,
                            semantic_anomaly: bool,
                            command_type: CommandType,
                            param_violations: List[str],
                            context_reason: str,
                            ml_risk: float) -> Tuple[bool, float, str, str, float]:
        """
        Aggregate all detection layers
        
        Returns: (is_injection, confidence, method, explanation, risk_score)
        """
        # Calculate risk score
        risk_score = 0.0
        risk_factors = []
        
        if unauthorized:
            risk_score += 0.3
            risk_factors.append("unauthorized command")
        
        if param_anomaly:
            risk_score += 0.2
            risk_factors.append(f"parameter violations: {', '.join(param_violations)}")
        
        if context_violation:
            risk_score += 0.3
            risk_factors.append(f"context violation: {context_reason}")
        
        if privilege_esc:
            risk_score += 0.4
            risk_factors.append("privilege escalation")
        
        if semantic_anomaly:
            risk_score += ml_risk * 0.3
            risk_factors.append(f"semantic anomaly (ML risk={ml_risk:.2f})")
        
        risk_score = min(risk_score, 1.0)
        
        # Determine if injection
        if privilege_esc or (context_violation and unauthorized):
            # Critical combinations
            return True, 0.95, "privilege_context", f"Critical injection: {', '.join(risk_factors)}", risk_score
        
        if context_violation:
            return True, 0.85, "context", context_reason, risk_score
        
        if unauthorized and param_anomaly:
            return True, 0.80, "unauthorized_params", f"Unauthorized command with bad params: {', '.join(risk_factors)}", risk_score
        
        if param_anomaly and len(param_violations) >= 2:
            return True, 0.70, "parameters", f"Multiple parameter violations: {', '.join(param_violations)}", risk_score
        
        if unauthorized:
            return True, 0.65, "unauthorized", f"Command not authorized in {self.current_state.value} state", risk_score
        
        if semantic_anomaly:
            return True, 0.60, "semantic", f"ML-based anomaly detected (risk={ml_risk:.2f})", risk_score
        
        # All clear
        return False, 0.0, "none", "No injection detected", risk_score
    
    def reset(self):
        """Reset detector state"""
        self.current_state = FlightState.DISARMED
        self.mission_active = False
        self.altitude = 0.0
        self.armed = False
        self.total_commands = 0
        self.detected_injections = 0
        self.unauthorized_count = 0
        self.parameter_violations = 0
        self.context_violations = 0
        self.privilege_violations = 0
        print("Injection Detector reset")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get detector statistics"""
        return {
            "total_commands": self.total_commands,
            "detected_injections": self.detected_injections,
            "unauthorized_count": self.unauthorized_count,
            "parameter_violations": self.parameter_violations,
            "context_violations": self.context_violations,
            "privilege_violations": self.privilege_violations,
            "detection_rate": self.detected_injections / self.total_commands if self.total_commands > 0 else 0.0,
            "current_state": self.current_state.value
        }


if __name__ == "__main__":
    # Test Injection detector
    print("Testing Injection Detector\n")
    
    detector = InjectionDetector()
    
    # Test 1: Normal command
    print("1. Normal command (ARM on ground):")
    detector.update_state(state=FlightState.DISARMED)
    metrics = detector.check_command(
        CommandType.ARM_DISARM,
        {"arm": 1},
        source_authenticated=True
    )
    print(f"   Injection={metrics.is_injection}, Risk={metrics.risk_score:.2f}")
    
    # Test 2: Unauthorized disarm in flight
    print("\n2. INJECTION: Disarm while in flight:")
    detector.update_state(state=FlightState.IN_FLIGHT, altitude=50.0, armed=True)
    metrics = detector.check_command(
        CommandType.ARM_DISARM,
        {"arm": 0},
        source_authenticated=True
    )
    print(f"   Injection={metrics.is_injection}, Confidence={metrics.confidence:.2f}, Risk={metrics.risk_score:.2f}")
    print(f"   {metrics.explanation}")
    
    # Test 3: Parameter injection
    print("\n3. INJECTION: Extreme altitude parameter:")
    detector.update_state(state=FlightState.IN_FLIGHT)
    metrics = detector.check_command(
        CommandType.NAVIGATION,
        {"altitude": 500.0, "latitude": 47.0, "longitude": -122.0},
        source_authenticated=True
    )
    print(f"   Injection={metrics.is_injection}, Confidence={metrics.confidence:.2f}, Risk={metrics.risk_score:.2f}")
    print(f"   {metrics.explanation}")
    
    # Test 4: Privilege escalation
    print("\n4. INJECTION: Unauthenticated critical command:")
    detector.update_state(state=FlightState.IN_FLIGHT)
    metrics = detector.check_command(
        CommandType.MODE_CHANGE,
        {"mode": "MANUAL"},
        source_authenticated=False  # NOT authenticated
    )
    print(f"   Injection={metrics.is_injection}, Confidence={metrics.confidence:.2f}, Risk={metrics.risk_score:.2f}")
    print(f"   {metrics.explanation}")
    
    # Test 5: Mode change during landing
    print("\n5. INJECTION: Mode change during landing:")
    detector.update_state(state=FlightState.LANDING, altitude=5.0)
    metrics = detector.check_command(
        CommandType.MODE_CHANGE,
        {"mode": "GUIDED"},
        source_authenticated=True
    )
    print(f"   Injection={metrics.is_injection}, Confidence={metrics.confidence:.2f}, Risk={metrics.risk_score:.2f}")
    print(f"   {metrics.explanation}")
    
    # Statistics
    print("\n6. Statistics:")
    stats = detector.get_statistics()
    for key, value in stats.items():
        print(f"   {key}: {value}")
