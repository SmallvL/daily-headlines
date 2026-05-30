from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.admin.schemas import (
    AuditLogPage,
    GroupCreate,
    GroupDetailRead,
    GroupMemberAdd,
    GroupRead,
    PushAction,
    PushSubscriptionRead,
    TemplateCreate,
    TemplatePush,
    TemplateRead,
    UserCreate,
    UserListPage,
    UserRead,
    UserRoleUpdate,
    UserStatusUpdate,
)
from app.modules.admin.service import admin_service
from app.modules.auth.router import CurrentUserDep
from app.shared.responses import ApiResponse

router = APIRouter()
DbDep = Annotated[Session, Depends(get_db)]

# ── User Management ──


@router.get("/users", response_model=ApiResponse[UserListPage])
def list_users(
    current_user: CurrentUserDep,
    db: DbDep,
    q: str | None = None,
) -> ApiResponse[UserListPage]:
    return ApiResponse(data=admin_service.list_users(db, current_user, q=q))


@router.patch("/users/{user_id}/role", response_model=ApiResponse[UserRead])
def update_user_role(
    user_id: str,
    payload: UserRoleUpdate,
    current_user: CurrentUserDep,
    db: DbDep,
) -> ApiResponse[UserRead]:
    return ApiResponse(data=admin_service.update_user_role(db, current_user, user_id, payload))


@router.patch("/users/{user_id}/status", response_model=ApiResponse[UserRead])
def update_user_status(
    user_id: str,
    payload: UserStatusUpdate,
    current_user: CurrentUserDep,
    db: DbDep,
) -> ApiResponse[UserRead]:
    return ApiResponse(data=admin_service.update_user_status(db, current_user, user_id, payload))


@router.post("/users", response_model=ApiResponse[UserRead])
def create_user(
    payload: UserCreate,
    current_user: CurrentUserDep,
    db: DbDep,
) -> ApiResponse[UserRead]:
    return ApiResponse(data=admin_service.create_user(db, current_user, payload))


# ── Group Management ──


@router.get("/groups", response_model=ApiResponse[list[GroupRead]])
def list_groups(
    current_user: CurrentUserDep,
    db: DbDep,
) -> ApiResponse[list[GroupRead]]:
    return ApiResponse(data=admin_service.list_groups(db, current_user))


@router.get("/groups/{group_id}", response_model=ApiResponse[GroupDetailRead])
def get_group(
    group_id: str,
    current_user: CurrentUserDep,
    db: DbDep,
) -> ApiResponse[GroupDetailRead]:
    return ApiResponse(data=admin_service.get_group(db, current_user, group_id))


@router.post("/groups", response_model=ApiResponse[GroupRead])
def create_group(
    payload: GroupCreate,
    current_user: CurrentUserDep,
    db: DbDep,
) -> ApiResponse[GroupRead]:
    return ApiResponse(data=admin_service.create_group(db, current_user, payload))


@router.delete("/groups/{group_id}", response_model=ApiResponse[dict[str, bool]])
def delete_group(
    group_id: str,
    current_user: CurrentUserDep,
    db: DbDep,
) -> ApiResponse[dict[str, bool]]:
    admin_service.delete_group(db, current_user, group_id)
    return ApiResponse(data={"deleted": True})


@router.post("/groups/{group_id}/members", response_model=ApiResponse[GroupDetailRead])
def add_group_members(
    group_id: str,
    payload: GroupMemberAdd,
    current_user: CurrentUserDep,
    db: DbDep,
) -> ApiResponse[GroupDetailRead]:
    return ApiResponse(data=admin_service.add_group_members(db, current_user, group_id, payload))


@router.delete("/groups/{group_id}/members/{user_id}", response_model=ApiResponse[dict[str, bool]])
def remove_group_member(
    group_id: str,
    user_id: str,
    current_user: CurrentUserDep,
    db: DbDep,
) -> ApiResponse[dict[str, bool]]:
    admin_service.remove_group_member(db, current_user, group_id, user_id)
    return ApiResponse(data={"removed": True})


# ── Source Templates ──


@router.get("/templates", response_model=ApiResponse[list[TemplateRead]])
def list_templates(
    current_user: CurrentUserDep,
    db: DbDep,
) -> ApiResponse[list[TemplateRead]]:
    return ApiResponse(data=admin_service.list_templates(db, current_user))


@router.post("/templates", response_model=ApiResponse[TemplateRead])
def create_template(
    payload: TemplateCreate,
    current_user: CurrentUserDep,
    db: DbDep,
) -> ApiResponse[TemplateRead]:
    return ApiResponse(data=admin_service.create_template(db, current_user, payload))


@router.delete("/templates/{template_id}", response_model=ApiResponse[dict[str, bool]])
def delete_template(
    template_id: str,
    current_user: CurrentUserDep,
    db: DbDep,
) -> ApiResponse[dict[str, bool]]:
    admin_service.delete_template(db, current_user, template_id)
    return ApiResponse(data={"deleted": True})


@router.post(
    "/templates/{template_id}/push",
    response_model=ApiResponse[list[PushSubscriptionRead]],
)
def push_template(
    template_id: str,
    payload: TemplatePush,
    current_user: CurrentUserDep,
    db: DbDep,
) -> ApiResponse[list[PushSubscriptionRead]]:
    return ApiResponse(data=admin_service.push_template(db, current_user, template_id, payload))


# ── Push Subscriptions (user side) ──


@router.get("/pushes/mine", response_model=ApiResponse[list[PushSubscriptionRead]])
def list_my_pushes(
    current_user: CurrentUserDep,
    db: DbDep,
) -> ApiResponse[list[PushSubscriptionRead]]:
    return ApiResponse(data=admin_service.list_my_pushes(db, current_user))


@router.patch("/pushes/{push_id}", response_model=ApiResponse[PushSubscriptionRead])
def act_on_push(
    push_id: str,
    payload: PushAction,
    current_user: CurrentUserDep,
    db: DbDep,
) -> ApiResponse[PushSubscriptionRead]:
    return ApiResponse(data=admin_service.act_on_push(db, current_user, push_id, payload))


# ── Audit Logs ──


@router.get("/audit-logs", response_model=ApiResponse[AuditLogPage])
def list_audit_logs(
    current_user: CurrentUserDep,
    db: DbDep,
    action: str | None = None,
    resource_type: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> ApiResponse[AuditLogPage]:
    return ApiResponse(
        data=admin_service.list_audit_logs(
            db, current_user,
            action=action, resource_type=resource_type,
            page=page, page_size=page_size,
        )
    )
