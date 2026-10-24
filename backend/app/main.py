"""FastAPI application initialization with CORS and API routes."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routes_chat import router as chat_router
from .api.routes_search import router as search_router
from .api.routes_cart import router as cart_router
from .core.database import Base, engine
import backend.app.models  # noqa: F401 - ensures all models are registered

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager: initializes SQLite database tables on startup."""
    logger.info("Initializing SQLite database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables verified.")
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

# Include Routers
app.include_router(chat_router)
app.include_router(search_router)
app.include_router(cart_router)


@app.get("/health", tags=["System"])
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "ecommerce_agent", "version": "1.0.0"}


@app.get("/", tags=["System"])
async def root():
    """API Root with documentation link."""
    return {
        "message": "Welcome to E-Commerce AI Agent API!",
        "docs_url": "/docs",
        "chat_endpoint": "/api/chat",
        "search_endpoint": "/api/search",
    }
