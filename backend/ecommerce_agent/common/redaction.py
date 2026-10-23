"""Redaction helpers so credentials never reach logs, API responses or the DB."""
from __future__ import annotations

import re

# ``api_key=...`` as it appears in a URL query string.
_QUERY_KEY = re.compile(r"(api_key=)[^&\s\"']+", re.IGNORECASE)
# Any provider token we know about: sk-..., long hex SerpAPI keys.
_TOKEN = re.compile(r"\b(sk-[A-Za-z0-9_\-]{8,}|[a-f0-9]{40,})\b")

MASK = "***"


def _configured_secrets() -> tuple[str, ...]:
    try:
        from .config import get_settings

        settings = get_settings()
    except Exception:  # noqa: BLE001 - redaction must never raise
        return ()
    values = (
        getattr(settings, "serpapi_api_key", "") or "",
        getattr(settings, "openai_api_key", "") or "",
            getattr(settings, "langsmith_api_key", "") or "",
        )
    # Longest first so a secret containing another one is masked wholly.
    # Short values would mask unrelated words, so ignore them.
    return tuple(
        sorted((v for v in values if len(v) >= 8), key=len, reverse=True)
    )


def redact(text: str) -> str:
    """Return ``text`` with configured secrets and key-shaped tokens masked."""
    if not text:
        return text
    for secret in _configured_secrets():
        if secret in text:
            text = text.replace(secret, MASK)
    text = _QUERY_KEY.sub(rf"\1{MASK}", text)
    return _TOKEN.sub(MASK, text)
