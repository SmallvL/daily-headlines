"""Toutiao content parser module."""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.plugins.base import FeedItem, ParseResult


class ToutiaoParser:
    """Toutiao content parser."""
    
    @staticmethod
    def parse_article(item: Dict[str, Any]) -> Optional[FeedItem]:
        """Parse a Toutiao article/item.
        
        Args:
            item: Raw item data from API
        
        Returns:
            FeedItem or None if parsing fails
        """
        try:
            # Skip non-content items
            cell_type = item.get("cell_type", 0)
            if cell_type not in [0, 1, 2, 4, 8]:  # Various content types
                return None
            
            # Get basic info
            group_id = str(item.get("group_id", item.get("item_id", "")))
            title = item.get("title", "")
            abstract = item.get("abstract", "")
            
            if not title and not abstract:
                return None
            
            # Source info
            source = item.get("source", "")
            media_info = item.get("media_info", {})
            if not source and media_info:
                source = media_info.get("name", "")
            
            # Image
            image_url = None
            image_list = item.get("image_list", [])
            if image_list:
                image_url = image_list[0].get("url", "")
            elif item.get("middle_image", {}).get("url"):
                image_url = item["middle_image"]["url"]
            elif item.get("large_image", {}).get("url"):
                image_url = item["large_image"]["url"]
            
            # Published time
            published_at = None
            publish_time = item.get("publish_time", item.get("behot_time", 0))
            if publish_time:
                try:
                    published_at = datetime.fromtimestamp(
                        publish_time,
                        tz=timezone.utc
                    ).isoformat()
                except:
                    pass
            
            # URL
            source_url = item.get("source_url", "")
            if source_url:
                url = source_url
                if not url.startswith("http"):
                    url = f"https://www.toutiao.com{source_url}"
            else:
                url = f"https://www.toutiao.com/article/{group_id}/"
            
            # Tags
            tags = []
            tag = item.get("tag", "")
            if tag:
                tags.append(tag)
            
            # Extra info
            extra = {
                "cell_type": cell_type,
                "article_type": item.get("article_type", ""),
                "has_video": item.get("has_video", False),
                "has_image": item.get("has_image", False),
                "comment_count": item.get("comment_count", 0),
                "digg_count": item.get("digg_count", 0),
                "repin_count": item.get("repin_count", 0),
            }
            
            return FeedItem(
                title=title,
                url=url,
                summary=abstract[:200] if abstract else None,
                content=abstract,
                image_url=image_url,
                author=source,
                published_at=published_at,
                source_id=group_id,
                tags=tags,
                extra=extra
            )
            
        except Exception as e:
            return None
    
    @staticmethod
    def parse_feed_response(data: Dict[str, Any]) -> ParseResult:
        """Parse Toutiao feed API response.
        
        Args:
            data: API response data
        
        Returns:
            ParseResult with parsed items
        """
        try:
            items = data.get("data", [])
            if not items:
                items = data.get("return_data", {}).get("data", [])
            
            parsed_items = []
            for item in items:
                parsed = ToutiaoParser.parse_article(item)
                if parsed:
                    parsed_items.append(parsed.__dict__)
            
            has_more = data.get("has_more", True)
            max_behot = data.get("max_behot_time", "")
            next_cursor = str(max_behot) if has_more and max_behot else None
            
            return ParseResult(
                success=True,
                items=parsed_items,
                has_more=has_more,
                next_cursor=next_cursor,
                total_count=len(parsed_items)
            )
            
        except Exception as e:
            return ParseResult(
                success=False,
                error=str(e)
            )
    
    @staticmethod
    def parse_user_articles_response(data: Dict[str, Any]) -> ParseResult:
        """Parse user articles response.
        
        Args:
            data: API response data
        
        Returns:
            ParseResult with parsed items
        """
        try:
            items = data.get("data", [])
            parsed_items = []
            
            for item in items:
                parsed = ToutiaoParser.parse_article(item)
                if parsed:
                    parsed_items.append(parsed.__dict__)
            
            has_more = data.get("has_more", False)
            offset = data.get("offset", "")
            
            return ParseResult(
                success=True,
                items=parsed_items,
                has_more=has_more,
                next_cursor=str(offset) if has_more else None,
                total_count=data.get("total_count", len(parsed_items))
            )
            
        except Exception as e:
            return ParseResult(
                success=False,
                error=str(e)
            )
