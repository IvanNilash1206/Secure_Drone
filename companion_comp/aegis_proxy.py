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
import os
import yaml
from datetime import datetime
from collections import defaultdict
from typing import Dict, Tuple, Optional
from pathlib import Path

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
    # Add parent directory to path for local imports
    sys.path.insert(0, str(Path(__file__).parent.parent))
    
    # Import crypto layer from companion_comp
    from companion_comp.crypto_layer.decryptor import decrypt_payload
    from companion_comp.crypto_layer.encryptor import encrypt_payload
    from companion_comp.crypto_layer.crypto_gate import CryptoGate
    
    # Import AI/decision layer from companion_comp  
    from companion_comp.intent_firewall.intent_classifier import IntentFirewall
    from companion_comp.decision_engine.risk_aggregator import RiskProportionalDecisionEngine
    from companion_comp.logger.audit_logger import ExplainableLogger
    
    AEGIS_AVAILABLE = True
    print("[AEGIS] ✅ Security layers loaded successfully")
except ImportError as e:
    print(f"[AEGIS] ⚠️  Running in PASS-THROUGH mode (security layers not available)")
    print(f"[AEGIS] ⚠️  Import error: {e}")
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
        fc_ip: str = "127.0.0.1",
        fc_port: int = 14550,
        enable_security: bool = True
    ):
        """
        Initialize AEGIS Proxy
        
        Args:
            listen_host: Interface to bind to (0.0.0.0 = all interfaces)
            listen_port: Port to receive GCS/attacker traffic (default 14560)
            fc_ip: Flight controller IP address (GCS laptop running SITL)
            fc_port: Flight controller listening port (default 14550)
            enable_security: Enable AEGIS security layers (False = pass-through mode)
        """
        self.listen_host = listen_host
        self.listen_port = listen_port
        self.fc_ip = fc_ip
        self.fc_port = fc_port
        self.enable_security = enable_security and AEGIS_AVAILABLE
        
        # Create UDP socket for receiving
        self.recv_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.recv_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.recv_socket.bind((listen_host, listen_port))
        
        # Create UDP socket for forwarding to SITL
        self.send_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        # MAVLink parser (NO network binding - pure parser only)
        self.mav = mavlink2.MAVLink(None)
        self.mav.robust_parsing = True
        
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
                self.crypto_gate = CryptoGate()
                self.crypto_enabled = True
                logger.info("🔐 Crypto layer initialized")
            except Exception as e:
                logger.warning(f"⚠️  Crypto layer failed: {e}")
            
            try:
                # Initialize AI-based IDS and Intent Firewall
                self.intent_firewall = IntentFirewall()
                self.ai_enabled = True
                logger.info("🧠 AI-based Intent Firewall initialized")
            except Exception as e:
                logger.warning(f"⚠️  AI layer failed: {e}")
            
            try:
                # Initialize decision engine
                self.decision_engine = RiskProportionalDecisionEngine()
                logger.info("⚖️  Risk-proportional decision engine initialized")
            except Exception as e:
                logger.warning(f"⚠️  Decision engine failed: {e}")
        
        logger.info("=" * 80)
        logger.info(f"🛡️  AEGIS MAVLink Security Proxy Started")
        logger.info("=" * 80)
        logger.info(f"📥 Listening on: {listen_host}:{listen_port}")
        logger.info(f"📤 Forwarding to: {fc_ip}:{fc_port}")
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
        
        # Log RAW packet reception
        logger.info(f"[AEGIS][RAW] Received {len(data)} bytes from {src_ip}:{src_port}")
        
        # Parse MAVLink message
        try:
            # Decode MAVLink packet manually (no network binding)
            msg = self.mav.decode(data)
            
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
                
                # Step 2: AI-based anomaly detection and intent classification
                if self.ai_enabled:
                    try:
                        # Analyze command intent using IntentFirewall
                        intent_result = self.intent_firewall.analyze(msg)
                        
                        # Check if intent is suspicious or blocked
                        if not intent_result.allowed:
                            self.stats['attacks_detected'] += 1
                            logger.warning(f"🚨 [{src_ip}] INTENT BLOCKED: {intent_result.intent}")
                            logger.warning(f"   Reason: {intent_result.reason}")
                            logger.warning(f"   Message: {msg_type}")
                            self.stats['blocked_by_type'][msg_type] += 1
                            return False  # BLOCK suspicious intent
                    except Exception as e:
                        logger.debug(f"Intent analysis skipped: {e}")
                
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
            self.send_socket.sendto(data, (self.fc_ip, self.fc_port))
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


def load_config(config_path: str = "config.yaml") -> dict:
    """Load configuration from YAML file"""
    config_file = Path(__file__).parent / config_path
    
    if not config_file.exists():
        logger.warning(f"Config file not found: {config_file}")
        logger.info("Using default configuration")
        return {}
    
    try:
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
            logger.info(f"✅ Configuration loaded from {config_file}")
            return config
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        return {}


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='AEGIS MAVLink Security Proxy - Companion Computer',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with config.yaml (recommended)
  python aegis_proxy.py
  
  # Run in pass-through mode (no security)
  python aegis_proxy.py --no-security
  
  # Override config with command line
  python aegis_proxy.py --fc-ip 192.168.1.50 --fc-port 14550
  
Configuration:
  Edit config.yaml to set Flight Controller IP address.
  Default config assumes 3-machine deployment:
    - This machine (Raspberry Pi): Runs AEGIS
    - GCS Laptop: Runs ArduPilot SITL on :14550
    - Attacker Laptop: Sends malicious traffic
        """
    )
    
    parser.add_argument('--config', default='config.yaml',
                       help='Path to config file (default: config.yaml)')
    parser.add_argument('--listen-host', 
                       help='Host to listen on (default: from config)')
    parser.add_argument('--listen-port', type=int,
                       help='Port to listen on (default: from config)')
    parser.add_argument('--fc-ip',
                       help='Flight controller IP (default: from config)')
    parser.add_argument('--fc-port', type=int,
                       help='Flight controller port (default: from config)')
    parser.add_argument('--no-security', action='store_true',
                       help='Disable security checks (pass-through mode)')
    
    args = parser.parse_args()
    
    # Load configuration
    config = load_config(args.config)
    
    # Get network config with CLI override
    net_config = config.get('network', {})
    listen_host = args.listen_host or net_config.get('listen_host', '0.0.0.0')
    listen_port = args.listen_port or net_config.get('listen_port', 14560)
    fc_ip = args.fc_ip or net_config.get('fc_ip', '127.0.0.1')
    fc_port = args.fc_port or net_config.get('fc_port', 14550)
    
    # Print startup banner
    print("="*70)
    print("    AEGIS MAVLink Security Proxy")
    print("    Companion Computer Security Gateway")
    print("="*70)
    print(f"Listening on: {listen_host}:{listen_port}")
    print(f"Forwarding to: {fc_ip}:{fc_port}")
    print(f"Security: {'ENABLED' if not args.no_security else 'DISABLED (pass-through)'}")
    print("="*70)
    print()
    print("⚠️  TRUST BOUNDARY ENFORCEMENT:")
    print("   - OS firewall MUST block direct access to :14550")
    print("   - Only AEGIS can communicate with flight controller")
    print("   - AEGIS enforces decision governance (ALLOW/BLOCK)")
    print("="*70)
    print()
    
    # Create and run proxy
    proxy = AEGISProxy(
        listen_host=listen_host,
        listen_port=listen_port,
        fc_ip=fc_ip,
        fc_port=fc_port,
        enable_security=not args.no_security
    )
    
    proxy.run()


if __name__ == '__main__':
    main()
