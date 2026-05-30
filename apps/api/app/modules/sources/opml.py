"""OPML import/export for RSS sources."""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.auth.schemas import CurrentUser
from app.modules.sources.models import Source, Subscription

logger = logging.getLogger(__name__)


# ── OPML Export ──


def export_opml(db: Session, current_user: CurrentUser) -> str:
    """Export user's RSS sources as OPML XML."""
    sources = db.scalars(
        select(Source)
        .join(Subscription, Subscription.source_id == Source.id)
        .where(Subscription.user_id == current_user.id)
        .where(Source.type == "rss")
        .where(Source.deleted_at.is_(None))
        .order_by(Source.name)
    ).all()

    # Build OPML XML
    opml = ET.Element("opml", version="2.0")
    head = ET.SubElement(opml, "head")
    ET.SubElement(head, "title").text = "My Daily Headlines - RSS Subscriptions"
    ET.SubElement(head, "dateCreated").text = datetime.now(timezone.utc).isoformat()

    body = ET.SubElement(opml, "body")
    for source in sources:
        ET.SubElement(
            body,
            "outline",
            text=source.name,
            title=source.name,
            type="rss",
            xmlUrl=source.endpoint,
            htmlUrl=source.endpoint,
        )

    # Pretty print
    ET.indent(opml, space="  ")
    xml_str = ET.tostring(opml, encoding="unicode", xml_declaration=True)
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_str.split("?>", 1)[1]


# ── OPML Import ──


class OpmlImportResult:
    def __init__(self):
        self.imported: int = 0
        self.skipped: int = 0
        self.errors: list[str] = []
        self.sources: list[dict] = []


def import_opml(
    db: Session,
    current_user: CurrentUser,
    xml_content: str,
) -> OpmlImportResult:
    """Import RSS sources from OPML XML."""
    result = OpmlImportResult()

    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError as e:
        result.errors.append(f"Invalid XML: {e}")
        return result

    # Find all outline elements with xmlUrl
    outlines = root.findall(".//outline[@xmlUrl]") + root.findall(".//outline[@xmlurl]")

    if not outlines:
        result.errors.append("No RSS feeds found in OPML file")
        return result

    # Get existing endpoints to avoid duplicates
    existing_endpoints = set(
        db.scalars(
            select(Source.endpoint)
            .where(Source.created_by == current_user.id)
            .where(Source.deleted_at.is_(None))
        ).all()
    )

    for outline in outlines:
        xml_url = outline.get("xmlUrl") or outline.get("xmlurl", "").strip()
        title = (outline.get("title") or outline.get("text") or xml_url).strip()

        if not xml_url:
            result.errors.append(f"Skipping outline with no xmlUrl: {title}")
            continue

        if xml_url in existing_endpoints:
            result.skipped += 1
            continue

        try:
            # Create source
            source = Source(
                id=f"source_{uuid4().hex}",
                name=title[:160],
                type="rss",
                endpoint=xml_url,
                config_json="{}",
                created_by=current_user.id,
            )
            db.add(source)

            # Create subscription
            db.add(
                Subscription(
                    id=f"sub_{uuid4().hex}",
                    user_id=current_user.id,
                    source_id=source.id,
                )
            )

            existing_endpoints.add(xml_url)
            result.imported += 1
            result.sources.append({"name": title, "endpoint": xml_url})

        except Exception as e:
            result.errors.append(f"Failed to import {title}: {e}")

    if result.imported > 0:
        db.commit()

    return result
