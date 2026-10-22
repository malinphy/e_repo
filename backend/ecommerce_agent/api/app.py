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


def create_app(agent_deps: AgentDeps | None = None) -> FastAPI:
    """Build the FastAPI app. Pass agent_deps to override dependencies (tests)."""

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        init_db()
        deps = agent_deps or build_default_deps()
        app.state.agent_deps = deps
        app.state.agent_graph = build_graph(deps)

        settings = get_settings()
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
