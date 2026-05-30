from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class FeedItem(Base):
    __tablename__ = "feed_items"
    __table_args__ = (
        UniqueConstraint("source_id", "dedupe_key", name="uq_feed_item_source_dedupe"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id"), nullable=False, index=True)
    external_id: Mapped[str | None] = mapped_column(String(512))
    dedupe_key: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text)
    content_md: Mapped[str | None] = mapped_column(Text)
    url: Mapped[str | None] = mapped_column(Text)
    image_url: Mapped[str | None] = mapped_column(Text)
    author: Mapped[str | None] = mapped_column(String(255))
    language: Mapped[str | None] = mapped_column(String(32))
    published_at: Mapped[str | None] = mapped_column(DateTime(timezone=True))
    fetched_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())
    raw_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())


class UserItemState(Base):
    __tablename__ = "user_item_states"
    __table_args__ = (UniqueConstraint("user_id", "item_id", name="uq_user_item_state"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    item_id: Mapped[str] = mapped_column(ForeignKey("feed_items.id"), nullable=False, index=True)
    read_at: Mapped[str | None] = mapped_column(DateTime(timezone=True))
    saved_at: Mapped[str | None] = mapped_column(DateTime(timezone=True))
    hidden_at: Mapped[str | None] = mapped_column(DateTime(timezone=True))
    tags_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    updated_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())
