"""
Layer 1: Command Intake
Parses raw MAVLink packets into structured command objects
"""

import time
from typing import Optional, Dict, Any
from pymavlink import mavutil
from dataclasses import dataclass, asdict
import json


@dataclass
class CommandObject:
    """Standardized command representation"""
    msg_id: int
    command_type: str
    params: Dict[str, Any]
    mode: Optional[str]
    source: str  # "gcs", "companion", "autonomy"
    sys_id: int
    comp_id: int
    timestamp: float
    raw_msg: Dict[str, Any]
    
    def to_dict(self):
        return asdict(self)
    
    def to_json(self):
        return json.dumps(self.to_dict(), indent=2)


class CommandIntake:
    """
    Extracts and classifies MAVLink commands
    Output: Structured CommandObject for downstream layers
    """
    
    # MAVLink message types that are commands (not telemetry)
    COMMAND_MSG_TYPES = {
        "COMMAND_LONG",
        "COMMAND_INT",
        "SET_POSITION_TARGET_GLOBAL_INT",
        "SET_POSITION_TARGET_LOCAL_NED",
        "MISSION_ITEM",
        "MISSION_ITEM_INT",
        "SET_MODE",
        "PARAM_SET",
        "MANUAL_CONTROL"
    }
    
    # Command classification
    COMMAND_CLASSES = {
        # Navigation commands
        "SET_POSITION_TARGET_GLOBAL_INT": "NAVIGATION",
        "SET_POSITION_TARGET_LOCAL_NED": "NAVIGATION",
        "MISSION_ITEM": "NAVIGATION",
        "MISSION_ITEM_INT": "NAVIGATION",
        
        # Mode changes
        "SET_MODE": "MODE_CHANGE",
        "COMMAND_LONG": "VARIED",  # Depends on command param
        
        # Manual control
        "MANUAL_CONTROL": "MANUAL",
        
        # Configuration
        "PARAM_SET": "CONFIG"
    }
    
    def __init__(self, connection_string: str = 'udp:127.0.0.1:14550'):
        """Initialize MAVLink connection"""
        self.master = mavutil.mavlink_connection(connection_string)
        print(f"✅ Command Intake Layer initialized: {connection_string}")
    
    def is_command(self, msg_type: str) -> bool:
        """Check if message is a command (vs telemetry)"""
        return msg_type in self.COMMAND_MSG_TYPES
    
    def classify_command(self, msg_type: str, msg_dict: Dict) -> str:
        """Determine command class"""
        base_class = self.COMMAND_CLASSES.get(msg_type, "UNKNOWN")
        
        # Special handling for COMMAND_LONG
        if msg_type == "COMMAND_LONG":
            command_id = msg_dict.get("command", 0)
            return self._classify_command_long(command_id)
        
        return base_class
    
    def _classify_command_long(self, command_id: int) -> str:
        """Classify COMMAND_LONG based on MAV_CMD"""
        # MAV_CMD mapping
        cmd_map = {
            16: "NAVIGATION",      # MAV_CMD_NAV_WAYPOINT
            20: "RETURN",           # MAV_CMD_NAV_RETURN_TO_LAUNCH
            21: "LAND",             # MAV_CMD_NAV_LAND
            22: "TAKEOFF",          # MAV_CMD_NAV_TAKEOFF
            400: "ARM",             # MAV_CMD_COMPONENT_ARM_DISARM
            176: "MODE_CHANGE",     # MAV_CMD_DO_SET_MODE
            183: "EMERGENCY",       # MAV_CMD_DO_SET_HOME
        }
        return cmd_map.get(command_id, "COMMAND")
    
    def infer_source(self, sys_id: int, comp_id: int) -> str:
        """Infer command source from system/component ID"""
        # GCS typically uses sys_id=255
        if sys_id == 255:
            return "gcs"
        # Companion computer typically 1-10
        elif 1 <= sys_id <= 10:
            return "companion"
        # Autopilot itself
        elif sys_id == 1 and comp_id == 1:
            return "autopilot"
        else:
            return "unknown"
    
    def extract_params(self, msg_type: str, msg_dict: Dict) -> Dict[str, Any]:
        """Extract relevant parameters based on message type"""
        params = {}
        
        if msg_type == "SET_POSITION_TARGET_GLOBAL_INT":
            params = {
                "lat": msg_dict.get("lat_int", 0) / 1e7,  # Convert to degrees
                "lon": msg_dict.get("lon_int", 0) / 1e7,
                "alt": msg_dict.get("alt", 0),
                "vx": msg_dict.get("vx", 0),
                "vy": msg_dict.get("vy", 0),
                "vz": msg_dict.get("vz", 0),
                "type_mask": msg_dict.get("type_mask", 0)
            }
        
        elif msg_type == "SET_POSITION_TARGET_LOCAL_NED":
            params = {
                "x": msg_dict.get("x", 0),
                "y": msg_dict.get("y", 0),
                "z": msg_dict.get("z", 0),
                "vx": msg_dict.get("vx", 0),
                "vy": msg_dict.get("vy", 0),
                "vz": msg_dict.get("vz", 0),
                "type_mask": msg_dict.get("type_mask", 0)
            }
        
        elif msg_type == "COMMAND_LONG":
            params = {
                "command": msg_dict.get("command", 0),
                "param1": msg_dict.get("param1", 0),
                "param2": msg_dict.get("param2", 0),
                "param3": msg_dict.get("param3", 0),
                "param4": msg_dict.get("param4", 0),
                "param5": msg_dict.get("param5", 0),
                "param6": msg_dict.get("param6", 0),
                "param7": msg_dict.get("param7", 0)
            }
        
        elif msg_type == "MISSION_ITEM_INT":
            params = {
                "seq": msg_dict.get("seq", 0),
                "command": msg_dict.get("command", 0),
                "lat": msg_dict.get("x", 0) / 1e7,
                "lon": msg_dict.get("y", 0) / 1e7,
                "alt": msg_dict.get("z", 0),
                "autocontinue": msg_dict.get("autocontinue", 0)
            }
        
        elif msg_type == "SET_MODE":
            params = {
                "custom_mode": msg_dict.get("custom_mode", 0),
                "base_mode": msg_dict.get("base_mode", 0)
            }
        
        else:
            # Generic fallback - copy all fields
            params = msg_dict.copy()
        
        return params
    
    def parse_command(self, msg) -> Optional[CommandObject]:
        """
        Convert raw MAVLink message to CommandObject
        Returns None if not a command message
        """
        msg_type = msg.get_type()
        
        # Skip non-command messages
        if not self.is_command(msg_type):
            return None
        
        msg_dict = msg.to_dict()
        
        # Extract metadata
        sys_id = msg_dict.get("target_system", 0)
        comp_id = msg_dict.get("target_component", 0)
        
        # Build CommandObject
        cmd_obj = CommandObject(
            msg_id=msg.get_msgId(),
            command_type=self.classify_command(msg_type, msg_dict),
            params=self.extract_params(msg_type, msg_dict),
            mode=None,  # Will be enriched by later layers
            source=self.infer_source(sys_id, comp_id),
            sys_id=sys_id,
            comp_id=comp_id,
            timestamp=time.time(),
            raw_msg=msg_dict
        )
        
        return cmd_obj
    
    def listen(self, callback=None) -> None:
        """
        Main listening loop
        Calls callback(CommandObject) for each command
        """
        print("🔐 Command Intake Layer active - listening for commands...")
        
        while True:
            msg = self.master.recv_match(blocking=True)
            
            if not msg:
                continue
            
            # Skip bad data
            if msg.get_type() == "BAD_DATA":
                continue
            
            # Parse command
            cmd_obj = self.parse_command(msg)
            
            if cmd_obj:
                # Print structured output
                print(f"\n{'='*60}")
                print(f"🚨 COMMAND INTERCEPTED")
                print(f"{'='*60}")
                print(f"Type:      {cmd_obj.command_type}")
                print(f"Source:    {cmd_obj.source}")
                print(f"Timestamp: {cmd_obj.timestamp}")
                print(f"Params:    {json.dumps(cmd_obj.params, indent=11)}")
                print(f"{'='*60}\n")
                
                # Send to next layer
                if callback:
                    callback(cmd_obj)
            else:
                # Telemetry - just note it
                print(f"📡 Telemetry: {msg.get_type()}", end='\r')


def main():
    """Standalone test of Command Intake Layer"""
    intake = CommandIntake()
    
    def test_callback(cmd: CommandObject):
        """Test callback that prints JSON"""
        print("JSON Output:")
        print(cmd.to_json())
    
    intake.listen(callback=test_callback)


if __name__ == "__main__":
    main()
