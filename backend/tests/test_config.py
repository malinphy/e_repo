"""Tests for application settings (Singleton + env loading + secret masking)."""
from __future__ import annotations

from pathlib import Path

from ecommerce_agent.common.config import get_settings, load_env_file, mask_secret


def _write_env(tmp_path: Path, content: str) -> Path:
    path = tmp_path / ".env"
    path.write_text(content, encoding="utf-8")
    return path


def test_settings_is_cached_singleton() -> None:
    assert get_settings() is get_settings()


def test_settings_reads_env_file() -> None:
    settings = get_settings()
    assert settings.llm_provider
    assert settings.openai_default_model
    assert settings.api_port > 0


def test_mask_secret_hides_middle() -> None:
    masked = mask_secret("sk-proj-abcdefghijklmnop")
    assert masked == "***mnop (len=24)"
    assert "abcdefghij" not in masked


def test_mask_secret_handles_empty_and_short_values() -> None:
    assert mask_secret("") == "<not set>"
    assert mask_secret("abc") == "***"


def test_load_env_file_overrides_stale_environment(tmp_path, monkeypatch) -> None:
    import os

    monkeypatch.setenv("OPENAI_API_KEY", "sk-stale-from-shell")
    path = _write_env(tmp_path, "OPENAI_API_KEY=sk-fresh-from-file\n")

    replaced = load_env_file(path, override=True)

    assert replaced == ["OPENAI_API_KEY"]
    assert os.environ["OPENAI_API_KEY"] == "sk-fresh-from-file"


def test_load_env_file_reports_only_values_it_replaced(tmp_path, monkeypatch) -> None:
    import os

    monkeypatch.delenv("SERPAPI_API_KEY", raising=False)
    path = _write_env(tmp_path, "SERPAPI_API_KEY=brand-new\nOTHER_KEY=x\n")

    replaced = load_env_file(path, override=True)

    assert replaced == []  # nothing existed before, so nothing was replaced
    assert os.environ["SERPAPI_API_KEY"] == "brand-new"


def test_load_env_file_can_defer_to_real_environment(tmp_path, monkeypatch) -> None:
    import os

    monkeypatch.setenv("OPENAI_API_KEY", "sk-from-shell")
    path = _write_env(tmp_path, "OPENAI_API_KEY=sk-from-file\n")

    replaced = load_env_file(path, override=False)

    assert replaced == []
    assert os.environ["OPENAI_API_KEY"] == "sk-from-shell"


def test_load_env_file_ignores_missing_file(tmp_path) -> None:
    assert load_env_file(tmp_path / "absent.env") == []
