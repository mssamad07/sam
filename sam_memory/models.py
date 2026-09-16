"""
Data models for Sam's Tiered Memory system.
"""
import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class MemoryEntry(BaseModel):
    """Represents an atomic stored memory or persistent entity."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    category: str = Field(default="fact", description="Category e.g. profile, preference, fact, reminder")
    key: str = Field(description="Descriptive identifier or slot name")
    value: str = Field(description="Stored textual memory content")
    importance: int = Field(default=3, ge=1, le=5, description="Importance score 1-5")
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class MemorySearchResult(BaseModel):
    """Ranked search result combining memory entry with relevance score."""

    entry: MemoryEntry
    score: float = Field(ge=0.0, le=1.0)
