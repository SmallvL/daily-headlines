"""Weibo content parser module."""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.plugins.base import FeedItem, ParseResult


class WeiboParser:
    """Weibo content parser."""
    
    @staticmethod
    def clean_html(html: str) -> str:
        """Clean HTML tags from content."""
        if not html:
            return ""
        # Remove HTML tags but keep text
        text = re.sub(r'<[^>]+>', '', html)
        # Decode HTML entities
        text = text.replace('&nbsp;', ' ')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        text = text.replace('&amp;', '&')
        text = text.replace('&quot;', '"')
        text = text.replace('&#39;', "'")
        return text.strip()
    
    @staticmethod
    def parse_weibo_time(created_at: str) -> Optional[str]:
        """Parse Weibo time format to ISO format.
        
        Args:
            created_at: Weibo time string (e.g., "Mon Oct 10 12:00:00 +0800 2023")
        
        Returns:
            ISO format time string
        """
        if not created_at:
            return None
        
        try:
            # Weibo uses format like "Mon Oct 10 12:00:00 +0800 2023"
            dt = datetime.strptime(created_at, "%a %b %d %H:%M:%S %z %Y")
            return dt.isoformat()
        except ValueError:
            try:
                # Try alternative format
                dt = datetime.fromisoformat(created_at.replace("+0800", "+08:00"))
                return dt.isoformat()
            except:
                return created_at
    
    @staticmethod
    def extract_images(pic_ids: List[str], pic_infos: Dict[str, Any]) -> List[str]:
        """Extract image URLs from pic_ids and pic_infos."""
        images = []
        for pic_id in pic_ids:
            if pic_id in pic_infos:
                info = pic_infos[pic_id]
                # Try to get large image first
                if "large" in info:
                    images.append(info["large"].get("url", ""))
                elif "original" in info:
                    images.append(info["original"].get("url", ""))
                elif "bmiddle" in info:
                    images.append(info["bmiddle"].get("url", ""))
        return images
    
    @staticmethod
    def parse_status(status: Dict[str, Any]) -> Optional[FeedItem]:
        """Parse a single Weibo status.
        
        Args:
            status: Raw status data from API
        
        Returns:
            FeedItem or None if parsing fails
        """
        try:
            mid = str(status.get("mid", status.get("id", "")))
            user = status.get("user", {})
            author = user.get("screen_name", "Unknown")
            avatar = user.get("profile_image_url", "")
            
            # Parse time
            created_at = status.get("created_at", "")
            published_at = WeiboParser.parse_weibo_time(created_at)
            
            # Parse content
            text_raw = status.get("text_raw", "")
            text = WeiboParser.clean_html(status.get("text", text_raw))
            
            if not text and not text_raw:
                return None
            
            # Get title (first line or first 50 chars)
            lines = text.split("\n")
            title = lines[0][:50] if lines[0] else text[:50]
            if len(lines[0]) > 50:
                title += "..."
            
            # Extract images
            pic_ids = status.get("pic_ids", [])
            pic_infos = status.get("pic_infos", {})
            images = WeiboParser.extract_images(pic_ids, pic_infos)
            
            # Check for retweeted status
            retweeted = status.get("retweeted_status", {})
            if retweeted:
                rt_user = retweeted.get("user", {})
                rt_text = WeiboParser.clean_html(retweeted.get("text", ""))
                text = f"转发 @{rt_user.get('screen_name', '')}: {rt_text}\n\n原文: {text}"
                
                # Add retweeted images
                rt_pic_ids = retweeted.get("pic_ids", [])
                rt_pic_infos = retweeted.get("pic_infos", {})
                images.extend(WeiboParser.extract_images(rt_pic_ids, rt_pic_infos))
            
            # Build URL
            url = f"https://weibo.com/{user.get('id', '')}/{status.get('mblogid', mid)}"
            
            # Extra info
            extra = {
                "reposts_count": status.get("reposts_count", 0),
                "comments_count": status.get("comments_count", 0),
                "attitudes_count": status.get("attitudes_count", 0),
                "source": status.get("source", ""),
                "is_retweeted": bool(retweeted)
            }
            
            return FeedItem(
                title=title,
                url=url,
                summary=text[:200] if text else None,
                content=text,
                image_url=images[0] if images else None,
                author=author,
                published_at=published_at,
                source_id=mid,
                tags=[],
                extra=extra
            )
            
        except Exception as e:
            return None
    
    @staticmethod
    def parse_timeline_response(data: Dict[str, Any]) -> ParseResult:
        """Parse Weibo timeline API response.
        
        Args:
            data: API response data
        
        Returns:
            ParseResult with parsed items
        """
        try:
            statuses = data.get("statuses", [])
            parsed_items = []
            
            for status in statuses:
                parsed = WeiboParser.parse_status(status)
                if parsed:
                    parsed_items.append(parsed.__dict__)
            
            has_more = data.get("has_visible", False) or len(statuses) >= 20
            
            return ParseResult(
                success=True,
                items=parsed_items,
                has_more=has_more,
                next_cursor=str(data.get("max_id", "")) if has_more else None,
                total_count=data.get("total_number", len(parsed_items))
            )
            
        except Exception as e:
            return ParseResult(
                success=False,
                error=str(e)
            )
    
    @staticmethod
    def parse_user_blogs_response(data: Dict[str, Any]) -> ParseResult:
        """Parse user blogs API response.
        
        Args:
            data: API response data
        
        Returns:
            ParseResult with parsed items
        """
        try:
            statuses = data.get("data", {}).get("list", [])
            parsed_items = []
            
            for status in statuses:
                parsed = WeiboParser.parse_status(status)
                if parsed:
                    parsed_items.append(parsed.__dict__)
            
            since_id = data.get("data", {}).get("since_id", "")
            has_more = bool(since_id)
            
            return ParseResult(
                success=True,
                items=parsed_items,
                has_more=has_more,
                next_cursor=since_id if has_more else None,
                total_count=data.get("data", {}).get("total", len(parsed_items))
            )
            
        except Exception as e:
            return ParseResult(
                success=False,
                error=str(e)
            )
