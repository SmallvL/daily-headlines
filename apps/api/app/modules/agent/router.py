from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.agent import service as agent_service
from app.modules.agent.schemas import (
    AgentDraftConfirm,
    AgentDraftCreate,
    AgentDraftList,
    AgentDraftRead,
    AgentDraftUpdate,
    LlmProviderCreate,
    LlmProviderList,
    LlmProviderRead,
    LlmProviderUpdate,
)
from app.modules.auth.router import CurrentUserDep
from app.shared.responses import ApiResponse

router = APIRouter()

DbDep = Annotated[Session, Depends(get_db)]


# ── LLM Providers ──


@router.get("/providers", response_model=ApiResponse[LlmProviderList])
def list_providers(
    db: DbDep,
    _user: CurrentUserDep,
):
    items = agent_service.list_providers(db)
    return ApiResponse(data=LlmProviderList(items=items))


@router.post("/providers", response_model=ApiResponse[LlmProviderRead])
def create_provider(
    data: LlmProviderCreate,
    db: DbDep,
    _user: CurrentUserDep,
):
    return ApiResponse(data=agent_service.create_provider(db, data))


@router.patch(
    "/providers/{provider_id}", response_model=ApiResponse[LlmProviderRead]
)
def update_provider(
    provider_id: str,
    data: LlmProviderUpdate,
    db: DbDep,
    _user: CurrentUserDep,
):
    result = agent_service.update_provider(db, provider_id, data)
    if not result:
        raise HTTPException(status_code=404, detail="Provider not found")
    return ApiResponse(data=result)


@router.delete("/providers/{provider_id}", response_model=ApiResponse[dict])
def delete_provider(
    provider_id: str,
    db: DbDep,
    _user: CurrentUserDep,
):
    if not agent_service.delete_provider(db, provider_id):
        raise HTTPException(status_code=404, detail="Provider not found")
    return ApiResponse(data={"deleted": True})


# ── Agent Drafts ──


@router.get("/drafts", response_model=ApiResponse[AgentDraftList])
def list_drafts(
    db: DbDep,
    user: CurrentUserDep,
    limit: int = 20,
    offset: int = 0,
):
    items, total = agent_service.list_drafts(db, user.id, limit, offset)
    return ApiResponse(data=AgentDraftList(items=items, total=total))


@router.post("/drafts/generate", response_model=ApiResponse[AgentDraftRead])
async def generate_draft(
    data: AgentDraftCreate,
    db: DbDep,
    user: CurrentUserDep,
):
    try:
        result = await agent_service.generate_draft(
            db, user.id, data.provider_id, data.prompt_md
        )
        return ApiResponse(data=result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(
            status_code=502, detail=f"LLM call failed: {e}"
        ) from e


@router.patch(
    "/drafts/{draft_id}", response_model=ApiResponse[AgentDraftRead]
)
def update_draft(
    draft_id: str,
    data: AgentDraftUpdate,
    db: DbDep,
    user: CurrentUserDep,
):
    result = agent_service.update_draft(db, draft_id, user.id, data)
    if not result:
        raise HTTPException(status_code=404, detail="Draft not found")
    return ApiResponse(data=result)


@router.post("/drafts/{draft_id}/confirm", response_model=ApiResponse[dict])
def confirm_draft(
    draft_id: str,
    body: AgentDraftConfirm,
    db: DbDep,
    user: CurrentUserDep,
):
    agent_service.update_draft(
        db,
        draft_id,
        user.id,
        AgentDraftUpdate(source_draft_json=body.source_draft_json),
    )
    result = agent_service.confirm_draft(db, draft_id, user)
    if not result:
        raise HTTPException(status_code=404, detail="Draft not found")
    return ApiResponse(data=result)


@router.delete("/drafts/{draft_id}", response_model=ApiResponse[dict])
def delete_draft(
    draft_id: str,
    db: DbDep,
    user: CurrentUserDep,
):
    if not agent_service.delete_draft(db, draft_id, user.id):
        raise HTTPException(status_code=404, detail="Draft not found")
    return ApiResponse(data={"deleted": True})
