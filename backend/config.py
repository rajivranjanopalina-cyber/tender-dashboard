import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Turso database
    turso_database_url: str = ""
    turso_auth_token: str = ""

    # Portal credential encryption
    secret_key: str = ""

    # Dashboard auth
    dashboard_password_hash: str = ""
    jwt_secret: str = ""

    # Scraper cron auth
    scrape_secret: str = ""

    # Vercel Blob
    blob_read_write_token: str = ""

    # Company info for proposals
    company_name: str = ""
    company_address: str = ""
    company_contact: str = ""

    # External renderer (future)
    external_renderer_url: str = ""

    # Timezone
    tz: str = "Asia/Kolkata"

    model_config = {"env_file": ".env", "case_sensitive": False}


def get_settings() -> Settings:
    return Settings()


settings = get_settings()
