from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.core.config import settings
from app.core.database import SessionLocal
from app.modules.sources.service import source_service


class SchedulerService:
    def __init__(self) -> None:
        self._scheduler: AsyncIOScheduler | None = None

    def start(self) -> None:
        if self._scheduler and self._scheduler.running:
            return
        scheduler = AsyncIOScheduler(timezone="UTC")
        scheduler.add_job(
            self.run_due_sources,
            "interval",
            seconds=settings.scheduler_interval_seconds,
            id="run_due_sources",
            max_instances=1,
            coalesce=True,
        )
        scheduler.start()
        self._scheduler = scheduler

    def stop(self) -> None:
        if self._scheduler and self._scheduler.running:
            self._scheduler.shutdown(wait=False)
        self._scheduler = None

    async def run_due_sources(self) -> int:
        db = SessionLocal()
        try:
            return await source_service.run_due_scheduled_sources(db)
        finally:
            db.close()


scheduler_service = SchedulerService()
