"""ASGI server entrypoint."""
from __future__ import annotations

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import uvicorn
from backend.app.main import app

if __name__ == "__main__":
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))
    reload = os.environ.get("RELOAD", "false").lower() in ("true", "1") if host == "0.0.0.0" else True
    print(f"[*] Starting E-Commerce Agent API on http://{host}:{port} (Docs: http://{host}:{port}/docs)")
    uvicorn.run("backend.app.main:app", host=host, port=port, reload=reload)
