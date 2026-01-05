import time
import json
import os

LOG_FILE = "logs/decision_log.jsonl"

def log_event(status, reason, command):
    event = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "status": status,
        "reason": reason,
        "command": command
    }

    # Ensure logs directory exists
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(event) + "\n")