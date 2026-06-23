"""Weibo plugin implementation."""
from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional

import httpx

from app.plugins.base import (
    AuthMethod, AuthResult, FeedItem, ParseResult, QRCodeStatus, SourcePlugin
)

from .auth import WeiboAuth, WEIBO_API
from .parser import WeiboParser

logger = logging.getLogger(__name__)


class WeiboPlugin(SourcePlugin):
    """Weibo source plugin with QR code authentication."""
    
    plugin_id = "weibo"
    display_name = "微博"
    description = "微博动态、关注、原创等内容订阅"
    icon_url = "https://weibo.com/favicon.ico"
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
                    "description": "从浏览器复制的 Cookie（包含 SUB 等）"
                },
                "fetch_type": {
                    "type": "string",
                    "enum": ["timeline", "my_blog"],
                    "default": "timeline",
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
        """Perform Weibo authentication."""
        if method == AuthMethod.QRCODE:
            try:
                qrcode_url, qrcode_image, session_id = await WeiboAuth.generate_qrcode()
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
            
            is_valid = await WeiboAuth.validate_credentials(credentials)
            if is_valid:
                user_info = await WeiboAuth.get_user_info(credentials)
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
        return await WeiboAuth.poll_qrcode_status(session_id)
    
    async def validate_credentials(self, credentials: Dict[str, Any]) -> bool:
        """Validate credentials."""
        return await WeiboAuth.validate_credentials(credentials)
    
    async def refresh_credentials(self, credentials: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Refresh credentials."""
        if await self.validate_credentials(credentials):
            return credentials
        return None
    
    async def get_user_info(self, credentials: Dict[str, Any]) -> Optional[Dict[str, str]]:
        """Get user info."""
        return await WeiboAuth.get_user_info(credentials)
    
    async def get_subscription_types(self) -> List[Dict[str, str]]:
        """Get available subscription types."""
        return [
            {
                "id": "timeline",
                "name": "关注动态",
                "description": "关注用户的动态更新"
            },
            {
                "id": "my_blog",
                "name": "我的微博",
                "description": "自己发布的微博"
            }
        ]
    
    async def fetch_feed(
        self,
        credentials: Optional[Dict[str, Any]] = None,
        config: Optional[Dict[str, Any]] = None,
        cursor: Optional[str] = None,
        limit: int = 20
    ) -> ParseResult:
        """Fetch Weibo feed content."""
        if not credentials:
            return ParseResult(success=False, error="未认证，请先登录")
        
        fetch_type = (config or {}).get("fetch_type", "timeline")
        
        try:
            headers = self.get_headers(credentials)
            headers["Referer"] = "https://weibo.com/"
            async with httpx.AsyncClient(
                headers=headers,
                cookies=credentials.get("cookies", {}),
                timeout=30.0
            ) as client:
                if fetch_type == "timeline":
                    # Fetch friends timeline
                    params = {
                        "list_id": "",
                        "max_id": cursor or "",
                        "count": limit,
                        "locale": "zh-CN",
                    }
                    response = await client.get(
                        WEIBO_API["feed_friends"],
                        params=params
                    )
                    data = response.json()
                    
                    if data.get("ok") != 1:
                        return ParseResult(
                            success=False,
                            error=data.get("msg", "获取信息流失败")
                        )
                    
                    return WeiboParser.parse_timeline_response(data)
                
                elif fetch_type == "my_blog":
                    # Fetch user's own blogs
                    uid = credentials.get("uid", "")
                    if not uid:
                        return ParseResult(
                            success=False,
                            error="无法获取用户ID"
                        )
                    
                    params = {
                        "uid": uid,
                        "page": int(cursor or "1"),
                        "feature": 0,
                    }
                    response = await client.get(
                        WEIBO_API["feed_mymblog"],
                        params=params
                    )
                    data = response.json()
                    
                    if data.get("ok") != 1:
                        return ParseResult(
                            success=False,
                            error=data.get("msg", "获取微博失败")
                        )
                    
                    return WeiboParser.parse_user_blogs_response(data)
                
                else:
                    return ParseResult(
                        success=False,
                        error=f"不支持的内容类型: {fetch_type}"
                    )
                    
        except httpx.TimeoutException:
            return ParseResult(success=False, error="请求超时，请检查网络")
        except Exception as e:
            logger.exception(f"Failed to fetch Weibo feed: {e}")
            return ParseResult(success=False, error=str(e))
