"""ASGI server entrypoint."""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import uvicorn
from backend.app.main import app

if __name__ == "__main__":
    print("[*] Starting E-Commerce Agent API on http://127.0.0.1:8000 (Docs: http://127.0.0.1:8000/docs)")
    uvicorn.run("backend.app.main:app", host="127.0.0.1", port=8000, reload=True)
