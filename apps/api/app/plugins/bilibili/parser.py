"""Bilibili content parser module."""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.plugins.base import FeedItem, ParseResult

logger = logging.getLogger(__name__)


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
            
            # Timestamp — B站 may return pub_ts as int or string
            timestamp = author_module.get("pub_ts", 0)
            try:
                timestamp = int(timestamp) if timestamp else 0
            except (TypeError, ValueError):
                timestamp = 0
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
                archive = major.get("archive") or {}
                title = archive.get("title", "")
                content = archive.get("desc", content)
                image_url = archive.get("cover", "")
                bvid = archive.get("bvid", "")
                if bvid:
                    # Prefer bangumi/ep URL if available (for 番剧 episodes)
                    jump_url = archive.get("jump_url", "")
                    if jump_url and "bangumi" in jump_url:
                        url = jump_url if jump_url.startswith("http") else ("https:" + jump_url if jump_url.startswith("//") else f"https://www.bilibili.com{jump_url}")
                    else:
                        url = f"https://www.bilibili.com/video/{bvid}"
                    extra["bvid"] = bvid
                extra["duration"] = archive.get("duration_text", "")
                extra["play_count"] = archive.get("stat", {}).get("play", 0)
                
            elif dynamic_type == "DYNAMIC_TYPE_DRAW":
                # Image dynamic
                draw = major.get("draw") or {}
                draw_items = draw.get("items", []) if isinstance(draw, dict) else []
                if draw_items:
                    image_url = draw_items[0].get("src", "")
                # Use desc text as title for image dynamics
                if not title and content:
                    title = content[:50] + ("..." if len(content) > 50 else "")
                extra["image_count"] = len(draw_items)
                
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
                
            elif dynamic_type == "DYNAMIC_TYPE_LIVE" or dynamic_type == "DYNAMIC_TYPE_LIVE_RCMD":
                # Live room
                live = major.get("live", {}) or major.get("live_rcmd", {})
                title = f"[直播] {live.get('title', '')}"
                image_url = live.get("cover", "")
                extra["live_status"] = live.get("status", 0)

            elif dynamic_type == "DYNAMIC_TYPE_FORWARD":
                # Forwarded dynamic — use desc as title, try to fetch original
                if content:
                    title = content[:50] + ("..." if len(content) > 50 else "")
                orig = item.get("orig", {})
                if orig:
                    orig_modules = orig.get("modules", {})
                    orig_major = orig_modules.get("module_dynamic", {}).get("major", {})
                    orig_archive = orig_major.get("archive", {})
                    if orig_archive:
                        title = title or f"[转发] {orig_archive.get('title', '')}"
                        image_url = orig_archive.get("cover", "")

            elif dynamic_type == "DYNAMIC_TYPE_PGC" or dynamic_type == "DYNAMIC_TYPE_PGC_UNION":
                # 番剧/影视
                pgc = major.get("pgc", {}) or major.get("pgc_union", {})
                title = pgc.get("title", "")
                content = pgc.get("text1", content)
                image_url = pgc.get("cover", "")
                if pgc.get("jump_url"):
                    url = pgc["jump_url"]
                    if url.startswith("//"):
                        url = "https:" + url

            elif dynamic_type == "DYNAMIC_TYPE_COMMON_SQUARE" or dynamic_type == "DYNAMIC_TYPE_COMMON_VERTICAL":
                # Generic content card
                common = major.get("common", {})
                title = common.get("title", "")
                content = common.get("desc", content)
                image_url = common.get("cover", "")
                if common.get("jump_url"):
                    url = common["jump_url"]
                    if url.startswith("//"):
                        url = "https:" + url

            elif dynamic_type == "DYNAMIC_TYPE_MUSIC":
                # 音频
                music = major.get("music", {})
                title = music.get("title", "")
                image_url = music.get("cover", "")

            else:
                # Unknown type — preserve as text dynamic with raw type info
                if content:
                    title = content[:50] + ("..." if len(content) > 50 else "")
                else:
                    title = f"[{dynamic_type}] {dynamic_id}"

            if not title:
                title = f"动态 {dynamic_id}"

            # Upgrade http:// to https:// to avoid mixed-content warnings
            if image_url and isinstance(image_url, str) and image_url.startswith("http://"):
                image_url = "https://" + image_url[len("http://"):]
            if url and url.startswith("http://"):
                url = "https://" + url[len("http://"):]

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
            logger.exception("Failed to parse Bilibili dynamic: %s", e)
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
