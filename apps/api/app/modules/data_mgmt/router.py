import os
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.auth.router import require_admin
from app.modules.data_mgmt.service import data_mgmt_service
from app.modules.data_mgmt.schemas import (
    ExportInfo,
    MaintenanceResult,
    PurgeAllResult,
    PurgePreview,
    RetentionConfigRead,
    RetentionConfigUpdate,
    StorageStats,
)
from app.shared.responses import ApiResponse

router = APIRouter()
DbDep = Annotated[Session, Depends(get_db)]

DB_PATH = os.environ.get("DATABASE_URL", "sqlite:///./daily_headlines.db").replace("sqlite:///", "")


@router.get("/stats", response_model=ApiResponse[StorageStats])
def get_storage_stats(
    db: DbDep,
    _admin: None = Depends(require_admin),
) -> ApiResponse[StorageStats]:
    stats = data_mgmt_service.get_storage_stats(db, DB_PATH)
    return ApiResponse(data=stats)


@router.get("/retention-configs", response_model=ApiResponse[list[RetentionConfigRead]])
def list_retention_configs(
    db: DbDep,
    _admin: None = Depends(require_admin),
) -> ApiResponse[list[RetentionConfigRead]]:
    configs = data_mgmt_service.list_configs(db)
    return ApiResponse(data=[RetentionConfigRead.model_validate(c) for c in configs])


@router.put(
    "/retention-configs/{table_name}",
    response_model=ApiResponse[RetentionConfigRead],
)
def update_retention_config(
    table_name: str,
    body: RetentionConfigUpdate,
    db: DbDep,
    _admin: None = Depends(require_admin),
) -> ApiResponse[RetentionConfigRead]:
    updates = body.model_dump(exclude_unset=True)
    cfg = data_mgmt_service.update_config(db, table_name, updates)
    if not cfg:
        raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found in retention configs")
    return ApiResponse(data=RetentionConfigRead.model_validate(cfg))


@router.post("/purge/preview", response_model=ApiResponse[list[PurgePreview]])
def preview_purge(
    db: DbDep,
    table_name: str | None = Query(default=None),
    _admin: None = Depends(require_admin),
) -> ApiResponse[list[PurgePreview]]:
    previews = data_mgmt_service.preview_purge(db, table_name)
    return ApiResponse(data=previews)


@router.post("/purge/execute", response_model=ApiResponse[PurgeAllResult])
def execute_purge(
    db: DbDep,
    table_name: str | None = Query(default=None),
    vacuum: bool = Query(default=True),
    _admin: None = Depends(require_admin),
) -> ApiResponse[PurgeAllResult]:
    result = data_mgmt_service.execute_purge(db, table_name, vacuum=vacuum)
    return ApiResponse(data=result)


@router.post("/export")
@router.get("/export")
def export_data(
    db: DbDep,
    _admin: None = Depends(require_admin),
    tables: str | None = Query(default=None, description="Comma-separated table names"),
    fmt: str = Query(default="json", pattern="^(json|csv)$"),
    source_id: str | None = Query(default=None),
) -> Response:
    table_list = [t.strip() for t in tables.split(",")] if tables else None
    content, info = data_mgmt_service.export_data(
        db, tables=table_list, fmt=fmt, source_id=source_id,
    )
    media_type = "application/json" if fmt == "json" else "text/csv"
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={info.filename}"},
    )


@router.get("/export/info", response_model=ApiResponse[ExportInfo])
def export_info(
    db: DbDep,
    _admin: None = Depends(require_admin),
    tables: str | None = Query(default=None),
    fmt: str = Query(default="json", pattern="^(json|csv)$"),
) -> ApiResponse[ExportInfo]:
    table_list = [t.strip() for t in tables.split(",")] if tables else None
    _, info = data_mgmt_service.export_data(db, tables=table_list, fmt=fmt)
    return ApiResponse(data=info)


@router.post("/vacuum", response_model=ApiResponse[MaintenanceResult])
def run_vacuum(
    db: DbDep,
    _admin: None = Depends(require_admin),
) -> ApiResponse[MaintenanceResult]:
    result = data_mgmt_service.run_vacuum(db)
    return ApiResponse(data=MaintenanceResult(
        action="vacuum",
        success=result.get("success", False),
        details=result,
    ))
