from src.ai_layer.inference import evaluate_command
from src.ai_layer.decision_gate import decision

# Example normal-looking command
normal_features = [0.001, 0.002, 1.0, 0.5, 0.01, 0]
score = evaluate_command(normal_features)
print("Normal score:", score, decision(score))

# Example anomalous command
attack_features = [5.0, 5.0, 200.0, 0.1, 50.0, 1]
score = evaluate_command(attack_features)
print("Attack score:", score, decision(score))
