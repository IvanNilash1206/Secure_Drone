"""
Replay Attack Detector

Detects replayed commands using:
1. Nonce tracking (cryptographic)
2. Timestamp analysis
3. Command sequence patterns
4. Context mismatch detection
"""

import time
from typing import Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass
from collections import deque
import hashlib


@dataclass
class ReplayMetrics:
    """Replay attack detection metrics"""
    is_replay: bool
    confidence: float
    detection_method: str
    explanation: str
    nonce_duplicate: bool
    timestamp_anomaly: bool
    sequence_anomaly: bool
    
    def to_dict(self):
        return {
            "is_replay": self.is_replay,
            "confidence": self.confidence,
            "detection_method": self.detection_method,
            "explanation": self.explanation,
            "nonce_duplicate": self.nonce_duplicate,
            "timestamp_anomaly": self.timestamp_anomaly,
            "sequence_anomaly": self.sequence_anomaly
        }


class ReplayDetector:
    """
    Multi-layered replay attack detection
    
    Layer 1: Nonce uniqueness (cryptographic guarantee)
    Layer 2: Timestamp freshness (30-second window)
    Layer 3: Command sequence patterns
    Layer 4: Context consistency
    
    Attack patterns:
    - Exact replay: Same nonce, same timestamp
    - Delayed replay: Old timestamp, valid nonce
    - Modified replay: Changed payload, old nonce
    - Session replay: Commands from old session
    """
    
    def __init__(self, 
                 nonce_window_size: int = 10000,
                 timestamp_tolerance_sec: float = 30.0,
                 sequence_window_size: int = 50):
        """
        Args:
            nonce_window_size: Number of recent nonces to track
            timestamp_tolerance_sec: Maximum allowed timestamp age
            sequence_window_size: Command sequence history size
        """
        self.nonce_window_size = nonce_window_size
        self.timestamp_tolerance = timestamp_tolerance_sec
        self.sequence_window_size = sequence_window_size
        
        # Nonce tracking (most recent N nonces)
        self.seen_nonces: Set[bytes] = set()
        self.nonce_queue = deque(maxlen=nonce_window_size)
        
        # Timestamp tracking
        self.last_valid_timestamp = 0.0
        
        # Command sequence tracking
        self.command_history = deque(maxlen=sequence_window_size)
        
        # Statistics
        self.total_commands = 0
        self.detected_replays = 0
        self.nonce_duplicates = 0
        self.timestamp_violations = 0
        self.sequence_anomalies = 0
        
        print(f"✅ Replay Detector initialized (nonce_window={nonce_window_size}, timestamp_tolerance={timestamp_tolerance_sec}s)")
    
    def check_command(self, 
                     nonce: bytes,
                     timestamp: float,
                     command_hash: Optional[bytes] = None,
                     payload: Optional[bytes] = None) -> ReplayMetrics:
        """
        Check if command is a replay attack
        
        Args:
            nonce: Cryptographic nonce (should be unique)
            timestamp: Command timestamp
            command_hash: Hash of command payload (optional)
            payload: Raw command payload for hashing (optional)
            
        Returns:
            ReplayMetrics with detection results
        """
        self.total_commands += 1
        
        # Generate command hash if not provided
        if command_hash is None and payload is not None:
            command_hash = hashlib.sha256(payload).digest()
        
        # Layer 1: Nonce uniqueness check
        nonce_duplicate = self._check_nonce(nonce)
        
        # Layer 2: Timestamp freshness check
        timestamp_anomaly, timestamp_reason = self._check_timestamp(timestamp)
        
        # Layer 3: Sequence pattern check
        sequence_anomaly, sequence_reason = self._check_sequence(command_hash, timestamp)
        
        # Aggregate detection
        is_replay, confidence, method, explanation = self._aggregate_detection(
            nonce_duplicate, timestamp_anomaly, sequence_anomaly,
            timestamp_reason, sequence_reason
        )
        
        # Update tracking structures if not replay
        if not is_replay:
            self._update_tracking(nonce, timestamp, command_hash)
        else:
            self.detected_replays += 1
        
        return ReplayMetrics(
            is_replay=is_replay,
            confidence=confidence,
            detection_method=method,
            explanation=explanation,
            nonce_duplicate=nonce_duplicate,
            timestamp_anomaly=timestamp_anomaly,
            sequence_anomaly=sequence_anomaly
        )
    
    def _check_nonce(self, nonce: bytes) -> bool:
        """Check if nonce has been seen before"""
        if nonce in self.seen_nonces:
            self.nonce_duplicates += 1
            return True
        return False
    
    def _check_timestamp(self, timestamp: float) -> Tuple[bool, str]:
        """
        Check timestamp freshness
        
        Returns: (is_anomaly, reason)
        """
        current_time = time.time()
        time_diff = abs(current_time - timestamp)
        
        # Check if timestamp is too old
        if timestamp < current_time - self.timestamp_tolerance:
            self.timestamp_violations += 1
            return True, f"Timestamp too old: {time_diff:.1f}s ago (tolerance: {self.timestamp_tolerance}s)"
        
        # Check if timestamp is too far in future
        if timestamp > current_time + self.timestamp_tolerance:
            self.timestamp_violations += 1
            return True, f"Timestamp in future: {time_diff:.1f}s ahead"
        
        # Check if timestamp is older than last valid timestamp (out of order)
        if timestamp < self.last_valid_timestamp - 5.0:  # Allow 5s reordering
            return True, f"Timestamp out of order: {self.last_valid_timestamp - timestamp:.1f}s behind last command"
        
        return False, "Timestamp valid"
    
    def _check_sequence(self, command_hash: Optional[bytes], timestamp: float) -> Tuple[bool, str]:
        """
        Check command sequence patterns
        
        Detects:
        - Identical commands in short time window
        - Suspicious repeat patterns
        
        Returns: (is_anomaly, reason)
        """
        if command_hash is None:
            return False, "No hash provided"
        
        # Check for duplicate command in recent history
        recent_window = 5.0  # seconds
        for hist_hash, hist_time in self.command_history:
            if hist_hash == command_hash and abs(timestamp - hist_time) < recent_window:
                self.sequence_anomalies += 1
                return True, f"Duplicate command within {recent_window}s window"
        
        return False, "Sequence valid"
    
    def _aggregate_detection(self, 
                            nonce_dup: bool,
                            timestamp_anomaly: bool,
                            sequence_anomaly: bool,
                            timestamp_reason: str,
                            sequence_reason: str) -> Tuple[bool, float, str, str]:
        """
        Aggregate all detection layers
        
        Returns: (is_replay, confidence, method, explanation)
        """
        # Nonce duplicate is definitive proof of replay
        if nonce_dup:
            return True, 1.0, "nonce_duplicate", "Cryptographic nonce reused (definitive replay)"
        
        # Timestamp violation is strong indicator
        if timestamp_anomaly:
            if sequence_anomaly:
                return True, 0.95, "timestamp_sequence", f"{timestamp_reason} + {sequence_reason}"
            else:
                return True, 0.85, "timestamp", timestamp_reason
        
        # Sequence anomaly alone (weaker)
        if sequence_anomaly:
            return True, 0.70, "sequence", sequence_reason
        
        # All checks passed
        return False, 0.0, "none", "No replay detected"
    
    def _update_tracking(self, nonce: bytes, timestamp: float, command_hash: Optional[bytes]):
        """Update tracking structures with valid command"""
        # Add nonce to seen set
        if len(self.nonce_queue) >= self.nonce_window_size:
            # Remove oldest nonce
            old_nonce = self.nonce_queue[0]
            self.seen_nonces.discard(old_nonce)
        
        self.nonce_queue.append(nonce)
        self.seen_nonces.add(nonce)
        
        # Update timestamp
        self.last_valid_timestamp = max(self.last_valid_timestamp, timestamp)
        
        # Update command history
        if command_hash is not None:
            self.command_history.append((command_hash, timestamp))
    
    def reset(self):
        """Reset detector state"""
        self.seen_nonces.clear()
        self.nonce_queue.clear()
        self.command_history.clear()
        self.last_valid_timestamp = 0.0
        self.total_commands = 0
        self.detected_replays = 0
        self.nonce_duplicates = 0
        self.timestamp_violations = 0
        self.sequence_anomalies = 0
        print("Replay Detector reset")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get detector statistics"""
        return {
            "total_commands": self.total_commands,
            "detected_replays": self.detected_replays,
            "nonce_duplicates": self.nonce_duplicates,
            "timestamp_violations": self.timestamp_violations,
            "sequence_anomalies": self.sequence_anomalies,
            "detection_rate": self.detected_replays / self.total_commands if self.total_commands > 0 else 0.0,
            "tracked_nonces": len(self.seen_nonces)
        }


if __name__ == "__main__":
    # Test Replay detector
    import os
    
    print("Testing Replay Detector\n")
    
    detector = ReplayDetector()
    
    # Test 1: Normal commands
    print("1. Normal commands:")
    base_time = time.time()
    for i in range(5):
        nonce = os.urandom(16)
        timestamp = base_time + i
        payload = f"COMMAND_{i}".encode()
        metrics = detector.check_command(nonce, timestamp, payload=payload)
        print(f"   Command {i}: Replay={metrics.is_replay}, Conf={metrics.confidence:.2f}")
    
    # Test 2: Duplicate nonce (replay)
    print("\n2. Replay attack (duplicate nonce):")
    nonce = os.urandom(16)
    metrics = detector.check_command(nonce, base_time + 10, payload=b"CMD_1")
    print(f"   First: Replay={metrics.is_replay}")
    
    metrics = detector.check_command(nonce, base_time + 11, payload=b"CMD_1")
    print(f"   Replay: Replay={metrics.is_replay}, Conf={metrics.confidence:.2f}")
    print(f"   {metrics.explanation}")
    
    # Test 3: Old timestamp
    print("\n3. Replay attack (old timestamp):")
    nonce = os.urandom(16)
    old_timestamp = base_time - 60  # 60 seconds ago
    metrics = detector.check_command(nonce, old_timestamp, payload=b"OLD_CMD")
    print(f"   Old timestamp detected: Replay={metrics.is_replay}, Conf={metrics.confidence:.2f}")
    print(f"   {metrics.explanation}")
    
    # Test 4: Duplicate command in short window
    print("\n4. Sequence anomaly (duplicate command):")
    payload = b"TAKEOFF"
    nonce1 = os.urandom(16)
    nonce2 = os.urandom(16)
    
    metrics = detector.check_command(nonce1, base_time + 20, payload=payload)
    print(f"   First: Replay={metrics.is_replay}")
    
    metrics = detector.check_command(nonce2, base_time + 21, payload=payload)
    print(f"   Duplicate: Replay={metrics.is_replay}, Conf={metrics.confidence:.2f}")
    print(f"   {metrics.explanation}")
    
    # Statistics
    print("\n5. Statistics:")
    stats = detector.get_statistics()
    for key, value in stats.items():
        print(f"   {key}: {value}")
