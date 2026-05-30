from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.auth.router import CurrentUserDep
from app.modules.search.schemas import SavedSearchCreate, SavedSearchRead
from app.modules.search.service import search_service
from app.shared.responses import ApiResponse

router = APIRouter()
DbDep = Annotated[Session, Depends(get_db)]


@router.get("/saved-searches", response_model=ApiResponse[list[SavedSearchRead]])
def list_saved_searches(
    current_user: CurrentUserDep,
    db: DbDep,
) -> ApiResponse[list[SavedSearchRead]]:
    return ApiResponse(data=search_service.list_saved_searches(db, current_user))


@router.post("/saved-searches", response_model=ApiResponse[SavedSearchRead])
def create_saved_search(
    payload: SavedSearchCreate,
    current_user: CurrentUserDep,
    db: DbDep,
) -> ApiResponse[SavedSearchRead]:
    return ApiResponse(data=search_service.create_saved_search(db, current_user, payload))


@router.delete("/saved-searches/{search_id}", response_model=ApiResponse[dict[str, bool]])
def delete_saved_search(
    search_id: str,
    current_user: CurrentUserDep,
    db: DbDep,
) -> ApiResponse[dict[str, bool]]:
    search_service.delete_saved_search(db, current_user, search_id)
    return ApiResponse(data={"deleted": True})
