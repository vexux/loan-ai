"""
Domain-Agnostic Cryptographic Data Protection.
Provides AES-256 GCM encryption and decryption for sensitive payload data at rest.
"""
import os
import base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# 256-bit key (in production, loaded from environment/vault)
_DEFAULT_KEY = os.environ.get("AGENT_ENCRYPTION_KEY", "0123456789abcdef0123456789abcdef")[:32].encode("utf-8")


class DataEncryption:
    def __init__(self, key: bytes = _DEFAULT_KEY) -> None:
        self.aesgcm = AESGCM(key)

    def encrypt(self, plaintext: str) -> str:
        """Encrypts plaintext string using AES-256-GCM and returns base64 string."""
        nonce = os.urandom(12)
        ciphertext = self.aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
        # Store nonce + ciphertext together
        payload = nonce + ciphertext
        return base64.b64encode(payload).decode("utf-8")

    def decrypt(self, encoded_ciphertext: str) -> str:
        """Decrypts base64 encoded ciphertext string."""
        data = base64.b64decode(encoded_ciphertext.encode("utf-8"))
        nonce = data[:12]
        ciphertext = data[12:]
        decrypted = self.aesgcm.decrypt(nonce, ciphertext, None)
        return decrypted.decode("utf-8")
