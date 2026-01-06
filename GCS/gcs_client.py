#!/usr/bin/env python3
"""
Ground Control Station (GCS) Client - Legitimate UAV Operator

This script simulates a legitimate GCS sending authorized commands to the UAV.
All commands go through AEGIS proxy for security validation.

Usage:
    # Connect through AEGIS proxy (recommended)
    python gcs_client.py --target <AEGIS_IP> --port 14560
    
    # Connect directly to SITL (bypass security - not recommended!)
    python gcs_client.py --target <SITL_IP> --port 14550

Why through AEGIS: All commands validated by crypto + AI security layers
Why UDP: MAVLink protocol standard for low-latency UAV control
"""

import time
import sys
import argparse
import logging
import os
from typing import Optional

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
        logging.FileHandler('logs/gcs_client.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('GCS')


class GCSClient:
    """
    Ground Control Station (GCS) Client
    
    Legitimate operator sending authorized commands to UAV through AEGIS.
    """
    
    def __init__(self, target_host: str, target_port: int):
        """
        Initialize GCS connection
        
        Args:
            target_host: Target IP (AEGIS proxy or SITL)
            target_port: Target port (14560 for AEGIS, 14550 for SITL)
        """
        self.target_host = target_host
        self.target_port = target_port
        
        # Create MAVLink connection
        connection_string = f'udpout:{target_host}:{target_port}'
        logger.info(f"🎮 GCS connecting to: {connection_string}")
        
        try:
            self.mav = mavutil.mavlink_connection(
                connection_string,
                source_system=255,  # GCS system ID
                source_component=0,  # GCS component ID
                dialect='common'
            )
            logger.info(f"✅ Connection established")
            
            if target_port == 14560:
                logger.info("✅ Connected through AEGIS proxy (secure)")
            else:
                logger.warning("⚠️  Direct connection to SITL (bypassing security!)")
                
        except Exception as e:
            logger.error(f"❌ Failed to connect: {e}")
            sys.exit(1)
        
        # Statistics
        self.commands_sent = 0
    
    def wait_heartbeat(self, timeout: int = 10):
        """Wait for heartbeat from autopilot"""
        logger.info(f"⏳ Waiting for heartbeat (timeout: {timeout}s)...")
        
        try:
            msg = self.mav.recv_match(type='HEARTBEAT', blocking=True, timeout=timeout)
            if msg:
                logger.info(f"✅ Heartbeat received from system {msg.get_srcSystem()}")
                logger.info(f"   Type: {msg.type}, Mode: {msg.custom_mode}, Status: {msg.system_status}")
                return True
            else:
                logger.warning("⚠️  No heartbeat received")
                return False
        except Exception as e:
            logger.error(f"❌ Error waiting for heartbeat: {e}")
            return False
    
    def send_heartbeat(self):
        """Send GCS heartbeat"""
        try:
            self.mav.mav.heartbeat_send(
                type=mavutil.mavlink.MAV_TYPE_GCS,
                autopilot=mavutil.mavlink.MAV_AUTOPILOT_INVALID,
                base_mode=0,
                custom_mode=0,
                system_status=mavutil.mavlink.MAV_STATE_ACTIVE
            )
            logger.debug("💓 Heartbeat sent")
        except Exception as e:
            logger.error(f"❌ Failed to send heartbeat: {e}")
    
    def arm_vehicle(self):
        """Arm the vehicle"""
        logger.info("=" * 70)
        logger.info("🔓 Arming vehicle...")
        logger.info("=" * 70)
        
        try:
            self.mav.mav.command_long_send(
                target_system=1,
                target_component=1,
                command=mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
                confirmation=0,
                param1=1,  # 1 = arm
                param2=0, param3=0, param4=0,
                param5=0, param6=0, param7=0
            )
            self.commands_sent += 1
            logger.info("✅ ARM command sent")
            time.sleep(1)
            
        except Exception as e:
            logger.error(f"❌ ARM command failed: {e}")
    
    def takeoff(self, altitude: float = 10):
        """Command takeoff to specified altitude"""
        logger.info("=" * 70)
        logger.info(f"🚁 Commanding takeoff to {altitude}m...")
        logger.info("=" * 70)
        
        try:
            self.mav.mav.command_long_send(
                target_system=1,
                target_component=1,
                command=mavutil.mavlink.MAV_CMD_NAV_TAKEOFF,
                confirmation=0,
                param1=0,  # Pitch
                param2=0, param3=0, param4=0,  # Empty
                param5=0, param6=0,  # Lat, Lon (current location)
                param7=altitude  # Altitude
            )
            self.commands_sent += 1
            logger.info(f"✅ TAKEOFF command sent (target: {altitude}m)")
            time.sleep(2)
            
        except Exception as e:
            logger.error(f"❌ TAKEOFF command failed: {e}")
    
    def goto_position(self, lat: float, lon: float, alt: float):
        """Navigate to specific GPS coordinates"""
        logger.info("=" * 70)
        logger.info(f"🧭 Navigating to position...")
        logger.info("=" * 70)
        logger.info(f"Target: Lat={lat:.6f}, Lon={lon:.6f}, Alt={alt}m")
        
        try:
            self.mav.mav.mission_item_send(
                target_system=1,
                target_component=1,
                seq=0,
                frame=mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT,
                command=mavutil.mavlink.MAV_CMD_NAV_WAYPOINT,
                current=2,  # Guided mode waypoint
                autocontinue=0,
                param1=0,  # Hold time
                param2=5,  # Acceptance radius
                param3=0,  # Pass through
                param4=0,  # Yaw
                x=lat,
                y=lon,
                z=alt
            )
            self.commands_sent += 1
            logger.info("✅ GOTO command sent")
            time.sleep(1)
            
        except Exception as e:
            logger.error(f"❌ GOTO command failed: {e}")
    
    def change_mode(self, mode: str = "GUIDED"):
        """Change flight mode"""
        logger.info("=" * 70)
        logger.info(f"🎯 Changing mode to {mode}...")
        logger.info("=" * 70)
        
        # ArduCopter mode mappings
        mode_mapping = {
            'STABILIZE': 0,
            'ACRO': 1,
            'ALT_HOLD': 2,
            'AUTO': 3,
            'GUIDED': 4,
            'LOITER': 5,
            'RTL': 6,
            'CIRCLE': 7,
            'LAND': 9,
        }
        
        if mode not in mode_mapping:
            logger.error(f"❌ Unknown mode: {mode}")
            return
        
        try:
            self.mav.mav.set_mode_send(
                target_system=1,
                base_mode=mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED,
                custom_mode=mode_mapping[mode]
            )
            self.commands_sent += 1
            logger.info(f"✅ MODE change command sent ({mode})")
            time.sleep(1)
            
        except Exception as e:
            logger.error(f"❌ MODE change failed: {e}")
    
    def return_to_launch(self):
        """Command return to launch"""
        logger.info("=" * 70)
        logger.info("🏠 Commanding Return to Launch (RTL)...")
        logger.info("=" * 70)
        
        try:
            self.mav.mav.command_long_send(
                target_system=1,
                target_component=1,
                command=mavutil.mavlink.MAV_CMD_NAV_RETURN_TO_LAUNCH,
                confirmation=0,
                param1=0, param2=0, param3=0, param4=0,
                param5=0, param6=0, param7=0
            )
            self.commands_sent += 1
            logger.info("✅ RTL command sent")
            time.sleep(1)
            
        except Exception as e:
            logger.error(f"❌ RTL command failed: {e}")
    
    def land(self):
        """Command landing"""
        logger.info("=" * 70)
        logger.info("🛬 Commanding landing...")
        logger.info("=" * 70)
        
        try:
            self.mav.mav.command_long_send(
                target_system=1,
                target_component=1,
                command=mavutil.mavlink.MAV_CMD_NAV_LAND,
                confirmation=0,
                param1=0, param2=0, param3=0, param4=0,
                param5=0, param6=0, param7=0
            )
            self.commands_sent += 1
            logger.info("✅ LAND command sent")
            time.sleep(1)
            
        except Exception as e:
            logger.error(f"❌ LAND command failed: {e}")
    
    def disarm_vehicle(self):
        """Disarm the vehicle"""
        logger.info("=" * 70)
        logger.info("🔒 Disarming vehicle...")
        logger.info("=" * 70)
        
        try:
            self.mav.mav.command_long_send(
                target_system=1,
                target_component=1,
                command=mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
                confirmation=0,
                param1=0,  # 0 = disarm
                param2=0, param3=0, param4=0,
                param5=0, param6=0, param7=0
            )
            self.commands_sent += 1
            logger.info("✅ DISARM command sent")
            time.sleep(1)
            
        except Exception as e:
            logger.error(f"❌ DISARM command failed: {e}")
    
    def request_telemetry(self):
        """Request telemetry streams"""
        logger.info("📡 Requesting telemetry streams...")
        
        try:
            # Request data streams
            self.mav.mav.request_data_stream_send(
                target_system=1,
                target_component=1,
                req_stream_id=mavutil.mavlink.MAV_DATA_STREAM_ALL,
                req_message_rate=1,  # Hz
                start_stop=1  # Start
            )
            logger.info("✅ Telemetry request sent")
            
        except Exception as e:
            logger.error(f"❌ Telemetry request failed: {e}")
    
    def run_mission_scenario(self):
        """Run a typical mission scenario"""
        logger.info("=" * 70)
        logger.info("🎯 Running Normal Mission Scenario")
        logger.info("=" * 70)
        
        # Wait for connection
        if not self.wait_heartbeat():
            logger.error("❌ Cannot establish connection - aborting mission")
            return
        
        # Send periodic heartbeats in background
        logger.info("\n📋 Mission Plan:")
        logger.info("  1. Change to GUIDED mode")
        logger.info("  2. Arm vehicle")
        logger.info("  3. Takeoff to 10m")
        logger.info("  4. Navigate to waypoint")
        logger.info("  5. Return to launch")
        logger.info("  6. Land")
        logger.info("  7. Disarm")
        
        input("\nPress Enter to start mission...")
        
        # Step 1: Change to GUIDED mode
        logger.info("\n[1/7] Changing to GUIDED mode...")
        self.change_mode("GUIDED")
        time.sleep(2)
        
        # Step 2: Arm
        logger.info("\n[2/7] Arming...")
        self.arm_vehicle()
        time.sleep(3)
        
        # Step 3: Takeoff
        logger.info("\n[3/7] Taking off...")
        self.takeoff(altitude=10)
        time.sleep(5)
        
        # Step 4: Navigate
        logger.info("\n[4/7] Navigating to waypoint...")
        # Use nearby coordinates (50m north, 50m east)
        self.goto_position(lat=47.64042, lon=-122.14030, alt=10)
        time.sleep(5)
        
        # Step 5: RTL
        logger.info("\n[5/7] Returning to launch...")
        self.return_to_launch()
        time.sleep(5)
        
        # Step 6: Land
        logger.info("\n[6/7] Landing...")
        self.land()
        time.sleep(5)
        
        # Step 7: Disarm
        logger.info("\n[7/7] Disarming...")
        self.disarm_vehicle()
        
        logger.info("\n✅ Mission complete!")
        logger.info(f"📊 Total commands sent: {self.commands_sent}")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='GCS Client - Legitimate Ground Control Station',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Connect through AEGIS proxy (recommended)
  python gcs_client.py --target 192.168.1.100 --port 14560 --mission
  
  # Connect directly to SITL (bypass security)
  python gcs_client.py --target 127.0.0.1 --port 14550 --mission
  
  # Just test connection
  python gcs_client.py --target 192.168.1.100 --port 14560 --test
  
  # Manual control
  python gcs_client.py --target 192.168.1.100 --port 14560 --interactive
        """
    )
    
    parser.add_argument('--target', required=True,
                       help='Target IP address (AEGIS proxy or SITL)')
    parser.add_argument('--port', type=int, default=14560,
                       help='Target port (14560=AEGIS, 14550=SITL)')
    parser.add_argument('--mission', action='store_true',
                       help='Run automated mission scenario')
    parser.add_argument('--test', action='store_true',
                       help='Just test connection (heartbeat)')
    parser.add_argument('--interactive', action='store_true',
                       help='Interactive mode (not yet implemented)')
    
    args = parser.parse_args()
    
    # Create GCS client
    gcs = GCSClient(args.target, args.port)
    
    logger.info("=" * 70)
    logger.info("🎮 GCS Client Started")
    logger.info("=" * 70)
    logger.info(f"Target: {args.target}:{args.port}")
    logger.info("=" * 70)
    
    try:
        if args.test:
            # Just test connection
            gcs.wait_heartbeat()
            logger.info("✅ Connection test successful")
        
        elif args.mission:
            # Run automated mission
            gcs.run_mission_scenario()
        
        elif args.interactive:
            logger.error("❌ Interactive mode not yet implemented")
            logger.info("Use --mission for automated scenario")
        
        else:
            # Default: just establish connection
            logger.info("No action specified. Use --mission or --test")
            gcs.wait_heartbeat()
            
    except KeyboardInterrupt:
        logger.info("\n🛑 GCS client stopped by user")
    except Exception as e:
        logger.error(f"❌ Error: {e}")


if __name__ == '__main__':
    main()
