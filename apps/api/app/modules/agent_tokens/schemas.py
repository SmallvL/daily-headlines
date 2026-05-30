from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

# ── Scope 定义 ──

AgentScope = Literal[
    "read:feed",      # 读取信息流
    "read:sources",   # 读取信息源
    "export:data",    # 导出数据
    "read:profile",   # 读取用户资料
]

# ── Token CRUD ──


class AgentTokenCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    scopes: list[AgentScope] = Field(default=["read:feed"])
    expires_in_days: int | None = Field(default=90, ge=1, le=365)


class AgentTokenRead(BaseModel):
    id: str
    name: str
    prefix: str
    scopes: list[str]
    enabled: bool
    last_used_at: datetime | None
    expires_at: datetime | None
    created_at: datetime | None
    revoked_at: datetime | None


class AgentTokenCreated(BaseModel):
    """创建后一次性返回的明文 token"""
    id: str
    name: str
    token: str  # 只在创建时返回一次
    prefix: str
    scopes: list[str]
    expires_at: datetime | None
    created_at: datetime | None


class AgentTokenList(BaseModel):
    items: list[AgentTokenRead]


# ── Export ──

ExportFormat = Literal["json", "csv"]
ExportType = Literal["feed", "sources"]


class ExportRequest(BaseModel):
    format: ExportFormat = "json"
    type: ExportType = "feed"
    query: str | None = None
    source_type: str | None = None
    limit: int = Field(default=100, ge=1, le=10000)


class ExportJobRead(BaseModel):
    id: str
    status: str  # pending | processing | completed | failed
    format: str
    type: str
    record_count: int | None
    file_path: str | None
    error_message: str | None
    created_at: datetime | None
    completed_at: datetime | None
