"""FastAPI application initialization with CORS and API routes."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .api.routes_chat import router as chat_router
from .api.routes_search import router as search_router
from .api.routes_cart import router as cart_router
from .core.database import Base, engine
import backend.app.models  # noqa: F401 - ensures all models are registered

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIST = REPO_ROOT / "frontend" / "dist"

# Ensure SQLite database tables exist on module import (supports TestClient without lifespan context)
Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager: initializes SQLite database tables on startup."""
    logger.info("Initializing SQLite database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables verified.")
    from .agent.graph import get_compiled_shop_graph
    await get_compiled_shop_graph()
    logger.info("LangGraph AsyncSqliteSaver checkpointer initialized.")
    yield


app = FastAPI(
    title="E-Commerce AI Agent API",
    description="Agentic shopping assistant API powered by LangGraph, FastAPI, and SerpAPI (Walmart, eBay, Amazon, Google Shopping).",
    version="1.0.0",
    lifespan=lifespan,
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers (API endpoints take priority)
app.include_router(chat_router)
app.include_router(search_router)
app.include_router(cart_router)


@app.get("/health", tags=["System"])
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "ecommerce_agent", "version": "1.0.0"}


# Mount static assets if compiled frontend exists
if (FRONTEND_DIST / "assets").is_dir():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST / "assets")), name="assets")


@app.get("/", tags=["System"])
async def root(request: Request):
    """API Root: returns React SPA in browser or API metadata JSON if requested programmatically."""
    accept_header = request.headers.get("accept", "")
    if "text/html" in accept_header and (FRONTEND_DIST / "index.html").is_file():
        return FileResponse(FRONTEND_DIST / "index.html")
    return {
        "message": "Welcome to E-Commerce AI Agent API!",
        "docs_url": "/docs",
        "chat_endpoint": "/api/chat",
        "search_endpoint": "/api/search",
    }


# Catch-all for SPA client routing
@app.get("/{full_path:path}", include_in_schema=False)
async def serve_spa(full_path: str):
    file_path = FRONTEND_DIST / full_path
    if file_path.is_file():
        return FileResponse(file_path)
    if (FRONTEND_DIST / "index.html").is_file():
        return FileResponse(FRONTEND_DIST / "index.html")
    return JSONResponse(status_code=404, content={"detail": f"Path '{full_path}' not found."})
