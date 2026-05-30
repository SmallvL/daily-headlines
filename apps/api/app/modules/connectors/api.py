from datetime import datetime
from hashlib import sha256
from typing import Any

import httpx

from app.modules.feed.schemas import FeedItemCreate


def _get_path(value: Any, path: str | None) -> Any:
    if not path:
        return value
    current = value
    for part in path.split("."):
        if isinstance(current, dict):
            current = current.get(part)
        elif isinstance(current, list) and part.isdigit():
            current = current[int(part)]
        else:
            return None
    return current


def _as_text(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _as_datetime(value: Any) -> datetime | None:
    text = _as_text(value)
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def api_dedupe_key(source_id: str, external_id: str | None, url: str | None, title: str) -> str:
    material = external_id or url or title
    return sha256(f"{source_id}:{material}".encode()).hexdigest()


class ApiConnector:
    async def fetch(
        self,
        source_id: str,
        endpoint: str,
        config: dict,
        limit: int = 20,
        extra_headers: dict[str, str] | None = None,
    ) -> tuple[str | None, list[FeedItemCreate]]:
        # Build headers with auth support
        headers = {}
        if extra_headers:
            headers.update(extra_headers)

        async with httpx.AsyncClient(
            timeout=15.0,
            follow_redirects=True,
            headers=headers if headers else None,
        ) as client:
            response = await client.get(endpoint)
            response.raise_for_status()

        payload = response.json()
        items_path = config.get("items_path")
        mappings = config.get("mappings") or {}
        raw_items = _get_path(payload, items_path)
        if not isinstance(raw_items, list):
            raw_items = payload if isinstance(payload, list) else []

        items: list[FeedItemCreate] = []
        for raw_item in raw_items[:limit]:
            if not isinstance(raw_item, dict):
                continue
            title = _as_text(_get_path(raw_item, mappings.get("title"))) or "Untitled"
            url = _as_text(_get_path(raw_item, mappings.get("url")))
            external_id = _as_text(_get_path(raw_item, mappings.get("id"))) or url
            summary = _as_text(_get_path(raw_item, mappings.get("summary")))
            items.append(
                FeedItemCreate(
                    source_id=source_id,
                    external_id=external_id,
                    title=title,
                    summary=summary,
                    content_md=summary,
                    url=url,
                    image_url=_as_text(_get_path(raw_item, mappings.get("image_url"))),
                    author=_as_text(_get_path(raw_item, mappings.get("author"))),
                    published_at=_as_datetime(_get_path(raw_item, mappings.get("published_at"))),
                    raw_json=raw_item,
                )
            )

        title = (
            _as_text(_get_path(payload, config.get("title_path")))
            if isinstance(payload, dict)
            else None
        )
        return title, items


api_connector = ApiConnector()
