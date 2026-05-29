import base64
import hashlib
import logging
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.config import settings

logger = logging.getLogger("deploy_platform")


def _derive_key() -> bytes:
    """Derive a 32-byte AES-256 key from the JWT secret key using SHA-256."""
    return hashlib.sha256(settings.jwt_secret_key.encode("utf-8")).digest()


def encrypt_password(plain: str) -> str:
    """Encrypt a plaintext password using AES-256-GCM.

    Returns a base64-encoded string containing the 12-byte nonce followed
    by the ciphertext.
    """
    if not plain:
        return ""
    key = _derive_key()
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, plain.encode("utf-8"), None)
    return base64.b64encode(nonce + ciphertext).decode("utf-8")


def decrypt_password(cipher: str) -> str:
    """Decrypt a password previously encrypted with encrypt_password.

    Expects a base64-encoded string where the first 12 bytes are the nonce
    and the rest is the ciphertext.
    """
    if not cipher:
        return ""
    key = _derive_key()
    aesgcm = AESGCM(key)
    try:
        data = base64.b64decode(cipher)
        nonce = data[:12]
        ciphertext = data[12:]
        return aesgcm.decrypt(nonce, ciphertext, None).decode("utf-8")
    except Exception:
        logger.warning("Failed to decrypt password, returning raw value as fallback")
        return cipher
