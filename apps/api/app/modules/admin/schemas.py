from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

# ── User Management ──


class UserCreate(BaseModel):
    username: str = Field(min_length=2, max_length=64)
    password: str = Field(min_length=6, max_length=128)
    display_name: str = Field(min_length=1, max_length=120)
    email: EmailStr | None = None
    role: str = Field(default="user", pattern=r"^(admin|user)$")


class UserRead(BaseModel):
    id: str
    username: str
    email: str | None
    display_name: str
    role: str
    status: str
    last_login_at: datetime | None
    created_at: datetime | None


class UserRoleUpdate(BaseModel):
    role: str = Field(pattern=r"^(admin|user)$")


class UserStatusUpdate(BaseModel):
    status: str = Field(pattern=r"^(active|disabled)$")


class UserListPage(BaseModel):
    items: list[UserRead]
    total: int


# ── Group Management ──

class GroupCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = None


class GroupRead(BaseModel):
    id: str
    name: str
    description: str | None
    member_count: int
    created_by: str
    created_at: datetime | None


class GroupMemberRead(BaseModel):
    user_id: str
    username: str
    display_name: str
    joined_at: datetime | None


class GroupDetailRead(BaseModel):
    id: str
    name: str
    description: str | None
    members: list[GroupMemberRead]
    created_by: str
    created_at: datetime | None


class GroupMemberAdd(BaseModel):
    user_ids: list[str]


# ── Source Templates ──

class TemplateCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    type: str = Field(pattern=r"^(rss|api|web)$")
    endpoint: str
    config: dict = Field(default_factory=dict)
    description: str | None = None


class TemplateRead(BaseModel):
    id: str
    name: str
    type: str
    endpoint: str
    config: dict
    description: str | None
    created_by: str
    created_at: datetime | None


class TemplatePush(BaseModel):
    target_type: str = Field(pattern=r"^(user|group)$")
    target_ids: list[str]


# ── Push Subscriptions ──

class PushSubscriptionRead(BaseModel):
    id: str
    user_id: str
    template_id: str
    template_name: str
    source_id: str | None
    status: str
    pushed_by: str
    created_at: datetime | None


class PushAction(BaseModel):
    action: str = Field(pattern=r"^(accept|ignore)$")


# ── Audit Logs ──

class AuditLogRead(BaseModel):
    id: str
    actor_id: str
    action: str
    resource_type: str
    resource_id: str | None
    details: dict
    created_at: datetime | None


class AuditLogPage(BaseModel):
    items: list[AuditLogRead]
    total: int
    page: int
    page_size: int
