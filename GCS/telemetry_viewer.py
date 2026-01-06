#!/usr/bin/env python3
"""
Telemetry Viewer Module

Displays real-time telemetry from UAV.
"""
import time
import sys
from pymavlink import mavutil

class TelemetryViewer:
    def __init__(self, mav):
        self.mav = mav
        self.telemetry = {
            "gps": None,
            "attitude": None,
            "altitude": None,
            "battery": None,
            "mode": None,
            "armed": False
        }
    
    def request_streams(self):
        """Request telemetry streams"""
        print("[TELEMETRY] Requesting data streams...")
        try:
            self.mav.mav.request_data_stream_send(
                target_system=1,
                target_component=1,
                req_stream_id=mavutil.mavlink.MAV_DATA_STREAM_ALL,
                req_message_rate=1,  # 1 Hz
                start_stop=1
            )
            print("[TELEMETRY] Streams requested")
        except Exception as e:
            print(f"[TELEMETRY] Error requesting streams: {e}")
    
    def update(self):
        """Receive and update telemetry"""
        msg = self.mav.recv_match(blocking=False)
        
        if msg is None:
            return
        
        msg_type = msg.get_type()
        
        if msg_type == "GPS_RAW_INT":
            self.telemetry["gps"] = {
                "lat": msg.lat / 1e7,
                "lon": msg.lon / 1e7,
                "alt": msg.alt / 1000.0,
                "satellites": msg.satellites_visible
            }
        
        elif msg_type == "ATTITUDE":
            self.telemetry["attitude"] = {
                "roll": msg.roll,
                "pitch": msg.pitch,
                "yaw": msg.yaw
            }
        
        elif msg_type == "GLOBAL_POSITION_INT":
            self.telemetry["altitude"] = {
                "relative": msg.relative_alt / 1000.0,
                "absolute": msg.alt / 1000.0
            }
        
        elif msg_type == "SYS_STATUS":
            self.telemetry["battery"] = {
                "voltage": msg.voltage_battery / 1000.0,
                "current": msg.current_battery / 100.0,
                "remaining": msg.battery_remaining
            }
        
        elif msg_type == "HEARTBEAT":
            self.telemetry["mode"] = msg.custom_mode
            self.telemetry["armed"] = (msg.base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED) != 0
    
    def display(self):
        """Display telemetry"""
        print("\n" + "="*60)
        print("                    TELEMETRY")
        print("="*60)
        
        if self.telemetry["gps"]:
            gps = self.telemetry["gps"]
            print(f"GPS: Lat={gps['lat']:.6f}, Lon={gps['lon']:.6f}, Alt={gps['alt']:.1f}m, Sats={gps['satellites']}")
        
        if self.telemetry["altitude"]:
            alt = self.telemetry["altitude"]
            print(f"Altitude: Relative={alt['relative']:.1f}m, Absolute={alt['absolute']:.1f}m")
        
        if self.telemetry["attitude"]:
            att = self.telemetry["attitude"]
            print(f"Attitude: Roll={att['roll']:.2f}, Pitch={att['pitch']:.2f}, Yaw={att['yaw']:.2f}")
        
        if self.telemetry["battery"]:
            bat = self.telemetry["battery"]
            print(f"Battery: {bat['voltage']:.1f}V, {bat['current']:.1f}A, {bat['remaining']}%")
        
        print(f"Mode: {self.telemetry['mode']}, Armed: {self.telemetry['armed']}")
        print("="*60)
    
    def run(self, duration_sec: int = 60):
        """Run telemetry viewer"""
        self.request_streams()
        
        print(f"[TELEMETRY] Monitoring for {duration_sec} seconds...")
        start_time = time.time()
        last_display = 0
        
        try:
            while (time.time() - start_time) < duration_sec:
                self.update()
                
                # Display every 2 seconds
                if time.time() - last_display >= 2:
                    self.display()
                    last_display = time.time()
                
                time.sleep(0.1)
        
        except KeyboardInterrupt:
            print("\n[TELEMETRY] Stopped by user")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python telemetry_viewer.py <target_ip> <target_port> [duration]")
        sys.exit(1)
    
    target_ip = sys.argv[1]
    target_port = int(sys.argv[2])
    duration = int(sys.argv[3]) if len(sys.argv) > 3 else 60
    
    connection_string = f'udpout:{target_ip}:{target_port}'
    mav = mavutil.mavlink_connection(connection_string, source_system=255)
    
    time.sleep(1)
    
    viewer = TelemetryViewer(mav)
    viewer.run(duration)
