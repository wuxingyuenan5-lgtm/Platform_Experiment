from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ResearchWatchlistItem(BaseModel):
    code: str = Field(min_length=5, max_length=12)
    name: str = Field(min_length=1, max_length=128)
    group: str = Field(min_length=1, max_length=128)


class ReplaceResearchWatchlistRequest(BaseModel):
    items: list[ResearchWatchlistItem] = Field(max_length=200)
    expected_version: int = Field(alias="expectedVersion", ge=0)


class ResearchWatchlistResponse(BaseModel):
    items: list[ResearchWatchlistItem]
    row_version: int = Field(alias="rowVersion", ge=0)
    updated_at: datetime | None = Field(default=None, alias="updatedAt")


class MarketLayoutRow(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    id: str = Field(min_length=1, max_length=128)
    name: str = Field(min_length=1, max_length=128)
    symbol: str = Field(min_length=1, max_length=64)
    tv_symbol: str = Field(default="", alias="tvSymbol", max_length=128)


class MarketLayoutGroup(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    label: str = Field(min_length=1, max_length=128)
    rows: list[MarketLayoutRow] = Field(max_length=200)


class ReplaceMarketLayoutRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    groups: list[MarketLayoutGroup] | None = Field(default=None, max_length=30)
    expected_version: int = Field(alias="expectedVersion", ge=0)

    @model_validator(mode="after")
    def bounded_unique_layout(self) -> ReplaceMarketLayoutRequest:
        groups = self.groups or []
        rows = [row for group in groups for row in group.rows]
        if len(rows) > 200 or len({row.id for row in rows}) != len(rows):
            raise ValueError("At most 200 distinct rows are allowed")
        if len({group.label for group in groups}) != len(groups):
            raise ValueError("Group labels must be unique")
        return self


class MarketLayoutResponse(BaseModel):
    groups: list[MarketLayoutGroup] | None
    row_version: int = Field(alias="rowVersion", ge=0)
    updated_at: datetime | None = Field(alias="updatedAt")
