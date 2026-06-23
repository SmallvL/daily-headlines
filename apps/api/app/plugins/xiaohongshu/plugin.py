"""Xiaohongshu plugin implementation."""
from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional

import httpx

from app.plugins.base import (
    AuthMethod, AuthResult, FeedItem, ParseResult, QRCodeStatus, SourcePlugin
)

from .auth import XiaohongshuAuth, XHS_API
from .parser import XiaohongshuParser

logger = logging.getLogger(__name__)


class XiaohongshuPlugin(SourcePlugin):
    """Xiaohongshu (Little Red Book) source plugin."""
    
    plugin_id = "xiaohongshu"
    display_name = "小红书"
    description = "小红书笔记、关注、推荐等内容订阅"
    icon_url = "https://www.xiaohongshu.com/favicon.ico"
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
                    "description": "从浏览器复制的 Cookie（包含 web_session 等）"
                },
                "fetch_type": {
                    "type": "string",
                    "enum": ["follow", "recommend", "user_notes"],
                    "default": "follow",
                    "title": "内容类型",
                    "description": "获取的内容类型"
                },
                "user_id": {
                    "type": "string",
                    "title": "用户ID",
                    "description": "获取指定用户的笔记（仅用户笔记类型）"
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
        """Perform Xiaohongshu authentication."""
        if method == AuthMethod.QRCODE:
            try:
                qrcode_url, qrcode_image, session_id = await XiaohongshuAuth.generate_qrcode()
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
            
            is_valid = await XiaohongshuAuth.validate_credentials(credentials)
            if is_valid:
                user_info = await XiaohongshuAuth.get_user_info(credentials)
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
        return await XiaohongshuAuth.poll_qrcode_status(session_id)
    
    async def validate_credentials(self, credentials: Dict[str, Any]) -> bool:
        """Validate credentials."""
        return await XiaohongshuAuth.validate_credentials(credentials)
    
    async def refresh_credentials(self, credentials: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Refresh credentials."""
        if await self.validate_credentials(credentials):
            return credentials
        return None
    
    async def get_user_info(self, credentials: Dict[str, Any]) -> Optional[Dict[str, str]]:
        """Get user info."""
        return await XiaohongshuAuth.get_user_info(credentials)
    
    async def get_subscription_types(self) -> List[Dict[str, str]]:
        """Get available subscription types."""
        return [
            {
                "id": "follow",
                "name": "关注动态",
                "description": "关注用户的笔记更新"
            },
            {
                "id": "recommend",
                "name": "推荐内容",
                "description": "小红书推荐内容"
            },
            {
                "id": "user_notes",
                "name": "用户笔记",
                "description": "指定用户的笔记列表"
            }
        ]
    
    async def fetch_feed(
        self,
        credentials: Optional[Dict[str, Any]] = None,
        config: Optional[Dict[str, Any]] = None,
        cursor: Optional[str] = None,
        limit: int = 20
    ) -> ParseResult:
        """Fetch Xiaohongshu feed content."""
        if not credentials:
            return ParseResult(success=False, error="未认证，请先登录")
        
        fetch_type = (config or {}).get("fetch_type", "follow")
        
        try:
            headers = self.get_headers(credentials)
            headers["Referer"] = "https://www.xiaohongshu.com/"
            async with httpx.AsyncClient(
                headers=headers,
                cookies=credentials.get("cookies", {}),
                timeout=30.0
            ) as client:
                if fetch_type == "follow":
                    # Fetch follow feed
                    params = {
                        "cursor": cursor or "",
                        "num": limit,
                        "refresh_type": 1,
                    }
                    response = await client.get(
                        XHS_API["feed_follow"],
                        params=params
                    )
                    data = response.json()
                    
                    if not data.get("success"):
                        return ParseResult(
                            success=False,
                            error=data.get("msg", "获取关注动态失败")
                        )
                    
                    return XiaohongshuParser.parse_feed_response(data.get("data", {}))
                
                elif fetch_type == "recommend":
                    # Fetch recommend feed
                    payload = {
                        "cursor_score": cursor or "",
                        "num": limit,
                        "refresh_type": 1,
                        "note_index": 0,
                        "unread_begin_note_id": "",
                        "unread_end_note_id": "",
                        "unread_note_count": 0,
                        "category": "homefeed_recommend",
                    }
                    response = await client.post(
                        XHS_API["feed_recommend"],
                        json=payload
                    )
                    data = response.json()
                    
                    if not data.get("success"):
                        return ParseResult(
                            success=False,
                            error=data.get("msg", "获取推荐内容失败")
                        )
                    
                    return XiaohongshuParser.parse_feed_response(data.get("data", {}))
                
                elif fetch_type == "user_notes":
                    # Fetch user notes
                    user_id = (config or {}).get("user_id", "")
                    if not user_id:
                        return ParseResult(
                            success=False,
                            error="请指定用户ID"
                        )
                    
                    params = {
                        "user_id": user_id,
                        "cursor": cursor or "",
                        "num": limit,
                    }
                    response = await client.get(
                        XHS_API["user_notes"],
                        params=params
                    )
                    data = response.json()
                    
                    if not data.get("success"):
                        return ParseResult(
                            success=False,
                            error=data.get("msg", "获取用户笔记失败")
                        )
                    
                    return XiaohongshuParser.parse_user_notes_response(data)
                
                else:
                    return ParseResult(
                        success=False,
                        error=f"不支持的内容类型: {fetch_type}"
                    )
                    
        except httpx.TimeoutException:
            return ParseResult(success=False, error="请求超时，请检查网络")
        except Exception as e:
            logger.exception(f"Failed to fetch Xiaohongshu feed: {e}")
            return ParseResult(success=False, error=str(e))
