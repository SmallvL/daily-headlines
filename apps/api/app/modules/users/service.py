from app.modules.auth.schemas import CurrentUser
from app.modules.users.schemas import UserProfile


class UserService:
    def get_profile(self, current_user: CurrentUser) -> UserProfile:
        return UserProfile(**current_user.model_dump())


user_service = UserService()
