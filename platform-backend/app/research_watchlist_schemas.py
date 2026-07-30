from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

ResearchMarket = Literal["a_share"]


class ResearchWatchlistItem(BaseModel):
    security_code: str = Field(alias="securityCode", pattern=r"^\d{6}$")
    security_name: str = Field(alias="securityName", min_length=1, max_length=128)
    group: str = Field(min_length=1, max_length=64)


class ResearchWatchlistResponse(BaseModel):
    market: ResearchMarket = "a_share"
    version: int = Field(ge=0)
    updated_at: datetime | None = Field(default=None, alias="updatedAt")
    items: list[ResearchWatchlistItem]


class ReplaceResearchWatchlistRequest(BaseModel):
    expected_version: int = Field(alias="expectedVersion", ge=0)
    items: list[ResearchWatchlistItem] = Field(max_length=200)

    @model_validator(mode="after")
    def validate_unique_codes(self) -> ReplaceResearchWatchlistRequest:
        codes = [item.security_code for item in self.items]
        if len(codes) != len(set(codes)):
            raise ValueError("watchlist securityCode values must be unique")
        return self
