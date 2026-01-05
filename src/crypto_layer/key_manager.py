from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization
import os
import time
import struct
import secrets
from enum import Enum
from typing import Optional, Tuple, Dict, Any
from dataclasses import dataclass
from src.logging_config import logger

# Key file paths
ROOT_KEY_FILE = "crypto_layer/root_key.pem"
SESSION_KEY_FILE = "crypto_layer/session_key.bin"
KEY_METADATA_FILE = "crypto_layer/key_metadata.json"

# Key lifetimes (in seconds)
ROOT_KEY_LIFETIME = 365 * 24 * 3600  # 1 year
SESSION_KEY_LIFETIME = 30 * 60  # 30 minutes
GRACE_PERIOD = 5 * 60  # 5 minutes grace period for rotation

# Key rotation triggers
MAX_COMMANDS_PER_SESSION = 1000
ROTATION_CHECK_INTERVAL = 60  # Check every minute

class KeyState(Enum):
    ACTIVE = "active"
    GRACE = "grace"
    EXPIRED = "expired"
    REVOKED = "revoked"

class KeyType(Enum):
    ROOT = "root"
    SESSION = "session"

@dataclass
class KeyMetadata:
    key_type: KeyType
    state: KeyState
    created_at: float
    expires_at: float
    session_id: str
    command_count: int = 0
    last_rotation: float = 0.0
    risk_level: str = "low"

class KeyManager:
    """
    Hierarchical Key Management System

    Implements the secure key hierarchy:
    Root Key (KR) → Session Key (KS) → Message Keys (via nonces)

    Key Lifecycle: Provisioning → Activation → Usage → Rotation → Revocation → Destruction
    """

    def __init__(self):
        self._root_key: Optional[ec.EllipticCurvePrivateKey] = None
        self._session_key: Optional[bytes] = None
        self._metadata: Dict[str, KeyMetadata] = {}
        self._command_counter = 0
        self._last_rotation_check = time.time()

        # Ensure crypto directory exists
        os.makedirs("crypto_layer", exist_ok=True)

        # Load or initialize keys
        self._load_or_initialize_keys()

    def _load_or_initialize_keys(self):
        """Load existing keys or provision new ones"""
        try:
            # Check if root key exists
            if os.path.exists(ROOT_KEY_FILE):
                self._load_root_key()
                # Check if session key exists
                if os.path.exists(SESSION_KEY_FILE):
                    self._load_session_key()
                    self._load_metadata()
                    logger.info("Keys loaded successfully")
                else:
                    logger.warning("Root key found but session key missing, deriving new session key")
                    self._derive_session_key()
                    self._save_metadata()
            else:
                logger.warning("No existing keys found, provisioning new root key")
                self._provision_root_key()
                self._derive_session_key()
                self._save_metadata()
        except Exception as e:
            logger.error(f"Error loading/initializing keys: {e}")
            # If anything fails, provision fresh keys
            logger.warning("Provisioning fresh keys due to error")
            self._provision_root_key()
            self._derive_session_key()
            self._save_metadata()

    def _provision_root_key(self):
        """Provision new root key (KR) - long-term trust anchor"""
        logger.info("Provisioning new root key (KR)")
        self._root_key = ec.generate_private_key(ec.SECP256R1())

        # Save root key encrypted (in production, this should be in a secure element)
        pem = self._root_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()  # In production: use secure encryption
        )

        with open(ROOT_KEY_FILE, "wb") as f:
            f.write(pem)

        # Initialize root key metadata
        self._metadata["root"] = KeyMetadata(
            key_type=KeyType.ROOT,
            state=KeyState.ACTIVE,
            created_at=time.time(),
            expires_at=time.time() + ROOT_KEY_LIFETIME,
            session_id="root"
        )

        logger.info("Root key provisioned successfully")

    def _load_root_key(self):
        """Load root key from secure storage"""
        with open(ROOT_KEY_FILE, "rb") as f:
            pem_data = f.read()

        self._root_key = serialization.load_pem_private_key(pem_data, password=None)
        logger.debug("Root key loaded")

    def _derive_session_key(self, session_id: Optional[str] = None) -> bytes:
        """Derive session key (KS) from root key using HKDF"""
        if session_id is None:
            session_id = secrets.token_hex(16)

        logger.info(f"Deriving new session key for session: {session_id}")

        # Use HKDF to derive session key from root key
        root_key_bytes = self._root_key.private_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )

        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=32,  # AES-256
            salt=None,
            info=b"session-key-derivation"
        )

        session_key = hkdf.derive(root_key_bytes + session_id.encode())

        # Save session key (in production: RAM only, never to disk)
        with open(SESSION_KEY_FILE, "wb") as f:
            f.write(session_key)

        self._session_key = session_key

        # Initialize session key metadata
        self._metadata["session"] = KeyMetadata(
            key_type=KeyType.SESSION,
            state=KeyState.ACTIVE,
            created_at=time.time(),
            expires_at=time.time() + SESSION_KEY_LIFETIME,
            session_id=session_id,
            command_count=0,
            risk_level="low"
        )

        logger.info("Session key derived and activated")
        return session_key

    def _load_session_key(self):
        """Load session key from temporary storage"""
        with open(SESSION_KEY_FILE, "rb") as f:
            self._session_key = f.read()
        logger.debug("Session key loaded")

    def _load_metadata(self):
        """Load key metadata"""
        import json
        try:
            with open(KEY_METADATA_FILE, "r") as f:
                data = json.load(f)
                for key, meta in data.items():
                    self._metadata[key] = KeyMetadata(
                        key_type=KeyType(meta["key_type"]),
                        state=KeyState(meta["state"]),
                        created_at=meta["created_at"],
                        expires_at=meta["expires_at"],
                        session_id=meta["session_id"],
                        command_count=meta.get("command_count", 0),
                        last_rotation=meta.get("last_rotation", 0.0),
                        risk_level=meta.get("risk_level", "low")
                    )

            # Ensure root metadata exists if root key is loaded
            if "root" not in self._metadata and self._root_key:
                logger.warning("Root key exists but metadata missing, recreating root metadata")
                self._metadata["root"] = KeyMetadata(
                    key_type=KeyType.ROOT,
                    state=KeyState.ACTIVE,
                    created_at=time.time() - 100,  # Assume it was created recently
                    expires_at=time.time() + ROOT_KEY_LIFETIME,
                    session_id="root"
                )
                self._save_metadata()

        except FileNotFoundError:
            pass

    def _save_metadata(self):
        """Save key metadata"""
        import json
        data = {}
        for key, metadata in self._metadata.items():
            data[key] = {
                "key_type": metadata.key_type.value,
                "state": metadata.state.value,
                "created_at": metadata.created_at,
                "expires_at": metadata.expires_at,
                "session_id": metadata.session_id,
                "command_count": getattr(metadata, 'command_count', 0),
                "last_rotation": getattr(metadata, 'last_rotation', 0.0),
                "risk_level": getattr(metadata, 'risk_level', 'low')
            }
        with open(KEY_METADATA_FILE, "w") as f:
            json.dump(data, f, indent=2)

    def get_active_session_key(self) -> bytes:
        """Get the currently active session key, checking for rotation needs"""
        self._check_rotation_triggers()

        if not self._session_key:
            raise ValueError("No active session key")

        metadata = self._metadata.get("session")
        if not metadata:
            raise ValueError("Session key metadata missing")

        current_time = time.time()

        # Check if key is expired
        if current_time > metadata.expires_at:
            logger.error("Session key expired")
            raise ValueError("Session key expired - rotation required")

        # Check if key is revoked
        if metadata.state == KeyState.REVOKED:
            logger.error("Session key revoked")
            raise ValueError("Session key revoked")

        return self._session_key

    def _check_rotation_triggers(self):
        """Check if key rotation is needed based on various triggers"""
        current_time = time.time()

        # Only check periodically to avoid overhead
        if current_time - self._last_rotation_check < ROTATION_CHECK_INTERVAL:
            return

        self._last_rotation_check = current_time
        metadata = self._metadata.get("session")

        if not metadata:
            return

        rotation_needed = False
        reason = ""

        # Time-based rotation
        if current_time > metadata.expires_at - GRACE_PERIOD:
            rotation_needed = True
            reason = "time-based"

        # Command count rotation
        elif metadata.command_count >= MAX_COMMANDS_PER_SESSION:
            rotation_needed = True
            reason = "command-count"

        # Risk-based rotation (placeholder for AI integration)
        elif metadata.risk_level in ["high", "critical"]:
            rotation_needed = True
            reason = "risk-escalation"

        if rotation_needed:
            logger.warning(f"Key rotation triggered: {reason}")
            self.rotate_session_key(reason)

    def rotate_session_key(self, reason: str = "manual"):
        """Perform seamless session key rotation"""
        logger.info(f"Initiating session key rotation: {reason}")

        old_metadata = self._metadata.get("session")
        if old_metadata:
            # Enter grace period for old key
            old_metadata.state = KeyState.GRACE
            old_metadata.expires_at = time.time() + GRACE_PERIOD

        # Derive new session key
        new_session_id = secrets.token_hex(16)
        self._derive_session_key(new_session_id)

        # Update metadata
        new_metadata = self._metadata["session"]
        new_metadata.last_rotation = time.time()

        self._save_metadata()

        logger.info("Session key rotation completed successfully")

    def revoke_session_key(self, reason: str = "emergency"):
        """Emergency key revocation"""
        logger.critical(f"Emergency session key revocation: {reason}")

        metadata = self._metadata.get("session")
        if metadata:
            metadata.state = KeyState.REVOKED
            self._save_metadata()

        # Securely erase session key from memory and disk
        self._destroy_session_key()

        logger.critical("Session key revoked and destroyed")

    def _destroy_session_key(self):
        """Securely destroy session key"""
        logger.info("Destroying session key")

        # Overwrite in memory
        if self._session_key:
            self._session_key = secrets.token_bytes(32)
            self._session_key = None

        # Overwrite on disk
        try:
            with open(SESSION_KEY_FILE, "wb") as f:
                f.write(secrets.token_bytes(32))
            os.remove(SESSION_KEY_FILE)
        except FileNotFoundError:
            pass

        # Reset command counter
        self._command_counter = 0

        logger.info("Session key destroyed securely")

    def increment_command_counter(self):
        """Increment command counter for rotation tracking"""
        self._command_counter += 1
        metadata = self._metadata.get("session")
        if metadata:
            metadata.command_count = self._command_counter
            self._save_metadata()

    def update_risk_level(self, risk_level: str):
        """Update risk level for rotation decisions"""
        metadata = self._metadata.get("session")
        if metadata:
            metadata.risk_level = risk_level
            self._save_metadata()
            logger.info(f"Risk level updated to: {risk_level}")

    def get_key_status(self) -> Dict[str, Any]:
        """Get comprehensive key status for monitoring"""
        status = {}
        current_time = time.time()

        for key_name, metadata in self._metadata.items():
            status[key_name] = {
                "state": metadata.state.value,
                "created_at": metadata.created_at,
                "expires_at": metadata.expires_at,
                "time_to_expiry": metadata.expires_at - current_time,
                "session_id": metadata.session_id,
                "command_count": getattr(metadata, 'command_count', 0),
                "risk_level": getattr(metadata, 'risk_level', 'unknown')
            }

        return status

    def validate_key_hierarchy(self) -> bool:
        """Validate the integrity of the key hierarchy"""
        try:
            # Check root key exists and is valid
            if not self._root_key:
                return False

            # Check session key exists and is valid
            if not self._session_key or len(self._session_key) != 32:
                return False

            # Check metadata consistency
            root_meta = self._metadata.get("root")
            session_meta = self._metadata.get("session")

            if not root_meta or not session_meta:
                return False

            if root_meta.state != KeyState.ACTIVE:
                return False

            current_time = time.time()
            if current_time > root_meta.expires_at:
                return False

            # Session key can be in grace period
            if session_meta.state not in [KeyState.ACTIVE, KeyState.GRACE]:
                return False

            return True

        except Exception as e:
            logger.error(f"Key hierarchy validation failed: {e}")
            return False

# Global key manager instance
key_manager = KeyManager()

# Legacy compatibility functions
def generate_key():
    """Legacy function - now delegates to key manager"""
    logger.warning("Using legacy generate_key - consider migrating to KeyManager")
    return key_manager._derive_session_key()

def load_key():
    """Legacy function - now returns active session key"""
    logger.warning("Using legacy load_key - consider migrating to KeyManager")
    return key_manager.get_active_session_key()

if __name__ == "__main__":
    # Initialize key hierarchy
    km = KeyManager()
    print("✅ Key hierarchy initialized")
    print(f"Key status: {km.get_key_status()}")
