import uuid

from sqlalchemy.orm import Session

from app.modules.auth.schemas import CurrentUser
from app.modules.preferences.models import UserPreference
from app.modules.preferences.schemas import UserPreferenceRead, UserPreferenceUpdate


def _to_read(p: UserPreference) -> UserPreferenceRead:
    return UserPreferenceRead(
        user_id=p.user_id,
        language=p.language,
        theme=p.theme,
        default_view=p.default_view,
        login_background_url=p.login_background_url,
        updated_at=p.updated_at,
    )


def get_or_create_preference(db: Session, user: CurrentUser) -> UserPreferenceRead:
    pref = (
        db.query(UserPreference)
        .filter(UserPreference.user_id == user.id)
        .first()
    )
    if not pref:
        pref = UserPreference(
            id=uuid.uuid4().hex[:16],
            user_id=user.id,
            language="zh-CN",
            theme="light",
            default_view="list",
            login_background_url=None,
        )
        db.add(pref)
        db.commit()
        db.refresh(pref)
    return _to_read(pref)


def update_preference(
    db: Session, user: CurrentUser, data: UserPreferenceUpdate
) -> UserPreferenceRead:
    pref = (
        db.query(UserPreference)
        .filter(UserPreference.user_id == user.id)
        .first()
    )
    if not pref:
        pref = UserPreference(
            id=uuid.uuid4().hex[:16],
            user_id=user.id,
        )
        db.add(pref)

    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(pref, k, v)

    db.commit()
    db.refresh(pref)
    return _to_read(pref)
