from src.ai_layer.trust_model import TrustModel

trust_model = TrustModel()

def evaluate_command(feature_vector):
    score = trust_model.trust_score(feature_vector)
    return score
