from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    type: Mapped[str] = mapped_column(String(32), nullable=False)
    endpoint: Mapped[str] = mapped_column(Text, nullable=False)
    config_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    created_by: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    last_fetch_at: Mapped[str | None] = mapped_column(DateTime(timezone=True))
    schedule_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    schedule_mode: Mapped[str] = mapped_column(String(16), nullable=False, default="interval")
    schedule_interval_minutes: Mapped[int | None] = mapped_column(Integer)
    cron_expression: Mapped[str | None] = mapped_column(String(64))
    cron_days_of_week: Mapped[str | None] = mapped_column(String(32))
    cron_hour: Mapped[int | None] = mapped_column(Integer)
    cron_minute: Mapped[int | None] = mapped_column(Integer)
    next_fetch_at: Mapped[str | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())
    deleted_at: Mapped[str | None] = mapped_column(DateTime(timezone=True))

    subscriptions: Mapped[list["Subscription"]] = relationship(back_populates="source", cascade="all, delete-orphan")
    fetch_logs: Mapped[list["SourceFetchLog"]] = relationship(back_populates="source", cascade="all, delete-orphan")
    feed_items: Mapped[list["FeedItem"]] = relationship(cascade="all, delete-orphan")


class Subscription(Base):
    __tablename__ = "subscriptions"
    __table_args__ = (UniqueConstraint("user_id", "source_id", name="uq_subscription_user_source"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id", ondelete="CASCADE"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    settings_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())

    source: Mapped["Source"] = relationship(back_populates="subscriptions")


class SourceFetchLog(Base):
    __tablename__ = "source_fetch_logs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    source: Mapped["Source"] = relationship(back_populates="fetch_logs")
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id", ondelete="CASCADE"), nullable=False, index=True)
    trigger: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    inserted_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    skipped_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[str | None] = mapped_column(Text)
    attempt: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    next_retry_at: Mapped[str | None] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[str] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[str | None] = mapped_column(DateTime(timezone=True))
