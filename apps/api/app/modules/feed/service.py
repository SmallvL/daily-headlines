import json
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import desc, or_, select
from sqlalchemy.orm import Session

from app.modules.auth.schemas import CurrentUser
from app.modules.feed.models import FeedItem, UserItemState
from app.modules.feed.schemas import FeedItemRead, ItemStateRead
from app.modules.sources.models import Source, Subscription


class FeedService:
    def list_items(
        self,
        db: Session,
        current_user: CurrentUser,
        q: str | None = None,
        source_type: str | None = None,
        source_id: str | None = None,
        has_image: bool | None = None,
        saved: bool | None = None,
        read: bool | None = None,
        include_hidden: bool = False,
        limit: int = 50,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[FeedItemRead], int]:
        """Return (items, total_count) with pagination support."""
        # Build base statement (without limit/offset) for counting
        base = (
            select(FeedItem, UserItemState)
            .join(Source, Source.id == FeedItem.source_id)
            .join(Subscription, Subscription.source_id == Source.id)
            .outerjoin(
                UserItemState,
                (UserItemState.item_id == FeedItem.id)
                & (UserItemState.user_id == current_user.id),
            )
            .where(Subscription.user_id == current_user.id)
            .where(Subscription.status == "active")
        )
        if q:
            keyword = f"%{q.strip()}%"
            base = base.where(
                or_(
                    FeedItem.title.ilike(keyword),
                    FeedItem.summary.ilike(keyword),
                    FeedItem.content_md.ilike(keyword),
                    FeedItem.author.ilike(keyword),
                    Source.name.ilike(keyword),
                )
            )
        if source_type:
            base = base.where(Source.type == source_type)
        if source_id:
            base = base.where(FeedItem.source_id == source_id)
        if has_image is not None:
            base = base.where(
                FeedItem.image_url.is_not(None) if has_image else FeedItem.image_url.is_(None)
            )
        if saved is not None:
            base = base.where(
                UserItemState.saved_at.is_not(None) if saved else UserItemState.saved_at.is_(None)
            )
        if read is not None:
            base = base.where(
                UserItemState.read_at.is_not(None) if read else UserItemState.read_at.is_(None)
            )
        if not include_hidden:
            base = base.where(
                or_(UserItemState.hidden_at.is_(None), UserItemState.id.is_(None))
            )

        # Count total
        from sqlalchemy import func
        count_stmt = select(func.count()).select_from(base.subquery())
        total = db.scalar(count_stmt) or 0

        # Apply ordering and pagination
        effective_page_size = min(page_size, 100)
        effective_page = max(page, 1)
        offset = (effective_page - 1) * effective_page_size

        statement = base.order_by(
            desc(FeedItem.published_at),
            desc(FeedItem.fetched_at),
        ).limit(effective_page_size).offset(offset)

        rows = db.execute(statement).all()
        # Build source name map for efficient lookup
        source_ids = {item.source_id for item, _ in rows}
        source_names: dict[str, str] = {}
        if source_ids:
            sources = db.scalars(
                select(Source).where(Source.id.in_(source_ids))
            ).all()
            source_names = {s.id: s.name for s in sources}
        items = [
            self._to_read(
                item, state, source_names.get(item.source_id, "")
            )
            for item, state in rows
        ]
        return items, total

    def mark_saved(
        self,
        db: Session,
        current_user: CurrentUser,
        item_id: str,
        saved: bool,
    ) -> ItemStateRead:
        state = self._get_or_create_state(db, current_user, item_id)
        state.saved_at = datetime.now(timezone.utc) if saved else None
        db.commit()
        return self._state_to_read(state)

    def mark_read(
        self,
        db: Session,
        current_user: CurrentUser,
        item_id: str,
        read: bool,
    ) -> ItemStateRead:
        state = self._get_or_create_state(db, current_user, item_id)
        state.read_at = datetime.now(timezone.utc) if read else None
        db.commit()
        return self._state_to_read(state)

    def mark_hidden(
        self,
        db: Session,
        current_user: CurrentUser,
        item_id: str,
        hidden: bool,
    ) -> ItemStateRead:
        state = self._get_or_create_state(db, current_user, item_id)
        state.hidden_at = datetime.now(timezone.utc) if hidden else None
        db.commit()
        return self._state_to_read(state)

    def _get_or_create_state(
        self,
        db: Session,
        current_user: CurrentUser,
        item_id: str,
    ) -> UserItemState:
        item = db.get(FeedItem, item_id)
        if not item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feed item not found")
        state = db.scalars(
            select(UserItemState)
            .where(UserItemState.user_id == current_user.id)
            .where(UserItemState.item_id == item_id)
        ).first()
        if state:
            return state
        state = UserItemState(
            id=f"state_{uuid4().hex}",
            user_id=current_user.id,
            item_id=item_id,
        )
        db.add(state)
        db.flush()
        return state

    def _to_read(
        self,
        item: FeedItem,
        state: UserItemState | None = None,
        source_name: str = "",
    ) -> FeedItemRead:
        return FeedItemRead(
            id=item.id,
            source_id=item.source_id,
            source_name=source_name,
            title=item.title,
            summary=item.summary,
            url=item.url,
            image_url=item.image_url,
            author=item.author,
            published_at=item.published_at,
            fetched_at=item.fetched_at,
            is_read=bool(state and state.read_at),
            is_saved=bool(state and state.saved_at),
            is_hidden=bool(state and state.hidden_at),
        )

    def _state_to_read(self, state: UserItemState) -> ItemStateRead:
        return ItemStateRead(
            item_id=state.item_id,
            is_read=bool(state.read_at),
            is_saved=bool(state.saved_at),
            is_hidden=bool(state.hidden_at),
        )


def raw_json(value: dict) -> str:
    return json.dumps(value, ensure_ascii=False)


feed_service = FeedService()
