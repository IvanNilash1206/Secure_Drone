import pandas as pd
from sklearn.ensemble import IsolationForest
import joblib

DATA_FILE = "ai_layer/normal_flight_data.csv"
MODEL_FILE = "ai_layer/trust_model.joblib"

# Load normal data
df = pd.read_csv(DATA_FILE)

# Train Isolation Forest
model = IsolationForest(
    n_estimators=200,
    contamination=0.05,   # assume ≤5% anomalies
    random_state=42
)

model.fit(df.values)

# Save model
joblib.dump(model, MODEL_FILE)
print("✅ Trust model trained and saved")
