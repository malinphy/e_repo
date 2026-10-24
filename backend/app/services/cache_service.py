"""Product cache service with SQLite TTL persistence."""
from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from sqlalchemy import delete, select

from ..core.database import SessionLocal
from ..models.product_cache import ProductCache
from ..schemas.product import Product

logger = logging.getLogger(__name__)


class ProductCacheService:
    """Manages cached SerpAPI search results with configurable TTL."""

    DEFAULT_TTL_HOURS = 24

    @staticmethod
    def compute_hash(query: str, engine: str) -> str:
        """Create deterministic SHA256 hash for query and engine combination."""
        normalized = f"{engine.strip().lower()}:{query.strip().lower()}"
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    @classmethod
    def get(cls, query: str, engine: str) -> Optional[List[Product]]:
        """Fetch unexpired cached products for a query and engine."""
        query_hash = cls.compute_hash(query, engine)
        db = SessionLocal()
        try:
            record = db.scalar(
                select(ProductCache).where(ProductCache.query_hash == query_hash)
            )
            if not record:
                return None

            if record.is_expired():
                logger.info("Cache expired for [engine=%s, query='%s'], deleting.", engine, query)
                db.execute(delete(ProductCache).where(ProductCache.id == record.id))
                db.commit()
                return None

            logger.info("Cache hit for [engine=%s, query='%s'] (%d items)", engine, query, len(record.results_json))
            return [Product.model_validate(p) for p in record.results_json]
        except Exception as exc:
            logger.warning("Cache retrieval failed for '%s': %s", query, exc)
            return None
        finally:
            db.close()

    @classmethod
    def set(
        cls,
        query: str,
        engine: str,
        products: List[Product],
        ttl_hours: int = DEFAULT_TTL_HOURS,
    ) -> None:
        """Save or overwrite search results in cache with TTL."""
        if not products:
            return

        query_hash = cls.compute_hash(query, engine)
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(hours=ttl_hours)
        serialized_products = [p.model_dump() for p in products]

        db = SessionLocal()
        try:
            # Delete existing if any (upsert simulation in SQLite)
            db.execute(delete(ProductCache).where(ProductCache.query_hash == query_hash))

            new_record = ProductCache(
                query_hash=query_hash,
                query=query.strip(),
                engine=engine.strip().lower(),
                results_json=serialized_products,
                created_at=now,
                expires_at=expires_at,
            )
            db.add(new_record)
            db.commit()
            logger.info("Cached %d products for [engine=%s, query='%s'] until %s", len(products), engine, query, expires_at)
        except Exception as exc:
            db.rollback()
            logger.warning("Cache write failed for '%s': %s", query, exc)
        finally:
            db.close()
