from datetime import datetime
from typing import Literal
from urllib.parse import urlparse

from pydantic import BaseModel, field_validator

Language = Literal["zh-CN", "en-US"]
Theme = Literal["light", "dark", "system"]
DefaultView = Literal["list", "grid", "compact"]


class UserPreferenceRead(BaseModel):
    user_id: str
    language: Language
    theme: Theme
    default_view: DefaultView
    login_background_url: str | None = None
    updated_at: datetime | None


class UserPreferenceUpdate(BaseModel):
    language: Language | None = None
    theme: Theme | None = None
    default_view: DefaultView | None = None
    login_background_url: str | None = None

    @field_validator("login_background_url")
    @classmethod
    def validate_login_background_url(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        if any(ord(ch) < 32 for ch in v):
            raise ValueError("URL must not contain control characters")
        # Allow relative paths (e.g., /uploads/xxx.jpg) and absolute URLs
        if v.startswith("/"):
            return v
        parsed = urlparse(v)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("Invalid URL")
        return v
