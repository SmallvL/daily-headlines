"""Health check and monitoring metrics endpoints."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.shared.responses import ApiResponse

router = APIRouter()
DbDep = Annotated[Session, Depends(get_db)]

# --- Global metrics collector ---

_start_time = time.monotonic()


@dataclass
class MetricsCollector:
    """Simple in-process metrics collector."""

    request_count: int = 0
    error_count: int = 0
    total_response_ms: float = 0.0
    _lock: object = field(default_factory=lambda: None, repr=False)

    def record_request(self, elapsed_ms: float, is_error: bool = False) -> None:
        self.request_count += 1
        self.total_response_ms += elapsed_ms
        if is_error:
            self.error_count += 1

    @property
    def uptime_seconds(self) -> float:
        return time.monotonic() - _start_time

    @property
    def avg_response_ms(self) -> float:
        if self.request_count == 0:
            return 0.0
        return self.total_response_ms / self.request_count


metrics = MetricsCollector()


# --- Endpoints ---


@router.get("/health")
def health(db: DbDep) -> ApiResponse[dict]:
    """Enhanced health check with DB connectivity test."""
    checks: dict[str, str] = {"api": "ok"}
    overall_ok = True

    # Database check
    try:
        db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:
        checks["database"] = f"error: {exc}"
        overall_ok = False

    return ApiResponse(
        data={
            "status": "ok" if overall_ok else "degraded",
            "version": settings.app_version,
            "checks": checks,
            "uptime_seconds": round(metrics.uptime_seconds),
        }
    )


@router.get("/metrics")
def get_metrics() -> ApiResponse[dict]:
    """Application metrics endpoint for monitoring."""
    return ApiResponse(
        data={
            "uptime_seconds": round(metrics.uptime_seconds, 1),
            "requests": {
                "total": metrics.request_count,
                "errors": metrics.error_count,
                "avg_response_ms": round(metrics.avg_response_ms, 1),
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "version": settings.app_version,
            "database": settings.database_url.split("://")[0],
        }
    )
