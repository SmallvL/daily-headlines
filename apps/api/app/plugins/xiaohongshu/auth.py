"""Xiaohongshu (Little Red Book) authentication module."""
from __future__ import annotations

import asyncio
import time
import uuid
from typing import Any, Dict, Optional, Tuple

import httpx

from app.plugins.base import AuthMethod, AuthResult, QRCodeStatus

# Xiaohongshu API endpoints
XHS_API = {
    "qrcode_create": "https://customer.xiaohongshu.com/login/qr-code/create",
    "qrcode_check": "https://customer.xiaohongshu.com/login/qr-code/check",
    "user_info": "https://edith.xiaohongshu.com/api/sns/web/v1/user/selfinfo",
    "feed_follow": "https://edith.xiaohongshu.com/api/sns/web/v1/feed/follow",
    "feed_recommend": "https://edith.xiaohongshu.com/api/sns/web/v1/homefeed",
    "user_notes": "https://edith.xiaohongshu.com/api/sns/web/v1/user_posted",
}

# In-memory QR code session storage
_qrcode_sessions: Dict[str, Dict[str, Any]] = {}


class XiaohongshuAuth:
    """Xiaohongshu authentication handler."""
    
    @staticmethod
    async def generate_qrcode() -> Tuple[str, bytes, str]:
        """Generate QR code for Xiaohongshu login.
        
        Returns:
            Tuple of (qrcode_url, qrcode_image_bytes, session_id)
        """
        async with httpx.AsyncClient(
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://www.xiaohongshu.com/",
                "Origin": "https://www.xiaohongshu.com",
            },
            timeout=30.0
        ) as client:
            # Generate a unique session ID
            session_id = str(uuid.uuid4())
            
            # Create QR code
            response = await client.post(
                XHS_API["qrcode_create"],
                json={"qr_id": session_id}
            )
            
            if response.status_code != 200:
                # Fallback: generate QR code with a URL
                qrcode_url = f"https://www.xiaohongshu.com/scan?qr_id={session_id}"
                qrcode_image = _generate_qrcode_image(qrcode_url)
                
                _qrcode_sessions[session_id] = {
                    "created_at": time.time(),
                    "status": QRCodeStatus.PENDING,
                    "credentials": None
                }
                
                return qrcode_url, qrcode_image, session_id
            
            data = response.json()
            qr_url = data.get("data", {}).get("qr_url", "")
            
            if not qr_url:
                qr_url = f"https://www.xiaohongshu.com/scan?qr_id={session_id}"
            
            qrcode_image = _generate_qrcode_image(qr_url)
            
            _qrcode_sessions[session_id] = {
                "created_at": time.time(),
                "status": QRCodeStatus.PENDING,
                "credentials": None
            }
            
            return qr_url, qrcode_image, session_id
    
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
                    "Referer": "https://www.xiaohongshu.com/",
                },
                timeout=30.0
            ) as client:
                response = await client.get(
                    XHS_API["qrcode_check"],
                    params={"qr_id": session_id}
                )
                
                data = response.json()
                status_code = data.get("data", {}).get("status", "")
                
                if status_code == "CONFIRMED":
                    # Login successful
                    cookies = dict(response.cookies)
                    
                    credentials = {
                        "cookies": cookies,
                        "cookie_string": "; ".join(f"{k}={v}" for k, v in cookies.items()),
                        "login_time": time.time()
                    }
                    
                    session["status"] = QRCodeStatus.CONFIRMED
                    session["credentials"] = credentials
                    
                    # Get user info
                    user_info = await XiaohongshuAuth.get_user_info(credentials)
                    
                    return QRCodeStatus(
                        status=QRCodeStatus.CONFIRMED,
                        credentials=credentials,
                        user_info=user_info
                    )
                
                elif status_code == "SCANNED":
                    return QRCodeStatus(status=QRCodeStatus.SCANNED)
                
                elif status_code == "EXPIRED":
                    del _qrcode_sessions[session_id]
                    return QRCodeStatus(
                        status=QRCodeStatus.EXPIRED,
                        error="QR code expired"
                    )
                
                else:
                    return QRCodeStatus(status=QRCodeStatus.PENDING)
                    
        except Exception as e:
            return QRCodeStatus(
                status=QRCodeStatus.PENDING,
                error=str(e)
            )
    
    @staticmethod
    async def get_user_info(credentials: Dict[str, Any]) -> Optional[Dict[str, str]]:
        """Get Xiaohongshu user info."""
        try:
            async with httpx.AsyncClient(
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Referer": "https://www.xiaohongshu.com/",
                },
                cookies=credentials.get("cookies", {}),
                timeout=30.0
            ) as client:
                response = await client.get(XHS_API["user_info"])
                data = response.json()
                
                if data.get("success"):
                    user_data = data.get("data", {})
                    return {
                        "username": user_data.get("nickname", ""),
                        "avatar": user_data.get("imageb", ""),
                        "uid": user_data.get("userid", ""),
                        "description": user_data.get("desc", "")
                    }
        except Exception:
            pass
        return None
    
    @staticmethod
    async def validate_credentials(credentials: Dict[str, Any]) -> bool:
        """Validate Xiaohongshu credentials."""
        user_info = await XiaohongshuAuth.get_user_info(credentials)
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
