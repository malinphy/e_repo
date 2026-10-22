"""API request/response schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from ..services.engine_search import DEFAULT_NUM, MAX_NUM


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    user_id: str | None = None
    thread_id: int | None = Field(
        default=None, description="Associate this search with a chat thread (for history/memory)."
    )


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    user_id: str | None = None
    thread_id: int | None = Field(
        default=None, description="Continue this chat thread; loads and appends its history."
    )


class ProductOut(BaseModel):
    title: str | None = None
    price: Any | None = None
    source: str | None = None
    link: str | None = None
    rating: Any | None = None
    reviews: Any | None = None
    engine: str | None = None

    @classmethod
    def from_orm_row(cls, row: Any) -> "ProductOut":
        return cls(
            title=row.title,
            price=row.price,
            source=row.source,
            link=row.link,
            rating=row.rating,
            reviews=row.reviews,
            engine=row.engine,
        )


class SearchResponse(BaseModel):
    run_id: int | None = None
    thread_id: int | None = None
    query: str
    engines: list[str] = Field(default_factory=list)
    answer: str = ""
    products: list[ProductOut] = Field(default_factory=list)
    results: dict[str, list[ProductOut]] = Field(
        default_factory=dict, description="Same products grouped by marketplace."
    )
    engine_errors: dict[str, str] = Field(default_factory=dict)
    error: str | None = None


class ChatResponse(BaseModel):
    run_id: int | None = None
    thread_id: int | None = None
    query: str = ""
    answer: str = ""
    products: list[ProductOut] = Field(default_factory=list)
    results: dict[str, list[ProductOut]] = Field(
        default_factory=dict, description="Same products grouped by marketplace."
    )
    engine_errors: dict[str, str] = Field(default_factory=dict)
    error: str | None = None


class EngineSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    num: int = Field(default=DEFAULT_NUM, ge=1, le=MAX_NUM)


class MultiEngineSearchRequest(EngineSearchRequest):
    engines: list[str] | None = Field(
        default=None, description="Engines to query; omit to use every configured engine."
    )


class EnginesOut(BaseModel):
    engines: list[str] = Field(default_factory=list)


class EngineSearchResponse(BaseModel):
    engine: str
    query: str
    query_param: str | None = None
    count: int = 0
    products: list[ProductOut] = Field(default_factory=list)
    error: str | None = None


class MultiEngineSearchResponse(BaseModel):
    query: str
    engines: list[str] = Field(default_factory=list)
    count: int = 0
    results: dict[str, list[ProductOut]] = Field(default_factory=dict)
    errors: dict[str, str] = Field(default_factory=dict)


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


class EngineCallOut(BaseModel):
    engine: str
    result_count: int = 0
    error: str | None = None
    created_at: datetime | None = None

    @classmethod
    def from_orm_row(cls, row: Any) -> "EngineCallOut":
        return cls(
            engine=row.engine,
            result_count=row.result_count,
            error=row.error,
            created_at=row.created_at,
        )


class RunEnginesOut(BaseModel):
    run_id: int
    query: str
    engines: list[EngineCallOut] = Field(default_factory=list)


class RunEngineOut(BaseModel):
    run_id: int
    engine: str
    query: str = ""
    result_count: int = 0
    products: list[ProductOut] = Field(default_factory=list)
    error: str | None = None
    created_at: datetime | None = None


class HealthOut(BaseModel):
    status: str = "ok"
    version: str
    engines: list[str] = Field(default_factory=list)


# --- Chat thread / message schemas ---


class CreateThreadRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=64)
    title: str | None = Field(default=None, max_length=255)


class ChatThreadOut(BaseModel):
    id: int
    user_id: str
    title: str | None = None
    created_at: datetime

    @classmethod
    def from_orm_row(cls, row: Any) -> "ChatThreadOut":
        return cls(
            id=row.id,
            user_id=row.user_id,
            title=row.title,
            created_at=row.created_at,
        )


class SendMessageRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    user_id: str | None = None
    thread_id: int | None = None


class ChatMessageOut(BaseModel):
    id: int
    thread_id: int
    role: str
    content: str
    run_id: int | None = None
    created_at: datetime

    @classmethod
    def from_orm_row(cls, row: Any) -> "ChatMessageOut":
        return cls(
            id=row.id,
            thread_id=row.thread_id,
            role=row.role,
            content=row.content,
            run_id=row.run_id,
            created_at=row.created_at,
        )


class ThreadHistoryOut(BaseModel):
    thread_id: int
    messages: list[ChatMessageOut] = Field(default_factory=list)
