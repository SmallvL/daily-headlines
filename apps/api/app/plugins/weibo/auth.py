"""Weibo authentication module with QR code login support."""
from __future__ import annotations

import asyncio
import time
from typing import Any, Dict, Optional, Tuple

import httpx

from app.plugins.base import AuthMethod, AuthResult, QRCodeStatus

# Weibo API endpoints
WEIBO_API = {
    "qrcode_image": "https://login.sina.com.cn/sso/qrcode/image",
    "qrcode_check": "https://login.sina.com.cn/sso/login.php",
    "user_info": "https://weibo.com/ajax/profile/info",
    "feed_friends": "https://weibo.com/ajax/feed/friendstimeline",
    "feed_mymblog": "https://weibo.com/ajax/statuses/mymblog",
}

# In-memory QR code session storage
_qrcode_sessions: Dict[str, Dict[str, Any]] = {}


class WeiboAuth:
    """Weibo authentication handler."""
    
    @staticmethod
    async def generate_qrcode() -> Tuple[str, bytes, str]:
        """Generate QR code for Weibo login.
        
        Returns:
            Tuple of (qrcode_url, qrcode_image_bytes, session_id)
        """
        async with httpx.AsyncClient(
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://weibo.com/",
            },
            timeout=30.0
        ) as client:
            # Get QR code image
            response = await client.get(
                WEIBO_API["qrcode_image"],
                params={"entry": "sso", "size": 180}
            )
            
            # Extract session from response
            if response.status_code != 200 or not response.content:
                raise Exception("微博二维码接口已变更，请使用 Cookie 方式登录（从浏览器复制微博 Cookie）")
            
            qrcode_image = response.content
            
            # Try to get alt from cookies or response
            alt = ""
            for cookie in response.cookies.items():
                if cookie[0] == "SSOLoginState":
                    alt = cookie[1]
            
            if not alt:
                # Generate a unique session ID
                alt = f"weibo_{int(time.time() * 1000)}"
            
            # For Weibo, the QR code URL is the image itself
            qrcode_url = f"https://login.sina.com.cn/sso/qrcode/image?entry=sso&size=180&alt={alt}"
            
            # Store session
            _qrcode_sessions[alt] = {
                "created_at": time.time(),
                "status": QRCodeStatus.PENDING,
                "credentials": None
            }
            
            return qrcode_url, qrcode_image, alt
    
    @staticmethod
    async def poll_qrcode_status(session_id: str) -> QRCodeStatus:
        """Poll QR code scan status.
        
        Args:
            session_id: QR code session ID (alt parameter)
        
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
        
        try:
            async with httpx.AsyncClient(
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Referer": "https://weibo.com/",
                },
                timeout=30.0,
                follow_redirects=True
            ) as client:
                # Check login status
                response = await client.get(
                    WEIBO_API["qrcode_check"],
                    params={
                        "entry": "sso",
                        "returntype": "TEXT",
                        "crossdomain": 1,
                        "cdult": 3,
                        "domain": "weibo.com",
                        "alt": session_id,
                        "savestate": 30,
                        "action": "login"
                    }
                )
                
                data = response.json()
                
                if data.get("retcode") == 20000000:
                    # Login successful
                    cookies = dict(response.cookies)
                    
                    # Get crossdomain cookies
                    crossdomain_url = data.get("data", {}).get("crossdomain_url", "")
                    if crossdomain_url:
                        try:
                            await client.get(crossdomain_url)
                            cookies.update(dict(response.cookies))
                        except Exception:
                            pass
                    
                    credentials = {
                        "cookies": cookies,
                        "cookie_string": "; ".join(f"{k}={v}" for k, v in cookies.items()),
                        "uid": data.get("data", {}).get("uid", ""),
                        "login_time": time.time()
                    }
                    
                    session["status"] = QRCodeStatus.CONFIRMED
                    session["credentials"] = credentials
                    
                    # Get user info
                    user_info = await WeiboAuth.get_user_info(credentials)
                    
                    return QRCodeStatus(
                        status=QRCodeStatus.CONFIRMED,
                        credentials=credentials,
                        user_info=user_info
                    )
                
                elif data.get("retcode") == 50114001:
                    # Not scanned yet
                    return QRCodeStatus(status=QRCodeStatus.PENDING)
                
                elif data.get("retcode") == 50114002:
                    # Scanned but not confirmed
                    return QRCodeStatus(status=QRCodeStatus.SCANNED)
                
                else:
                    # Other status
                    return QRCodeStatus(
                        status=QRCodeStatus.PENDING,
                        error=data.get("reason", "")
                    )
                    
        except Exception as e:
            return QRCodeStatus(
                status=QRCodeStatus.PENDING,
                error=str(e)
            )
    
    @staticmethod
    async def get_user_info(credentials: Dict[str, Any]) -> Optional[Dict[str, str]]:
        """Get Weibo user info.
        
        Args:
            credentials: Authentication credentials
        
        Returns:
            Dict with user info or None
        """
        try:
            async with httpx.AsyncClient(
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Referer": "https://weibo.com/",
                    "X-Requested-With": "XMLHttpRequest",
                },
                cookies=credentials.get("cookies", {}),
                timeout=30.0
            ) as client:
                response = await client.get(WEIBO_API["user_info"])
                data = response.json()
                
                if data.get("ok") == 1:
                    user_data = data.get("data", {}).get("user", {})
                    return {
                        "username": user_data.get("screen_name", ""),
                        "avatar": user_data.get("avatar_hd", ""),
                        "uid": str(user_data.get("id", "")),
                        "description": user_data.get("description", ""),
                        "followers_count": str(user_data.get("followers_count", 0)),
                        "friends_count": str(user_data.get("friends_count", 0))
                    }
        except Exception:
            pass
        return None
    
    @staticmethod
    async def validate_credentials(credentials: Dict[str, Any]) -> bool:
        """Validate Weibo credentials."""
        user_info = await WeiboAuth.get_user_info(credentials)
        return user_info is not None


def _generate_qrcode_image(url: str, box_size: int = 10) -> bytes:
    """Generate QR code image."""
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
        return b""
