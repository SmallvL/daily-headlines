import csv
import hashlib
import io
import json
import logging
import os
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.modules.agent_tokens.models import AgentToken
from app.modules.agent_tokens.schemas import (
    AgentTokenCreate,
    AgentTokenCreated,
    AgentTokenRead,
    ExportRequest,
)
from app.modules.auth.schemas import CurrentUser
from app.modules.feed.models import FeedItem
from app.modules.sources.models import Source

logger = logging.getLogger(__name__)

# ── Token 生成与验证 ──

TOKEN_PREFIX = "dh_"
EXPORT_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "exports")


def _generate_token() -> tuple[str, str, str]:
    """生成 token，返回 (raw_token, token_hash, prefix)"""
    raw = uuid.uuid4().hex + uuid.uuid4().hex
    token = f"{TOKEN_PREFIX}{raw}"
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    prefix = token[:10]  # "dh_xxxxxxx"
    return token, token_hash, prefix


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _to_read(t: AgentToken) -> AgentTokenRead:
    return AgentTokenRead(
        id=t.id,
        name=t.name,
        prefix=t.prefix,
        scopes=t.scopes.split(",") if t.scopes else [],
        enabled=t.enabled,
        last_used_at=t.last_used_at,
        expires_at=t.expires_at,
        created_at=t.created_at,
        revoked_at=t.revoked_at,
    )


# ── Token CRUD ──


def create_token(
    db: Session, user: CurrentUser, data: AgentTokenCreate
) -> AgentTokenCreated:
    raw_token, token_hash, prefix = _generate_token()
    expires_at = None
    if data.expires_in_days:
        expires_at = datetime.now(timezone.utc) + timedelta(days=data.expires_in_days)

    token = AgentToken(
        id=uuid.uuid4().hex[:16],
        user_id=user.id,
        name=data.name,
        token_hash=token_hash,
        prefix=prefix,
        scopes=",".join(data.scopes),
        expires_at=expires_at,
    )
    db.add(token)
    db.commit()
    db.refresh(token)

    return AgentTokenCreated(
        id=token.id,
        name=token.name,
        token=raw_token,  # 只在创建时返回明文
        prefix=prefix,
        scopes=data.scopes,
        expires_at=token.expires_at,
        created_at=token.created_at,
    )


def list_tokens(db: Session, user_id: str) -> list[AgentTokenRead]:
    rows = (
        db.query(AgentToken)
        .filter(AgentToken.user_id == user_id)
        .order_by(desc(AgentToken.created_at))
        .all()
    )
    return [_to_read(r) for r in rows]


def revoke_token(db: Session, user_id: str, token_id: str) -> bool:
    t = (
        db.query(AgentToken)
        .filter(AgentToken.id == token_id, AgentToken.user_id == user_id)
        .first()
    )
    if not t:
        return False
    t.revoked_at = datetime.now(timezone.utc)
    t.enabled = False
    db.commit()
    return True


def validate_token(db: Session, token_str: str) -> tuple[AgentToken, str] | None:
    """验证 token，返回 (AgentToken, user_id) 或 None"""
    token_hash = _hash_token(token_str)
    t = db.query(AgentToken).filter(AgentToken.token_hash == token_hash).first()
    if not t:
        return None
    if not t.enabled or t.revoked_at:
        return None
    if t.expires_at:
        # Handle both string and datetime
        if isinstance(t.expires_at, str):
            exp = datetime.fromisoformat(t.expires_at)
        else:
            exp = t.expires_at
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        if exp < datetime.now(timezone.utc):
            return None
    # 更新最后使用时间
    t.last_used_at = datetime.now(timezone.utc)
    db.commit()
    return t, t.user_id


def check_scope(token: AgentToken, required_scope: str) -> bool:
    """检查 token 是否有指定 scope"""
    scopes = token.scopes.split(",") if token.scopes else []
    return required_scope in scopes


# ── 数据导出 ──


def export_feed(
    db: Session, user_id: str, req: ExportRequest
) -> tuple[str, int]:
    """导出信息流数据，返回 (content, count)"""
    from app.modules.sources.models import Subscription

    q = (
        db.query(FeedItem)
        .join(Source, Source.id == FeedItem.source_id)
        .join(Subscription, Subscription.source_id == Source.id)
        .filter(Subscription.user_id == user_id)
        .filter(Source.deleted_at.is_(None))
    )
    if req.query:
        q = q.filter(FeedItem.title.contains(req.query))
    if req.source_type:
        q = q.filter(Source.type == req.source_type)

    items = q.order_by(desc(FeedItem.published_at)).limit(req.limit).all()

    if req.format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["id", "title", "url", "summary", "source", "published_at"])
        for item in items:
            writer.writerow([
                item.id,
                item.title,
                item.url,
                item.summary or "",
                item.source_id,
                item.published_at or "",
            ])
        return output.getvalue(), len(items)
    else:
        data = [
            {
                "id": item.id,
                "title": item.title,
                "url": item.url,
                "summary": item.summary,
                "source_id": item.source_id,
                "published_at": str(item.published_at) if item.published_at else None,
            }
            for item in items
        ]
        return json.dumps(data, ensure_ascii=False, indent=2), len(items)


def export_sources(
    db: Session, user_id: str, req: ExportRequest
) -> tuple[str, int]:
    """导出信息源数据，返回 (content, count)"""
    q = db.query(Source).filter(Source.created_by == user_id, Source.deleted_at.is_(None))
    if req.query:
        q = q.filter(Source.name.contains(req.query))
    if req.source_type:
        q = q.filter(Source.type == req.source_type)

    sources = q.order_by(desc(Source.created_at)).limit(req.limit).all()

    if req.format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["id", "name", "type", "endpoint", "status", "created_at"])
        for s in sources:
            writer.writerow([s.id, s.name, s.type, s.endpoint, s.status, s.created_at])
        return output.getvalue(), len(sources)
    else:
        data = [
            {
                "id": s.id,
                "name": s.name,
                "type": s.type,
                "endpoint": s.endpoint,
                "status": s.status,
                "created_at": str(s.created_at) if s.created_at else None,
            }
            for s in sources
        ]
        return json.dumps(data, ensure_ascii=False, indent=2), len(sources)
