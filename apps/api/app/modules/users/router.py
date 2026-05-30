from fastapi import APIRouter

from app.modules.auth.router import CurrentUserDep
from app.modules.users.schemas import UserProfile
from app.modules.users.service import user_service
from app.shared.responses import ApiResponse

router = APIRouter()


@router.get("/me", response_model=ApiResponse[UserProfile])
def profile(current_user: CurrentUserDep) -> ApiResponse[UserProfile]:
    return ApiResponse(data=user_service.get_profile(current_user))
