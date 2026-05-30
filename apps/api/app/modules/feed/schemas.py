from datetime import datetime, timezone

from pydantic import BaseModel, Field, field_serializer


class FeedItemCreate(BaseModel):
    source_id: str
    external_id: str | None = None
    title: str
    summary: str | None = None
    content_md: str | None = None
    url: str | None = None
    image_url: str | None = None
    author: str | None = None
    language: str | None = None
    published_at: datetime | None = None
    raw_json: dict = Field(default_factory=dict)


class FeedItemRead(BaseModel):
    id: str
    source_id: str
    source_name: str = ""
    title: str
    summary: str | None
    url: str | None
    image_url: str | None
    author: str | None
    published_at: datetime | None
    fetched_at: datetime | None
    is_read: bool = False
    is_saved: bool = False
    is_hidden: bool = False

    @field_serializer("published_at", "fetched_at")
    @classmethod
    def _ensure_utc(cls, v: datetime | None) -> str | None:
        """Serialize datetimes with explicit UTC suffix so JS `new Date()` parses correctly."""
        if v is None:
            return None
        # If naive (no tzinfo), assume UTC (SQLite stores without tz)
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        return v.isoformat()


class FeedItemList(BaseModel):
    items: list[FeedItemRead]
    total: int = 0
    page: int = 1
    page_size: int = 50


class ItemStateRead(BaseModel):
    item_id: str
    is_read: bool
    is_saved: bool
    is_hidden: bool
