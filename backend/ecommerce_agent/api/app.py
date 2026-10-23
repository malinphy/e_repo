"""FastAPI application factory."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from .. import __version__
from ..agent.deps import AgentDeps
from ..agent.graph import build_graph
from ..agent.runner import build_default_deps
from ..common.config import OVERRIDDEN_ENV, get_settings, mask_secret
from ..common.db.init_db import init_db
from . import health, root, routes_agent, routes_chat, routes_engines, routes_history

logger = logging.getLogger(__name__)


def _configure_langsmith(settings) -> None:
    """Enable LangSmith tracing when a key is present.

    LangChain/LangGraph runs are traced automatically once the environment is
    configured; doing it here (instead of relying on import-time env reads)
    keeps the setting explicit and testable. Tracing is off by default and
    only activates when ``langsmith_api_key`` is set and ``langsmith_tracing``
    is true.

    The API key is read from ``LANGSMITH_API_KEY`` in the environment (already
    loaded from ``.env``); ``langsmith.configure`` only controls the enabled
    flag and project name.
    """
    if not (settings.langsmith_api_key and settings.langsmith_tracing):
        return
    try:
        import os

        import langsmith

        os.environ.setdefault("LANGSMITH_API_KEY", settings.langsmith_api_key)
        langsmith.configure(
            enabled=True,
            project_name=settings.langsmith_project,
        )
        logger.info(
            "langsmith tracing enabled: project=%s key=%s",
            settings.langsmith_project,
            mask_secret(settings.langsmith_api_key),
        )
    except Exception as exc:  # noqa: BLE001 - tracing must never break startup
        logger.warning("failed to enable langsmith tracing: %s", exc)


def create_app(agent_deps: AgentDeps | None = None) -> FastAPI:
    """Build the FastAPI app. Pass agent_deps to override dependencies (tests)."""

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        init_db()
        deps = agent_deps or build_default_deps()
        app.state.agent_deps = deps
        app.state.agent_graph = build_graph(deps)

        settings = get_settings()
        _configure_langsmith(settings)
        logger.info(
            "config: llm_provider=%s openai_key=%s serpapi_key=%s engines=%d overridden_env=%s",
            settings.llm_provider,
            mask_secret(settings.openai_api_key),
            mask_secret(settings.serpapi_api_key),
            len(deps.engines),
            OVERRIDDEN_ENV or "none",
        )
        yield

    app = FastAPI(
        title="E-commerce Agent API",
        version=__version__,
        lifespan=lifespan,
    )

    app.include_router(root.router)
    app.include_router(health.router)
    app.include_router(routes_agent.router)
    app.include_router(routes_chat.router)
    app.include_router(routes_engines.router)
    app.include_router(routes_history.router)

    return app
