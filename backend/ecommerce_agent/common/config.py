"""Application settings (Singleton via lru_cache)."""
from __future__ import annotations

import logging
import os
from functools import lru_cache
from pathlib import Path

from dotenv import dotenv_values, load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict


REPO_ROOT = Path(__file__).resolve().parents[3]
DOTENV_PATH = REPO_ROOT / ".env"

logger = logging.getLogger(__name__)


def _override_enabled() -> bool:
    raw = os.environ.get("DOTENV_OVERRIDE", "1").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def load_env_file(
    dotenv_path: Path | None = None,
    override: bool | None = None,
) -> list[str]:
    """Load ``.env`` into ``os.environ``; return names that replaced a value.

    ``.env`` is the single source of truth for this project, so a stale shell
    or Windows-user variable must not silently win. Loading it into
    ``os.environ`` also fixes libraries that read keys directly from the
    environment instead of through ``Settings``.

    Pass ``DOTENV_OVERRIDE=0`` to let real environment variables take
    precedence again (useful in CI or containers).
    """
    path = dotenv_path or DOTENV_PATH
    if not path.is_file():
        return []
    if override is None:
        override = _override_enabled()

    file_values = {k: v for k, v in dotenv_values(path).items() if v is not None}
    replaced = [
        name
        for name, value in file_values.items()
        if override and os.environ.get(name) not in (None, value)
    ]

    load_dotenv(path, override=override)
    if replaced:
        logger.warning(
            "environment variables overridden by %s: %s",
            path,
            ", ".join(sorted(replaced)),
        )
    return sorted(replaced)


# Runs at import time on purpose: third-party clients read os.environ directly,
# so the file has to be in the environment before anything builds them.
OVERRIDDEN_ENV = load_env_file()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(DOTENV_PATH),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LLM
    llm_provider: str = "openai"
    openai_api_key: str = ""
    openai_default_model: str = "gpt-4o-mini"

    # SerpAPI
    serpapi_api_key: str = ""

    # SQLite
    sqlite_path: str = str(REPO_ROOT / "backend" / "data" / "ecommerce_agent.db")

    # Agent
    agent_default_engines: tuple[str, ...] = ("google_shopping", "amazon", "ebay", "walmart")

    # API
    api_host: str = "127.0.0.1"
    api_port: int = 8000


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


def mask_secret(value: str, keep: int = 4) -> str:
    """Render a secret for logs: presence, length and a short tail."""
    if not value:
        return "<not set>"
    if len(value) <= keep:
        return "*" * len(value)
    return f"***{value[-keep:]} (len={len(value)})"
