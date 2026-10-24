"""Database initialization script: creates all SQLite tables."""
from __future__ import annotations

import sys
from pathlib import Path

# Add project root to sys.path so it can be run directly: `python backend/app/init_db.py`
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from sqlalchemy import inspect
from backend.app.core.config import get_settings
from backend.app.core.database import Base, engine
import backend.app.models  # noqa: F401 - ensures all models are registered with Base.metadata


def init_database() -> None:
    """Create all registered database tables in SQLite."""
    settings = get_settings()
    print(f"[*] Initializing SQLite database at: {settings.sqlite_db_path}")

    try:
        # Create all tables
        Base.metadata.create_all(bind=engine)
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()

        print("[+] SQLite tables created successfully!")
        print("[*] Created tables:")
        for table in sorted(existing_tables):
            print(f"    - {table}")

    except Exception as exc:
        print(f"[!] Error creating SQLite tables: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    init_database()
