"""Application configuration using Pydantic Settings."""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[3]
DOTENV_PATH = REPO_ROOT / ".env"
SQLITE_DIR = REPO_ROOT / "backend" / "data"
SQLITE_PATH = SQLITE_DIR / "ecommerce.db"

# Force load .env into os.environ with override=True to overwrite stale Windows user/system env vars
if DOTENV_PATH.is_file():
    load_dotenv(dotenv_path=DOTENV_PATH, override=True)
else:
    load_dotenv(override=True)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(DOTENV_PATH) if DOTENV_PATH.is_file() else ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database configuration (SQLite only)
    sqlite_db_path: str = str(SQLITE_PATH)

    # API Keys
    OPENAI_API_KEY: str = ""
    SERPAPI_API_KEY: str = ""
    LANGSMITH_API_KEY: str = ""
    LANGSMITH_TRACING: bool = False
    LANGSMITH_PROJECT: str = "ecommerce-agent"

    @property
    def sync_database_url(self) -> str:
        """Returns SQLite database URL."""
        # Ensure directory exists
        Path(self.sqlite_db_path).parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{self.sqlite_db_path}"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
