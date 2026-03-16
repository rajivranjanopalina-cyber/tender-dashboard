import sys
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    secret_key: str
    data_dir: str = "/data"
    tz: str = "Asia/Kolkata"

    model_config = {"env_file": ".env", "case_sensitive": False}

def _load_settings() -> Settings:
    try:
        return Settings()
    except Exception:
        print("FATAL: SECRET_KEY environment variable is not set. Cannot start.")
        sys.exit(1)

settings = _load_settings()
