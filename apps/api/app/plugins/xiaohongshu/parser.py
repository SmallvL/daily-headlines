"""Xiaohongshu content parser module."""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.plugins.base import FeedItem, ParseResult


class XiaohongshuParser:
    """Xiaohongshu content parser."""
    
    @staticmethod
    def parse_note(note: Dict[str, Any]) -> Optional[FeedItem]:
        """Parse a Xiaohongshu note.
        
        Args:
            note: Raw note data from API
        
        Returns:
            FeedItem or None if parsing fails
        """
        try:
            note_id = note.get("id", "")
            user = note.get("user", {})
            author = user.get("nickname", "Unknown")
            
            # Title and content
            title = note.get("title", "")
            desc = note.get("desc", "")
            
            if not title and not desc:
                return None
            
            # Use first line of desc as title if no title
            if not title:
                lines = desc.split("\n")
                title = lines[0][:50] if lines[0] else f"笔记 {note_id}"
                if len(lines[0]) > 50:
                    title += "..."
            
            # Images
            image_url = None
            images = note.get("images", [])
            if images:
                image_url = images[0].get("url", "")
            elif note.get("cover", {}).get("url"):
                image_url = note["cover"]["url"]
            
            # Published time
            published_at = None
            if note.get("time"):
                try:
                    published_at = datetime.fromtimestamp(
                        note["time"] / 1000,
                        tz=timezone.utc
                    ).isoformat()
                except:
                    pass
            
            # Tags
            tags = []
            for tag in note.get("tag_list", []):
                if tag.get("name"):
                    tags.append(tag["name"])
            
            # Extra info
            extra = {
                "type": note.get("type", "normal"),  # normal or video
                "liked_count": note.get("liked_count", 0),
                "collected_count": note.get("collected_count", 0),
                "comment_count": note.get("comment_count", 0),
                "share_count": note.get("share_count", 0),
            }
            
            # URL
            note_type = "explore" if note.get("type") == "normal" else "discovery/item"
            url = f"https://www.xiaohongshu.com/{note_type}/{note_id}"
            
            return FeedItem(
                title=title,
                url=url,
                summary=desc[:200] if desc else None,
                content=desc,
                image_url=image_url,
                author=author,
                published_at=published_at,
                source_id=note_id,
                tags=tags,
                extra=extra
            )
            
        except Exception as e:
            return None
    
    @staticmethod
    def parse_feed_response(data: Dict[str, Any]) -> ParseResult:
        """Parse Xiaohongshu feed API response.
        
        Args:
            data: API response data
        
        Returns:
            ParseResult with parsed items
        """
        try:
            items = data.get("items", [])
            parsed_items = []
            
            for item in items:
                # Some API responses wrap note in "note_card"
                note = item.get("note_card", item)
                parsed = XiaohongshuParser.parse_note(note)
                if parsed:
                    parsed_items.append(parsed.__dict__)
            
            has_more = data.get("has_more", False)
            cursor = data.get("cursor", "")
            
            return ParseResult(
                success=True,
                items=parsed_items,
                has_more=has_more,
                next_cursor=cursor if has_more else None,
                total_count=len(parsed_items)
            )
            
        except Exception as e:
            return ParseResult(
                success=False,
                error=str(e)
            )
    
    @staticmethod
    def parse_user_notes_response(data: Dict[str, Any]) -> ParseResult:
        """Parse user posted notes response.
        
        Args:
            data: API response data
        
        Returns:
            ParseResult with parsed items
        """
        try:
            notes = data.get("data", {}).get("notes", [])
            parsed_items = []
            
            for note in notes:
                parsed = XiaohongshuParser.parse_note(note)
                if parsed:
                    parsed_items.append(parsed.__dict__)
            
            has_more = data.get("data", {}).get("has_more", False)
            cursor = data.get("data", {}).get("cursor", "")
            
            return ParseResult(
                success=True,
                items=parsed_items,
                has_more=has_more,
                next_cursor=cursor if has_more else None,
                total_count=data.get("data", {}).get("total", len(parsed_items))
            )
            
        except Exception as e:
            return ParseResult(
                success=False,
                error=str(e)
            )
