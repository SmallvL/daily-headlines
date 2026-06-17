# Plugin Template — Adding a New Website Source

## Directory Structure

```
app/plugins/<name>/
├── __init__.py
├── plugin.py
├── auth.py
└── parser.py
```

## \_\_init\_\_.py

```python
from .plugin import <Name>Plugin

Plugin = <Name>Plugin
```

## plugin.py

```python
"""<Name> plugin implementation."""
from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional

import httpx

from app.plugins.base import (
    AuthMethod, AuthResult, FeedItem, ParseResult, QRCodeStatus, SourcePlugin
)

from .auth import <Name>Auth
from .parser import <Name>Parser

logger = logging.getLogger(__name__)


class <Name>Plugin(SourcePlugin):
    plugin_id = "<name>"
    display_name = "<Display Name>"
    description = "<Description>"
    icon_url = "<favicon URL>"
    supported_auth_methods = [AuthMethod.QRCODE, AuthMethod.COOKIE]
    default_source_type = "api"

    async def get_auth_config_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "method": {
                    "type": "string",
                    "enum": ["qrcode", "cookie"],
                    "default": "qrcode"
                },
                "cookie_string": {
                    "type": "string",
                    "title": "Cookie 字符串",
                },
                "fetch_type": {
                    "type": "string",
                    "enum": ["feed"],
                    "default": "feed",
                    "title": "内容类型",
                }
            },
            "required": ["method"]
        }

    async def authenticate(self, method, credentials=None, callback=None) -> AuthResult:
        if method == AuthMethod.QRCODE:
            try:
                qrcode_url, qrcode_image, session_id = await <Name>Auth.generate_qrcode()
                return AuthResult(
                    success=True,
                    qrcode_url=qrcode_url,
                    qrcode_image=qrcode_image,
                    credentials={"qrcode_session_id": session_id},
                    expires_in=300
                )
            except Exception as e:
                return AuthResult(success=False, error=str(e))
        elif method == AuthMethod.COOKIE:
            is_valid = await <Name>Auth.validate_credentials(credentials)
            if is_valid:
                return AuthResult(success=True, credentials=credentials)
            return AuthResult(success=False, error="Cookie invalid or expired")
        return AuthResult(success=False, error=f"Unsupported auth: {method}")

    async def check_qrcode_status(self, session_id: str) -> QRCodeStatus:
        return await <Name>Auth.poll_qrcode_status(session_id)

    async def validate_credentials(self, credentials: Dict[str, Any]) -> bool:
        return await <Name>Auth.validate_credentials(credentials)

    async def refresh_credentials(self, credentials: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if await self.validate_credentials(credentials):
            return credentials
        return None

    async def get_user_info(self, credentials: Dict[str, Any]) -> Optional[Dict[str, str]]:
        return await <Name>Auth.get_user_info(credentials)

    async def get_subscription_types(self) -> List[Dict[str, str]]:
        return [{"id": "feed", "name": "Feed", "description": "Content feed"}]

    async def fetch_feed(self, credentials=None, config=None, cursor=None, limit=20) -> ParseResult:
        if not credentials:
            return ParseResult(success=False, error="Not authenticated")
        try:
            async with httpx.AsyncClient(
                headers=self.get_headers(credentials),
                cookies=credentials.get("cookies", {}),
                timeout=30.0
            ) as client:
                response = await client.get("<API URL>", params={"cursor": cursor or ""})
                data = response.json()
                return <Name>Parser.parse_response(data)
        except httpx.TimeoutException:
            return ParseResult(success=False, error="Request timed out")
        except Exception as e:
            logger.exception(f"Failed to fetch: {e}")
            return ParseResult(success=False, error=str(e))
```

## auth.py

```python
"""<Name> authentication handler."""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Tuple

import httpx

from app.plugins.base import QRCodeStatus

logger = logging.getLogger(__name__)

API = {
    "qrcode_generate": "<QR code generation URL>",
    "qrcode_poll": "<QR code poll URL>",
    "user_info": "<User info URL>",
}


class <Name>Auth:
    @staticmethod
    async def generate_qrcode() -> Tuple[str, str, str]:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(API["qrcode_generate"])
            data = resp.json()
            # Extract qrcode_url, generate base64 image, return session_id
            ...

    @staticmethod
    async def poll_qrcode_status(session_id: str) -> QRCodeStatus:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(API["qrcode_poll"], params={"session": session_id})
            data = resp.json()
            # Map response to QRCodeStatus
            ...

    @staticmethod
    async def validate_credentials(credentials: Dict[str, Any]) -> bool:
        try:
            async with httpx.AsyncClient(
                cookies=credentials.get("cookies", {}),
                timeout=10.0
            ) as client:
                resp = await client.get(API["user_info"])
                return resp.status_code == 200
        except Exception:
            return False

    @staticmethod
    async def get_user_info(credentials: Dict[str, Any]) -> Optional[Dict[str, str]]:
        try:
            async with httpx.AsyncClient(
                cookies=credentials.get("cookies", {}),
                timeout=10.0
            ) as client:
                resp = await client.get(API["user_info"])
                if resp.status_code == 200:
                    data = resp.json()
                    return {"uid": data.get("uid", ""), "name": data.get("name", "")}
        except Exception:
            return None
```

## parser.py

```python
"""<Name> content parser."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.plugins.base import FeedItem, ParseResult


class <Name>Parser:
    @staticmethod
    def parse_response(data: Dict[str, Any]) -> ParseResult:
        items: List[FeedItem] = []
        for raw in data.get("items", []):
            item = FeedItem(
                title=raw.get("title", ""),
                url=raw.get("url", ""),
                summary=raw.get("summary", ""),
                image_url=raw.get("image_url"),
                author=raw.get("author"),
                published_at=raw.get("timestamp"),
                source_id=raw.get("id"),
                tags=raw.get("tags", []),
            )
            items.append(item)
        return ParseResult(
            success=True,
            items=items,
            has_more=data.get("has_more", False),
            next_cursor=data.get("next_cursor"),
        )
```
