#!/usr/bin/env python3
"""
Mission Sender Module

Sends autonomous mission waypoints to UAV.
"""
import time
import sys
import yaml
from pymavlink import mavutil

class MissionSender:
    def __init__(self, mav):
        self.mav = mav
        self.waypoints = []
    
    def add_waypoint(self, lat: float, lon: float, alt: float):
        """Add waypoint to mission"""
        self.waypoints.append({"lat": lat, "lon": lon, "alt": alt})
        print(f"[MISSION] Waypoint {len(self.waypoints)} added: {lat:.6f}, {lon:.6f}, {alt}m")
    
    def upload_mission(self):
        """Upload mission to UAV"""
        print(f"[MISSION] Uploading {len(self.waypoints)} waypoints...")
        
        for i, wp in enumerate(self.waypoints):
            try:
                self.mav.mav.mission_item_send(
                    target_system=1,
                    target_component=1,
                    seq=i,
                    frame=mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT,
                    command=mavutil.mavlink.MAV_CMD_NAV_WAYPOINT,
                    current=0 if i > 0 else 1,  # First waypoint is current
                    autocontinue=1,
                    param1=0,  # Hold time
                    param2=5,  # Acceptance radius
                    param3=0,  # Pass through
                    param4=0,  # Yaw
                    x=wp["lat"],
                    y=wp["lon"],
                    z=wp["alt"]
                )
                print(f"[MISSION] Waypoint {i+1} sent")
                time.sleep(0.5)
            except Exception as e:
                print(f"[MISSION] Error sending waypoint {i+1}: {e}")
        
        print(f"[MISSION] Mission upload complete!")
    
    def clear_mission(self):
        """Clear mission"""
        self.waypoints = []
        print("[MISSION] Mission cleared")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python mission_sender.py <target_ip> <target_port>")
        sys.exit(1)
    
    target_ip = sys.argv[1]
    target_port = int(sys.argv[2])
    
    connection_string = f'udpout:{target_ip}:{target_port}'
    mav = mavutil.mavlink_connection(connection_string, source_system=255)
    
    time.sleep(1)
    
    sender = MissionSender(mav)
    
    # Example mission: square pattern
    sender.add_waypoint(47.6404, -122.1403, 10)
    sender.add_waypoint(47.6414, -122.1403, 10)
    sender.add_waypoint(47.6414, -122.1393, 10)
    sender.add_waypoint(47.6404, -122.1393, 10)
    
    sender.upload_mission()
