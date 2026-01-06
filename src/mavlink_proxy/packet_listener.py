from src.logging_config import logger
from pymavlink import mavutil

COMMAND_MESSAGES = {
    "SET_POSITION_TARGET_GLOBAL_INT",
    "SET_POSITION_TARGET_LOCAL_NED",
    "MISSION_ITEM",
    "MISSION_ITEM_INT",
    "COMMAND_LONG"
}

master = mavutil.mavlink_connection('udp:0.0.0.0:14550')

logger.info("AEGIS Proxy active")
print("🔐 AEGIS Proxy active...")

while True:
    msg = master.recv_match(blocking=True)
    if not msg:
        continue

    msg_type = msg.get_type()

    if msg_type == "BAD_DATA":
        logger.debug("Received BAD_DATA")
        continue

    if msg_type in COMMAND_MESSAGES:
        log_msg = f"COMMAND intercepted: {msg_type} | {msg.to_dict()}"
        logger.info(log_msg)
        print(f"🚨 {log_msg}")
    else:
        logger.debug(f"Telemetry: {msg_type}")
        print(f"📡 Telemetry: {msg_type}")