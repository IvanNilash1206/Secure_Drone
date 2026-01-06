from collections import deque
import time

class CommandHistory:
    def __init__(self, max_len=20):
        self.commands = deque(maxlen=max_len)

    def add(self, command_dict):
        self.commands.append({
            "command": command_dict,
            "timestamp": time.time()
        })

    def last(self):
        if len(self.commands) < 2:
            return None, None
        return self.commands[-2], self.commands[-1]
