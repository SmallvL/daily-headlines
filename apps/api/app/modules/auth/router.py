from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.auth.schemas import CurrentUser, LoginRequest, TokenPair
from app.modules.auth.service import auth_service
from app.shared.responses import ApiResponse

router = APIRouter()
bearer_scheme = HTTPBearer(auto_error=True)
BearerCredentials = Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)]
DbDep = Annotated[Session, Depends(get_db)]


def get_current_user(
    credentials: BearerCredentials,
    db: DbDep,
) -> CurrentUser:
    return auth_service.get_current_user(db, credentials.credentials)


CurrentUserDep = Annotated[CurrentUser, Depends(get_current_user)]


def require_admin(current_user: CurrentUserDep) -> CurrentUser:
    """Dependency that enforces admin role at the router level."""
    if "admin" not in (current_user.roles or []):
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限",
        )
    return current_user


AdminDep = Annotated[CurrentUser, Depends(require_admin)]


@router.post("/login", response_model=ApiResponse[TokenPair])
def login(payload: LoginRequest, db: DbDep) -> ApiResponse[TokenPair]:
    return ApiResponse(data=auth_service.login(db, payload))


@router.get("/me", response_model=ApiResponse[CurrentUser])
def me(current_user: CurrentUserDep) -> ApiResponse[CurrentUser]:
    return ApiResponse(data=current_user)
