import joblib
import numpy as np

MODEL_FILE = "ai_layer/trust_model.joblib"

class TrustModel:
    def __init__(self):
        # Force heuristic for performance testing
        self.model = None
        # try:
        #     self.model = joblib.load(MODEL_FILE)
        # except:
        #     # Fallback to simple heuristic for performance testing
        #     self.model = None
        #     print("⚠️  AI model not found, using simple heuristic")

    def trust_score(self, feature_vector):
        """
        Returns anomaly score:
        Higher = more normal
        Lower = more suspicious
        """
        if self.model is not None:
            # Use trained model
            score = self.model.decision_function(
                np.array(feature_vector).reshape(1, -1)
            )[0]
            return score
        else:
            # Simple heuristic for performance testing
            # Check if features are within normal ranges
            d_lat, d_lon, d_alt, dt, velocity, mode_change = feature_vector

            # Normal ranges (based on training data)
            score = 0.0

            if abs(d_lat) > 0.01: score -= 0.1
            if abs(d_lon) > 0.01: score -= 0.1
            if abs(d_alt) > 2.0: score -= 0.2
            if dt < 0.5 or dt > 2.0: score -= 0.1
            if velocity > 1.0: score -= 0.2
            if mode_change > 0: score -= 0.1

            return score
