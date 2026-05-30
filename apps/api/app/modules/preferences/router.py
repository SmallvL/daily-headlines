from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.auth.router import CurrentUserDep
from app.modules.preferences import service as pref_service
from app.modules.preferences.schemas import UserPreferenceRead, UserPreferenceUpdate
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
