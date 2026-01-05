import logging
from pymavlink import mavutil

logging.basicConfig(
    filename="logs/command_log.txt",
    level=logging.INFO,
    format="%(asctime)s %(message)s"
)

COMMAND_MESSAGES = {
    "SET_POSITION_TARGET_GLOBAL_INT",
    "SET_POSITION_TARGET_LOCAL_NED",
    "MISSION_ITEM",
    "MISSION_ITEM_INT",
    "COMMAND_LONG"
}

master = mavutil.mavlink_connection('udp:127.0.0.1:14550')

print("🔐 AEGIS Proxy active...")

while True:
    msg = master.recv_match(blocking=True)
    if not msg:
        continue

    msg_type = msg.get_type()

    if msg_type == "BAD_DATA":
        continue

    if msg_type in COMMAND_MESSAGES:
        log_msg = f"COMMAND intercepted: {msg_type} | {msg.to_dict()}"
        print(f"🚨 {log_msg}")
        logging.info(log_msg)
    else:
        print(f"📡 Telemetry: {msg_type}")