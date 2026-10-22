"""High-level agent runner used by the API layer."""
from __future__ import annotations

from typing import Any

from ..common.config import get_settings
from ..common.db.engine import get_session_factory
from ..common.llm.factory import build_llm_provider
from ..repositories.agent_runs_repo import AgentRunRepository
from ..tools.serpapi.factory import build_all_engines
from .deps import AgentDeps
from .graph import build_graph


def build_default_deps() -> AgentDeps:
    """Construct production dependencies from settings (Factory + Singleton)."""
    settings = get_settings()

    def _llm_factory():
        provider = build_llm_provider(
            settings.llm_provider,
            api_key=settings.openai_api_key,
            default_model=settings.openai_default_model,
        )
        return provider.get_chat_model()

    engines = (
        build_all_engines(settings.serpapi_api_key) if settings.serpapi_api_key else {}
    )

    return AgentDeps(
        engines=engines,
        llm_factory=_llm_factory,
        session_factory=get_session_factory(),
    )


def run_agent(
    query: str,
    user_id: str | None = None,
    thread_id: int | None = None,
    deps: AgentDeps | None = None,
    graph: Any | None = None,
) -> dict[str, Any]:
    """Run the agent end-to-end and return the final state."""
    deps = deps or build_default_deps()

    session = deps.session_factory()
    try:
        run = AgentRunRepository(session).create(query=query, user_id=user_id)
        session.commit()
        run_id = run.id
    finally:
        session.close()

    compiled = graph or build_graph(deps)
    final_state = compiled.invoke(
        {
            "query": query,
            "user_id": user_id,
            "thread_id": thread_id,
            "run_id": run_id,
        },
        config={"recursion_limit": 25},
    )
    return dict(final_state)
