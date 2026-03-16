# tests/test_config.py
import os
import pytest

def test_config_reads_secret_key():
    # settings is a singleton — test that it reads SECRET_KEY from env
    from backend.config import settings
    assert settings.secret_key == os.environ["SECRET_KEY"]

def test_config_default_data_dir():
    # DATA_DIR is not set in conftest.py — verify the default is /data
    # Remove it if somehow set, check default
    saved = os.environ.pop("DATA_DIR", None)
    try:
        import importlib
        import backend.config as cfg_mod
        importlib.reload(cfg_mod)
        assert cfg_mod.settings.data_dir == "/data"
    finally:
        if saved:
            os.environ["DATA_DIR"] = saved
        importlib.reload(cfg_mod)

def test_config_default_tz():
    from backend.config import settings
    assert settings.tz == "Asia/Kolkata"
