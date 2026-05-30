from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.agent_tokens import service as token_service
from app.modules.agent_tokens.schemas import (
    AgentTokenCreate,
    AgentTokenCreated,
    AgentTokenList,
    ExportRequest,
)
from app.modules.auth.router import CurrentUserDep
from app.shared.responses import ApiResponse

router = APIRouter()

DbDep = Annotated[Session, Depends(get_db)]


# ── Token CRUD ──


@router.get("/tokens", response_model=ApiResponse[AgentTokenList])
def list_tokens(
    db: DbDep,
    user: CurrentUserDep,
):
    items = token_service.list_tokens(db, user.id)
    return ApiResponse(data=AgentTokenList(items=items))


@router.post("/tokens", response_model=ApiResponse[AgentTokenCreated])
def create_token(
    data: AgentTokenCreate,
    db: DbDep,
    user: CurrentUserDep,
):
    result = token_service.create_token(db, user, data)
    return ApiResponse(data=result)


@router.delete("/tokens/{token_id}", response_model=ApiResponse[dict])
def revoke_token(
    token_id: str,
    db: DbDep,
    user: CurrentUserDep,
):
    if not token_service.revoke_token(db, user.id, token_id):
        raise HTTPException(status_code=404, detail="Token not found")
    return ApiResponse(data={"revoked": True})


# ── Agent Token 认证入口 ──


def _get_agent_user(request: Request, db: Session) -> tuple[str, list[str]]:
    """从 Authorization header 验证 agent token，返回 (user_id, scopes)"""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")

    token_str = auth[7:]
    result = token_service.validate_token(db, token_str)
    if not result:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    agent_token, user_id = result
    scopes = agent_token.scopes.split(",") if agent_token.scopes else []
    return user_id, scopes


# ── 数据导出 API ──


@router.post("/export")
def export_data(
    req: ExportRequest,
    request: Request,
    db: DbDep,
):
    """Agent token 数据导出端点"""
    user_id, scopes = _get_agent_user(request, db)

    if "export:data" not in scopes and "read:feed" not in scopes:
        raise HTTPException(status_code=403, detail="Insufficient scope")

    if req.type == "feed":
        content, count = token_service.export_feed(db, user_id, req)
    elif req.type == "sources":
        if "read:sources" not in scopes:
            raise HTTPException(status_code=403, detail="Insufficient scope: read:sources required")
        content, count = token_service.export_sources(db, user_id, req)
    else:
        raise HTTPException(status_code=400, detail="Invalid export type")

    if req.format == "csv":
        return PlainTextResponse(
            content,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=export_{req.type}.csv"},
        )
    else:
        return PlainTextResponse(
            content,
            media_type="application/json",
        )


# ── Agent 信息端点 ──


@router.get("/me")
def agent_me(
    request: Request,
    db: DbDep,
):
    """Agent token 持有者信息"""
    user_id, scopes = _get_agent_user(request, db)
    return ApiResponse(data={
        "user_id": user_id,
        "scopes": scopes,
        "type": "agent_token",
    })
