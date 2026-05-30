"""Bilibili content parser module."""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.plugins.base import FeedItem, ParseResult


class BilibiliParser:
    """Bilibili content parser."""
    
    @staticmethod
    def parse_dynamic(item: Dict[str, Any]) -> Optional[FeedItem]:
        """Parse a dynamic/feed item from Bilibili API.
        
        Args:
            item: Raw dynamic item from API
        
        Returns:
            FeedItem or None if parsing fails
        """
        try:
            # Get basic info
            dynamic_id = str(item.get("id_str", ""))
            modules = item.get("modules", {})
            
            # Author info
            author_module = modules.get("module_author", {})
            author = author_module.get("name", "Unknown")
            avatar = author_module.get("face", "")
            
            # Timestamp
            timestamp = author_module.get("pub_ts", 0)
            published_at = datetime.fromtimestamp(
                timestamp, 
                tz=timezone.utc
            ).isoformat() if timestamp else None
            
            # Content
            dynamic_module = modules.get("module_dynamic", {})
            major = dynamic_module.get("major", {})
            desc = dynamic_module.get("desc", {})
            
            title = ""
            content = desc.get("text", "") if desc else ""
            image_url = None
            url = f"https://www.bilibili.com/dynamic/{dynamic_id}"
            tags = []
            extra = {"dynamic_type": item.get("type", "")}
            
            # Parse different dynamic types
            dynamic_type = item.get("type", "")
            
            if dynamic_type == "DYNAMIC_TYPE_AV":
                # Video dynamic
                archive = major.get("archive", {})
                title = archive.get("title", "")
                content = archive.get("desc", content)
                image_url = archive.get("cover", "")
                bvid = archive.get("bvid", "")
                if bvid:
                    url = f"https://www.bilibili.com/video/{bvid}"
                    extra["bvid"] = bvid
                extra["duration"] = archive.get("duration_text", "")
                extra["play_count"] = archive.get("stat", {}).get("play", 0)
                
            elif dynamic_type == "DYNAMIC_TYPE_DRAW":
                # Image dynamic
                draw = major.get("draw", {})
                items = draw.get("items", [])
                if items:
                    image_url = items[0].get("src", "")
                extra["image_count"] = len(items)
                
            elif dynamic_type == "DYNAMIC_TYPE_WORD":
                # Text dynamic
                if not title and content:
                    # Use first 50 chars as title
                    title = content[:50] + ("..." if len(content) > 50 else "")
                    
            elif dynamic_type == "DYNAMIC_TYPE_ARTICLE":
                # Article
                article = major.get("article", {})
                title = article.get("title", "")
                content = article.get("desc", content)
                image_url = article.get("image_urls", [None])[0] if article.get("image_urls") else None
                url = f"https://www.bilibili.com/read/cv{article.get('id', '')}"
                
            elif dynamic_type == "DYNAMIC_TYPE_LIVE":
                # Live room
                live = major.get("live", {})
                title = f"[直播] {live.get('title', '')}"
                image_url = live.get("cover", "")
                extra["live_status"] = live.get("status", 0)
                
            else:
                # Unknown type, skip
                return None
            
            if not title:
                title = f"动态 {dynamic_id}"
            
            return FeedItem(
                title=title,
                url=url,
                summary=content[:200] if content else None,
                content=content,
                image_url=image_url,
                author=author,
                published_at=published_at,
                source_id=dynamic_id,
                tags=tags,
                extra=extra
            )
            
        except Exception as e:
            return None
    
    @staticmethod
    def parse_dynamics_response(data: Dict[str, Any]) -> ParseResult:
        """Parse Bilibili dynamics API response.
        
        Args:
            data: API response data
        
        Returns:
            ParseResult with parsed items
        """
        try:
            items = data.get("items", [])
            has_more = data.get("has_more", False)
            offset = data.get("offset", "")
            
            parsed_items = []
            for item in items:
                parsed = BilibiliParser.parse_dynamic(item)
                if parsed:
                    parsed_items.append(parsed.__dict__)
            
            return ParseResult(
                success=True,
                items=parsed_items,
                has_more=has_more,
                next_cursor=offset if has_more else None,
                total_count=data.get("total", len(parsed_items))
            )
            
        except Exception as e:
            return ParseResult(
                success=False,
                error=str(e)
            )
    
    @staticmethod
    def parse_feed_response(data: Dict[str, Any]) -> ParseResult:
        """Parse Bilibili feed API response.
        
        Args:
            data: API response data
        
        Returns:
            ParseResult with parsed items
        """
        try:
            items = data.get("items", [])
            has_more = data.get("has_more", False)
            offset = data.get("offset", "")
            
            parsed_items = []
            for item in items:
                parsed = BilibiliParser.parse_dynamic(item)
                if parsed:
                    parsed_items.append(parsed.__dict__)
            
            return ParseResult(
                success=True,
                items=parsed_items,
                has_more=has_more,
                next_cursor=offset if has_more else None,
                total_count=data.get("total", len(parsed_items))
            )
            
        except Exception as e:
            return ParseResult(
                success=False,
                error=str(e)
            )
    
    @staticmethod
    def parse_article_list(data: Dict[str, Any]) -> ParseResult:
        """Parse Bilibili article list response.
        
        Args:
            data: API response data
        
        Returns:
            ParseResult with parsed articles
        """
        try:
            articles = data.get("articles", [])
            parsed_items = []
            
            for article in articles:
                article_id = article.get("id", "")
                cvid = article.get("cvid", article_id)
                
                parsed_items.append(FeedItem(
                    title=article.get("title", ""),
                    url=f"https://www.bilibili.com/read/cv{cvid}",
                    summary=article.get("summary", ""),
                    content=article.get("content", ""),
                    image_url=article.get("image_urls", [None])[0] if article.get("image_urls") else None,
                    author=article.get("author_name", ""),
                    published_at=datetime.fromtimestamp(
                        article.get("publish_time", 0),
                        tz=timezone.utc
                    ).isoformat() if article.get("publish_time") else None,
                    source_id=str(article_id),
                    tags=[],
                    extra={
                        "view_count": article.get("stats", {}).get("view", 0),
                        "like_count": article.get("stats", {}).get("like", 0),
                        "reply_count": article.get("stats", {}).get("reply", 0)
                    }
                ).__dict__)
            
            return ParseResult(
                success=True,
                items=parsed_items,
                has_more=data.get("has_more", False),
                next_cursor=str(data.get("next_offset", "")) if data.get("has_more") else None
            )
            
        except Exception as e:
            return ParseResult(
                success=False,
                error=str(e)
            )
