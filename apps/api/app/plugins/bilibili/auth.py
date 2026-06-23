"""Bilibili authentication module with QR code login support."""
from __future__ import annotations

import asyncio
import hashlib
import time
import urllib.parse
from typing import Any, Dict, Optional, Tuple

import httpx

from app.plugins.base import AuthMethod, AuthResult, QRCodeStatus

# Bilibili API endpoints
BILIBILI_API = {
    "qrcode_generate": "https://passport.bilibili.com/x/passport-login/web/qrcode/generate",
    "qrcode_poll": "https://passport.bilibili.com/x/passport-login/web/qrcode/poll",
    "user_info": "https://api.bilibili.com/x/web-interface/nav",
    # "dynamic" = 关注用户的动态（feed/all），需要登录
    # "space" = 指定 UP 主的动态，需要 host_mid 参数
    "feed_dynamic": "https://api.bilibili.com/x/polymer/web-dynamic/v1/feed/all",
    "feed_space": "https://api.bilibili.com/x/polymer/web-dynamic/v1/feed/space",
    "feed_attention": "https://api.bilibili.com/x/polymer/web-dynamic/v1/feed/all",
}

# In-memory QR code session storage (in production, use Redis)
_qrcode_sessions: Dict[str, Dict[str, Any]] = {}


def _get_wbi_keys() -> Tuple[str, str]:
    """Generate WBI signature keys (simplified)."""
    # This is a simplified version - in production, fetch from API
    return "7cd084941338484aae1ad9425b84077c", "4932caff0ff746eab6f01bf08b70ac45"


def _sign_wbi(params: Dict[str, Any], wbi_key: str) -> str:
    """Generate WBI signature for request."""
    # Simplified WBI signing
    sorted_params = sorted(params.items())
    query = urllib.parse.urlencode(sorted_params)
    return hashlib.md5((query + wbi_key).encode()).hexdigest()


class BilibiliAuth:
    """Bilibili authentication handler with QR code login support."""
    
    @staticmethod
    async def generate_qrcode() -> Tuple[str, bytes, str]:
        """Generate QR code for Bilibili login.
        
        Returns:
            Tuple of (qrcode_url, qrcode_image_bytes, session_id)
        """
        async with httpx.AsyncClient(
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://www.bilibili.com/",
            },
            timeout=30.0
        ) as client:
            response = await client.get(BILIBILI_API["qrcode_generate"])
            data = response.json()
            
            if data["code"] != 0:
                raise Exception(f"Failed to generate QR code: {data.get('message')}")
            
            qrcode_url = data["data"]["url"]
            session_id = data["data"]["qrcode_key"]
            
            # Generate QR code image
            qrcode_image = _generate_qrcode_image(qrcode_url)
            
            # Store session
            _qrcode_sessions[session_id] = {
                "created_at": time.time(),
                "status": QRCodeStatus.PENDING,
                "credentials": None
            }
            
            return qrcode_url, qrcode_image, session_id
    
    @staticmethod
    async def poll_qrcode_status(session_id: str) -> QRCodeStatus:
        """Poll QR code scan status.
        
        Args:
            session_id: QR code session ID
        
        Returns:
            QRCodeStatus with current status
        """
        if session_id not in _qrcode_sessions:
            return QRCodeStatus(
                status=QRCodeStatus.EXPIRED,
                error="Session not found"
            )
        
        session = _qrcode_sessions[session_id]
        
        # Check if expired (5 minutes)
        if time.time() - session["created_at"] > 300:
            del _qrcode_sessions[session_id]
            return QRCodeStatus(
                status=QRCodeStatus.EXPIRED,
                error="QR code expired"
            )
        
        async with httpx.AsyncClient(
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://www.bilibili.com/",
            },
            timeout=30.0
        ) as client:
            response = await client.get(
                BILIBILI_API["qrcode_poll"],
                params={"qrcode_key": session_id}
            )
            data = response.json()
            
            if data["code"] != 0:
                return QRCodeStatus(
                    status=QRCodeStatus.EXPIRED,
                    error=data.get("message", "Unknown error")
                )
            
            status_code = data["data"]["code"]
            
            if status_code == 0:
                # Login successful — B站 returns cookies via the sync URL query string
                login_data = data["data"]
                cookies = dict(response.cookies)
                redirect_url = login_data.get("url", "")
                if redirect_url:
                    # Parse cookies from the redirect URL query string
                    parsed = urllib.parse.urlparse(redirect_url)
                    qs = urllib.parse.parse_qs(parsed.query)
                    for key in ("SESSDATA", "bili_jct", "DedeUserID", "DedeUserID__ckMd5", "sid"):
                        if key in qs and qs[key]:
                            cookies[key] = qs[key][0]
                # Also follow the sync URL to set any remaining cookies
                if redirect_url and "SESSDATA" in cookies:
                    try:
                        sync_resp = await client.get(redirect_url, follow_redirects=False)
                        for k, v in sync_resp.cookies.items():
                            if k not in cookies:
                                cookies[k] = v
                    except Exception:
                        pass

                credentials = {
                    "cookies": cookies,
                    "cookie_string": "; ".join(f"{k}={v}" for k, v in cookies.items()),
                    "uid": cookies.get("DedeUserID") or str(login_data.get("uid", "")),
                    "login_time": time.time(),
                    "refresh_token": login_data.get("refresh_token"),
                }

                # Update session
                session["status"] = QRCodeStatus.CONFIRMED
                session["credentials"] = credentials

                # Get user info
                user_info = await BilibiliAuth.get_user_info(credentials)

                return QRCodeStatus(
                    status=QRCodeStatus.CONFIRMED,
                    credentials=credentials,
                    user_info=user_info
                )
            
            elif status_code == 86101:
                # Not scanned yet
                return QRCodeStatus(status=QRCodeStatus.PENDING)
            
            elif status_code == 86090:
                # Scanned but not confirmed
                return QRCodeStatus(status=QRCodeStatus.SCANNED)
            
            elif status_code == 86038:
                # Expired
                del _qrcode_sessions[session_id]
                return QRCodeStatus(
                    status=QRCodeStatus.EXPIRED,
                    error="QR code expired"
                )
            
            else:
                return QRCodeStatus(
                    status=QRCodeStatus.CANCELLED,
                    error=f"Unknown status: {status_code}"
                )
    
    @staticmethod
    async def get_user_info(credentials: Dict[str, Any]) -> Optional[Dict[str, str]]:
        """Get Bilibili user info.
        
        Args:
            credentials: Authentication credentials
        
        Returns:
            Dict with user info or None
        """
        try:
            async with httpx.AsyncClient(
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Referer": "https://www.bilibili.com/",
                },
                cookies=credentials.get("cookies", {}),
                timeout=30.0
            ) as client:
                response = await client.get(BILIBILI_API["user_info"])
                data = response.json()
                
                if data["code"] == 0 and data.get("data", {}).get("isLogin"):
                    user_data = data["data"]
                    return {
                        "username": user_data.get("uname", ""),
                        "avatar": user_data.get("face", ""),
                        "uid": str(user_data.get("mid", "")),
                        "level": str(user_data.get("level_info", {}).get("current_level", ""))
                    }
        except Exception:
            pass
        return None
    
    @staticmethod
    async def validate_credentials(credentials: Dict[str, Any]) -> bool:
        """Validate Bilibili credentials.
        
        Args:
            credentials: Stored credentials
        
        Returns:
            True if credentials are valid
        """
        user_info = await BilibiliAuth.get_user_info(credentials)
        return user_info is not None
    
    @staticmethod
    async def check_login_status(credentials: Dict[str, Any]) -> Dict[str, Any]:
        """Check Bilibili login status.
        
        Args:
            credentials: Stored credentials
        
        Returns:
            Dict with login status info
        """
        user_info = await BilibiliAuth.get_user_info(credentials)
        
        if user_info:
            return {
                "is_login": True,
                "user_info": user_info
            }
        return {"is_login": False}


def _generate_qrcode_image(url: str, box_size: int = 10) -> bytes:
    """Generate QR code image from URL.
    
    Args:
        url: URL to encode
        box_size: Size of each box in pixels
    
    Returns:
        PNG image bytes
    """
    try:
        import qrcode
        from io import BytesIO
        
        qr = qrcode.QRCode(version=1, box_size=box_size, border=4)
        qr.add_data(url)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        return buffer.getvalue()
    except ImportError:
        # If qrcode not installed, return empty bytes
        return b""
