from src.ai_layer.command_history import CommandHistory
from src.ai_layer.feature_extractor import extract_features

history = CommandHistory()

cmd1 = {"lat": 12.0, "lon": 77.0, "alt": 10.0, "mode": "AUTO"}
cmd2 = {"lat": 12.001, "lon": 77.002, "alt": 12.0, "mode": "AUTO"}
cmd3 = {"lat": 12.5, "lon": 78.0, "alt": 100.0, "mode": "GUIDED"}

history.add(cmd1)
history.add(cmd2)
prev, curr = history.last()
print("Features 1:", extract_features(prev, curr))

history.add(cmd3)
prev, curr = history.last()
print("Features 2:", extract_features(prev, curr))
