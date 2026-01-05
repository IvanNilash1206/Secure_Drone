"""
Feature Extractor V2: Context-Aware Intent Inference

Extracts three categories of features for ML model:
1. Command features: msg_id, command_type, parameter magnitudes
2. Temporal features: windowed patterns, frequencies, transitions
3. Context features: flight_mode, mission_phase, battery, altitude, armed_state

Design principles:
- Semantic features only (no raw bytes)
- Normalized, bounded values
- Deterministic extraction
- Fast computation (<1ms per command)
"""

import numpy as np
import time
from collections import deque
from typing import Dict, List, Optional, Any
from dataclasses import dataclass


# MAVLink message type mappings (subset of common commands)
MAVLINK_MSG_TYPES = {
    'COMMAND_LONG': 76,
    'COMMAND_INT': 75,
    'SET_POSITION_TARGET_LOCAL_NED': 84,
    'SET_POSITION_TARGET_GLOBAL_INT': 86,
    'SET_MODE': 11,
    'MISSION_ITEM': 39,
    'MISSION_COUNT': 44,
    'PARAM_SET': 23,
    'ARM_DISARM': 400,  # MAV_CMD
}

# Flight modes (simplified)
FLIGHT_MODES = {
    'MANUAL': 0,
    'STABILIZE': 1,
    'GUIDED': 2,
    'AUTO': 3,
    'RTL': 4,
    'LAND': 5,
    'LOITER': 6,
}

# Mission phases (when in AUTO mode)
MISSION_PHASES = {
    'NONE': 0,
    'TAKEOFF': 1,
    'CRUISE': 2,
    'WAYPOINT': 3,
    'LANDING_APPROACH': 4,
    'LANDING': 5,
}


@dataclass
class CommandContext:
    """Complete context at time of command"""
    # Command metadata
    msg_id: int
    command_type: str
    target_system: int
    target_component: int
    
    # Command parameters (normalized)
    param1: float = 0.0
    param2: float = 0.0
    param3: float = 0.0
    param4: float = 0.0
    param5: float = 0.0  # lat or x
    param6: float = 0.0  # lon or y
    param7: float = 0.0  # alt or z
    
    # Vehicle state
    flight_mode: str = 'MANUAL'
    mission_phase: str = 'NONE'
    armed: bool = False
    battery_level: float = 1.0  # [0, 1]
    altitude: float = 0.0  # meters
    velocity: float = 0.0  # m/s
    
    # Timing
    timestamp: float = 0.0


class FeatureExtractorV2:
    """
    Context-aware feature extraction for intent inference
    
    Maintains temporal window of N previous commands
    Computes temporal patterns and transitions
    Combines command + context features
    """
    
    def __init__(self, window_size: int = 7):
        """
        Args:
            window_size: Number of previous commands to maintain (5-10 recommended)
        """
        self.window_size = window_size
        self.command_window = deque(maxlen=window_size)
        
        # Feature schema (total 37 features)
        self.feature_names = [
            # Command features (10)
            'msg_id_encoded',
            'command_type_encoded',
            'param1_norm',
            'param2_norm',
            'param3_norm',
            'param4_norm',
            'param_magnitude',
            'target_sys',
            'target_comp',
            'time_since_last_cmd',
            
            # Temporal features (15)
            'cmd_frequency_1s',
            'cmd_frequency_5s',
            'intent_transitions',
            'param_variance',
            'param_mean_change',
            'repetition_count',
            'mode_changes_window',
            'time_std_dev',
            'cmd_type_diversity',
            'param1_trend',
            'param2_trend',
            'velocity_trend',
            'altitude_change_rate',
            'sequential_same_cmd',
            'burst_detected',
            
            # Context features (12)
            'flight_mode_encoded',
            'mission_phase_encoded',
            'armed_state',
            'battery_level',
            'altitude_norm',
            'velocity_norm',
            'is_high_altitude',
            'is_low_battery',
            'is_high_velocity',
            'mode_context_match',
            'altitude_category',
            'risk_context_flag',
        ]
        
        self.n_features = len(self.feature_names)
        
        print(f"✅ FeatureExtractorV2 initialized: {self.n_features} features, window={window_size}")
    
    def extract(self, command_ctx: CommandContext) -> Optional[np.ndarray]:
        """
        Extract feature vector from command + context
        
        Args:
            command_ctx: Complete command context
            
        Returns:
            Feature vector (37-dim) or None if insufficient history
        """
        # Add to history
        self.command_window.append(command_ctx)
        
        # Need at least 2 commands for temporal features
        if len(self.command_window) < 2:
            return None
        
        # Extract all feature categories
        cmd_features = self._extract_command_features(command_ctx)
        temporal_features = self._extract_temporal_features()
        context_features = self._extract_context_features(command_ctx)
        
        # Concatenate
        feature_vector = np.concatenate([
            cmd_features,
            temporal_features,
            context_features
        ])
        
        assert len(feature_vector) == self.n_features, \
            f"Feature mismatch: expected {self.n_features}, got {len(feature_vector)}"
        
        return feature_vector
    
    def _extract_command_features(self, ctx: CommandContext) -> np.ndarray:
        """Extract features from current command (10 features)"""
        
        # Encode message ID (normalize to [0, 1])
        msg_id_norm = ctx.msg_id / 300.0  # typical MAVLink range
        
        # Encode command type (hash to [0, 1])
        cmd_type_hash = hash(ctx.command_type) % 1000 / 1000.0
        
        # Normalize parameters (clip to reasonable ranges)
        param1_norm = np.clip(ctx.param1 / 100.0, -1, 1)
        param2_norm = np.clip(ctx.param2 / 100.0, -1, 1)
        param3_norm = np.clip(ctx.param3 / 100.0, -1, 1)
        param4_norm = np.clip(ctx.param4 / 100.0, -1, 1)
        
        # Magnitude of parameter vector
        param_mag = np.sqrt(
            ctx.param1**2 + ctx.param2**2 + ctx.param3**2 + ctx.param4**2
        )
        param_mag_norm = np.clip(param_mag / 200.0, 0, 1)
        
        # Target IDs (normalize)
        target_sys_norm = ctx.target_system / 255.0
        target_comp_norm = ctx.target_component / 255.0
        
        # Time since last command
        if len(self.command_window) >= 2:
            time_delta = ctx.timestamp - self.command_window[-2].timestamp
            time_delta_norm = np.clip(time_delta / 5.0, 0, 1)  # normalize by 5 seconds
        else:
            time_delta_norm = 0.0
        
        return np.array([
            msg_id_norm,
            cmd_type_hash,
            param1_norm,
            param2_norm,
            param3_norm,
            param4_norm,
            param_mag_norm,
            target_sys_norm,
            target_comp_norm,
            time_delta_norm,
        ], dtype=np.float32)
    
    def _extract_temporal_features(self) -> np.ndarray:
        """Extract windowed temporal patterns (15 features)"""
        
        window = list(self.command_window)
        n = len(window)
        
        if n < 2:
            return np.zeros(15, dtype=np.float32)
        
        # Command timestamps
        timestamps = [c.timestamp for c in window]
        time_diffs = np.diff(timestamps)
        
        # 1. Command frequency (last 1 second)
        recent_window = 1.0  # seconds
        recent_count = sum(1 for t in timestamps if timestamps[-1] - t <= recent_window)
        cmd_freq_1s = np.clip(recent_count / 10.0, 0, 1)  # normalize by 10 cmd/s
        
        # 2. Command frequency (last 5 seconds)
        recent_window_5s = 5.0
        recent_count_5s = sum(1 for t in timestamps if timestamps[-1] - t <= recent_window_5s)
        cmd_freq_5s = np.clip(recent_count_5s / 50.0, 0, 1)  # normalize by 50 cmd/5s
        
        # 3. Intent transitions (mode changes)
        mode_changes = sum(
            1 for i in range(1, n) 
            if window[i].flight_mode != window[i-1].flight_mode
        )
        intent_transitions = np.clip(mode_changes / 5.0, 0, 1)
        
        # 4. Parameter variance
        param1_values = [c.param1 for c in window]
        param_var = np.var(param1_values) if len(param1_values) > 1 else 0.0
        param_var_norm = np.clip(param_var / 100.0, 0, 1)
        
        # 5. Mean parameter change
        param_changes = np.abs(np.diff(param1_values)) if len(param1_values) > 1 else [0]
        param_mean_change = np.clip(np.mean(param_changes) / 50.0, 0, 1)
        
        # 6. Repetition count (same command type)
        last_cmd_type = window[-1].command_type
        repetition = sum(1 for c in window if c.command_type == last_cmd_type)
        repetition_norm = np.clip(repetition / n, 0, 1)
        
        # 7. Mode changes in window
        mode_changes_norm = np.clip(mode_changes / n, 0, 1)
        
        # 8. Time standard deviation (regularity)
        time_std = np.std(time_diffs) if len(time_diffs) > 1 else 0.0
        time_std_norm = np.clip(time_std / 2.0, 0, 1)
        
        # 9. Command type diversity
        unique_types = len(set(c.command_type for c in window))
        cmd_diversity = unique_types / n
        
        # 10-11. Parameter trends (increasing/decreasing)
        param1_trend = self._compute_trend([c.param1 for c in window])
        param2_trend = self._compute_trend([c.param2 for c in window])
        
        # 12. Velocity trend
        velocity_trend = self._compute_trend([c.velocity for c in window])
        
        # 13. Altitude change rate
        altitudes = [c.altitude for c in window]
        alt_changes = np.diff(altitudes)
        alt_change_rate = np.clip(np.mean(np.abs(alt_changes)) / 10.0, 0, 1) if len(alt_changes) > 0 else 0.0
        
        # 14. Sequential same command (immediate repetition)
        sequential_same = 1.0 if n >= 2 and window[-1].command_type == window[-2].command_type else 0.0
        
        # 15. Burst detection (>5 commands in <1 second)
        burst_detected = 1.0 if cmd_freq_1s > 0.5 else 0.0
        
        return np.array([
            cmd_freq_1s,
            cmd_freq_5s,
            intent_transitions,
            param_var_norm,
            param_mean_change,
            repetition_norm,
            mode_changes_norm,
            time_std_norm,
            cmd_diversity,
            param1_trend,
            param2_trend,
            velocity_trend,
            alt_change_rate,
            sequential_same,
            burst_detected,
        ], dtype=np.float32)
    
    def _extract_context_features(self, ctx: CommandContext) -> np.ndarray:
        """Extract vehicle state context (12 features)"""
        
        # 1. Flight mode encoded
        mode_encoded = FLIGHT_MODES.get(ctx.flight_mode, 0) / len(FLIGHT_MODES)
        
        # 2. Mission phase encoded
        phase_encoded = MISSION_PHASES.get(ctx.mission_phase, 0) / len(MISSION_PHASES)
        
        # 3. Armed state
        armed_state = 1.0 if ctx.armed else 0.0
        
        # 4. Battery level (already [0, 1])
        battery = np.clip(ctx.battery_level, 0, 1)
        
        # 5. Altitude normalized
        altitude_norm = np.clip(ctx.altitude / 100.0, 0, 1)  # normalize by 100m
        
        # 6. Velocity normalized
        velocity_norm = np.clip(ctx.velocity / 20.0, 0, 1)  # normalize by 20 m/s
        
        # 7. High altitude flag
        is_high_altitude = 1.0 if ctx.altitude > 50.0 else 0.0
        
        # 8. Low battery flag
        is_low_battery = 1.0 if ctx.battery_level < 0.2 else 0.0
        
        # 9. High velocity flag
        is_high_velocity = 1.0 if ctx.velocity > 15.0 else 0.0
        
        # 10. Mode-context match (is command appropriate for mode?)
        mode_match = self._check_mode_context_match(ctx)
        
        # 11. Altitude category (0=ground, 0.5=low, 1=high)
        if ctx.altitude < 5.0:
            alt_category = 0.0
        elif ctx.altitude < 30.0:
            alt_category = 0.5
        else:
            alt_category = 1.0
        
        # 12. Risk context flag (combination of dangerous states)
        risk_flag = 1.0 if (is_low_battery or is_high_altitude or is_high_velocity) else 0.0
        
        return np.array([
            mode_encoded,
            phase_encoded,
            armed_state,
            battery,
            altitude_norm,
            velocity_norm,
            is_high_altitude,
            is_low_battery,
            is_high_velocity,
            mode_match,
            alt_category,
            risk_flag,
        ], dtype=np.float32)
    
    def _compute_trend(self, values: List[float]) -> float:
        """
        Compute trend direction: -1 (decreasing), 0 (stable), +1 (increasing)
        Returns normalized [-1, 1]
        """
        if len(values) < 2:
            return 0.0
        
        # Simple linear regression slope
        x = np.arange(len(values))
        y = np.array(values)
        
        # Avoid division by zero
        if np.std(x) == 0:
            return 0.0
        
        slope = np.corrcoef(x, y)[0, 1] if len(values) > 2 else 0.0
        
        # Normalize to [-1, 1]
        return np.clip(slope, -1, 1)
    
    def _check_mode_context_match(self, ctx: CommandContext) -> float:
        """
        Check if command type matches current flight mode
        Returns 1.0 if match, 0.0 if mismatch
        """
        mode = ctx.flight_mode
        cmd = ctx.command_type
        
        # Simple heuristics
        if mode == 'MANUAL' and 'POSITION' in cmd:
            return 0.0  # Position commands in manual mode = suspicious
        
        if mode == 'AUTO' and 'MANUAL_CONTROL' in cmd:
            return 0.0  # Manual override in auto = intent mismatch
        
        if mode == 'LAND' and 'TAKEOFF' in cmd:
            return 0.0  # Takeoff during landing = mismatch
        
        # Default: assume match
        return 1.0
    
    def reset(self):
        """Clear command history"""
        self.command_window.clear()
    
    def get_feature_names(self) -> List[str]:
        """Return feature names for model training"""
        return self.feature_names


# Helper function to create CommandContext from MAVLink packet
def mavlink_to_context(msg: Dict[str, Any], vehicle_state: Dict[str, Any]) -> CommandContext:
    """
    Convert MAVLink message + vehicle state to CommandContext
    
    Args:
        msg: MAVLink message dict with keys: msg_id, command_type, params, target_system, target_component
        vehicle_state: Current vehicle state dict with keys: flight_mode, armed, battery, altitude, velocity, etc.
        
    Returns:
        CommandContext object
    """
    return CommandContext(
        msg_id=msg.get('msg_id', 0),
        command_type=msg.get('command_type', 'UNKNOWN'),
        target_system=msg.get('target_system', 1),
        target_component=msg.get('target_component', 1),
        param1=msg.get('param1', 0.0),
        param2=msg.get('param2', 0.0),
        param3=msg.get('param3', 0.0),
        param4=msg.get('param4', 0.0),
        param5=msg.get('param5', 0.0),
        param6=msg.get('param6', 0.0),
        param7=msg.get('param7', 0.0),
        flight_mode=vehicle_state.get('flight_mode', 'MANUAL'),
        mission_phase=vehicle_state.get('mission_phase', 'NONE'),
        armed=vehicle_state.get('armed', False),
        battery_level=vehicle_state.get('battery_level', 1.0),
        altitude=vehicle_state.get('altitude', 0.0),
        velocity=vehicle_state.get('velocity', 0.0),
        timestamp=time.time()
    )


if __name__ == "__main__":
    # Test feature extraction
    extractor = FeatureExtractorV2(window_size=7)
    
    # Simulate command sequence
    for i in range(10):
        ctx = CommandContext(
            msg_id=76,
            command_type='SET_POSITION_TARGET',
            target_system=1,
            target_component=1,
            param1=float(i),
            param2=float(i * 2),
            param3=0.0,
            flight_mode='GUIDED',
            armed=True,
            battery_level=0.8,
            altitude=25.0 + i,
            velocity=5.0,
            timestamp=time.time() + i * 0.5
        )
        
        features = extractor.extract(ctx)
        
        if features is not None:
            print(f"Command {i}: {features.shape} features")
            print(f"  First 5: {features[:5]}")
            print(f"  Context: mode={ctx.flight_mode}, armed={ctx.armed}, alt={ctx.altitude:.1f}m")
    
    print(f"\n✅ Feature extraction test complete")
    print(f"Feature names ({len(extractor.feature_names)}):")
    for i, name in enumerate(extractor.feature_names):
        print(f"  {i+1}. {name}")
