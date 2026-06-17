from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl, field_validator, model_validator

from app.modules.feed.schemas import FeedItemRead

SourceType = Literal["rss", "api", "web"]
ScheduleMode = Literal["interval", "cron"]
AuthType = Literal["none", "cookie", "bearer", "api_key", "custom_headers", "qrcode", "plugin"]


class AuthConfig(BaseModel):
    """Authentication configuration for a source."""
    auth_type: AuthType = "none"
    cookies: str | None = None  # For cookie auth
    token: str | None = None  # For bearer auth
    header_name: str | None = None  # For api_key auth (custom header name)
    api_key: str | None = None  # For api_key auth
    headers: dict[str, str] | None = None  # For custom_headers auth
    plugin_id: str | None = None  # For plugin-based auth
    plugin_credentials: dict | None = None  # Plugin-specific credentials
    plugin_config: dict | None = None  # Plugin-specific configuration


class SourceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    type: SourceType = "rss"
    endpoint: HttpUrl
    config: dict = Field(default_factory=dict)
    auth: AuthConfig = Field(default_factory=AuthConfig)
    schedule_enabled: bool = False
    schedule_mode: ScheduleMode = "interval"
    schedule_interval_minutes: int | None = Field(default=None, ge=5, le=10080)
    cron_expression: str | None = None
    cron_days_of_week: str | None = None
    cron_hour: int | None = Field(default=None, ge=0, le=23)
    cron_minute: int | None = Field(default=None, ge=0, le=59)

    @field_validator("name")
    @classmethod
    def sanitize_name(cls, v: str) -> str:
        allowed = v.strip()[:160]
        # Strip HTML tags for XSS prevention
        allowed = allowed.replace("<", "&lt;").replace(">", "&gt;")
        return allowed

    @model_validator(mode="after")
    def validate_schedule(self) -> "SourceCreate":
        if self.schedule_enabled:
            if (
                self.schedule_mode == "interval"
                and self.schedule_interval_minutes is None
            ):
                raise ValueError(
                    "schedule_interval_minutes is required"
                    " when schedule mode is interval"
                )
            if self.schedule_mode == "cron":
                if self.cron_hour is None or self.cron_minute is None:
                    raise ValueError(
                        "cron_hour and cron_minute are required"
                        " when schedule mode is cron"
                    )
        return self


class SourceRead(BaseModel):
    id: str
    name: str
    type: str
    endpoint: str
    status: str
    last_fetch_at: datetime | None
    schedule_enabled: bool
    schedule_mode: str = "interval"
    schedule_interval_minutes: int | None
    cron_expression: str | None = None
    cron_days_of_week: str | None = None
    cron_hour: int | None = None
    cron_minute: int | None = None
    next_fetch_at: datetime | None
    created_at: datetime | None
    auth_type: AuthType = "none"
    has_auth: bool = False
    plugin_id: str | None = None
    plugin_name: str | None = None
    plugin_user_info: dict | None = None


class SourceFetchLogRead(BaseModel):
    id: str
    source_id: str
    trigger: str
    status: str
    inserted_count: int
    skipped_count: int
    error_message: str | None
    attempt: int = 1
    max_attempts: int = 3
    next_retry_at: datetime | None = None
    started_at: datetime
    finished_at: datetime | None


class SourceScheduleUpdate(BaseModel):
    schedule_enabled: bool
    schedule_mode: ScheduleMode = "interval"
    schedule_interval_minutes: int | None = Field(default=None, ge=5, le=10080)
    cron_expression: str | None = None
    cron_days_of_week: str | None = None
    cron_hour: int | None = Field(default=None, ge=0, le=23)
    cron_minute: int | None = Field(default=None, ge=0, le=59)

    @model_validator(mode="after")
    def validate_schedule(self) -> "SourceScheduleUpdate":
        if self.schedule_enabled:
            if (
                self.schedule_mode == "interval"
                and self.schedule_interval_minutes is None
            ):
                raise ValueError(
                    "schedule_interval_minutes is required"
                    " when schedule mode is interval"
                )
            if self.schedule_mode == "cron":
                if self.cron_hour is None or self.cron_minute is None:
                    raise ValueError(
                        "cron_hour and cron_minute are required"
                        " when schedule mode is cron"
                    )
        return self


class SourceUpdate(BaseModel):
    """Partial update for source details (name, endpoint, config, type, auth)."""
    name: str | None = Field(default=None, min_length=1, max_length=160)
    type: SourceType | None = None
    endpoint: HttpUrl | None = None
    config: dict | None = None
    auth: AuthConfig | None = None


class SourceTemplate(BaseModel):
    """Exportable source template (no IDs, no timestamps, no auth secrets)."""
    name: str
    type: SourceType
    endpoint: str
    config: dict = Field(default_factory=dict)
    auth_type: AuthType = "none"
    schedule_enabled: bool = False
    schedule_mode: ScheduleMode = "interval"
    schedule_interval_minutes: int | None = None
    cron_expression: str | None = None
    cron_days_of_week: str | None = None
    cron_hour: int | None = None
    cron_minute: int | None = None


class SourceTestRequest(BaseModel):
    name: str = Field(default="Preview", max_length=160)
    type: SourceType = "rss"
    endpoint: HttpUrl
    config: dict = Field(default_factory=dict)
    auth: AuthConfig = Field(default_factory=AuthConfig)


class SourceTestResult(BaseModel):
    title: str | None = None
    items: list[FeedItemRead]


class FetchResult(BaseModel):
    log_id: str
    inserted: int
    skipped: int
    items: list[FeedItemRead]


class GlobalFetchLogQuery(BaseModel):
    source_id: str | None = None
    status: str | None = None
    trigger: str | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class GlobalFetchLogPage(BaseModel):
    items: list[SourceFetchLogRead]
    total: int
    page: int
    page_size: int
