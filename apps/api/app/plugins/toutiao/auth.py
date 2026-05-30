"""Toutiao (Today's Headlines) authentication module."""
from __future__ import annotations

import asyncio
import time
import uuid
from typing import Any, Dict, Optional, Tuple

import httpx

from app.plugins.base import AuthMethod, AuthResult, QRCodeStatus

# Toutiao API endpoints
TOUTIAO_API = {
    "qrcode_generate": "https://sso.toutiao.com/qrcode_generate/",
    "qrcode_check": "https://sso.toutiao.com/check_qrconnect/",
    "user_info": "https://www.toutiao.com/api/user/info/",
    "feed_follow": "https://www.toutiao.com/api/pc/feed/",
    "user_articles": "https://www.toutiao.com/api/pc/list/user/feed",
}

# In-memory QR code session storage
_qrcode_sessions: Dict[str, Dict[str, Any]] = {}


class ToutiaoAuth:
    """Toutiao authentication handler."""
    
    @staticmethod
    async def generate_qrcode() -> Tuple[str, bytes, str]:
        """Generate QR code for Toutiao login.
        
        Returns:
            Tuple of (qrcode_url, qrcode_image_bytes, session_id)
        """
        async with httpx.AsyncClient(
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://www.toutiao.com/",
                "Origin": "https://www.toutiao.com",
            },
            timeout=30.0
        ) as client:
            # Generate QR code
            response = await client.get(
                TOUTIAO_API["qrcode_generate"],
                params={
                    "service": "toutiao",
                    "aid": "24",
                    "account_sdk_source": "sso",
                    "sdk_version": "2.2.7",
                }
            )
            
            data = response.json()
            
            if data.get("error_code", -1) != 0:
                raise Exception(f"Failed to generate QR code: {data.get('error_message')}")
            
            qrcode_url = data.get("data", {}).get("qrcode", "")
            session_id = data.get("data", {}).get("session_id", "")
            
            if not session_id:
                session_id = str(uuid.uuid4())
            
            qrcode_image = _generate_qrcode_image(qrcode_url)
            
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
        
        try:
            async with httpx.AsyncClient(
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Referer": "https://www.toutiao.com/",
                },
                timeout=30.0
            ) as client:
                response = await client.get(
                    TOUTIAO_API["qrcode_check"],
                    params={
                        "session_id": session_id,
                        "service": "toutiao",
                        "aid": "24",
                    }
                )
                
                data = response.json()
                status_code = data.get("data", {}).get("status", "")
                
                if status_code == "1":
                    # Login successful
                    redirect_url = data.get("data", {}).get("redirect_url", "")
                    
                    # Follow redirect to get cookies
                    cookies = {}
                    if redirect_url:
                        try:
                            resp = await client.get(redirect_url)
                            cookies = dict(resp.cookies)
                        except Exception:
                            pass
                    
                    # Merge cookies
                    cookies.update(dict(response.cookies))
                    
                    credentials = {
                        "cookies": cookies,
                        "cookie_string": "; ".join(f"{k}={v}" for k, v in cookies.items()),
                        "login_time": time.time()
                    }
                    
                    session["status"] = QRCodeStatus.CONFIRMED
                    session["credentials"] = credentials
                    
                    # Get user info
                    user_info = await ToutiaoAuth.get_user_info(credentials)
                    
                    return QRCodeStatus(
                        status=QRCodeStatus.CONFIRMED,
                        credentials=credentials,
                        user_info=user_info
                    )
                
                elif status_code == "2":
                    # Scanned but not confirmed
                    return QRCodeStatus(status=QRCodeStatus.SCANNED)
                
                elif status_code == "3":
                    # Expired
                    del _qrcode_sessions[session_id]
                    return QRCodeStatus(
                        status=QRCodeStatus.EXPIRED,
                        error="QR code expired"
                    )
                
                else:
                    # Not scanned yet
                    return QRCodeStatus(status=QRCodeStatus.PENDING)
                    
        except Exception as e:
            return QRCodeStatus(
                status=QRCodeStatus.PENDING,
                error=str(e)
            )
    
    @staticmethod
    async def get_user_info(credentials: Dict[str, Any]) -> Optional[Dict[str, str]]:
        """Get Toutiao user info."""
        try:
            async with httpx.AsyncClient(
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Referer": "https://www.toutiao.com/",
                },
                cookies=credentials.get("cookies", {}),
                timeout=30.0
            ) as client:
                response = await client.get(TOUTIAO_API["user_info"])
                data = response.json()
                
                if data.get("message") == "success":
                    user_data = data.get("data", {})
                    return {
                        "username": user_data.get("name", ""),
                        "avatar": user_data.get("avatar_url", ""),
                        "uid": str(user_data.get("user_id", "")),
                        "description": user_data.get("description", "")
                    }
        except Exception:
            pass
        return None
    
    @staticmethod
    async def validate_credentials(credentials: Dict[str, Any]) -> bool:
        """Validate Toutiao credentials."""
        user_info = await ToutiaoAuth.get_user_info(credentials)
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
