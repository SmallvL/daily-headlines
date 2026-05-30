from sqlalchemy import Boolean, DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AgentToken(Base):
    __tablename__ = "agent_tokens"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(
        String(120), nullable=False
    )  # 用户可见的 token 名称
    token_hash: Mapped[str] = mapped_column(
        String(128), nullable=False, unique=True
    )  # SHA-256 hash
    prefix: Mapped[str] = mapped_column(
        String(10), nullable=False
    )  # token 前缀，用于显示 "dh_xxxx"
    scopes: Mapped[str] = mapped_column(
        Text, nullable=False, default="read"
    )  # 逗号分隔的 scope 列表
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_used_at: Mapped[str | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[str | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[str] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    revoked_at: Mapped[str | None] = mapped_column(DateTime(timezone=True))
