from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

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
