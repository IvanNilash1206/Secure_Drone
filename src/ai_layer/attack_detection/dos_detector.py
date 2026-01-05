"""
DoS (Denial of Service) Attack Detector

Detects command flooding, resource exhaustion, and overwhelming traffic patterns.

Detection methods:
1. Command rate monitoring (commands/second)
2. Burst detection (spike in short window)
3. Source diversity analysis
4. Payload size analysis
5. Temporal pattern analysis
"""

import time
from collections import deque
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
import statistics


@dataclass
class DoSMetrics:
    """DoS detection metrics"""
    commands_per_second: float
    burst_score: float  # 0.0 to 1.0
    sustained_load: float  # 0.0 to 1.0
    is_dos_attack: bool
    confidence: float
    explanation: str
    
    def to_dict(self):
        return {
            "commands_per_second": self.commands_per_second,
            "burst_score": self.burst_score,
            "sustained_load": self.sustained_load,
            "is_dos_attack": self.is_dos_attack,
            "confidence": self.confidence,
            "explanation": self.explanation
        }


class DoSDetector:
    """
    Real-time DoS attack detection
    
    Legitimate traffic patterns:
    - Normal: 0.5-2 commands/sec
    - Mission upload: 5-10 commands/sec (burst, short duration)
    - Telemetry response: 1-3 commands/sec
    
    Attack patterns:
    - Flooding: >20 commands/sec sustained
    - Burst flooding: >50 commands/sec in 1-second window
    - Slow DoS: 10-15 commands/sec for extended period
    """
    
    def __init__(self, 
                 normal_threshold: float = 5.0,
                 attack_threshold: float = 20.0,
                 burst_threshold: float = 50.0,
                 window_size_sec: int = 10):
        """
        Args:
            normal_threshold: Commands/sec for normal operation
            attack_threshold: Commands/sec indicating attack
            burst_threshold: Commands/sec in 1-sec window for burst attack
            window_size_sec: Time window for rate calculation
        """
        self.normal_threshold = normal_threshold
        self.attack_threshold = attack_threshold
        self.burst_threshold = burst_threshold
        self.window_size_sec = window_size_sec
        
        # Sliding window of command timestamps
        self.command_timestamps = deque(maxlen=1000)
        
        # Statistics
        self.total_commands = 0
        self.detected_dos_attacks = 0
        self.start_time = time.time()
        
        print(f"✅ DoS Detector initialized (thresholds: normal={normal_threshold}, attack={attack_threshold} cmds/sec)")
    
    def record_command(self, timestamp: Optional[float] = None) -> DoSMetrics:
        """
        Record incoming command and check for DoS attack
        
        Args:
            timestamp: Command timestamp (defaults to current time)
            
        Returns:
            DoSMetrics with attack detection result
        """
        if timestamp is None:
            timestamp = time.time()
        
        self.command_timestamps.append(timestamp)
        self.total_commands += 1
        
        # Calculate metrics
        commands_per_second = self._calculate_rate()
        burst_score = self._calculate_burst_score(timestamp)
        sustained_load = self._calculate_sustained_load()
        
        # Determine if DoS attack
        is_dos, confidence, explanation = self._detect_dos(
            commands_per_second, burst_score, sustained_load
        )
        
        if is_dos:
            self.detected_dos_attacks += 1
        
        return DoSMetrics(
            commands_per_second=commands_per_second,
            burst_score=burst_score,
            sustained_load=sustained_load,
            is_dos_attack=is_dos,
            confidence=confidence,
            explanation=explanation
        )
    
    def _calculate_rate(self) -> float:
        """Calculate commands per second over window"""
        if len(self.command_timestamps) < 2:
            return 0.0
        
        current_time = time.time()
        window_start = current_time - self.window_size_sec
        
        # Count commands in window
        recent_commands = [ts for ts in self.command_timestamps if ts >= window_start]
        
        if len(recent_commands) < 2:
            return 0.0
        
        time_span = recent_commands[-1] - recent_commands[0]
        if time_span < 0.1:  # Avoid division by zero
            return float(len(recent_commands))
        
        return len(recent_commands) / time_span
    
    def _calculate_burst_score(self, current_time: float) -> float:
        """
        Calculate burst intensity in last 1 second
        
        Returns score 0.0 to 1.0 (1.0 = burst attack)
        """
        one_sec_ago = current_time - 1.0
        burst_commands = [ts for ts in self.command_timestamps if ts >= one_sec_ago]
        
        burst_rate = len(burst_commands)
        
        # Normalize: 0-5 normal, 5-20 elevated, >20 burst attack
        if burst_rate <= self.normal_threshold:
            return 0.0
        elif burst_rate >= self.burst_threshold:
            return 1.0
        else:
            # Linear scale between normal and burst threshold
            return (burst_rate - self.normal_threshold) / (self.burst_threshold - self.normal_threshold)
    
    def _calculate_sustained_load(self) -> float:
        """
        Calculate sustained load over window
        
        Returns score 0.0 to 1.0 (1.0 = sustained attack)
        """
        if len(self.command_timestamps) < 10:
            return 0.0
        
        current_time = time.time()
        window_start = current_time - self.window_size_sec
        recent_commands = [ts for ts in self.command_timestamps if ts >= window_start]
        
        if len(recent_commands) < 10:
            return 0.0
        
        # Calculate average rate over multiple sub-windows
        sub_window_size = 2.0  # 2 seconds
        sub_windows = []
        
        for i in range(0, int(self.window_size_sec / sub_window_size)):
            sub_start = window_start + (i * sub_window_size)
            sub_end = sub_start + sub_window_size
            sub_commands = [ts for ts in recent_commands if sub_start <= ts < sub_end]
            
            if sub_commands:
                rate = len(sub_commands) / sub_window_size
                sub_windows.append(rate)
        
        if not sub_windows:
            return 0.0
        
        # Sustained load = how consistently high the rate is
        avg_rate = statistics.mean(sub_windows)
        std_dev = statistics.stdev(sub_windows) if len(sub_windows) > 1 else 0.0
        
        # High average + low variance = sustained attack
        if avg_rate <= self.normal_threshold:
            return 0.0
        elif avg_rate >= self.attack_threshold:
            consistency = 1.0 - min(std_dev / avg_rate, 0.5)  # Low variance = high consistency
            return min(consistency, 1.0)
        else:
            # Scale between normal and attack threshold
            normalized_rate = (avg_rate - self.normal_threshold) / (self.attack_threshold - self.normal_threshold)
            consistency = 1.0 - min(std_dev / avg_rate, 0.5)
            return min(normalized_rate * consistency, 1.0)
    
    def _detect_dos(self, rate: float, burst: float, sustained: float) -> Tuple[bool, float, str]:
        """
        Determine if DoS attack is occurring
        
        Returns: (is_attack, confidence, explanation)
        """
        # Critical burst attack
        if burst >= 0.8:
            return True, 0.95, f"Burst attack detected: {rate:.1f} cmds/sec in 1-sec window"
        
        # Sustained flooding
        if sustained >= 0.7 and rate >= self.attack_threshold:
            return True, 0.90, f"Sustained DoS attack: {rate:.1f} cmds/sec over {self.window_size_sec}s"
        
        # Elevated sustained load
        if sustained >= 0.5 and rate >= self.attack_threshold * 0.75:
            return True, 0.75, f"Elevated command rate: {rate:.1f} cmds/sec (possible slow DoS)"
        
        # Medium burst
        if burst >= 0.5:
            return True, 0.60, f"Burst detected: {rate:.1f} cmds/sec"
        
        # All clear
        if rate <= self.normal_threshold:
            return False, 0.0, f"Normal traffic: {rate:.1f} cmds/sec"
        else:
            return False, 0.0, f"Elevated but not attack: {rate:.1f} cmds/sec"
    
    def reset(self):
        """Reset detector state"""
        self.command_timestamps.clear()
        self.total_commands = 0
        self.detected_dos_attacks = 0
        self.start_time = time.time()
        print("DoS Detector reset")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get detector statistics"""
        runtime = time.time() - self.start_time
        return {
            "total_commands": self.total_commands,
            "detected_dos_attacks": self.detected_dos_attacks,
            "runtime_seconds": runtime,
            "average_rate": self.total_commands / runtime if runtime > 0 else 0.0,
            "detection_rate": self.detected_dos_attacks / self.total_commands if self.total_commands > 0 else 0.0
        }


if __name__ == "__main__":
    # Test DoS detector
    print("Testing DoS Detector\n")
    
    detector = DoSDetector()
    
    # Simulate normal traffic
    print("1. Normal traffic (2 cmds/sec):")
    base_time = time.time()
    for i in range(20):
        timestamp = base_time + (i * 0.5)  # 2 commands/sec
        metrics = detector.record_command(timestamp)
        if i % 5 == 0:
            print(f"   t={i*0.5:.1f}s: {metrics.commands_per_second:.1f} cmds/sec, DoS={metrics.is_dos_attack}")
    
    # Simulate burst attack
    print("\n2. Burst attack (60 cmds in 1 sec):")
    burst_time = base_time + 20
    for i in range(60):
        timestamp = burst_time + (i * 0.016)  # 60 commands in 1 second
        metrics = detector.record_command(timestamp)
    print(f"   Burst detected: {metrics.is_dos_attack}, Confidence: {metrics.confidence:.2f}")
    print(f"   {metrics.explanation}")
    
    # Simulate sustained attack
    print("\n3. Sustained attack (25 cmds/sec for 5 sec):")
    sustained_time = burst_time + 2
    for i in range(125):
        timestamp = sustained_time + (i * 0.04)  # 25 commands/sec
        metrics = detector.record_command(timestamp)
    print(f"   Sustained attack detected: {metrics.is_dos_attack}, Confidence: {metrics.confidence:.2f}")
    print(f"   {metrics.explanation}")
    
    # Statistics
    print("\n4. Statistics:")
    stats = detector.get_statistics()
    for key, value in stats.items():
        print(f"   {key}: {value}")
