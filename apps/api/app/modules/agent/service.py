import json
import logging
import uuid
from datetime import datetime, timezone

import httpx
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.modules.agent.models import AgentDraft, LlmProvider
from app.modules.agent.schemas import (
    AgentDraftUpdate,
    LlmProviderCreate,
    LlmProviderRead,
    LlmProviderUpdate,
)
from app.modules.auth.schemas import CurrentUser
from app.modules.sources.schemas import SourceCreate
from app.modules.sources.service import source_service

logger = logging.getLogger(__name__)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _mask_key(key: str) -> str:
    if len(key) <= 8:
        return "****"
    return key[:4] + "****" + key[-4:]


def _provider_to_read(p: LlmProvider) -> LlmProviderRead:
    return LlmProviderRead(
        id=p.id,
        name=p.name,
        base_url=p.base_url,
        api_key_masked=_mask_key(p.api_key),
        model=p.model,
        api_format=p.api_format,
        is_default=p.is_default,
        enabled=p.enabled,
        created_at=p.created_at,
    )


def _draft_to_read(d: AgentDraft) -> dict:
    return {
        "id": d.id,
        "user_id": d.user_id,
        "provider_id": d.provider_id,
        "prompt_md": d.prompt_md,
        "status": d.status,
        "source_draft_json": d.source_draft_json,
        "error_message": d.error_message,
        "llm_model": d.llm_model,
        "llm_tokens_used": d.llm_tokens_used,
        "llm_cost": d.llm_cost,
        "created_at": d.created_at,
        "updated_at": d.updated_at,
    }


# ── Provider CRUD ──


def list_providers(db: Session) -> list[LlmProviderRead]:
    rows = db.query(LlmProvider).order_by(LlmProvider.is_default.desc()).all()
    return [_provider_to_read(r) for r in rows]


def create_provider(db: Session, data: LlmProviderCreate) -> LlmProviderRead:
    if data.is_default:
        db.query(LlmProvider).filter(LlmProvider.is_default.is_(True)).update(
            {"is_default": False}
        )
    p = LlmProvider(id=uuid.uuid4().hex[:16], **data.model_dump())
    db.add(p)
    db.commit()
    db.refresh(p)
    return _provider_to_read(p)


def update_provider(
    db: Session, provider_id: str, data: LlmProviderUpdate
) -> LlmProviderRead | None:
    p = db.query(LlmProvider).filter(LlmProvider.id == provider_id).first()
    if not p:
        return None
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(p, k, v)
    if data.is_default:
        db.query(LlmProvider).filter(
            LlmProvider.id != provider_id, LlmProvider.is_default.is_(True)
        ).update({"is_default": False})
    db.commit()
    db.refresh(p)
    return _provider_to_read(p)


def delete_provider(db: Session, provider_id: str) -> bool:
    p = db.query(LlmProvider).filter(LlmProvider.id == provider_id).first()
    if not p:
        return False
    db.delete(p)
    db.commit()
    return True


def get_provider(db: Session, provider_id: str) -> LlmProvider | None:
    return db.query(LlmProvider).filter(LlmProvider.id == provider_id).first()


# ── LLM Call ──

SYSTEM_PROMPT = """You are a news source configuration assistant.
Given a user description in Markdown, generate a JSON configuration for a news source.

Return ONLY valid JSON — no explanation, no markdown fences, no extra text.

Required JSON structure:
{
  "name": "Source display name",
  "type": "rss" | "api" | "web",
  "endpoint": "URL",
  "config": {
    // For web: item_selector, title_selector, url_selector,
    // summary_selector, date_selector, author_selector, image_selector
    // For api: items_path, title_path, url_path,
    // summary_path, date_path, author_path, image_path
    // For rss type: empty object
  },
  "schedule_enabled": false,
  "schedule_interval_minutes": null
}

Rules:
- If the user describes a website to scrape, use type "web" with CSS selectors.
- If the user describes an API, use type "api" with JSON path selectors.
- If the user describes an RSS feed, use type "rss".
- Choose appropriate CSS selectors for web scraping (prefer class-based over tag-based).
- Keep selectors robust and specific enough to avoid false matches.
- Set reasonable schedule intervals (minimum 5 minutes).
- IMPORTANT: For image_selector, use CSS selectors that target <img> tags.
  Modern sites often use lazy loading — the selector should match the <img> element
  itself; the system automatically handles data-original/data-src/data-lazy-src attributes.
- For sites with <picture> elements, target the inner <img> tag (e.g., ".cover img").
"""


def _extract_content_from_openai_response(data: dict) -> str:
    """Extract text content from OpenAI-compatible response.

    Handles reasoning models (e.g. MiMo, DeepSeek-R1) that put the actual
    response in ``reasoning_content`` when ``content`` is empty.
    """
    msg = data["choices"][0]["message"]
    content = msg.get("content") or ""
    content = content.strip()

    if content:
        return content

    # Fallback: some reasoning models put output in reasoning_content
    reasoning = msg.get("reasoning_content") or ""
    reasoning = reasoning.strip()
    if not reasoning:
        return ""

    # Try to find a JSON object in the reasoning text
    # Look for the last complete JSON object (likely the final answer)
    import re
    json_matches = re.findall(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', reasoning)
    if json_matches:
        # Return the longest match (most likely the complete config)
        return max(json_matches, key=len)

    return reasoning


def _strip_code_fences(content: str) -> str:
    """Remove markdown code fences (```json ... ```) from LLM output."""
    content = content.strip()
    if content.startswith("```"):
        lines = content.split("\n")
        lines = [line for line in lines if not line.strip().startswith("```")]
        content = "\n".join(lines)
    return content.strip()


def _validate_source_draft(parsed: dict) -> None:
    """Validate that the parsed JSON has the minimum required fields."""
    required = ("name", "type", "endpoint")
    missing = [f for f in required if f not in parsed]
    if missing:
        raise ValueError(
            f"LLM output missing required fields: {', '.join(missing)}. "
            f"Got keys: {list(parsed.keys())}"
        )
    if parsed["type"] not in ("rss", "api", "web"):
        raise ValueError(f"Invalid source type: {parsed['type']!r}")


async def _call_openai(
    provider: LlmProvider, user_prompt: str
) -> tuple[dict, int, float]:
    """Call an OpenAI-compatible API with retry and reasoning-model support."""
    headers = {
        "Authorization": f"Bearer {provider.api_key}",
        "Content-Type": "application/json",
    }
    body = {
        "model": provider.model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.3,
        "max_tokens": 4000,
    }

    last_error: Exception | None = None
    for attempt in range(3):
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{provider.base_url.rstrip('/')}/chat/completions",
                headers=headers,
                json=body,
            )
            resp.raise_for_status()
            data = resp.json()

        content = _extract_content_from_openai_response(data)
        if not content:
            last_error = ValueError(
                f"LLM returned empty content (attempt {attempt + 1}/3). "
                f"Raw keys: {list(data.get('choices', [{}])[0].get('message', {}).keys())}"
            )
            logger.warning(str(last_error))
            import asyncio
            await asyncio.sleep(1)
            continue

        content = _strip_code_fences(content)

        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as e:
            last_error = ValueError(
                f"LLM returned invalid JSON (attempt {attempt + 1}/3): {e}. "
                f"Content preview: {content[:200]!r}"
            )
            logger.warning(str(last_error))
            import asyncio
            await asyncio.sleep(1)
            continue

        _validate_source_draft(parsed)

        usage = data.get("usage", {})
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        tokens = prompt_tokens + completion_tokens
        cost = tokens * 0.0000003

        return parsed, tokens, cost

    # All 3 attempts failed
    raise last_error or RuntimeError("LLM call failed after 3 attempts")


async def _call_anthropic(
    provider: LlmProvider, user_prompt: str
) -> tuple[dict, int, float]:
    """Call Anthropic Messages API with retry and validation."""
    headers = {
        "x-api-key": provider.api_key,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }
    body = {
        "model": provider.model,
        "max_tokens": 4000,
        "system": SYSTEM_PROMPT,
        "messages": [
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.3,
    }

    last_error: Exception | None = None
    for attempt in range(3):
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{provider.base_url.rstrip('/')}/messages",
                headers=headers,
                json=body,
            )
            resp.raise_for_status()
            data = resp.json()

        # Anthropic returns: { content: [{type: "text", text: "..."}], usage: {...} }
        content_blocks = data.get("content", [])
        content = ""
        for block in content_blocks:
            if block.get("type") == "text":
                content += block.get("text", "")

        content = _strip_code_fences(content)

        if not content:
            last_error = ValueError(
                f"Anthropic returned empty content (attempt {attempt + 1}/3)"
            )
            logger.warning(str(last_error))
            import asyncio
            await asyncio.sleep(1)
            continue

        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as e:
            last_error = ValueError(
                f"Anthropic returned invalid JSON (attempt {attempt + 1}/3): {e}. "
                f"Content preview: {content[:200]!r}"
            )
            logger.warning(str(last_error))
            import asyncio
            await asyncio.sleep(1)
            continue

        _validate_source_draft(parsed)

        usage = data.get("usage", {})
        input_tokens = usage.get("input_tokens", 0)
        output_tokens = usage.get("output_tokens", 0)
        tokens = input_tokens + output_tokens
        cost = tokens * 0.0000003

        return parsed, tokens, cost

    raise last_error or RuntimeError("Anthropic call failed after 3 attempts")


async def call_llm(
    provider: LlmProvider, user_prompt: str
) -> tuple[dict, int, float]:
    """Call LLM and return (parsed_json, tokens_used, cost)."""
    if provider.api_format == "anthropic":
        return await _call_anthropic(provider, user_prompt)
    return await _call_openai(provider, user_prompt)


# ── Draft CRUD ──


def list_drafts(
    db: Session, user_id: str, limit: int = 20, offset: int = 0
) -> tuple[list[dict], int]:
    q = db.query(AgentDraft).filter(AgentDraft.user_id == user_id)
    total = q.count()
    rows = q.order_by(desc(AgentDraft.created_at)).offset(offset).limit(limit).all()
    return [_draft_to_read(r) for r in rows], total


def get_draft(db: Session, draft_id: str) -> AgentDraft | None:
    return db.query(AgentDraft).filter(AgentDraft.id == draft_id).first()


async def generate_draft(
    db: Session, user_id: str, provider_id: str, prompt_md: str
) -> dict:
    provider = get_provider(db, provider_id)
    if not provider:
        raise ValueError("Provider not found")
    if not provider.enabled:
        raise ValueError("Provider is disabled")

    draft = AgentDraft(
        id=uuid.uuid4().hex[:16],
        user_id=user_id,
        provider_id=provider_id,
        prompt_md=prompt_md,
        status="drafting",
        llm_model=provider.model,
    )
    db.add(draft)
    db.commit()
    db.refresh(draft)

    try:
        parsed, tokens, cost = await call_llm(provider, prompt_md)
        draft.source_draft_json = json.dumps(parsed, ensure_ascii=False, indent=2)
        draft.status = "ready"
        draft.llm_tokens_used = tokens
        draft.llm_cost = cost
    except Exception as e:
        logger.exception("LLM call failed")
        draft.status = "failed"
        draft.error_message = str(e)[:500]

    db.commit()
    db.refresh(draft)
    return _draft_to_read(draft)


def update_draft(
    db: Session, draft_id: str, user_id: str, data: AgentDraftUpdate
) -> dict | None:
    d = (
        db.query(AgentDraft)
        .filter(AgentDraft.id == draft_id, AgentDraft.user_id == user_id)
        .first()
    )
    if not d:
        return None
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(d, k, v)
    db.commit()
    db.refresh(d)
    return _draft_to_read(d)


def confirm_draft(
    db: Session, draft_id: str, user: CurrentUser
) -> dict | None:
    d = (
        db.query(AgentDraft)
        .filter(AgentDraft.id == draft_id, AgentDraft.user_id == user.id)
        .first()
    )
    if not d:
        return None

    # Parse the source draft
    source_draft = json.loads(d.source_draft_json)

    # Create the actual source using source_service
    source_create = SourceCreate(
        name=source_draft["name"],
        type=source_draft["type"],
        endpoint=source_draft["endpoint"],
        config=source_draft.get("config", {}),
        schedule_enabled=source_draft.get("schedule_enabled", False),
        schedule_interval_minutes=source_draft.get("schedule_interval_minutes"),
    )
    created_source = source_service.create_source(db, user, source_create)
    logger.info(f"Source created from draft: {created_source.id} ({created_source.name})")

    # Mark draft as confirmed
    d.status = "confirmed"
    db.commit()

    # Return source info + draft info
    return {
        "source_id": created_source.id,
        "source_name": created_source.name,
        "source_type": created_source.type,
        "draft_id": d.id,
        **source_draft,
    }


def delete_draft(db: Session, draft_id: str, user_id: str) -> bool:
    d = (
        db.query(AgentDraft)
        .filter(AgentDraft.id == draft_id, AgentDraft.user_id == user_id)
        .first()
    )
    if not d:
        return False
    db.delete(d)
    db.commit()
    return True
