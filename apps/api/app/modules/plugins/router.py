"""Plugin router for source authentication and QR code login."""
from __future__ import annotations

import base64
import logging
from typing import Any, Dict, Optional
from uuid import uuid4

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.auth.router import CurrentUserDep
from app.plugins.base import AuthResult
from app.plugins.base.registry import get_plugin_registry, auto_discover_plugins
from app.shared.responses import ApiResponse

logger = logging.getLogger(__name__)

router = APIRouter()

# Auto-discover plugins on module load
auto_discover_plugins()


@router.get("")
async def list_plugins(
    current_user: CurrentUserDep,
) -> ApiResponse[list[dict[str, Any]]]:
    """List all available source plugins."""
    registry = get_plugin_registry()
    plugins = registry.list_plugins()
    return ApiResponse(data=plugins)


@router.get("/{plugin_id}")
async def get_plugin_info(
    plugin_id: str,
    current_user: CurrentUserDep,
) -> ApiResponse[dict[str, Any]]:
    """Get detailed plugin information."""
    registry = get_plugin_registry()
    plugin = registry.get(plugin_id)

    if not plugin:
        raise HTTPException(status_code=404, detail=f"Plugin '{plugin_id}' not found")

    auth_schema = await plugin.get_auth_config_schema()
    subscription_types = await plugin.get_subscription_types()

    return ApiResponse(data={
        "id": plugin.plugin_id,
        "name": plugin.display_name,
        "description": plugin.description,
        "icon_url": plugin.icon_url,
        "auth_methods": [m.value for m in plugin.supported_auth_methods],
        "source_type": plugin.default_source_type,
        "auth_schema": auth_schema,
        "subscription_types": subscription_types,
    })


@router.post("/{plugin_id}/auth/init")
async def init_auth(
    plugin_id: str,
    method: str = Query(..., description="Authentication method (qrcode, cookie)"),
    credentials: Optional[Dict[str, Any]] = Body(None),
    current_user: CurrentUserDep = None,
) -> ApiResponse[Dict[str, Any]]:
    """Initialize authentication for a plugin.

    For QR code auth, returns a QR code image and session ID.
    For cookie auth, validates the provided cookie string.
    """
    registry = get_plugin_registry()
    plugin = registry.get(plugin_id)

    if not plugin:
        raise HTTPException(status_code=404, detail=f"Plugin '{plugin_id}' not found")

    # Validate method
    from app.plugins.base import AuthMethod
    try:
        auth_method = AuthMethod(method)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid auth method: {method}")

    if auth_method not in plugin.supported_auth_methods:
        raise HTTPException(
            status_code=400,
            detail=f"Plugin '{plugin_id}' does not support auth method '{method}'"
        )

    # Perform authentication
    result: AuthResult = await plugin.authenticate(auth_method, credentials)

    if not result.success:
        raise HTTPException(status_code=400, detail=result.error or "Authentication failed")

    # Build response
    response_data: dict[str, Any] = {
        "success": True,
        "auth_method": method,
    }

    if auth_method == AuthMethod.QRCODE and result.qrcode_image:
        qrcode_base64 = base64.b64encode(result.qrcode_image).decode("utf-8")
        response_data["qrcode_image"] = f"data:image/png;base64,{qrcode_base64}"
        response_data["qrcode_url"] = result.qrcode_url
        response_data["session_id"] = (
            result.credentials.get("qrcode_session_id") if result.credentials else None
        )
        response_data["expires_in"] = result.expires_in

    if result.credentials:
        response_data["has_credentials"] = True

    return ApiResponse(data=response_data)


@router.get("/{plugin_id}/auth/qrcode/status")
async def check_qrcode_status(
    plugin_id: str,
    session_id: str = Query(..., description="QR code session ID"),
    current_user: CurrentUserDep = None,
) -> ApiResponse[Dict[str, Any]]:
    """Check QR code authentication status.

    Poll this endpoint after showing the QR code to the user.
    """
    registry = get_plugin_registry()
    plugin = registry.get(plugin_id)

    if not plugin:
        raise HTTPException(status_code=404, detail=f"Plugin '{plugin_id}' not found")

    status = await plugin.check_qrcode_status(session_id)

    response_data: dict[str, Any] = {
        "status": status.status,
    }

    from app.plugins.base import QRCodeStatus as QS
    if status.status == QS.CONFIRMED:
        response_data["success"] = True
        response_data["has_credentials"] = True
        if status.user_info:
            response_data["user_info"] = status.user_info
        if status.credentials:
            # Store credentials for retrieval (exclude session_id)
            clean_creds = {k: v for k, v in status.credentials.items() if k != "qrcode_session_id"}
            response_data["credentials"] = clean_creds
    elif status.status in [QS.EXPIRED, QS.CANCELLED]:
        response_data["success"] = False
        response_data["error"] = status.error
    else:
        response_data["success"] = False

    return ApiResponse(data=response_data)


@router.post("/{plugin_id}/auth/validate")
async def validate_credentials(
    plugin_id: str,
    credentials: Dict[str, Any],
    current_user: CurrentUserDep = None,
) -> ApiResponse[Dict[str, Any]]:
    """Validate plugin credentials."""
    registry = get_plugin_registry()
    plugin = registry.get(plugin_id)

    if not plugin:
        raise HTTPException(status_code=404, detail=f"Plugin '{plugin_id}' not found")

    is_valid = await plugin.validate_credentials(credentials)
    user_info = None

    if is_valid:
        user_info = await plugin.get_user_info(credentials)

    return ApiResponse(data={
        "valid": is_valid,
        "user_info": user_info,
    })


@router.post("/{plugin_id}/fetch")
async def fetch_plugin_feed(
    plugin_id: str,
    body: Dict[str, Any],
    current_user: CurrentUserDep = None,
) -> ApiResponse[Dict[str, Any]]:
    """Fetch feed content from a plugin (preview/test)."""
    registry = get_plugin_registry()
    plugin = registry.get(plugin_id)

    if not plugin:
        raise HTTPException(status_code=404, detail=f"Plugin '{plugin_id}' not found")

    credentials = body.get("credentials", {})
    config = body.get("config", {})
    cursor = body.get("cursor")
    limit = body.get("limit", 20)

    result = await plugin.fetch_feed(
        credentials=credentials,
        config=config,
        cursor=cursor,
        limit=limit
    )

    if not result.success:
        raise HTTPException(status_code=400, detail=result.error or "Failed to fetch feed")

    return ApiResponse(data={
        "items": result.items,
        "has_more": result.has_more,
        "next_cursor": result.next_cursor,
        "total_count": result.total_count,
    })
