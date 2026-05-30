from pydantic import BaseModel


class UserProfile(BaseModel):
    id: str
    username: str
    display_name: str
    roles: list[str]
    language: str = "zh-CN"
    theme: str = "system"
