from .decryptor import decrypt_payload
from .key_manager import key_manager
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.logging_config import logger
import time

class CryptoGate:
    """
    Cryptographic Gateway with Risk Assessment

    Implements the security boundary between encrypted commands and AI risk layer.
    Handles key validation, emergency protocols, and risk escalation.
    """

    def __init__(self):
        self.emergency_mode = False
        self.failsafe_commands = {
            b"RETURN_TO_LAUNCH",
            b"LAND",
            b"DISARM"
        }
        logger.info("CryptoGate initialized")

    def crypto_check(self, nonce: bytes, ciphertext: bytes) -> tuple[bool, bytes]:
        """
        Perform comprehensive cryptographic validation

        Returns: (success, payload) or (False, None)
        """
        logger.info("Performing comprehensive crypto validation")

        try:
            # Validate key hierarchy integrity
            if not key_manager.validate_key_hierarchy():
                logger.critical("Key hierarchy validation failed")
                self._enter_emergency_mode("key_hierarchy_corruption")
                return False, None

            # Attempt decryption
            payload = decrypt_payload(nonce, ciphertext)

            # Validate timestamp if present in payload
            if self._validate_timestamp(payload):
                logger.info("Crypto validation passed")
                return True, payload
            else:
                logger.warning("Timestamp validation failed")
                key_manager.update_risk_level("medium")
                return False, None

        except ValueError as e:
            error_msg = str(e)

            # Handle different failure types according to security matrix
            if "expired" in error_msg:
                logger.error("Key expired - initiating rotation")
                key_manager.rotate_session_key("expired_key")
                return False, None

            elif "revoked" in error_msg:
                logger.critical("Key revoked - emergency mode")
                self._enter_emergency_mode("key_revoked")
                return False, None

            elif "replay" in error_msg.lower():
                logger.warning("Replay attack detected")
                key_manager.update_risk_level("high")
                return False, None

            elif "emergency" in error_msg.lower():
                logger.critical("Cryptographic emergency - failsafe only")
                self.emergency_mode = True
                return False, None

            else:
                logger.error(f"Crypto validation failed: {e}")
                return False, None

        except Exception as e:
            logger.error(f"Unexpected crypto error: {e}")
            key_manager.update_risk_level("high")
            return False, None

    def _validate_timestamp(self, payload: bytes) -> bool:
        """
        Validate timestamp in payload if present
        Expected format: command|timestamp|metadata
        """
        try:
            payload_str = payload.decode('utf-8')
            parts = payload_str.split('|')

            if len(parts) >= 2:
                timestamp_str = parts[1]
                timestamp = float(timestamp_str)
                current_time = time.time()

                # Allow 30 second time skew
                if abs(current_time - timestamp) > 30:
                    logger.warning(f"Time skew detected: {abs(current_time - timestamp)}s")
                    return False

            return True

        except (ValueError, IndexError):
            # No timestamp present, allow
            return True

    def _enter_emergency_mode(self, reason: str):
        """Enter emergency mode - only failsafe commands allowed"""
        logger.critical(f"Entering emergency mode: {reason}")
        self.emergency_mode = True
        key_manager.revoke_session_key(reason)

    def is_emergency_mode(self) -> bool:
        """Check if system is in emergency mode"""
        return self.emergency_mode

    def get_failsafe_commands(self) -> set:
        """Get allowed commands in emergency mode"""
        return self.failsafe_commands

    def reset_emergency_mode(self):
        """Reset emergency mode (requires manual intervention)"""
        logger.warning("Emergency mode reset requested - manual verification required")
        # In production, this would require physical/admin verification
        self.emergency_mode = False

# Global crypto gate instance
crypto_gate = CryptoGate()

# Legacy compatibility function
def crypto_check(nonce, ciphertext):
    """Legacy function for backward compatibility"""
    return crypto_gate.crypto_check(nonce, ciphertext)
