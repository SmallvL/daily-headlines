from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.auth.router import CurrentUserDep
from app.modules.feed.schemas import FeedItemList, ItemStateRead
from app.modules.feed.service import feed_service
from app.shared.responses import ApiResponse

router = APIRouter()
DbDep = Annotated[Session, Depends(get_db)]


@router.get("/items", response_model=ApiResponse[FeedItemList])
def list_items(
    current_user: CurrentUserDep,
    db: DbDep,
    q: str | None = Query(default=None, max_length=120),
    source_type: str | None = Query(default=None, pattern="^(rss|api|web)$"),
    source_id: str | None = Query(default=None),
    has_image: bool | None = None,
    saved: bool | None = None,
    read: bool | None = None,
    include_hidden: bool = False,
    limit: int = Query(default=50, ge=1, le=100),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
) -> ApiResponse[FeedItemList]:
    items, total = feed_service.list_items(
        db,
        current_user,
        q=q,
        source_type=source_type,
        source_id=source_id,
        has_image=has_image,
        saved=saved,
        read=read,
        include_hidden=include_hidden,
        limit=limit,
        page=page,
        page_size=page_size,
    )
    return ApiResponse(
        data=FeedItemList(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
        )
    )


@router.post("/items/{item_id}/save", response_model=ApiResponse[ItemStateRead])
def save_item(
    item_id: str,
    current_user: CurrentUserDep,
    db: DbDep,
) -> ApiResponse[ItemStateRead]:
    return ApiResponse(data=feed_service.mark_saved(db, current_user, item_id, True))


@router.delete("/items/{item_id}/save", response_model=ApiResponse[ItemStateRead])
def unsave_item(
    item_id: str,
    current_user: CurrentUserDep,
    db: DbDep,
) -> ApiResponse[ItemStateRead]:
    return ApiResponse(data=feed_service.mark_saved(db, current_user, item_id, False))


@router.post("/items/{item_id}/read", response_model=ApiResponse[ItemStateRead])
def read_item(
    item_id: str,
    current_user: CurrentUserDep,
    db: DbDep,
) -> ApiResponse[ItemStateRead]:
    return ApiResponse(data=feed_service.mark_read(db, current_user, item_id, True))


@router.post("/items/{item_id}/hide", response_model=ApiResponse[ItemStateRead])
def hide_item(
    item_id: str,
    current_user: CurrentUserDep,
    db: DbDep,
) -> ApiResponse[ItemStateRead]:
    return ApiResponse(data=feed_service.mark_hidden(db, current_user, item_id, True))
