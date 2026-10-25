"""ProductCache model for caching SerpAPI search results with TTL."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, List
from sqlalchemy import DateTime, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column

from ..core.database import Base


class ProductCache(Base):
    __tablename__ = "products_cache"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    query_hash: Mapped[str] = mapped_column(
        String(64),
        index=True,
        nullable=False,
    )
    query: Mapped[str] = mapped_column(String(255), nullable=False)
    engine: Mapped[str] = mapped_column(String(50), nullable=False)
    results_json: Mapped[List[Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        index=True,
        nullable=False,
    )

    def is_expired(self) -> bool:
        """Check if cache record has expired."""
        now = datetime.now(self.expires_at.tzinfo) if self.expires_at.tzinfo else datetime.now(timezone.utc).replace(tzinfo=None)
        return now > self.expires_at

    def __repr__(self) -> str:
        return f"<ProductCache query='{self.query}' engine='{self.engine}' expires_at={self.expires_at}>"
