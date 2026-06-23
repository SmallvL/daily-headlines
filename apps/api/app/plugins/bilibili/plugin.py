"""Bilibili plugin implementation."""
from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional

import httpx

from app.plugins.base import (
    AuthMethod, AuthResult, FeedItem, ParseResult, QRCodeStatus, SourcePlugin
)

from .auth import BilibiliAuth, BILIBILI_API
from .parser import BilibiliParser

logger = logging.getLogger(__name__)


class BilibiliPlugin(SourcePlugin):
    """Bilibili source plugin with QR code authentication."""
    
    plugin_id = "bilibili"
    display_name = "哔哩哔哩"
    description = "B站动态、视频、文章等内容订阅"
    icon_url = "https://www.bilibili.com/favicon.ico"
    supported_auth_methods = [AuthMethod.QRCODE, AuthMethod.COOKIE]
    default_source_type = "api"
    
    async def get_auth_config_schema(self) -> Dict[str, Any]:
        """Return auth config schema for frontend."""
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
                    "description": "从浏览器复制的 Cookie（包含 SESSDATA 等）"
                },
                "fetch_type": {
                    "type": "string",
                    "enum": ["dynamic", "feed", "article"],
                    "default": "dynamic",
                    "title": "内容类型",
                    "description": "获取的内容类型"
                }
            },
            "required": ["method"]
        }
    
    async def authenticate(
        self,
        method: AuthMethod,
        credentials: Optional[Dict[str, Any]] = None,
        callback: Optional[Callable] = None
    ) -> AuthResult:
        """Perform Bilibili authentication.
        
        Args:
            method: Authentication method (qrcode or cookie)
            credentials: Existing credentials for re-auth
            callback: Callback for QR code status updates
        """
        if method == AuthMethod.QRCODE:
            try:
                qrcode_url, qrcode_image, session_id = await BilibiliAuth.generate_qrcode()
                return AuthResult(
                    success=True,
                    qrcode_url=qrcode_url,
                    qrcode_image=qrcode_image,
                    credentials={"qrcode_session_id": session_id},
                    expires_in=300  # 5 minutes
                )
            except Exception as e:
                return AuthResult(success=False, error=str(e))
        
        elif method == AuthMethod.COOKIE:
            if not credentials or "cookie_string" not in credentials:
                return AuthResult(
                    success=False,
                    error="Cookie 字符串不能为空"
                )
            
            # Validate cookie
            is_valid = await BilibiliAuth.validate_credentials(credentials)
            if is_valid:
                user_info = await BilibiliAuth.get_user_info(credentials)
                return AuthResult(
                    success=True,
                    credentials=credentials,
                    user_info=user_info
                )
            else:
                return AuthResult(
                    success=False,
                    error="Cookie 无效或已过期"
                )
        
        return AuthResult(
            success=False,
            error=f"不支持的认证方式: {method}"
        )
    
    async def check_qrcode_status(self, session_id: str) -> QRCodeStatus:
        """Check QR code scan status."""
        return await BilibiliAuth.poll_qrcode_status(session_id)
    
    async def validate_credentials(self, credentials: Dict[str, Any]) -> bool:
        """Validate credentials."""
        return await BilibiliAuth.validate_credentials(credentials)
    
    async def refresh_credentials(self, credentials: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Refresh credentials (Bilibili cookies don't support auto-refresh)."""
        # Check if current credentials are still valid
        if await self.validate_credentials(credentials):
            return credentials
        return None
    
    async def get_user_info(self, credentials: Dict[str, Any]) -> Optional[Dict[str, str]]:
        """Get user info."""
        return await BilibiliAuth.get_user_info(credentials)
    
    async def get_subscription_types(self) -> List[Dict[str, str]]:
        """Get available subscription types."""
        return [
            {
                "id": "dynamic",
                "name": "动态",
                "description": "关注用户的动态更新（视频、图文、转发等）"
            },
            {
                "id": "feed",
                "name": "信息流",
                "description": "综合信息流（推荐、关注等）"
            },
            {
                "id": "article",
                "name": "专栏文章",
                "description": "专栏文章更新"
            }
        ]
    
    async def fetch_feed(
        self,
        credentials: Optional[Dict[str, Any]] = None,
        config: Optional[Dict[str, Any]] = None,
        cursor: Optional[str] = None,
        limit: int = 20
    ) -> ParseResult:
        """Fetch Bilibili feed content.
        
        Args:
            credentials: Authentication credentials
            config: Source configuration (fetch_type, etc.)
            cursor: Pagination cursor
            limit: Number of items to fetch
        """
        if not credentials:
            return ParseResult(success=False, error="未认证，请先登录")
        
        fetch_type = (config or {}).get("fetch_type", "dynamic")
        
        try:
            headers = self.get_headers(credentials)
            headers["Referer"] = "https://www.bilibili.com/"
            async with httpx.AsyncClient(
                headers=headers,
                cookies=credentials.get("cookies", {}),
                timeout=30.0
            ) as client:
                if fetch_type == "dynamic":
                    # Fetch user's followed dynamics (feed/all)
                    params = {
                        "timezone_offset": -480,
                        "type": "all",
                        "offset": cursor or "",
                        "features": "itemOpusStyle,listOnlyfans,opusBigCover,onlyfansVote,decorationCard,onlyfansAssetsV2,forwardListHidden,ugcDelete",
                    }
                    response = await client.get(
                        BILIBILI_API["feed_dynamic"],
                        params=params
                    )
                    data = response.json()

                    if data.get("code") != 0:
                        return ParseResult(
                            success=False,
                            error=data.get("message", "获取动态失败")
                        )

                    return BilibiliParser.parse_dynamics_response(data.get("data", {}))
                
                elif fetch_type == "feed":
                    # Fetch attention feed
                    params = {
                        "offset": cursor or "",
                        "timezone_offset": -480,
                    }
                    response = await client.get(
                        BILIBILI_API["feed_attention"],
                        params=params
                    )
                    data = response.json()
                    
                    if data.get("code") != 0:
                        return ParseResult(
                            success=False,
                            error=data.get("message", "获取信息流失败")
                        )
                    
                    return BilibiliParser.parse_feed_response(data.get("data", {}))
                
                elif fetch_type == "article":
                    # Fetch articles
                    params = {
                        "category_id": 0,
                        "page_size": limit,
                        "sort_type": 0,
                        "pn": int(cursor or "1"),
                    }
                    response = await client.get(
                        "https://api.bilibili.com/x/article/list/web/articles",
                        params=params
                    )
                    data = response.json()
                    
                    if data.get("code") != 0:
                        return ParseResult(
                            success=False,
                            error=data.get("message", "获取文章失败")
                        )
                    
                    return BilibiliParser.parse_article_list(data.get("data", {}))
                
                else:
                    return ParseResult(
                        success=False,
                        error=f"不支持的内容类型: {fetch_type}"
                    )
                    
        except httpx.TimeoutException:
            return ParseResult(success=False, error="请求超时，请检查网络")
        except Exception as e:
            logger.exception(f"Failed to fetch Bilibili feed: {e}")
            return ParseResult(success=False, error=str(e))
