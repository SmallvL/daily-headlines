from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.modules.auth.router import CurrentUserDep
from app.modules.preferences import service as pref_service
from app.modules.preferences.schemas import UserPreferenceRead, UserPreferenceUpdate
from app.modules.users.models import User
from app.shared.responses import ApiResponse

router = APIRouter()

DbDep = Annotated[Session, Depends(get_db)]


@router.get("", response_model=ApiResponse[UserPreferenceRead])
def get_preference(
    db: DbDep,
    user: CurrentUserDep,
):
    """Get current user's preferences."""
    result = pref_service.get_or_create_preference(db, user)
    return ApiResponse(data=result)


@router.patch("", response_model=ApiResponse[UserPreferenceRead])
def update_preference(
    data: UserPreferenceUpdate,
    db: DbDep,
    user: CurrentUserDep,
):
    """Update current user's preferences."""
    result = pref_service.update_preference(db, user, data)
    return ApiResponse(data=result)


@router.get("/login-background", response_model=ApiResponse[str | None])
def get_login_background(db: DbDep):
    """Public endpoint: get login page background URL from admin preference."""
    admin = db.query(User).filter(User.username == settings.dev_admin_username).first()
    if not admin:
        return ApiResponse(data=None)
    pref = pref_service.get_or_create_preference(db, admin)
    return ApiResponse(data=pref.login_background_url)
