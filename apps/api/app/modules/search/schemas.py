from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class SavedSearchQuery(BaseModel):
    q: str | None = Field(default=None, max_length=120)
    source_type: Literal["rss", "api"] | None = None
    has_image: bool | None = None
    saved: bool | None = None
    read: bool | None = None
    include_hidden: bool | None = None


class SavedSearchCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    query: SavedSearchQuery


class SavedSearchRead(BaseModel):
    id: str
    name: str
    query: SavedSearchQuery
    created_at: datetime | None
