"""API request/response schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    user_id: str | None = None


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    user_id: str | None = None


class ProductOut(BaseModel):
    title: str | None = None
    price: Any | None = None
    source: str | None = None
    link: str | None = None
    rating: Any | None = None
    reviews: Any | None = None
    engine: str | None = None


class SearchResponse(BaseModel):
    run_id: int | None = None
    query: str
    engines: list[str] = Field(default_factory=list)
    answer: str = ""
    products: list[ProductOut] = Field(default_factory=list)
    error: str | None = None


class ChatResponse(BaseModel):
    run_id: int | None = None
    answer: str = ""
    products: list[ProductOut] = Field(default_factory=list)
    error: str | None = None


class SearchHistoryOut(BaseModel):
    id: int
    user_id: str | None = None
    query: str
    engines: list[str] = Field(default_factory=list)
    result_count: int = 0
    created_at: datetime

    @classmethod
    def from_orm_row(cls, row: Any) -> "SearchHistoryOut":
        return cls(
            id=row.id,
            user_id=row.user_id,
            query=row.query,
            engines=[e for e in (row.engines or "").split(",") if e],
            result_count=row.result_count,
            created_at=row.created_at,
        )


class RunOut(BaseModel):
    id: int
    user_id: str | None = None
    query: str
    final_answer: str = ""
    status: str
    error: str | None = None
    created_at: datetime

    @classmethod
    def from_orm_row(cls, row: Any) -> "RunOut":
        return cls(
            id=row.id,
            user_id=row.user_id,
            query=row.query,
            final_answer=row.final_answer,
            status=row.status,
            error=row.error,
            created_at=row.created_at,
        )


class HealthOut(BaseModel):
    status: str = "ok"
    version: str
    engines: list[str] = Field(default_factory=list)
