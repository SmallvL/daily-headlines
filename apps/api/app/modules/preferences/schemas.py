from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

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
    login_background_url: str | None = Field(default=None)

    @field_validator("login_background_url")
    @classmethod
    def validate_login_background_url(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if not (v.startswith("http://") or v.startswith("https://")):
            raise ValueError("URL must start with http:// or https://")
        return v
