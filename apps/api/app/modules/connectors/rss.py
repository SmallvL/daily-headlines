from datetime import datetime
from email.utils import parsedate_to_datetime
from hashlib import sha256
from typing import Any

import feedparser
import httpx

from app.modules.feed.schemas import FeedItemCreate


def _as_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None


def _first_image(entry: dict[str, Any]) -> str | None:
    """Extract the first image URL from an RSS/Atom entry.

    Checks (in order):
    1. media_content
    2. media_thumbnail
    3. enclosures with image type
    4. links with image type
    5. <img> tags in summary or content HTML
    """
    # 1. media:content
    media = entry.get("media_content") or []
    if media and isinstance(media, list):
        for m in media:
            url = m.get("url")
            if isinstance(url, str) and url.startswith("http"):
                return url

    # 2. media:thumbnail
    thumbs = entry.get("media_thumbnail") or []
    if thumbs and isinstance(thumbs, list):
        url = thumbs[0].get("url")
        if isinstance(url, str) and url.startswith("http"):
            return url

    # 3. enclosures (image types)
    enclosures = entry.get("enclosures") or []
    for enc in enclosures:
        if isinstance(enc, dict):
            href = enc.get("href") or enc.get("url")
            etype = enc.get("type", "")
            if isinstance(href, str) and href.startswith("http") and "image" in etype:
                return href

    # 4. links with image type
    links = entry.get("links") or []
    for link in links:
        if link.get("type", "").startswith("image/") and isinstance(link.get("href"), str):
            return link["href"]

    # 5. Parse <img> from summary/content HTML
    for html_field in ("summary", "content"):
        html_val = entry.get(html_field)
        if isinstance(html_val, list):
            html_val = html_val[0].get("value", "") if html_val else ""
        if html_val and "<img" in html_val:
            try:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(html_val, "html.parser")
                img = soup.find("img")
                if img:
                    src = img.get("data-original") or img.get("data-src") or img.get("src")
                    if src and src.startswith("http"):
                        return src
            except Exception:
                pass

    return None


def dedupe_key(source_id: str, external_id: str | None, url: str | None, title: str) -> str:
    material = external_id or url or title
    return sha256(f"{source_id}:{material}".encode()).hexdigest()


class RssConnector:
    async def fetch(
        self,
        source_id: str,
        endpoint: str,
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

        parsed = feedparser.parse(response.content)
        title = parsed.feed.get("title") if parsed.feed else None
        items: list[FeedItemCreate] = []

        for entry in parsed.entries[:limit]:
            link = entry.get("link")
            external_id = entry.get("id") or entry.get("guid") or link
            summary = entry.get("summary")
            content = entry.get("content", [{}])[0].get("value") if entry.get("content") else None
            published_at = _as_datetime(entry.get("published") or entry.get("updated"))
            raw = {
                key: entry.get(key)
                for key in ("id", "guid", "link", "title", "published", "updated")
            }
            items.append(
                FeedItemCreate(
                    source_id=source_id,
                    external_id=external_id,
                    title=entry.get("title") or "Untitled",
                    summary=summary,
                    content_md=content or summary,
                    url=link,
                    image_url=_first_image(entry),
                    author=entry.get("author"),
                    published_at=published_at,
                    raw_json=raw,
                )
            )

        return title, items


rss_connector = RssConnector()
