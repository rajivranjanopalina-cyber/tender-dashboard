import base64
import hashlib
from typing import Optional
from cryptography.fernet import Fernet
from backend.config import settings


def _get_fernet() -> Fernet:
    # Derive a 32-byte key via PBKDF2-HMAC-SHA256 (spec requirement), then base64-encode for Fernet
    # Salt is fixed (derived from key itself) — this is KDF for key stretching, not password storage
    salt = hashlib.sha256(b"tenderhub-static-salt").digest()[:16]
    key_bytes = hashlib.pbkdf2_hmac("sha256", settings.secret_key.encode(), salt, iterations=100_000)
    fernet_key = base64.urlsafe_b64encode(key_bytes)
    return Fernet(fernet_key)


def encrypt_password(plaintext: str) -> str:
    """Encrypt a password string. Returns Fernet token as string."""
    fernet = _get_fernet()
    return fernet.encrypt(plaintext.encode()).decode()


def decrypt_password(encrypted: Optional[str]) -> Optional[str]:
    """Decrypt a Fernet-encrypted password. Returns None if input is None."""
    if encrypted is None:
        return None
    fernet = _get_fernet()
    return fernet.decrypt(encrypted.encode()).decode()
