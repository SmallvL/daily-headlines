from datetime import datetime
from typing import Any

from pydantic import BaseModel


# ── Storage Stats ──
class TableStats(BaseModel):
    table_name: str
    record_count: int
    estimated_size_kb: float
    oldest_record: datetime | None = None
    newest_record: datetime | None = None


class StorageStats(BaseModel):
    db_path: str
    db_size_mb: float
    tables: list[TableStats]
    total_records: int
    last_vacuum_at: datetime | None = None


# ── Retention Config ──
class RetentionConfigRead(BaseModel):
    id: int
    table_name: str
    max_age_days: int | None
    max_records: int | None
    keep_saved: bool
    enabled: bool
    last_purge_at: datetime | None
    last_purge_count: int | None

    model_config = {"from_attributes": True}


class RetentionConfigUpdate(BaseModel):
    max_age_days: int | None = None
    max_records: int | None = None
    keep_saved: bool | None = None
    enabled: bool | None = None


# ── Purge ──
class PurgePreview(BaseModel):
    table_name: str
    records_to_delete: int
    oldest_to_keep: datetime | None = None
    criteria: str


class PurgeResult(BaseModel):
    table_name: str
    deleted_count: int
    duration_ms: int


class PurgeAllResult(BaseModel):
    results: list[PurgeResult]
    total_deleted: int
    db_size_before_mb: float
    db_size_after_mb: float
    vacuum_performed: bool


# ── Export ──
class ExportRequest(BaseModel):
    tables: list[str] | None = None  # None = all
    format: str = "json"  # json | csv
    source_id: str | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None


class ExportInfo(BaseModel):
    filename: str
    format: str
    tables_exported: list[str]
    total_records: int
    file_size_kb: float
    created_at: datetime


# ── Generic ──
class MaintenanceResult(BaseModel):
    action: str
    success: bool
    details: dict[str, Any] = {}
