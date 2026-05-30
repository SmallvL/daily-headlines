"""Image proxy to bypass hotlink protection (403 from B站/IT之家 etc.).

GET /api/proxy/image?url=<encoded_image_url>
Returns the image with proper Referer headers so origin servers don't block it.
"""

from __future__ import annotations

import re
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

router = APIRouter()

# Allowed image host patterns (regex)
ALLOWED_HOSTS = [
    r"^(.+\.)?hdslb\.com$",       # B站
    r"^(.+\.)?bilibili\.com$",     # B站
    r"^(.+\.)?ithome\.com$",       # IT之家
    r"^(.+\.)?img\.ithome\.com$",  # IT之家图片
    r"^(.+\.)?ithome\.net$",       # IT之家CDN
    r"^(.+\.)?sinaimg\.cn$",       # 新浪
    r"^(.+\.)?wpcom\.cn$",         # WordPress
    r"^(.+\.)?githubusercontent\.com$",  # GitHub
    r"^(.+\.)?36krcdn\.com$",      # 36氪
    r"^(.+\.)?36kr\.com$",         # 36氪
    r"^(.+\.)?nocode\.com$",       # nocode
    r"^(.+\.)?virxact\.com$",      # virxact
    r"^(.+\.)?126\.net$",          # 网易
    r"^(.+\.)?163\.com$",          # 网易
    r"^(.+\.)?qq\.com$",           # 腾讯
    r"^(.+\.)?weixin\.qq\.com$",   # 微信
    r"^(.+\.)?sohu\.com$",         # 搜狐
    r"^(.+\.)?zhihu\.com$",        # 知乎
    r"^(.+\.)?doubanio\.com$",     # 豆瓣
    r"^(.+\.)?douban\.com$",       # 豆瓣
]


def _is_host_allowed(host: str) -> bool:
    """Check if the image host is in the allowlist."""
    host = host.lower().split(":")[0]  # strip port
    return any(re.match(pattern, host) for pattern in ALLOWED_HOSTS)


@router.get("/image")
async def proxy_image(url: str = Query(..., description="Image URL to proxy")):
    """Proxy an image request to bypass hotlink protection."""

    # Validate URL
    try:
        parsed = urlparse(url)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid URL") from None

    if parsed.scheme not in ("http", "https"):
        raise HTTPException(status_code=400, detail="Only http/https URLs allowed")

    if not _is_host_allowed(parsed.netloc):
        raise HTTPException(
            status_code=403,
            detail=f"Host not allowed: {parsed.netloc}",
        )

    # Fetch with proper headers to bypass hotlink protection
    # Set Referer to the origin domain
    origin = f"{parsed.scheme}://{parsed.netloc}"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
        "Referer": origin,
        "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
    }

    async with httpx.AsyncClient(
        timeout=15.0,
        follow_redirects=True,
        verify=False,
    ) as client:
        try:
            resp = await client.get(url, headers=headers)
        except httpx.HTTPError as e:
            raise HTTPException(status_code=502, detail=f"Fetch failed: {e}") from e

    if resp.status_code != 200:
        raise HTTPException(
            status_code=resp.status_code,
            detail=f"Upstream returned {resp.status_code}",
        )

    # Determine content type
    content_type = resp.headers.get("content-type", "image/jpeg")
    if not content_type.startswith("image/"):
        content_type = "image/jpeg"

    # Return the image with caching headers
    return Response(
        content=resp.content,
        media_type=content_type,
        headers={
            "Cache-Control": "public, max-age=86400",  # cache 24h
            "Access-Control-Allow-Origin": "*",
        },
    )
