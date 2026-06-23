from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile
from pydantic import BaseModel, HttpUrl
from starlette.responses import Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.auth.router import CurrentUserDep
from app.modules.sources.opml import export_opml, import_opml
from app.modules.sources.presets import get_preset, list_presets, preset_to_source_create
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


# ── Auto-detect ──


class AutoDetectRequest(BaseModel):
    url: HttpUrl


class AutoDetectResult(BaseModel):
    type: str  # "rss" | "api" | "web"
    endpoint: str
    title: str | None = None
    config: dict = {}
    message: str = ""


@router.post("/auto-detect", response_model=ApiResponse[AutoDetectResult])
async def auto_detect_source(
    payload: AutoDetectRequest,
    current_user: CurrentUserDep,
) -> ApiResponse[AutoDetectResult]:
    """Auto-detect source type from a URL."""
    import httpx
    from selectolax.parser import HTMLParser
    import feedparser

    url = str(payload.url)
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/rss+xml, application/xml, text/xml, text/html, application/json, */*",
    }

    try:
        async with httpx.AsyncClient(
            timeout=15.0, follow_redirects=True, verify=False, headers=headers
        ) as client:
            response = await client.get(url)

        content_type = response.headers.get("content-type", "").lower()
        body = response.content

        # 1. Check if it's already an RSS/Atom feed
        if "rss" in content_type or "xml" in content_type or "atom" in content_type:
            parsed = feedparser.parse(body)
            if parsed.entries:
                title = parsed.feed.get("title") if parsed.feed else None
                return ApiResponse(data=AutoDetectResult(
                    type="rss",
                    endpoint=str(response.url),
                    title=title,
                    message="检测到 RSS/Atom 订阅源",
                ))

        # 2. Try parsing as RSS regardless of content-type
        parsed = feedparser.parse(body)
        if parsed.entries:
            title = parsed.feed.get("title") if parsed.feed else None
            return ApiResponse(data=AutoDetectResult(
                type="rss",
                endpoint=str(response.url),
                title=title,
                message="检测到 RSS/Atom 订阅源",
            ))

        # 3. Check if it's JSON API
        if "json" in content_type:
            try:
                data = response.json()
                if isinstance(data, list) and data:
                    return ApiResponse(data=AutoDetectResult(
                        type="api",
                        endpoint=str(response.url),
                        config={"items_path": "", "mappings": {}},
                        message="检测到 JSON API (数组格式)",
                    ))
                if isinstance(data, dict):
                    for key in ("items", "data", "results", "posts", "articles", "list"):
                        val = data.get(key)
                        if isinstance(val, list) and val:
                            return ApiResponse(data=AutoDetectResult(
                                type="api",
                                endpoint=str(response.url),
                                config={"items_path": key, "mappings": {}},
                                message=f"检测到 JSON API (items_path: {key})",
                            ))
            except Exception:
                pass

        # 4. RSS auto-discovery from HTML
        html_text = response.text
        parser = HTMLParser(html_text)
        for link in parser.css('link[type*="rss"], link[type*="atom"]'):
            href = link.attributes.get("href")
            if href:
                from urllib.parse import urljoin
                rss_url = urljoin(str(response.url), href)
                return ApiResponse(data=AutoDetectResult(
                    type="rss",
                    endpoint=rss_url,
                    message="从页面中发现了 RSS 订阅源",
                ))

        # 5. Fall back to web scraping
        page_title = None
        title_node = parser.css_first("title")
        if title_node:
            page_title = title_node.text(strip=True)

        return ApiResponse(data=AutoDetectResult(
            type="web",
            endpoint=str(response.url),
            title=page_title,
            message="未检测到 RSS 或 API，建议使用网页爬虫模式（需配置选择器）",
        ))

    except httpx.TimeoutException:
        return ApiResponse(data=AutoDetectResult(
            type="web",
            endpoint=url,
            message="请求超时，请检查 URL 或稍后重试",
        ))
    except Exception as e:
        return ApiResponse(data=AutoDetectResult(
            type="web",
            endpoint=url,
            message=f"检测失败: {str(e)}",
        ))


# ── Presets ──


@router.get("/presets", response_model=ApiResponse[list[dict]])
def list_source_presets(
    current_user: CurrentUserDep,
) -> ApiResponse[list[dict]]:
    """List all available source presets."""
    return ApiResponse(data=list_presets())


@router.post("/presets/{preset_id}/create", response_model=ApiResponse[SourceRead], status_code=201)
def create_from_preset(
    preset_id: str,
    current_user: CurrentUserDep,
    db: DbDep,
    name: str | None = None,
) -> ApiResponse[SourceRead]:
    """Create a source from a preset."""
    preset = get_preset(preset_id)
    if not preset:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Preset not found")

    payload = SourceCreate(**preset_to_source_create(preset, name))
    return ApiResponse(data=source_service.create_source(db, current_user, payload))


# ── Static routes first (no path params) ──


@router.get("", response_model=ApiResponse[list[SourceRead]])
def list_sources(
    current_user: CurrentUserDep,
    db: DbDep,
) -> ApiResponse[list[SourceRead]]:
    return ApiResponse(data=source_service.list_sources(db, current_user))


@router.post("", response_model=ApiResponse[SourceRead], status_code=201)
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


# ── Parametrized routes second (source_id etc.) ──


@router.get("/{source_id}", response_model=ApiResponse[SourceRead])
def get_source(
    source_id: str,
    current_user: CurrentUserDep,
    db: DbDep,
) -> ApiResponse[SourceRead]:
    return ApiResponse(data=source_service.get_source(db, current_user, source_id))


@router.post("/{source_id}/fetch-now", response_model=ApiResponse[FetchResult])
async def fetch_now(
    source_id: str,
    current_user: CurrentUserDep,
    db: DbDep,
) -> ApiResponse[FetchResult]:
    return ApiResponse(data=await source_service.fetch_source(db, current_user, source_id))


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


@router.post("/{source_id}/refresh-auth", response_model=ApiResponse[dict])
async def refresh_source_auth(
    source_id: str,
    current_user: CurrentUserDep,
    db: DbDep,
) -> ApiResponse[dict]:
    """Refresh plugin auth status for a source."""
    return ApiResponse(data=await source_service.refresh_source_auth(db, current_user, source_id))


@router.delete("/{source_id}", status_code=204)
def delete_source(
    source_id: str,
    current_user: CurrentUserDep,
    db: DbDep,
) -> None:
    source_service.delete_source(db, current_user, source_id)
    return Response(status_code=204)


@router.get("/{source_id}/export-template", response_model=ApiResponse[SourceTemplate])
def export_template(
    source_id: str,
    current_user: CurrentUserDep,
    db: DbDep,
) -> ApiResponse[SourceTemplate]:
    return ApiResponse(data=source_service.get_template(db, current_user, source_id))
