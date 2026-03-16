# tests/test_config.py
import os
import pytest
from pydantic import ValidationError

def test_config_reads_secret_key():
    from backend.config import settings
    assert settings.secret_key == "test-secret-key-32-bytes-padding!"

def test_config_default_data_dir(monkeypatch):
    monkeypatch.delenv("DATA_DIR", raising=False)
    from backend.config import Settings
    s = Settings(secret_key="any-key")
    assert s.data_dir == "/data"

def test_config_default_tz(monkeypatch):
    monkeypatch.delenv("TZ", raising=False)
    from backend.config import Settings
    s = Settings(secret_key="any-key")
    assert s.tz == "Asia/Kolkata"
