# tests/test_encryption.py
# Note: conftest.py already sets SECRET_KEY via setdefault before this module loads.
# The encryption tests are key-agnostic (round-trip tests) — they don't depend on a specific key value.
from backend.encryption import encrypt_password, decrypt_password

def test_encrypt_decrypt_roundtrip():
    plaintext = "my-secret-password"
    encrypted = encrypt_password(plaintext)
    assert encrypted != plaintext
    assert decrypt_password(encrypted) == plaintext

def test_encrypt_produces_different_tokens():
    encrypted1 = encrypt_password("same-password")
    encrypted2 = encrypt_password("same-password")
    # Fernet uses random IV — each token is different
    assert encrypted1 != encrypted2

def test_decrypt_none_returns_none():
    assert decrypt_password(None) is None

def test_empty_string():
    enc = encrypt_password("")
    assert decrypt_password(enc) == ""

def test_decrypt_invalid_token_raises():
    import pytest
    from cryptography.fernet import InvalidToken
    with pytest.raises(ValueError, match="invalid or key has changed"):
        decrypt_password("not-a-valid-fernet-token")
