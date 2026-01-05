"""
Layer 4: Mode-Aware Behavioral IDS (NOVEL COMPONENT 🧠)

Purpose: Detect behavioral anomalies RELATIVE to current flight mode
Same command ≠ same meaning across modes

Models are mode-conditioned:
- AUTO mode → mission consistency
- GUIDED mode → autonomy consistency  
- MANUAL mode → human-control behavior
"""

import math
from typing import Dict, List, Optional
from collections import deque
from dataclasses import dataclass
import json


@dataclass
class BehaviorScore:
    """Behavior analysis result"""
    behavior_score: float  # 0.0 = normal, 1.0 = highly anomalous
    anomaly_level: str     # "NONE", "LOW", "MEDIUM", "HIGH"
    anomaly_features: List[str]
    explanation: str
    
    def to_dict(self):
        return {
            "behavior_score": self.behavior_score,
            "anomaly_level": self.anomaly_level,
            "anomaly_features": self.anomaly_features,
            "explanation": self.explanation
        }


class ModeAwareIDS:
    """
    Behavioral anomaly detection conditioned on flight mode
    
    Key Insight: A rapid position change is normal in MANUAL, 
    but suspicious in AUTO mission mode.
    """
    
    def __init__(self):
        # Command history buffer (last 20 commands)
        self.command_buffer = deque(maxlen=20)
        
        # Per-mode statistics
        self.mode_stats = {
            "AUTO": {"cmd_freq": 0.0, "avg_velocity": 0.0},
            "GUIDED": {"cmd_freq": 0.0, "avg_velocity": 0.0},
            "MANUAL": {"cmd_freq": 0.0, "avg_velocity": 0.0}
        }
        
        # Current mode
        self.current_mode = "UNKNOWN"
        
        # Feature extraction
        self.last_command_time = None
        self.last_position = None
        
        print("✅ Mode-Aware IDS initialized")
    
    def update_mode(self, mode: str):
        """Update current flight mode"""
        self.current_mode = mode.upper()
    
    def extract_features(self, command_obj) -> Dict:
        """
        Extract behavioral features from command
        Mode-specific feature engineering
        """
        features = {}
        
        # Temporal features
        if self.last_command_time:
            dt = command_obj.timestamp - self.last_command_time
            features["time_since_last_cmd"] = dt
            features["command_frequency"] = 1.0 / dt if dt > 0 else 0.0
        else:
            features["time_since_last_cmd"] = 0.0
            features["command_frequency"] = 0.0
        
        # Spatial features
        params = command_obj.params
        
        if "lat" in params and "lon" in params and self.last_position:
            # Position delta
            d_lat = abs(params["lat"] - self.last_position["lat"])
            d_lon = abs(params["lon"] - self.last_position["lon"])
            d_alt = abs(params.get("alt", 0) - self.last_position.get("alt", 0))
            
            distance = math.sqrt(d_lat**2 + d_lon**2 + d_alt**2)
            
            features["position_jump"] = distance
            features["altitude_change"] = d_alt
            
            # Velocity estimate
            dt = features["time_since_last_cmd"]
            if dt > 0:
                features["implied_velocity"] = distance / dt
            else:
                features["implied_velocity"] = 0.0
        else:
            features["position_jump"] = 0.0
            features["altitude_change"] = 0.0
            features["implied_velocity"] = 0.0
        
        # Velocity features (if explicit)
        if "vx" in params and "vy" in params:
            vx = params["vx"]
            vy = params["vy"]
            vz = params.get("vz", 0.0)
            
            features["horizontal_velocity"] = math.sqrt(vx**2 + vy**2)
            features["vertical_velocity"] = abs(vz)
            features["velocity_magnitude"] = math.sqrt(vx**2 + vy**2 + vz**2)
        else:
            features["horizontal_velocity"] = 0.0
            features["vertical_velocity"] = 0.0
            features["velocity_magnitude"] = 0.0
        
        # Command type features
        features["command_type"] = command_obj.command_type
        features["is_emergency"] = 1 if command_obj.command_type == "EMERGENCY" else 0
        features["is_manual"] = 1 if command_obj.command_type == "MANUAL" else 0
        
        # Mode transition detection
        if len(self.command_buffer) > 0:
            last_cmd = self.command_buffer[-1]
            features["mode_change"] = 1 if last_cmd.get("mode") != self.current_mode else 0
        else:
            features["mode_change"] = 0
        
        return features
    
    def detect_anomalies(self, features: Dict, mode: str) -> List[str]:
        """
        Detect anomalous patterns based on mode
        Returns list of anomaly types detected
        """
        anomalies = []
        
        # Mode-specific thresholds
        thresholds = self._get_mode_thresholds(mode)
        
        # 1. Command frequency anomaly
        if features["command_frequency"] > thresholds["max_cmd_freq"]:
            anomalies.append("high_command_frequency")
        
        # 2. Velocity anomaly
        if features["implied_velocity"] > thresholds["max_velocity"]:
            anomalies.append("excessive_velocity")
        
        if features["horizontal_velocity"] > thresholds["max_horizontal_vel"]:
            anomalies.append("excessive_horizontal_velocity")
        
        # 3. Position jump anomaly (suspicious in AUTO, normal in MANUAL)
        if features["position_jump"] > thresholds["max_position_jump"]:
            anomalies.append("large_position_jump")
        
        # 4. Altitude anomaly
        if features["altitude_change"] > thresholds["max_altitude_change"]:
            anomalies.append("rapid_altitude_change")
        
        # 5. Mode transition spam
        if features["mode_change"] == 1:
            recent_mode_changes = sum(
                1 for cmd in list(self.command_buffer)[-5:]
                if cmd.get("mode_change", 0) == 1
            )
            if recent_mode_changes >= 3:
                anomalies.append("excessive_mode_switching")
        
        # 6. Temporal irregularity
        if len(self.command_buffer) >= 5:
            recent_times = [cmd["time_since_last"] for cmd in list(self.command_buffer)[-5:]]
            if len(recent_times) > 1:
                time_variance = self._calculate_variance(recent_times)
                if time_variance > thresholds["max_time_variance"]:
                    anomalies.append("irregular_timing")
        
        # 7. Emergency command in wrong mode
        if features["is_emergency"] == 1 and mode == "MANUAL":
            # Emergency commands shouldn't appear in manual mode normally
            anomalies.append("unexpected_emergency_command")
        
        return anomalies
    
    def _get_mode_thresholds(self, mode: str) -> Dict:
        """
        Mode-specific safety thresholds
        
        KEY DIFFERENCE: AUTO mode is stricter than MANUAL
        """
        if mode == "AUTO":
            return {
                "max_cmd_freq": 2.0,          # Commands/second
                "max_velocity": 10.0,          # m/s
                "max_horizontal_vel": 8.0,     # m/s
                "max_position_jump": 0.001,    # Very small in AUTO
                "max_altitude_change": 5.0,    # meters
                "max_time_variance": 0.5       # seconds²
            }
        elif mode == "GUIDED":
            return {
                "max_cmd_freq": 5.0,
                "max_velocity": 15.0,
                "max_horizontal_vel": 12.0,
                "max_position_jump": 0.01,
                "max_altitude_change": 10.0,
                "max_time_variance": 1.0
            }
        elif mode == "MANUAL":
            return {
                "max_cmd_freq": 10.0,         # Human can command rapidly
                "max_velocity": 20.0,
                "max_horizontal_vel": 20.0,
                "max_position_jump": 0.1,      # Large jumps OK in manual
                "max_altitude_change": 20.0,
                "max_time_variance": 2.0
            }
        else:
            # Conservative defaults for unknown mode
            return {
                "max_cmd_freq": 3.0,
                "max_velocity": 12.0,
                "max_horizontal_vel": 10.0,
                "max_position_jump": 0.005,
                "max_altitude_change": 8.0,
                "max_time_variance": 1.0
            }
    
    def _calculate_variance(self, values: List[float]) -> float:
        """Simple variance calculation"""
        if not values:
            return 0.0
        mean = sum(values) / len(values)
        return sum((x - mean)**2 for x in values) / len(values)
    
    def calculate_behavior_score(self, anomalies: List[str], features: Dict) -> float:
        """
        Convert anomalies to 0-1 score
        0.0 = normal, 1.0 = highly anomalous
        """
        if not anomalies:
            return 0.0
        
        # Weight anomalies by severity
        severity_weights = {
            "high_command_frequency": 0.3,
            "excessive_velocity": 0.4,
            "excessive_horizontal_velocity": 0.35,
            "large_position_jump": 0.5,  # Very suspicious
            "rapid_altitude_change": 0.4,
            "excessive_mode_switching": 0.6,  # Very suspicious
            "irregular_timing": 0.2,
            "unexpected_emergency_command": 0.7
        }
        
        total_score = sum(severity_weights.get(a, 0.3) for a in anomalies)
        
        # Normalize to [0, 1]
        behavior_score = min(1.0, total_score)
        
        return round(behavior_score, 2)
    
    def classify_anomaly_level(self, score: float) -> str:
        """Convert score to severity level"""
        if score < 0.3:
            return "NONE"
        elif score < 0.5:
            return "LOW"
        elif score < 0.7:
            return "MEDIUM"
        else:
            return "HIGH"
    
    def analyze(self, command_obj) -> BehaviorScore:
        """
        Main entry point: Analyze command behavior
        """
        # Extract features
        features = self.extract_features(command_obj)
        
        # Detect anomalies (mode-aware)
        anomalies = self.detect_anomalies(features, self.current_mode)
        
        # Calculate score
        score = self.calculate_behavior_score(anomalies, features)
        level = self.classify_anomaly_level(score)
        
        # Generate explanation
        if anomalies:
            explanation = f"Detected {len(anomalies)} anomalies: {', '.join(anomalies)}"
        else:
            explanation = f"Behavior consistent with {self.current_mode} mode expectations"
        
        # Update state
        self.last_command_time = command_obj.timestamp
        if "lat" in command_obj.params:
            self.last_position = {
                "lat": command_obj.params.get("lat", 0),
                "lon": command_obj.params.get("lon", 0),
                "alt": command_obj.params.get("alt", 0)
            }
        
        # Add to buffer
        self.command_buffer.append({
            "command_type": command_obj.command_type,
            "mode": self.current_mode,
            "time_since_last": features["time_since_last_cmd"],
            "mode_change": features["mode_change"],
            "timestamp": command_obj.timestamp
        })
        
        return BehaviorScore(
            behavior_score=score,
            anomaly_level=level,
            anomaly_features=anomalies,
            explanation=explanation
        )


def main():
    """Test Mode-Aware IDS"""
    ids = ModeAwareIDS()
    
    print("\n=== Scenario 1: AUTO Mode - Slow Navigation ===")
    ids.update_mode("AUTO")
    
    class NormalNav:
        command_type = "NAVIGATION"
        params = {"lat": 47.0001, "lon": -122.0001, "alt": 50.0}
        timestamp = 1000.0
    
    result = ids.analyze(NormalNav())
    print(json.dumps(result.to_dict(), indent=2))
    
    print("\n=== Scenario 2: AUTO Mode - Sudden Large Jump (ANOMALY) ===")
    class AnomalousJump:
        command_type = "NAVIGATION"
        params = {"lat": 47.01, "lon": -122.01, "alt": 50.0}  # Huge jump
        timestamp = 1001.0
    
    result = ids.analyze(AnomalousJump())
    print(json.dumps(result.to_dict(), indent=2))
    print(f"⚠️ Anomaly Level: {result.anomaly_level}")
    
    print("\n=== Scenario 3: MANUAL Mode - Same Jump (OK) ===")
    ids.update_mode("MANUAL")
    result = ids.analyze(AnomalousJump)
    print(json.dumps(result.to_dict(), indent=2))
    print(f"✅ Anomaly Level: {result.anomaly_level}")


if __name__ == "__main__":
    main()
