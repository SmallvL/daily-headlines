"""Toutiao plugin implementation."""
from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional

import httpx

from app.plugins.base import (
    AuthMethod, AuthResult, FeedItem, ParseResult, QRCodeStatus, SourcePlugin
)

from .auth import ToutiaoAuth, TOUTIAO_API
from .parser import ToutiaoParser

logger = logging.getLogger(__name__)


class ToutiaoPlugin(SourcePlugin):
    """Toutiao (Today's Headlines) source plugin."""
    
    plugin_id = "toutiao"
    display_name = "今日头条"
    description = "今日头条文章、关注、推荐等内容订阅"
    icon_url = "https://www.toutiao.com/favicon.ico"
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
                    "description": "从浏览器复制的 Cookie（包含 sso_uid_tt 等）"
                },
                "fetch_type": {
                    "type": "string",
                    "enum": ["feed", "user_articles"],
                    "default": "feed",
                    "title": "内容类型",
                    "description": "获取的内容类型"
                },
                "user_id": {
                    "type": "string",
                    "title": "用户ID",
                    "description": "获取指定用户的文章（仅用户文章类型）"
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
        """Perform Toutiao authentication."""
        if method == AuthMethod.QRCODE:
            try:
                qrcode_url, qrcode_image, session_id = await ToutiaoAuth.generate_qrcode()
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
            if not credentials or "cookie_string" not in credentials:
                return AuthResult(
                    success=False,
                    error="Cookie 字符串不能为空"
                )
            
            is_valid = await ToutiaoAuth.validate_credentials(credentials)
            if is_valid:
                user_info = await ToutiaoAuth.get_user_info(credentials)
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
        return await ToutiaoAuth.poll_qrcode_status(session_id)
    
    async def validate_credentials(self, credentials: Dict[str, Any]) -> bool:
        """Validate credentials."""
        return await ToutiaoAuth.validate_credentials(credentials)
    
    async def refresh_credentials(self, credentials: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Refresh credentials."""
        if await self.validate_credentials(credentials):
            return credentials
        return None
    
    async def get_user_info(self, credentials: Dict[str, Any]) -> Optional[Dict[str, str]]:
        """Get user info."""
        return await ToutiaoAuth.get_user_info(credentials)
    
    async def get_subscription_types(self) -> List[Dict[str, str]]:
        """Get available subscription types."""
        return [
            {
                "id": "feed",
                "name": "推荐",
                "description": "头条推荐内容"
            },
            {
                "id": "user_articles",
                "name": "用户文章",
                "description": "指定用户的原创文章"
            }
        ]
    
    async def fetch_feed(
        self,
        credentials: Optional[Dict[str, Any]] = None,
        config: Optional[Dict[str, Any]] = None,
        cursor: Optional[str] = None,
        limit: int = 20
    ) -> ParseResult:
        """Fetch Toutiao feed content."""
        if not credentials:
            return ParseResult(success=False, error="未认证，请先登录")
        
        fetch_type = (config or {}).get("fetch_type", "feed")
        
        try:
            headers = self.get_headers(credentials)
            headers["Referer"] = "https://www.toutiao.com/"
            async with httpx.AsyncClient(
                headers=headers,
                cookies=credentials.get("cookies", {}),
                timeout=30.0
            ) as client:
                if fetch_type == "feed":
                    # Fetch recommended feed
                    params = {
                        "max_behot_time": cursor or "",
                        "aid": "24",
                        "app_name": "web_search",
                        "offset": 0,
                        "count": limit,
                    }
                    response = await client.get(
                        TOUTIAO_API["feed_follow"],
                        params=params
                    )
                    data = response.json()
                    
                    return ToutiaoParser.parse_feed_response(data)
                
                elif fetch_type == "user_articles":
                    # Fetch user articles
                    user_id = (config or {}).get("user_id", "")
                    if not user_id:
                        return ParseResult(
                            success=False,
                            error="请指定用户ID"
                        )
                    
                    params = {
                        "user_id": user_id,
                        "count": limit,
                        "max_behot_time": cursor or "",
                    }
                    response = await client.get(
                        TOUTIAO_API["user_articles"],
                        params=params
                    )
                    data = response.json()
                    
                    return ToutiaoParser.parse_user_articles_response(data)
                
                else:
                    return ParseResult(
                        success=False,
                        error=f"不支持的内容类型: {fetch_type}"
                    )
                    
        except httpx.TimeoutException:
            return ParseResult(success=False, error="请求超时，请检查网络")
        except Exception as e:
            logger.exception(f"Failed to fetch Toutiao feed: {e}")
            return ParseResult(success=False, error=str(e))
