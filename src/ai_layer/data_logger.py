import csv
import os

LOG_FILE = "ai_layer/normal_flight_data.csv"

class FeatureLogger:
    def __init__(self):
        if not os.path.exists(LOG_FILE):
            with open(LOG_FILE, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "d_lat", "d_lon", "d_alt",
                    "dt", "velocity", "mode_change"
                ])

    def log(self, feature_vector):
        with open(LOG_FILE, "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(feature_vector)