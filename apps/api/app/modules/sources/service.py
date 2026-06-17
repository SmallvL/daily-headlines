import json
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth_utils import build_auth_headers, prepare_auth_for_storage
from app.modules.auth.schemas import CurrentUser
from app.modules.connectors.api import api_connector, api_dedupe_key
from app.modules.connectors.rss import dedupe_key, rss_connector
from app.modules.connectors.web import web_connector, web_dedupe_key
from app.modules.feed.models import FeedItem
from app.modules.feed.schemas import FeedItemRead
from app.modules.feed.service import feed_service, raw_json
from app.modules.sources.models import Source, SourceFetchLog, Subscription
from app.modules.sources.schemas import (
    FetchResult,
    SourceCreate,
    SourceFetchLogRead,
    SourceRead,
    SourceScheduleUpdate,
    SourceTemplate,
    SourceTestRequest,
    SourceTestResult,
    SourceUpdate,
)
from app.plugins.base.registry import get_plugin_registry


class SourceService:
    def list_sources(self, db: Session, current_user: CurrentUser) -> list[SourceRead]:
        statement = (
            select(Source)
            .join(Subscription, Subscription.source_id == Source.id)
            .where(Subscription.user_id == current_user.id)
            .where(Source.deleted_at.is_(None))
            .order_by(Source.created_at.desc())
        )
        return [self._to_read(source) for source in db.scalars(statement).all()]

    def create_source(
        self,
        db: Session,
        current_user: CurrentUser,
        payload: SourceCreate,
    ) -> SourceRead:
        # Prepare auth config for storage
        auth_data = prepare_auth_for_storage(
            payload.auth.auth_type,
            payload.auth.model_dump(exclude={"auth_type"})
        )

        # Merge auth config into config_json
        config = payload.config.copy()
        config["auth"] = auth_data

        source = Source(
            id=f"source_{uuid4().hex}",
            name=payload.name,
            type=payload.type,
            endpoint=str(payload.endpoint),
            config_json=json.dumps(config, ensure_ascii=False),
            created_by=current_user.id,
            schedule_enabled=payload.schedule_enabled,
            schedule_mode=payload.schedule_mode,
            schedule_interval_minutes=payload.schedule_interval_minutes,
            cron_expression=payload.cron_expression,
            cron_days_of_week=payload.cron_days_of_week,
            cron_hour=payload.cron_hour,
            cron_minute=payload.cron_minute,
            next_fetch_at=self._next_fetch_at(payload),
        )
        db.add(source)
        db.add(
            Subscription(
                id=f"sub_{uuid4().hex}",
                user_id=current_user.id,
                source_id=source.id,
            )
        )
        db.commit()
        db.refresh(source)
        return self._to_read(source)

    def delete_source(self, db: Session, current_user: CurrentUser, source_id: str) -> None:
        source = self._get_owned_source(db, current_user, source_id)
        source.deleted_at = datetime.now(timezone.utc)
        subscriptions = db.scalars(
            select(Subscription)
            .where(Subscription.source_id == source_id)
        ).all()
        for sub in subscriptions:
            sub.status = "deleted"
        db.commit()

    def update_source(
        self,
        db: Session,
        current_user: CurrentUser,
        source_id: str,
        payload: SourceUpdate,
    ) -> SourceRead:
        source = self._get_owned_source(db, current_user, source_id)
        if payload.name is not None:
            source.name = payload.name
        if payload.type is not None:
            source.type = payload.type
        if payload.endpoint is not None:
            source.endpoint = str(payload.endpoint)
        if payload.config is not None:
            # Merge with existing config
            existing_config = json.loads(source.config_json or "{}")
            existing_config.update(payload.config)
            source.config_json = json.dumps(existing_config, ensure_ascii=False)
        if payload.auth is not None:
            # Update auth config
            existing_config = json.loads(source.config_json or "{}")
            auth_data = prepare_auth_for_storage(
                payload.auth.auth_type,
                payload.auth.model_dump(exclude={"auth_type"})
            )
            existing_config["auth"] = auth_data
            source.config_json = json.dumps(existing_config, ensure_ascii=False)
        source.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(source)
        return self._to_read(source)

    async def test_source(
        self,
        db: Session,
        current_user: CurrentUser,
        payload: SourceTestRequest,
    ) -> SourceTestResult:
        """Test a source configuration without saving."""

        # Build auth headers
        config = payload.config.copy()
        auth_config = payload.auth.model_dump(exclude={"auth_type"})
        auth_data = prepare_auth_for_storage(payload.auth.auth_type, auth_config)
        config["auth"] = auth_data
        extra_headers = build_auth_headers(payload.auth.auth_type, auth_config)

        # Run the fetch
        title, items = await self._fetch_source_items(
            source_id="test",
            source_type=payload.type,
            endpoint=str(payload.endpoint),
            config=config,
            limit=5,
            extra_headers=extra_headers,
        )

        return SourceTestResult(
            title=title,
            items=[
                FeedItemRead(
                    id=f"test_{i}",
                    source_id="test",
                    source_name="Preview",
                    title=item.title,
                    summary=item.summary,
                    url=item.url,
                    image_url=item.image_url,
                    author=item.author,
                    published_at=item.published_at,
                    fetched_at=datetime.now(timezone.utc),
                    is_read=False,
                    is_saved=False,
                    is_hidden=False,
                )
                for i, item in enumerate(items)
            ],
        )

    async def fetch_source(
        self,
        db: Session,
        current_user: CurrentUser,
        source_id: str,
    ) -> FetchResult:
        source = self._get_owned_source(db, current_user, source_id)
        return await self._fetch_source(db, source, trigger="manual")

    async def _fetch_source(
        self,
        db: Session,
        source: Source,
        trigger: str,
        attempt: int = 1,
        max_attempts: int = 3,
    ) -> FetchResult:
        log = SourceFetchLog(
            id=f"fetchlog_{uuid4().hex}",
            source_id=source.id,
            trigger=trigger,
            status="running",
            attempt=attempt,
            max_attempts=max_attempts,
            started_at=datetime.now(timezone.utc),
        )
        db.add(log)
        db.flush()

        inserted = 0
        skipped = 0
        inserted_items: list[FeedItemRead] = []

        try:
            config = json.loads(source.config_json or "{}")

            # Extract auth config and build headers
            auth_data = config.get("auth", {})
            auth_type = auth_data.get("auth_type", "none")
            auth_config = auth_data.get("auth_config", {})
            extra_headers = build_auth_headers(auth_type, auth_config)
            
            # Extract plugin info
            plugin_id = auth_config.get("plugin_id")
            plugin_credentials = auth_config.get("plugin_credentials")
            plugin_config = auth_config.get("plugin_config")

            _, items = await self._fetch_source_items(
                source_id=source.id,
                source_type=source.type,
                endpoint=source.endpoint,
                config=config,
                extra_headers=extra_headers,
                plugin_id=plugin_id,
                plugin_credentials=plugin_credentials,
                plugin_config=plugin_config,
            )
            for item in items:
                key = self._dedupe_key(
                    source.type, source.id, item.external_id, item.url, item.title
                )
                existing = db.scalars(
                    select(FeedItem)
                    .where(FeedItem.source_id == source.id)
                    .where(FeedItem.dedupe_key == key)
                ).first()
                if existing:
                    skipped += 1
                    continue
                feed_item = FeedItem(
                    id=f"item_{uuid4().hex}",
                    source_id=source.id,
                    external_id=item.external_id,
                    dedupe_key=key,
                    title=item.title,
                    summary=item.summary,
                    content_md=item.content_md,
                    url=item.url,
                    image_url=item.image_url,
                    author=item.author,
                    language=item.language,
                    published_at=item.published_at,
                    raw_json=raw_json(item.raw_json),
                )
                db.add(feed_item)
                db.flush()
                inserted += 1
                inserted_items.append(feed_service._to_read(feed_item, None))

            source.last_fetch_at = datetime.now(timezone.utc)
            source.next_fetch_at = self._next_fetch_at_from_source(source)
            log.status = "success"
            log.inserted_count = inserted
            log.skipped_count = skipped
            log.finished_at = datetime.now(timezone.utc)
            db.commit()
            return FetchResult(
                log_id=log.id, inserted=inserted, skipped=skipped, items=inserted_items
            )
        except Exception as exc:
            log.status = "failed"
            log.error_message = str(exc)
            log.finished_at = datetime.now(timezone.utc)
            # Schedule retry with exponential backoff if attempts remain
            if attempt < max_attempts:
                backoff_seconds = min(300, (2 ** attempt) * 30)
                log.next_retry_at = datetime.now(timezone.utc) + timedelta(seconds=backoff_seconds)
                log.status = "retrying"
            db.commit()
            raise

    async def _fetch_source_items(
        self,
        source_id: str,
        source_type: str,
        endpoint: str,
        config: dict,
        limit: int = 20,
        extra_headers: dict[str, str] | None = None,
        plugin_id: str | None = None,
        plugin_credentials: dict | None = None,
        plugin_config: dict | None = None,
    ):
        # If using plugin, fetch via plugin
        if plugin_id and plugin_credentials:
            registry = get_plugin_registry()
            plugin = registry.get(plugin_id)
            if plugin:
                result = await plugin.fetch_feed(
                    credentials=plugin_credentials,
                    config=plugin_config or {},
                    limit=limit
                )
                if result.success:
                    # Convert plugin feed items to FeedItemRead format
                    items = []
                    for item_data in result.items:
                        items.append(FeedItemRead(
                            id=f"item_{uuid4().hex}",
                            source_id=source_id,
                            external_id=item_data.get("source_id", ""),
                            title=item_data.get("title", ""),
                            summary=item_data.get("summary"),
                            content_md=item_data.get("content"),
                            url=item_data.get("url", ""),
                            image_url=item_data.get("image_url"),
                            author=item_data.get("author"),
                            language=None,
                            published_at=item_data.get("published_at"),
                            raw_json=item_data,
                            created_at=datetime.now(timezone.utc),
                        ))
                    return (None, items)
                else:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=result.error or "Plugin fetch failed"
                    )

        # Fallback to standard connectors
        if source_type == "rss":
            return await rss_connector.fetch(source_id, endpoint, limit=limit, extra_headers=extra_headers)
        if source_type == "api":
            return await api_connector.fetch(source_id, endpoint, config=config, limit=limit, extra_headers=extra_headers)
        if source_type == "web":
            return await web_connector.fetch(source_id, endpoint, config=config, limit=limit, extra_headers=extra_headers)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported source type: {source_type}",
        )

    def update_schedule(
        self,
        db: Session,
        current_user: CurrentUser,
        source_id: str,
        payload: SourceScheduleUpdate,
    ) -> SourceRead:
        source = self._get_owned_source(db, current_user, source_id)
        source.schedule_enabled = payload.schedule_enabled
        source.schedule_mode = payload.schedule_mode
        source.schedule_interval_minutes = payload.schedule_interval_minutes
        source.cron_expression = payload.cron_expression
        source.cron_days_of_week = payload.cron_days_of_week
        source.cron_hour = payload.cron_hour
        source.cron_minute = payload.cron_minute
        source.next_fetch_at = self._next_fetch_at_from_source(source)
        source.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(source)
        return self._to_read(source)

    def list_all_fetch_logs(
        self,
        db: Session,
        current_user: CurrentUser,
        source_id: str | None = None,
        status: str | None = None,
        trigger: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        """List all fetch logs with pagination and filters."""
        statement = (
            select(SourceFetchLog)
            .join(Source, Source.id == SourceFetchLog.source_id)
            .join(Subscription, Subscription.source_id == Source.id)
            .where(Subscription.user_id == current_user.id)
        )
        if source_id:
            statement = statement.where(SourceFetchLog.source_id == source_id)
        if status:
            statement = statement.where(SourceFetchLog.status == status)
        if trigger:
            statement = statement.where(SourceFetchLog.trigger == trigger)

        # Count total
        from sqlalchemy import func
        count_stmt = select(func.count()).select_from(statement.subquery())
        total = db.scalar(count_stmt) or 0

        # Apply pagination
        offset = (page - 1) * page_size
        statement = statement.order_by(SourceFetchLog.started_at.desc())
        statement = statement.limit(page_size).offset(offset)

        logs = db.scalars(statement).all()
        return {
            "items": [self._to_log_read(log) for log in logs],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    def list_source_fetch_logs(
        self,
        db: Session,
        current_user: CurrentUser,
        source_id: str,
    ) -> list[SourceFetchLogRead]:
        """List fetch logs for a specific source."""
        # Verify ownership
        self._get_owned_source(db, current_user, source_id)

        statement = (
            select(SourceFetchLog)
            .where(SourceFetchLog.source_id == source_id)
            .order_by(SourceFetchLog.started_at.desc())
            .limit(20)
        )
        logs = db.scalars(statement).all()
        return [self._to_log_read(log) for log in logs]

    async def run_due_scheduled_sources(self, db: Session) -> int:
        """Run all sources that are due for scheduled fetching."""
        now = datetime.now(timezone.utc)
        statement = (
            select(Source)
            .where(Source.schedule_enabled == True)  # noqa: E712
            .where(Source.next_fetch_at <= now)
            .where(Source.deleted_at.is_(None))
        )
        sources = db.scalars(statement).all()
        completed = 0
        for source in sources:
            try:
                await self._fetch_source(db, source, trigger="schedule")
                completed += 1
            except Exception:
                # Log error but continue with other sources
                pass
        return completed

    def _dedupe_key(
        self,
        source_type: str,
        source_id: str,
        external_id: str | None,
        url: str | None,
        title: str,
    ) -> str:
        if source_type == "api":
            return api_dedupe_key(source_id, external_id, url, title)
        if source_type == "web":
            return web_dedupe_key(source_id, external_id, url, title)
        return dedupe_key(source_id, external_id, url, title)

    def _get_owned_source(self, db: Session, current_user: CurrentUser, source_id: str) -> Source:
        statement = (
            select(Source)
            .join(Subscription, Subscription.source_id == Source.id)
            .where(Source.id == source_id)
            .where(Subscription.user_id == current_user.id)
            .where(Source.deleted_at.is_(None))
        )
        source = db.scalars(statement).first()
        if not source:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")
        return source

    def _to_read(self, source: Source) -> SourceRead:
        config = json.loads(source.config_json or "{}")
        auth_data = config.get("auth", {})
        auth_type = auth_data.get("auth_type", "none")
        auth_config = auth_data.get("auth_config", {})
        
        # Get plugin info
        plugin_id = auth_config.get("plugin_id")
        plugin_name = None
        plugin_user_info = None
        
        if plugin_id:
            registry = get_plugin_registry()
            plugin = registry.get(plugin_id)
            if plugin:
                plugin_name = plugin.display_name
            plugin_credentials = auth_config.get("plugin_credentials", {})
            if plugin_credentials:
                plugin_user_info = plugin_credentials.get("user_info")

        return SourceRead(
            id=source.id,
            name=source.name,
            type=source.type,
            endpoint=source.endpoint,
            status=source.status,
            last_fetch_at=source.last_fetch_at,
            schedule_enabled=source.schedule_enabled,
            schedule_mode=source.schedule_mode,
            schedule_interval_minutes=source.schedule_interval_minutes,
            cron_expression=source.cron_expression,
            cron_days_of_week=source.cron_days_of_week,
            cron_hour=source.cron_hour,
            cron_minute=source.cron_minute,
            next_fetch_at=source.next_fetch_at,
            created_at=source.created_at,
            auth_type=auth_type,
            has_auth=auth_type != "none" and (bool(auth_config) or bool(plugin_id)),
            plugin_id=plugin_id,
            plugin_name=plugin_name,
            plugin_user_info=plugin_user_info,
        )

    def _to_log_read(self, log: SourceFetchLog) -> SourceFetchLogRead:
        return SourceFetchLogRead(
            id=log.id,
            source_id=log.source_id,
            trigger=log.trigger,
            status=log.status,
            inserted_count=log.inserted_count,
            skipped_count=log.skipped_count,
            error_message=log.error_message,
            attempt=log.attempt,
            max_attempts=log.max_attempts,
            next_retry_at=log.next_retry_at,
            started_at=log.started_at,
            finished_at=log.finished_at,
        )

    def _next_fetch_at(self, payload: SourceCreate) -> datetime | None:
        if not payload.schedule_enabled:
            return None
        now = datetime.now(timezone.utc)
        if payload.schedule_mode == "interval":
            minutes = payload.schedule_interval_minutes or 60
            return now + timedelta(minutes=minutes)
        if payload.schedule_mode == "cron":
            hour = payload.cron_hour or 0
            minute = payload.cron_minute or 0
            next_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if next_time <= now:
                next_time += timedelta(days=1)
            return next_time
        return None

    def _next_fetch_at_from_source(self, source: Source) -> datetime | None:
        if not source.schedule_enabled:
            return None
        now = datetime.now(timezone.utc)
        if source.schedule_mode == "interval":
            minutes = source.schedule_interval_minutes or 60
            return now + timedelta(minutes=minutes)
        if source.schedule_mode == "cron":
            hour = source.cron_hour or 0
            minute = source.cron_minute or 0
            next_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if next_time <= now:
                next_time += timedelta(days=1)
            return next_time
        return None

    def get_template(self, db: Session, current_user: CurrentUser, source_id: str) -> SourceTemplate:
        source = self._get_owned_source(db, current_user, source_id)
        config = json.loads(source.config_json or "{}")
        auth_data = config.get("auth", {})
        return SourceTemplate(
            name=source.name,
            type=source.type,
            endpoint=source.endpoint,
            config=config,
            auth_type=auth_data.get("auth_type", "none"),
            schedule_enabled=source.schedule_enabled,
            schedule_mode=source.schedule_mode,
            schedule_interval_minutes=source.schedule_interval_minutes,
            cron_expression=source.cron_expression,
            cron_days_of_week=source.cron_days_of_week,
            cron_hour=source.cron_hour,
            cron_minute=source.cron_minute,
        )

    def import_template(
        self,
        db: Session,
        current_user: CurrentUser,
        template: SourceTemplate,
    ) -> SourceRead:
        payload = SourceCreate(
            name=template.name,
            type=template.type,
            endpoint=template.endpoint,
            config=template.config,
            schedule_enabled=template.schedule_enabled,
            schedule_mode=template.schedule_mode,
            schedule_interval_minutes=template.schedule_interval_minutes,
            cron_expression=template.cron_expression,
            cron_days_of_week=template.cron_days_of_week,
            cron_hour=template.cron_hour,
            cron_minute=template.cron_minute,
        )
        return self.create_source(db, current_user, payload)


source_service = SourceService()
