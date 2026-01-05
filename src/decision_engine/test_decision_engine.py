import unittest
import json
import os
from src.decision_engine.decision_engine import decision_engine
from src.decision_engine.safe_mode import trigger_safe_mode
from src.decision_engine.logger import log_event, LOG_FILE

class TestDecisionEngine(unittest.TestCase):

    def setUp(self):
        # Clear log file before each test
        if os.path.exists(LOG_FILE):
            os.remove(LOG_FILE)

    def test_valid_command(self):
        """Test 1: Valid command should be accepted"""
        result = decision_engine(
            crypto_valid=True,
            trust_score=0.12,
            trust_threshold=0.0,
            command={"type": "waypoint", "lat": 37.7749, "lon": -122.4194}
        )
        self.assertTrue(result)

        # Check log
        with open(LOG_FILE, "r") as f:
            log_entry = json.loads(f.readline())
            self.assertEqual(log_entry["status"], "ACCEPTED")
            self.assertIn("Crypto valid & AI trust high", log_entry["reason"])

    def test_tampered_packet(self):
        """Test 2: Tampered packet should be rejected with safe mode"""
        result = decision_engine(
            crypto_valid=False,
            trust_score=0.20,
            trust_threshold=0.0,
            command={"type": "waypoint", "lat": 37.7749, "lon": -122.4194}
        )
        self.assertFalse(result)

        # Check log
        with open(LOG_FILE, "r") as f:
            log_entry = json.loads(f.readline())
            self.assertEqual(log_entry["status"], "REJECTED")
            self.assertIn("Crypto verification failed", log_entry["reason"])

    def test_insider_misuse(self):
        """Test 3: Insider misuse (low trust) should be rejected"""
        result = decision_engine(
            crypto_valid=True,
            trust_score=-0.4,
            trust_threshold=0.0,
            command={"type": "waypoint", "lat": 37.7749, "lon": -122.4194}
        )
        self.assertFalse(result)

        # Check log
        with open(LOG_FILE, "r") as f:
            log_entry = json.loads(f.readline())
            self.assertEqual(log_entry["status"], "REJECTED")
            self.assertIn("AI trust below threshold", log_entry["reason"])

if __name__ == '__main__':
    unittest.main()