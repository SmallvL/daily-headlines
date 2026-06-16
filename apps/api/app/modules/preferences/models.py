from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class UserPreference(Base):
    __tablename__ = "user_preferences"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True, unique=True
    )
    language: Mapped[str] = mapped_column(
        String(10), nullable=False, default="zh-CN"
    )  # zh-CN | en-US
    theme: Mapped[str] = mapped_column(
        String(20), nullable=False, default="light"
    )  # light | dark | system
    default_view: Mapped[str] = mapped_column(
        String(20), nullable=False, default="list"
    )  # list | grid | compact
    login_background_url: Mapped[str | None] = mapped_column(
        Text, nullable=True, default=None
    )
    created_at: Mapped[str] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[str] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
