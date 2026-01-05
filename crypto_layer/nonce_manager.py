import os
import struct

NONCE_SIZE = 12  # AES-GCM standard

class NonceManager:
    def __init__(self):
        self.counter = 0

    def next_nonce(self):
        self.counter += 1
        return struct.pack(">Q", self.counter).rjust(NONCE_SIZE, b'\x00')

    def extract_counter(self, nonce):
        return struct.unpack(">Q", nonce[-8:])[0]
