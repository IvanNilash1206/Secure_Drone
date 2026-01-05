"""
Layer 5: Shadow Execution (Digital Twin Lite) (NOVEL COMPONENT 🚀)

Purpose: Predict what will happen if we obey this command
NOT full simulation. NOT physics. Just risk prediction.

Predicts:
- Short-horizon trajectory (5-10 seconds)
- Geofence violations
- Energy impact
- Loss-of-control risk

Output is RISK, not motion.
"""

import math
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
import json


@dataclass
class PredictedOutcome:
    """Predicted consequences of executing command"""
    geofence_violation: bool
    time_to_violation: Optional[float]  # seconds until breach
    altitude_risk: bool  # Too high or too low
    velocity_risk: bool  # Too fast
    energy_margin: str  # "HIGH", "MEDIUM", "LOW", "CRITICAL"
    loss_of_control_risk: bool
    collision_risk: bool
    
    def to_dict(self):
        return {
            "geofence_violation": self.geofence_violation,
            "time_to_violation": self.time_to_violation,
            "altitude_risk": self.altitude_risk,
            "velocity_risk": self.velocity_risk,
            "energy_margin": self.energy_margin,
            "loss_of_control_risk": self.loss_of_control_risk,
            "collision_risk": self.collision_risk
        }


@dataclass
class ShadowResult:
    """Complete shadow execution output"""
    predicted_outcomes: PredictedOutcome
    trajectory_risk: float  # 0.0 to 1.0
    explanation: str
    
    def to_dict(self):
        return {
            "predicted_outcomes": self.predicted_outcomes.to_dict(),
            "trajectory_risk": self.trajectory_risk,
            "explanation": self.explanation
        }


class ShadowExecutor:
    """
    Lightweight kinematic prediction engine
    
    NOT a physics simulator. Just predicts obvious bad outcomes.
    Fast enough for real-time use (<10ms per prediction).
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """Initialize with safety bounds"""
        config = config or {}
        
        # Geofence boundaries (lat/lon/alt)
        self.geofence = {
            "center_lat": config.get("center_lat", 47.0),
            "center_lon": config.get("center_lon", -122.0),
            "radius_m": config.get("radius_m", 500),  # meters
            "min_alt": config.get("min_alt", 10),      # meters AGL
            "max_alt": config.get("max_alt", 120)      # meters AGL (FAA limit)
        }
        
        # Safety limits
        self.limits = {
            "max_horizontal_vel": config.get("max_horizontal_vel", 15.0),  # m/s
            "max_vertical_vel": config.get("max_vertical_vel", 5.0),       # m/s
            "max_accel": config.get("max_accel", 5.0),                     # m/s²
            "critical_battery": config.get("critical_battery", 20.0),       # percent
            "low_battery": config.get("low_battery", 30.0)                  # percent
        }
        
        # Current vehicle state
        self.current_position = {
            "lat": self.geofence["center_lat"],
            "lon": self.geofence["center_lon"],
            "alt": 0.0
        }
        self.current_velocity = {"vx": 0.0, "vy": 0.0, "vz": 0.0}
        self.battery_percent = 100.0
        self.airspeed = 0.0
        
        # Prediction horizon
        self.horizon_seconds = 10.0
        self.dt = 0.5  # Time step for integration
        
        print("✅ Shadow Executor initialized")
    
    def update_state(self, position: Dict = None, velocity: Dict = None, 
                     battery: float = None, airspeed: float = None):
        """Update current vehicle state from telemetry"""
        if position:
            self.current_position.update(position)
        if velocity:
            self.current_velocity.update(velocity)
        if battery is not None:
            self.battery_percent = battery
        if airspeed is not None:
            self.airspeed = airspeed
    
    def haversine_distance(self, lat1: float, lon1: float, 
                          lat2: float, lon2: float) -> float:
        """Calculate distance in meters between two lat/lon points"""
        R = 6371000  # Earth radius in meters
        
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        
        a = math.sin(dphi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c
    
    def predict_position(self, command_obj, t: float) -> Dict[str, float]:
        """
        Predict position at time t seconds in future
        Simple kinematic integration (constant velocity assumption)
        """
        params = command_obj.params
        
        # Extract target from command
        if "lat" in params and "lon" in params:
            # Position command
            target_lat = params["lat"]
            target_lon = params["lon"]
            target_alt = params.get("alt", self.current_position["alt"])
            
            # Linear interpolation toward target
            # (Real version would use velocity/acceleration constraints)
            alpha = min(1.0, t / 5.0)  # Assume 5s to reach target
            
            pred_lat = self.current_position["lat"] + alpha * (target_lat - self.current_position["lat"])
            pred_lon = self.current_position["lon"] + alpha * (target_lon - self.current_position["lon"])
            pred_alt = self.current_position["alt"] + alpha * (target_alt - self.current_position["alt"])
            
        elif "vx" in params and "vy" in params:
            # Velocity command
            vx = params["vx"]
            vy = params["vy"]
            vz = params.get("vz", 0.0)
            
            # Dead reckoning
            # Crude lat/lon conversion (good enough for small distances)
            meters_per_degree_lat = 111000
            meters_per_degree_lon = 111000 * math.cos(math.radians(self.current_position["lat"]))
            
            pred_lat = self.current_position["lat"] + (vy * t) / meters_per_degree_lat
            pred_lon = self.current_position["lon"] + (vx * t) / meters_per_degree_lon
            pred_alt = self.current_position["alt"] + vz * t
            
        else:
            # Unknown command type - assume no movement
            pred_lat = self.current_position["lat"]
            pred_lon = self.current_position["lon"]
            pred_alt = self.current_position["alt"]
        
        return {
            "lat": pred_lat,
            "lon": pred_lon,
            "alt": pred_alt
        }
    
    def check_geofence_violation(self, position: Dict) -> Tuple[bool, Optional[float]]:
        """
        Check if position violates geofence
        Returns (violated, distance_outside)
        """
        # Horizontal check
        dist_from_center = self.haversine_distance(
            self.geofence["center_lat"],
            self.geofence["center_lon"],
            position["lat"],
            position["lon"]
        )
        
        horizontal_violation = dist_from_center > self.geofence["radius_m"]
        
        # Vertical check
        vertical_violation = (
            position["alt"] < self.geofence["min_alt"] or 
            position["alt"] > self.geofence["max_alt"]
        )
        
        violated = horizontal_violation or vertical_violation
        distance_outside = max(0, dist_from_center - self.geofence["radius_m"])
        
        return violated, distance_outside if horizontal_violation else None
    
    def predict_trajectory_risk(self, command_obj) -> ShadowResult:
        """
        Main prediction: What happens if we execute this command?
        
        Returns risk assessment WITHOUT full simulation
        """
        # Predict position at multiple time steps
        trajectory_points = []
        time_to_violation = None
        violation_detected = False
        
        for t in [1.0, 2.5, 5.0, 7.5, 10.0]:
            pos = self.predict_position(command_obj, t)
            trajectory_points.append((t, pos))
            
            # Check geofence at this point
            violated, dist = self.check_geofence_violation(pos)
            if violated and time_to_violation is None:
                time_to_violation = t
                violation_detected = True
        
        # Check altitude risk
        final_pos = trajectory_points[-1][1]
        altitude_risk = (
            final_pos["alt"] < self.geofence["min_alt"] or 
            final_pos["alt"] > self.geofence["max_alt"]
        )
        
        # Check velocity risk
        params = command_obj.params
        vx = params.get("vx", 0.0)
        vy = params.get("vy", 0.0)
        vz = params.get("vz", 0.0)
        
        horizontal_vel = math.sqrt(vx**2 + vy**2)
        velocity_risk = (
            horizontal_vel > self.limits["max_horizontal_vel"] or
            abs(vz) > self.limits["max_vertical_vel"]
        )
        
        # Energy margin assessment
        if self.battery_percent < self.limits["critical_battery"]:
            energy_margin = "CRITICAL"
        elif self.battery_percent < self.limits["low_battery"]:
            energy_margin = "LOW"
        elif self.battery_percent < 50:
            energy_margin = "MEDIUM"
        else:
            energy_margin = "HIGH"
        
        # Loss of control risk (heuristic)
        loss_of_control = (
            velocity_risk or 
            altitude_risk or 
            energy_margin == "CRITICAL"
        )
        
        # Collision risk (simplified - would need obstacle map)
        collision_risk = altitude_risk  # Terrain collision if too low
        
        # Build outcome
        outcome = PredictedOutcome(
            geofence_violation=violation_detected,
            time_to_violation=time_to_violation,
            altitude_risk=altitude_risk,
            velocity_risk=velocity_risk,
            energy_margin=energy_margin,
            loss_of_control_risk=loss_of_control,
            collision_risk=collision_risk
        )
        
        # Calculate overall trajectory risk (0.0 to 1.0)
        risk_score = 0.0
        
        if violation_detected:
            # Urgent if violation is soon
            if time_to_violation and time_to_violation < 5.0:
                risk_score += 0.5
            else:
                risk_score += 0.3
        
        if altitude_risk:
            risk_score += 0.3
        
        if velocity_risk:
            risk_score += 0.2
        
        if energy_margin == "CRITICAL":
            risk_score += 0.4
        elif energy_margin == "LOW":
            risk_score += 0.2
        
        if loss_of_control:
            risk_score += 0.3
        
        trajectory_risk = min(1.0, risk_score)
        
        # Generate explanation
        explanation = self._generate_explanation(outcome, trajectory_risk, time_to_violation)
        
        return ShadowResult(
            predicted_outcomes=outcome,
            trajectory_risk=round(trajectory_risk, 2),
            explanation=explanation
        )
    
    def _generate_explanation(self, outcome: PredictedOutcome, 
                            risk: float, ttv: Optional[float]) -> str:
        """Human-readable explanation of prediction"""
        if risk < 0.3:
            return "Trajectory appears safe within prediction horizon"
        
        issues = []
        
        if outcome.geofence_violation:
            issues.append(f"geofence violation in {ttv:.1f}s")
        
        if outcome.altitude_risk:
            issues.append("altitude outside safe range")
        
        if outcome.velocity_risk:
            issues.append("velocity exceeds safety limits")
        
        if outcome.energy_margin in ["LOW", "CRITICAL"]:
            issues.append(f"{outcome.energy_margin.lower()} battery")
        
        if outcome.loss_of_control_risk:
            issues.append("loss of control risk")
        
        return f"Risk {risk:.2f}: " + ", ".join(issues)


def main():
    """Test Shadow Executor"""
    executor = ShadowExecutor(config={
        "center_lat": 47.0,
        "center_lon": -122.0,
        "radius_m": 300
    })
    
    # Set current state
    executor.update_state(
        position={"lat": 47.0, "lon": -122.0, "alt": 50.0},
        velocity={"vx": 5.0, "vy": 0.0, "vz": 0.0},
        battery=75.0
    )
    
    print("\n=== Test 1: Safe Navigation ===")
    class SafeCommand:
        command_type = "NAVIGATION"
        params = {"lat": 47.001, "lon": -122.001, "alt": 60.0}
    
    result = executor.predict_trajectory_risk(SafeCommand())
    print(json.dumps(result.to_dict(), indent=2))
    
    print("\n=== Test 2: Geofence Violation ===")
    class DangerCommand:
        command_type = "NAVIGATION"
        params = {"lat": 47.01, "lon": -122.01, "alt": 50.0}  # Way outside geofence
    
    result = executor.predict_trajectory_risk(DangerCommand())
    print(json.dumps(result.to_dict(), indent=2))
    print(f"⚠️ Trajectory Risk: {result.trajectory_risk}")


if __name__ == "__main__":
    main()
