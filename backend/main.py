"""ASGI entrypoint.

Preferred: uvicorn main:app --reload --app-dir backend
Convenience: python backend/main.py
"""
from __future__ import annotations

from ecommerce_agent.api.app import create_app
from ecommerce_agent.common.logging_setup import configure_logging

configure_logging()

app = create_app()


if __name__ == "__main__":
    import uvicorn

    from ecommerce_agent.common.config import get_settings

    settings = get_settings()
    uvicorn.run(app, host=settings.api_host, port=settings.api_port)
