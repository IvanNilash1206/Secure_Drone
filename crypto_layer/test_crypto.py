import unittest
from cryptography.exceptions import InvalidTag
from src.crypto_layer.encryptor import encrypt_payload
from src.crypto_layer.decryptor import decrypt_payload

class TestCryptoLayer(unittest.TestCase):

    def test_modified_packet(self):
        """Test 1: Modified packet should raise InvalidTag exception"""
        nonce, ct = encrypt_payload(b"TEST_COMMAND")
        ct_tampered = ct[:-1] + b"\x00"  # tamper with last byte

        with self.assertRaises(InvalidTag):
            decrypt_payload(nonce, ct_tampered)

    def test_replay_attack(self):
        """Test 2: Replay attack should be detected"""
        nonce, ct = encrypt_payload(b"CMD")

        # First decrypt should work
        plaintext = decrypt_payload(nonce, ct)
        self.assertEqual(plaintext, b"CMD")

        # Second decrypt with same nonce/ct should raise ValueError
        with self.assertRaises(ValueError) as context:
            decrypt_payload(nonce, ct)
        self.assertIn("Replay attack detected", str(context.exception))

if __name__ == '__main__':
    unittest.main()