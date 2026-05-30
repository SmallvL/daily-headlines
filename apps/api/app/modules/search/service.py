import json
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.auth.schemas import CurrentUser
from app.modules.search.models import SavedSearch
from app.modules.search.schemas import SavedSearchCreate, SavedSearchQuery, SavedSearchRead


class SearchService:
    def list_saved_searches(self, db: Session, current_user: CurrentUser) -> list[SavedSearchRead]:
        statement = (
            select(SavedSearch)
            .where(SavedSearch.user_id == current_user.id)
            .order_by(SavedSearch.created_at.desc())
        )
        return [self._to_read(saved_search) for saved_search in db.scalars(statement).all()]

    def create_saved_search(
        self,
        db: Session,
        current_user: CurrentUser,
        payload: SavedSearchCreate,
    ) -> SavedSearchRead:
        saved_search = SavedSearch(
            id=f"search_{uuid4().hex}",
            user_id=current_user.id,
            name=payload.name,
            query_json=payload.query.model_dump_json(exclude_none=True),
        )
        db.add(saved_search)
        db.commit()
        db.refresh(saved_search)
        return self._to_read(saved_search)

    def delete_saved_search(self, db: Session, current_user: CurrentUser, search_id: str) -> None:
        saved_search = db.scalars(
            select(SavedSearch)
            .where(SavedSearch.id == search_id)
            .where(SavedSearch.user_id == current_user.id)
        ).first()
        if not saved_search:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Saved search not found",
            )
        db.delete(saved_search)
        db.commit()

    def _to_read(self, saved_search: SavedSearch) -> SavedSearchRead:
        return SavedSearchRead(
            id=saved_search.id,
            name=saved_search.name,
            query=SavedSearchQuery(**json.loads(saved_search.query_json or "{}")),
            created_at=saved_search.created_at,
        )


search_service = SearchService()
