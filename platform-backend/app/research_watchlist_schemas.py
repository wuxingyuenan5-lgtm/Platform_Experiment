from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ResearchWatchlistItem(BaseModel):
    code: str = Field(min_length=6, max_length=12)
    name: str = Field(min_length=1, max_length=128)
    group: str = Field(min_length=1, max_length=128)


class ReplaceResearchWatchlistRequest(BaseModel):
    items: list[ResearchWatchlistItem] = Field(max_length=200)
    expected_version: int = Field(alias="expectedVersion", ge=0)


class ResearchWatchlistResponse(BaseModel):
    items: list[ResearchWatchlistItem]
    row_version: int = Field(alias="rowVersion", ge=0)
    updated_at: datetime | None = Field(default=None, alias="updatedAt")
