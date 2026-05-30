from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

# ── LLM Provider ──


ApiFormat = Literal["openai", "anthropic"]


class LlmProviderCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    base_url: str = Field(min_length=1)
    api_key: str = Field(min_length=1)
    model: str = Field(min_length=1, max_length=120)
    api_format: ApiFormat = "openai"
    is_default: bool = False


class LlmProviderUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    base_url: str | None = None
    api_key: str | None = None
    model: str | None = None
    api_format: ApiFormat | None = None
    is_default: bool | None = None
    enabled: bool | None = None


class LlmProviderRead(BaseModel):
    id: str
    name: str
    base_url: str
    api_key_masked: str
    model: str
    api_format: str
    is_default: bool
    enabled: bool
    created_at: datetime | None


# ── Agent Draft ──

DraftStatus = Literal["drafting", "ready", "confirmed", "failed"]


class AgentDraftCreate(BaseModel):
    provider_id: str
    prompt_md: str = Field(min_length=1)


class AgentDraftRead(BaseModel):
    id: str
    user_id: str
    provider_id: str
    prompt_md: str
    status: str
    source_draft_json: str
    error_message: str | None
    llm_model: str
    llm_tokens_used: int
    llm_cost: float
    created_at: datetime | None
    updated_at: datetime | None


class AgentDraftUpdate(BaseModel):
    source_draft_json: str | None = None
    status: str | None = None


class AgentDraftConfirm(BaseModel):
    source_draft_json: str


# ── Source Draft (embedded in source_draft_json) ──


class SourceDraft(BaseModel):
    """Structure the LLM should produce."""

    name: str
    type: Literal["rss", "api", "web"] = "rss"
    endpoint: str
    config: dict = Field(default_factory=dict)
    schedule_enabled: bool = False
    schedule_interval_minutes: int | None = None


class LlmProviderList(BaseModel):
    items: list[LlmProviderRead]


class AgentDraftList(BaseModel):
    items: list[AgentDraftRead]
    total: int
