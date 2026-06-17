from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.auth.router import CurrentUserDep
from app.modules.sources.opml import export_opml, import_opml
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
from app.modules.sources.service import source_service
from app.shared.responses import ApiResponse

router = APIRouter()
DbDep = Annotated[Session, Depends(get_db)]


@router.get("", response_model=ApiResponse[list[SourceRead]])
def list_sources(
    current_user: CurrentUserDep,
    db: DbDep,
) -> ApiResponse[list[SourceRead]]:
    return ApiResponse(data=source_service.list_sources(db, current_user))


@router.get("/{source_id}", response_model=ApiResponse[SourceRead])
def get_source(
    source_id: str,
    current_user: CurrentUserDep,
    db: DbDep,
) -> ApiResponse[SourceRead]:
    return ApiResponse(data=source_service.get_source(db, current_user, source_id))


@router.post("", response_model=ApiResponse[SourceRead])
def create_source(
    payload: SourceCreate,
    current_user: CurrentUserDep,
    db: DbDep,
) -> ApiResponse[SourceRead]:
    return ApiResponse(data=source_service.create_source(db, current_user, payload))


@router.post("/test", response_model=ApiResponse[SourceTestResult])
async def test_source(
    payload: SourceTestRequest,
    current_user: CurrentUserDep,
    db: DbDep,
) -> ApiResponse[SourceTestResult]:
    return ApiResponse(data=await source_service.test_source(db, current_user, payload))


@router.post("/{source_id}/fetch-now", response_model=ApiResponse[FetchResult])
async def fetch_now(
    source_id: str,
    current_user: CurrentUserDep,
    db: DbDep,
) -> ApiResponse[FetchResult]:
    return ApiResponse(data=await source_service.fetch_source(db, current_user, source_id))


@router.get("/fetch-logs", response_model=ApiResponse[dict])
def list_all_fetch_logs(
    current_user: CurrentUserDep,
    db: DbDep,
    source_id: str | None = None,
    status: str | None = None,
    trigger: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> ApiResponse[dict]:
    result = source_service.list_all_fetch_logs(
        db, current_user,
        source_id=source_id, status=status, trigger=trigger,
        page=page, page_size=page_size,
    )
    return ApiResponse(data=result)


@router.get("/{source_id}/fetch-logs", response_model=ApiResponse[list[SourceFetchLogRead]])
def list_source_fetch_logs(
    source_id: str,
    current_user: CurrentUserDep,
    db: DbDep,
) -> ApiResponse[list[SourceFetchLogRead]]:
    return ApiResponse(data=source_service.list_source_fetch_logs(db, current_user, source_id))


@router.patch("/{source_id}", response_model=ApiResponse[SourceRead])
def update_source(
    source_id: str,
    payload: SourceUpdate,
    current_user: CurrentUserDep,
    db: DbDep,
) -> ApiResponse[SourceRead]:
    return ApiResponse(data=source_service.update_source(db, current_user, source_id, payload))


@router.patch("/{source_id}/schedule", response_model=ApiResponse[SourceRead])
def update_schedule(
    source_id: str,
    payload: SourceScheduleUpdate,
    current_user: CurrentUserDep,
    db: DbDep,
) -> ApiResponse[SourceRead]:
    return ApiResponse(data=source_service.update_schedule(db, current_user, source_id, payload))


@router.delete("/{source_id}")
def delete_source(
    source_id: str,
    current_user: CurrentUserDep,
    db: DbDep,
) -> ApiResponse[None]:
    source_service.delete_source(db, current_user, source_id)
    return ApiResponse(data=None)


@router.get("/{source_id}/export-template", response_model=ApiResponse[SourceTemplate])
def export_template(
    source_id: str,
    current_user: CurrentUserDep,
    db: DbDep,
) -> ApiResponse[SourceTemplate]:
    return ApiResponse(data=source_service.get_template(db, current_user, source_id))


@router.post("/import-template", response_model=ApiResponse[SourceRead])
def import_template(
    template: SourceTemplate,
    current_user: CurrentUserDep,
    db: DbDep,
) -> ApiResponse[SourceRead]:
    return ApiResponse(data=source_service.import_template(db, current_user, template))


@router.get("/export/opml")
def export_sources_opml(
    current_user: CurrentUserDep,
    db: DbDep,
) -> Response:
    opml_content = export_opml(db, current_user)
    return Response(
        content=opml_content,
        media_type="application/xml",
        headers={"Content-Disposition": "attachment; filename=sources.opml"},
    )


@router.post("/import/opml", response_model=ApiResponse[list[SourceRead]])
def import_sources_opml(
    file: UploadFile = File(...),
    current_user: CurrentUserDep = None,
    db: DbDep = None,
) -> ApiResponse[list[SourceRead]]:
    content = file.file.read().decode("utf-8")
    sources = import_opml(db, current_user, content)
    return ApiResponse(data=sources)
