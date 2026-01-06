#!/usr/bin/env python3
"""
AEGIS MAVLink Proxy - Security Gateway for UAV Communications

This proxy sits between Ground Control Station (GCS) / Attackers and the Flight Controller (SITL).
ALL MAVLink traffic MUST flow through AEGIS - no direct connections allowed.

System Topology:
    GCS/Attacker → UDP:14560 → AEGIS Proxy → UDP:14550 → ArduPilot SITL
    
Port Explanation:
    - 14560: AEGIS listening port (public-facing)
    - 14550: ArduPilot SITL listening port (internal-only)
    
Why UDP: MAVLink protocol standard uses UDP for low-latency command/control
Why this architecture: AEGIS acts as mandatory security checkpoint

Security Integration:
    - Crypto Layer: Message encryption/decryption and authentication
    - AI Layer: Anomaly detection and intent classification
    - Decision Engine: Allow/block/modify decisions with logging
"""

import socket
import select
import time
import logging
import sys
from datetime import datetime
from collections import defaultdict
from typing import Dict, Tuple, Optional

# Import pymavlink for MAVLink message parsing
try:
    from pymavlink import mavutil
    from pymavlink.dialects.v20 import common as mavlink2
except ImportError:
    print("ERROR: pymavlink not installed!")
    print("Install with: pip install pymavlink")
    sys.exit(1)

# Import AEGIS security layers (optional - will work without them)
AEGIS_AVAILABLE = False
try:
    from src.crypto_layer.decryptor import Decryptor
    from src.crypto_layer.encryptor import Encryptor
    from src.ai_layer.mode_aware_ids import ModeAwareIDS
    from src.decision_engine.decision_engine import DecisionEngine
    AEGIS_AVAILABLE = True
    print("[AEGIS] ✅ Security layers loaded successfully")
except ImportError:
    print("[AEGIS] ⚠️  Running in PASS-THROUGH mode (security layers not available)")
    print("[AEGIS] ⚠️  All messages will be forwarded without security checks")


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/aegis_proxy.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('AEGIS-Proxy')


class AEGISProxy:
    """
    AEGIS MAVLink Security Proxy
    
    Responsibilities:
    1. Receive MAVLink messages from GCS and potential attackers (UDP:14560)
    2. Parse and log all incoming messages
    3. Apply security checks (crypto + AI validation)
    4. Forward approved messages to SITL (UDP:14550)
    5. Track statistics and detect anomalies
    """
    
    def __init__(
        self,
        listen_host: str = "0.0.0.0",
        listen_port: int = 14560,
        sitl_host: str = "127.0.0.1",
        sitl_port: int = 14550,
        enable_security: bool = True
    ):
        """
        Initialize AEGIS Proxy
        
        Args:
            listen_host: Interface to bind to (0.0.0.0 = all interfaces)
            listen_port: Port to receive GCS/attacker traffic (default 14560)
            sitl_host: SITL IP address (default 127.0.0.1 for local)
            sitl_port: SITL listening port (default 14550)
            enable_security: Enable AEGIS security layers (False = pass-through mode)
        """
        self.listen_host = listen_host
        self.listen_port = listen_port
        self.sitl_host = sitl_host
        self.sitl_port = sitl_port
        self.enable_security = enable_security and AEGIS_AVAILABLE
        
        # Create UDP socket for receiving
        self.recv_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.recv_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.recv_socket.bind((listen_host, listen_port))
        
        # Create UDP socket for forwarding to SITL
        self.send_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        # MAVLink parser
        self.mav = mavutil.mavlink_connection(
            f'udpin:{listen_host}:{listen_port}',
            dialect='common',
            robust_parsing=True
        )
        
        # Track connected clients
        self.clients: Dict[Tuple[str, int], dict] = {}
        
        # Statistics
        self.stats = {
            'total_received': 0,
            'total_forwarded': 0,
            'total_blocked': 0,
            'attacks_detected': 0,
            'messages_by_type': defaultdict(int),
            'blocked_by_type': defaultdict(int)
        }
        
        # Initialize security layers if enabled
        self.crypto_enabled = False
        self.ai_enabled = False
        
        if self.enable_security:
            try:
                # Initialize crypto layer
                self.decryptor = Decryptor()
                self.encryptor = Encryptor()
                self.crypto_enabled = True
                logger.info("🔐 Crypto layer initialized")
            except Exception as e:
                logger.warning(f"⚠️  Crypto layer failed: {e}")
            
            try:
                # Initialize AI-based IDS
                self.ids = ModeAwareIDS()
                self.ai_enabled = True
                logger.info("🧠 AI-based IDS initialized")
            except Exception as e:
                logger.warning(f"⚠️  AI layer failed: {e}")
            
            try:
                # Initialize decision engine
                self.decision_engine = DecisionEngine()
                logger.info("⚖️  Decision engine initialized")
            except Exception as e:
                logger.warning(f"⚠️  Decision engine failed: {e}")
        
        logger.info("=" * 80)
        logger.info(f"🛡️  AEGIS MAVLink Security Proxy Started")
        logger.info("=" * 80)
        logger.info(f"📥 Listening on: {listen_host}:{listen_port}")
        logger.info(f"📤 Forwarding to: {sitl_host}:{sitl_port}")
        logger.info(f"🔒 Security: {'ENABLED' if self.enable_security else 'DISABLED (PASS-THROUGH)'}")
        logger.info(f"   - Crypto: {'✅' if self.crypto_enabled else '❌'}")
        logger.info(f"   - AI IDS: {'✅' if self.ai_enabled else '❌'}")
        logger.info("=" * 80)
        
    def process_message(self, data: bytes, src_addr: Tuple[str, int]) -> bool:
        """
        Process incoming MAVLink message with security checks
        
        Args:
            data: Raw MAVLink message bytes
            src_addr: Source (IP, port) tuple
            
        Returns:
            True if message should be forwarded, False if blocked
        """
        src_ip, src_port = src_addr
        
        # Update client tracking
        if src_addr not in self.clients:
            self.clients[src_addr] = {
                'first_seen': time.time(),
                'last_seen': time.time(),
                'msg_count': 0
            }
            logger.info(f"🆕 New client: {src_ip}:{src_port}")
        
        self.clients[src_addr]['last_seen'] = time.time()
        self.clients[src_addr]['msg_count'] += 1
        
        # Parse MAVLink message
        try:
            # Try to parse as MAVLink
            msg = None
            for m in self.mav.parse_buffer(data):
                msg = m
                break
            
            if msg is None:
                logger.warning(f"⚠️  [{src_ip}] Invalid MAVLink message (length: {len(data)})")
                return False
            
            msg_type = msg.get_type()
            self.stats['messages_by_type'][msg_type] += 1
            
            # Log incoming message
            logger.info(f"📨 [{src_ip}:{src_port}] → {msg_type} (ID: {msg.get_msgId()})")
            
            # ============================================================
            # 🔒 SECURITY CHECKPOINT - Insert Security Logic Here
            # ============================================================
            
            if self.enable_security:
                # Step 1: Crypto validation (if encrypted)
                if self.crypto_enabled:
                    # Check for encrypted payload (custom implementation)
                    # For now, we assume messages are plaintext MAVLink
                    pass
                
                # Step 2: AI-based anomaly detection
                if self.ai_enabled:
                    # Extract features from MAVLink message
                    features = self._extract_features(msg, src_addr)
                    
                    # Run through IDS
                    is_anomaly = self.ids.detect_anomaly(features)
                    
                    if is_anomaly:
                        self.stats['attacks_detected'] += 1
                        logger.warning(f"🚨 [{src_ip}] ANOMALY DETECTED: {msg_type}")
                        logger.warning(f"   Message details: {msg}")
                        
                        # Specific attack detection
                        attack_type = self._classify_attack(msg, features)
                        if attack_type:
                            logger.error(f"🔴 [{src_ip}] ATTACK: {attack_type}")
                            self.stats['blocked_by_type'][msg_type] += 1
                            return False  # BLOCK malicious message
                
                # Step 3: Command-specific validation
                block_reason = self._validate_command(msg, src_addr)
                if block_reason:
                    logger.warning(f"🚫 [{src_ip}] BLOCKED: {block_reason}")
                    self.stats['blocked_by_type'][msg_type] += 1
                    return False
            
            # ============================================================
            # ✅ Message Approved - Forward to SITL
            # ============================================================
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error processing message from {src_ip}: {e}")
            return False
    
    def _extract_features(self, msg, src_addr: Tuple[str, int]) -> dict:
        """Extract features from MAVLink message for AI analysis"""
        features = {
            'msg_type': msg.get_type(),
            'msg_id': msg.get_msgId(),
            'src_system': msg.get_srcSystem(),
            'src_component': msg.get_srcComponent(),
            'timestamp': time.time(),
            'src_ip': src_addr[0],
            'msg_rate': self.clients[src_addr]['msg_count'] / 
                       (time.time() - self.clients[src_addr]['first_seen'] + 0.001)
        }
        
        # Extract message-specific fields
        msg_type = msg.get_type()
        
        if msg_type == 'COMMAND_LONG':
            features['command'] = msg.command
            features['param1'] = msg.param1
            features['param2'] = msg.param2
        elif msg_type == 'MISSION_ITEM':
            features['seq'] = msg.seq
            features['lat'] = msg.x
            features['lon'] = msg.y
            features['alt'] = msg.z
        elif msg_type == 'GPS_RAW_INT':
            features['lat'] = msg.lat / 1e7
            features['lon'] = msg.lon / 1e7
            features['alt'] = msg.alt / 1000.0
            features['satellites'] = msg.satellites_visible
        elif msg_type == 'SET_POSITION_TARGET_GLOBAL_INT':
            features['lat'] = msg.lat_int / 1e7
            features['lon'] = msg.lon_int / 1e7
            features['alt'] = msg.alt
        
        return features
    
    def _classify_attack(self, msg, features: dict) -> Optional[str]:
        """Classify type of attack based on message and features"""
        msg_type = msg.get_type()
        msg_rate = features.get('msg_rate', 0)
        
        # DoS Detection: High message rate
        if msg_rate > 50:  # More than 50 msgs/sec
            return f"DoS Flooding ({msg_rate:.1f} msgs/sec)"
        
        # GPS Spoofing Detection
        if msg_type == 'GPS_RAW_INT':
            lat = features.get('lat', 0)
            lon = features.get('lon', 0)
            sats = features.get('satellites', 0)
            
            # Check for suspicious GPS values
            if abs(lat) > 90 or abs(lon) > 180:
                return "GPS Spoofing (Invalid coordinates)"
            if sats > 30:  # Unrealistic satellite count
                return "GPS Spoofing (Impossible satellite count)"
        
        # Unauthorized Waypoint Injection
        if msg_type == 'MISSION_ITEM':
            # Could check against authorized mission boundaries
            alt = features.get('alt', 0)
            if alt > 500:  # Above 500m
                return "Waypoint Injection (Excessive altitude)"
        
        # Unauthorized Command Injection
        if msg_type == 'COMMAND_LONG':
            cmd = features.get('command', 0)
            dangerous_commands = [
                400,  # MAV_CMD_COMPONENT_ARM_DISARM
                20,   # MAV_CMD_NAV_RETURN_TO_LAUNCH
                21,   # MAV_CMD_NAV_LAND
            ]
            if cmd in dangerous_commands:
                return f"Command Injection (Dangerous command: {cmd})"
        
        return None
    
    def _validate_command(self, msg, src_addr: Tuple[str, int]) -> Optional[str]:
        """Validate specific command logic"""
        msg_type = msg.get_type()
        
        # Example: Block SET_MODE from unknown sources
        if msg_type == 'SET_MODE':
            # Could implement whitelist of authorized IPs
            pass
        
        # Example: Validate RTL commands
        if msg_type == 'COMMAND_LONG' and msg.command == 20:  # RTL
            # Could check if conditions are appropriate for RTL
            logger.info(f"⚠️  RTL command received from {src_addr[0]}")
        
        return None  # No blocking by default
    
    def forward_to_sitl(self, data: bytes):
        """Forward approved message to SITL"""
        try:
            self.send_socket.sendto(data, (self.sitl_host, self.sitl_port))
            self.stats['total_forwarded'] += 1
        except Exception as e:
            logger.error(f"❌ Failed to forward to SITL: {e}")
    
    def print_statistics(self):
        """Print current statistics"""
        logger.info("=" * 80)
        logger.info("📊 AEGIS Proxy Statistics")
        logger.info("=" * 80)
        logger.info(f"Total Received:  {self.stats['total_received']}")
        logger.info(f"Total Forwarded: {self.stats['total_forwarded']}")
        logger.info(f"Total Blocked:   {self.stats['total_blocked']}")
        logger.info(f"Attacks Detected: {self.stats['attacks_detected']}")
        logger.info(f"Active Clients:  {len(self.clients)}")
        
        if self.stats['messages_by_type']:
            logger.info("\nMessages by Type:")
            for msg_type, count in sorted(self.stats['messages_by_type'].items(), 
                                         key=lambda x: x[1], reverse=True)[:10]:
                logger.info(f"  {msg_type:30s}: {count}")
        
        if self.stats['blocked_by_type']:
            logger.info("\n🚫 Blocked by Type:")
            for msg_type, count in self.stats['blocked_by_type'].items():
                logger.info(f"  {msg_type:30s}: {count}")
        
        logger.info("=" * 80)
    
    def run(self):
        """Main proxy loop"""
        logger.info("🚀 AEGIS Proxy running... Press Ctrl+C to stop")
        
        last_stats_time = time.time()
        stats_interval = 30  # Print stats every 30 seconds
        
        try:
            while True:
                # Use select for non-blocking receive with timeout
                ready, _, _ = select.select([self.recv_socket], [], [], 1.0)
                
                if ready:
                    # Receive data
                    data, src_addr = self.recv_socket.recvfrom(4096)
                    self.stats['total_received'] += 1
                    
                    # Process with security checks
                    should_forward = self.process_message(data, src_addr)
                    
                    if should_forward:
                        # Forward to SITL
                        self.forward_to_sitl(data)
                        logger.debug(f"✅ Forwarded to SITL")
                    else:
                        # Blocked
                        self.stats['total_blocked'] += 1
                        logger.warning(f"🚫 Message BLOCKED from {src_addr[0]}")
                
                # Print periodic statistics
                if time.time() - last_stats_time > stats_interval:
                    self.print_statistics()
                    last_stats_time = time.time()
                    
        except KeyboardInterrupt:
            logger.info("\n🛑 Shutting down AEGIS Proxy...")
            self.print_statistics()
        finally:
            self.recv_socket.close()
            self.send_socket.close()


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='AEGIS MAVLink Security Proxy',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with full security (default)
  python aegis_proxy.py
  
  # Run in pass-through mode (no security)
  python aegis_proxy.py --no-security
  
  # Custom ports
  python aegis_proxy.py --listen-port 14560 --sitl-port 14550
  
  # Allow external connections
  python aegis_proxy.py --listen-host 0.0.0.0
        """
    )
    
    parser.add_argument('--listen-host', default='0.0.0.0',
                       help='Host to listen on (default: 0.0.0.0)')
    parser.add_argument('--listen-port', type=int, default=14560,
                       help='Port to listen on (default: 14560)')
    parser.add_argument('--sitl-host', default='127.0.0.1',
                       help='SITL host (default: 127.0.0.1)')
    parser.add_argument('--sitl-port', type=int, default=14550,
                       help='SITL port (default: 14550)')
    parser.add_argument('--no-security', action='store_true',
                       help='Disable security checks (pass-through mode)')
    
    args = parser.parse_args()
    
    # Create and run proxy
    proxy = AEGISProxy(
        listen_host=args.listen_host,
        listen_port=args.listen_port,
        sitl_host=args.sitl_host,
        sitl_port=args.sitl_port,
        enable_security=not args.no_security
    )
    
    proxy.run()


if __name__ == '__main__':
    main()
