from datetime import datetime
from typing import Literal

from pydantic import BaseModel

Language = Literal["zh-CN", "en-US"]
Theme = Literal["light", "dark", "system"]
DefaultView = Literal["list", "grid", "compact"]


class UserPreferenceRead(BaseModel):
    user_id: str
    language: Language
    theme: Theme
    default_view: DefaultView
    updated_at: datetime | None


class UserPreferenceUpdate(BaseModel):
    language: Language | None = None
    theme: Theme | None = None
    default_view: DefaultView | None = None
