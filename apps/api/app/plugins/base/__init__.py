"""Base classes and interfaces for source plugins."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Type

import httpx


class AuthMethod(str, Enum):
    """Supported authentication methods."""
    NONE = "none"
    COOKIE = "cookie"
    TOKEN = "token"
    QRCODE = "qrcode"  # 二维码扫码登录
    OAUTH = "oauth"     # OAuth 授权
    CUSTOM = "custom"


@dataclass
class AuthConfig:
    """Authentication configuration for a source."""
    method: AuthMethod = AuthMethod.NONE
    credentials: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AuthResult:
    """Result of an authentication attempt."""
    success: bool
    credentials: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    # For QR code auth
    qrcode_url: Optional[str] = None  # 二维码内容/URL
    qrcode_image: Optional[bytes] = None  # 二维码图片数据
    auth_url: Optional[str] = None  # 授权页面 URL
    expires_in: Optional[int] = None  # 过期时间（秒）
    user_info: Optional[Dict[str, str]] = None  # 用户信息（用户名、头像等）


@dataclass
class QRCodeStatus:
    """QR code scan status."""
    PENDING = "pending"  # 等待扫码
    SCANNED = "scanned"  # 已扫码，待确认
    CONFIRMED = "confirmed"  # 已确认
    EXPIRED = "expired"  # 已过期
    CANCELLED = "cancelled"  # 已取消
    
    status: str
    credentials: Optional[Dict[str, Any]] = None
    user_info: Optional[Dict[str, str]] = None  # 用户名、头像等
    error: Optional[str] = None


@dataclass
class ParseResult:
    """Result of content parsing."""
    success: bool
    items: List[Dict[str, Any]] = field(default_factory=list)
    error: Optional[str] = None
    has_more: bool = False
    next_cursor: Optional[str] = None
    total_count: Optional[int] = None


@dataclass
class FeedItem:
    """Parsed feed item."""
    title: str
    url: str
    summary: Optional[str] = None
    content: Optional[str] = None
    image_url: Optional[str] = None
    author: Optional[str] = None
    published_at: Optional[str] = None  # ISO format
    source_id: Optional[str] = None  # Platform-specific ID
    tags: List[str] = field(default_factory=list)
    extra: Dict[str, Any] = field(default_factory=dict)


class SourcePlugin(ABC):
    """Base class for source plugins."""
    
    # Plugin metadata
    plugin_id: str = ""  # Unique plugin identifier, e.g., "bilibili"
    display_name: str = ""  # Display name, e.g., "哔哩哔哩"
    description: str = ""  # Plugin description
    icon_url: Optional[str] = None  # Plugin icon URL
    supported_auth_methods: List[AuthMethod] = field(default_factory=lambda: [AuthMethod.NONE])
    default_source_type: str = "api"  # rss | api | web
    
    @abstractmethod
    async def get_auth_config_schema(self) -> Dict[str, Any]:
        """Return JSON Schema for authentication configuration.
        
        This defines what fields the frontend should show for this plugin's auth.
        """
        pass
    
    @abstractmethod
    async def authenticate(
        self, 
        method: AuthMethod,
        credentials: Optional[Dict[str, Any]] = None,
        callback: Optional[Callable] = None
    ) -> AuthResult:
        """Perform authentication.
        
        Args:
            method: Authentication method to use
            credentials: Existing credentials (for refresh/re-auth)
            callback: Optional callback for async auth flow (e.g., QR code status)
        
        Returns:
            AuthResult with success status and credentials
        """
        pass
    
    @abstractmethod
    async def check_qrcode_status(self, session_id: str) -> QRCodeStatus:
        """Check QR code authentication status.
        
        Args:
            session_id: QR code session identifier
        
        Returns:
            QRCodeStatus with current status
        """
        pass
    
    @abstractmethod
    async def validate_credentials(self, credentials: Dict[str, Any]) -> bool:
        """Validate if credentials are still valid.
        
        Args:
            credentials: Stored credentials
        
        Returns:
            True if credentials are valid
        """
        pass
    
    @abstractmethod
    async def refresh_credentials(self, credentials: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Refresh expired credentials if possible.
        
        Args:
            credentials: Expired credentials
        
        Returns:
            New credentials if refresh succeeded, None otherwise
        """
        pass
    
    @abstractmethod
    async def fetch_feed(
        self,
        credentials: Optional[Dict[str, Any]] = None,
        config: Optional[Dict[str, Any]] = None,
        cursor: Optional[str] = None,
        limit: int = 20
    ) -> ParseResult:
        """Fetch and parse feed content.
        
        Args:
            credentials: Authentication credentials
            config: Source-specific configuration
            cursor: Pagination cursor
            limit: Number of items to fetch
        
        Returns:
            ParseResult with parsed items
        """
        pass
    
    async def get_user_info(self, credentials: Dict[str, Any]) -> Optional[Dict[str, str]]:
        """Get authenticated user information.
        
        Args:
            credentials: Authentication credentials
        
        Returns:
            Dict with user info (username, avatar, etc.) or None
        """
        return None
    
    async def get_subscription_types(self) -> List[Dict[str, str]]:
        """Get available subscription/content types for this source.
        
        Returns:
            List of dicts with 'id', 'name', 'description' keys
        """
        return [{"id": "default", "name": "默认", "description": "默认内容源"}]
    
    def get_headers(self, credentials: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
        """Get HTTP headers for requests.
        
        Args:
            credentials: Authentication credentials
        
        Returns:
            Dict of HTTP headers
        """
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/html, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }
        return headers
    
    def _build_client(
        self, 
        credentials: Optional[Dict[str, Any]] = None,
        timeout: float = 30.0,
        verify_ssl: bool = True
    ) -> httpx.AsyncClient:
        """Build httpx client with proper headers and cookies.
        
        Args:
            credentials: Authentication credentials
            timeout: Request timeout in seconds
            verify_ssl: Verify SSL certificates
        
        Returns:
            Configured httpx.AsyncClient
        """
        headers = self.get_headers(credentials)
        cookies = {}
        
        if credentials:
            if "cookies" in credentials:
                cookies.update(credentials["cookies"])
            if "cookie_string" in credentials:
                # Parse cookie string
                for item in credentials["cookie_string"].split(";"):
                    item = item.strip()
                    if "=" in item:
                        key, value = item.split("=", 1)
                        cookies[key.strip()] = value.strip()
            if "token" in credentials:
                headers["Authorization"] = f"Bearer {credentials['token']}"
            if "api_key" in credentials:
                headers["X-API-Key"] = credentials["api_key"]
        
        return httpx.AsyncClient(
            headers=headers,
            cookies=cookies,
            timeout=timeout,
            verify=verify_ssl,
            follow_redirects=True
        )
