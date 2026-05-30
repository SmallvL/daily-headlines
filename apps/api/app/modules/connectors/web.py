"""Web page connector for fetching and parsing HTML content."""

import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urljoin

from selectolax.parser import HTMLParser

from app.modules.feed.schemas import FeedItemCreate


def _extract_text(node: Any, selector: str, selector_type: str = "css") -> str | None:
    """Extract text content from a node using CSS or XPath selector."""
    if not node or not selector:
        return None
    try:
        if selector_type == "xpath":
            # For XPath, we need to use lxml
            from lxml import html
            tree = html.fromstring(node.html if hasattr(node, 'html') else str(node))
            results = tree.xpath(selector)
            if results:
                return results[0].text_content().strip() if hasattr(results[0], 'text_content') else str(results[0]).strip()
        else:
            # CSS selector
            selected = node.css_first(selector)
            if selected:
                return selected.text(strip=True)
    except Exception:
        pass
    return None


def _extract_attr(node: Any, selector: str, attr: str, selector_type: str = "css") -> str | None:
    """Extract an attribute from a node using CSS or XPath selector."""
    if not node or not selector:
        return None
    try:
        if selector_type == "xpath":
            from lxml import html
            tree = html.fromstring(node.html if hasattr(node, 'html') else str(node))
            results = tree.xpath(selector)
            if results:
                elem = results[0]
                if hasattr(elem, 'get'):
                    return elem.get(attr)
                return str(elem).strip() if elem else None
        else:
            selected = node.css_first(selector)
            if selected:
                return selected.attributes.get(attr)
    except Exception:
        pass
    return None


def _extract_image(node: Any, selector: str, selector_type: str = "css") -> str | None:
    """Extract image URL from a node, trying multiple attributes."""
    if not node or not selector:
        return None
    try:
        if selector_type == "xpath":
            from lxml import html
            tree = html.fromstring(node.html if hasattr(node, 'html') else str(node))
            results = tree.xpath(selector)
            if results:
                elem = results[0]
                if hasattr(elem, 'get'):
                    # Try multiple attributes
                    for attr in ['src', 'data-src', 'data-original', 'data-lazy-src', 'data-actualsrc']:
                        val = elem.get(attr)
                        if val:
                            return val
                    # Try srcset
                    srcset = elem.get('srcset')
                    if srcset:
                        return srcset.split(',')[0].strip().split(' ')[0]
                return str(elem).strip() if elem else None
        else:
            selected = node.css_first(selector)
            if selected:
                # Try multiple attributes for lazy loading
                for attr in ['src', 'data-src', 'data-original', 'data-lazy-src', 'data-actualsrc']:
                    val = selected.attributes.get(attr)
                    if val:
                        return val
                # Try srcset
                srcset = selected.attributes.get('srcset')
                if srcset:
                    return srcset.split(',')[0].strip().split(' ')[0]
    except Exception:
        pass
    return None


def _parse_date(date_str: str | None) -> datetime | None:
    """Parse various date formats."""
    if not date_str:
        return None
    
    # Common date formats
    formats = [
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%Y/%m/%d %H:%M:%S",
        "%Y/%m/%d",
        "%d/%m/%Y %H:%M:%S",
        "%B %d, %Y",
        "%b %d, %Y",
    ]
    
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str.strip(), fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            continue
    
    return None


def web_dedupe_key(source_id: str, external_id: str | None, url: str | None, title: str) -> str:
    """Generate a deduplication key for web items."""
    import hashlib
    content = f"{source_id}:{url or ''}:{title}"
    return hashlib.md5(content.encode()).hexdigest()


def _generate_id(url: str | None, title: str, source_id: str) -> str:
    """Generate a unique ID for a feed item."""
    import hashlib
    content = f"{source_id}:{url or ''}:{title}"
    return hashlib.md5(content.encode()).hexdigest()


class WebConnector:
    """Fetch and parse web pages using CSS selectors or XPath."""

    async def fetch(
        self,
        source_id: str,
        endpoint: str,
        config: dict,
        limit: int = 20,
        extra_headers: dict[str, str] | None = None,
    ) -> tuple[str | None, list[FeedItemCreate]]:
        """
        Fetch a web page and extract items based on selectors.

        config keys:
            selector_type: "css" or "xpath" (default: "css")
            item_selector: selector for each item container
            title_selector: selector for title (within item)
            url_selector: selector for link (href attribute, within item)
            summary_selector: selector for summary text (within item)
            image_selector: selector for image (src attribute, within item)
            author_selector: selector for author text (within item)
            date_selector: selector for date text (within item)
            allowed_domains: list of allowed domain strings
        """
        import httpx

        selector_type = config.get("selector_type", "css")
        allowed_domains = config.get("allowed_domains") or []

        # Build headers with auth support
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
                " (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }
        if extra_headers:
            headers.update(extra_headers)

        async with httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            verify=False,
            headers=headers,
        ) as client:
            response = await client.get(endpoint)
            response.raise_for_status()

        html = response.text
        base_url = str(response.url)

        # Extract page title
        page_title = None
        if selector_type == "css":
            parser = HTMLParser(html)
            title_node = parser.css_first("title")
            if title_node:
                page_title = title_node.text(strip=True)
        else:
            from lxml import html as lxml_html
            tree = lxml_html.fromstring(html)
            title_results = tree.xpath("//title/text()")
            if title_results:
                page_title = title_results[0].strip()

        # Get item selector
        item_selector = config.get("item_selector")
        if not item_selector:
            return page_title, []

        # Extract items
        items: list[FeedItemCreate] = []

        if selector_type == "css":
            parser = HTMLParser(html)
            item_nodes = parser.css(item_selector)
        else:
            from lxml import html as lxml_html
            tree = lxml_html.fromstring(html)
            item_nodes = tree.xpath(item_selector)

        for node in item_nodes[:limit]:
            # Extract fields
            title = _extract_text(node, config.get("title_selector", ""), selector_type)
            if not title:
                continue

            url = _extract_attr(node, config.get("url_selector", ""), "href", selector_type)
            if url:
                url = urljoin(base_url, url)

            # Check domain restriction
            if allowed_domains and url:
                from urllib.parse import urlparse
                parsed = urlparse(url)
                if parsed.netloc not in allowed_domains:
                    continue

            summary = _extract_text(node, config.get("summary_selector", ""), selector_type)
            image_url = _extract_image(node, config.get("image_selector", ""), selector_type)
            if image_url:
                image_url = urljoin(base_url, image_url)

            author = _extract_text(node, config.get("author_selector", ""), selector_type)
            date_str = _extract_text(node, config.get("date_selector", ""), selector_type)
            published_at = _parse_date(date_str)

            item = FeedItemCreate(
                external_id=_generate_id(url, title, source_id),
                title=title,
                summary=summary,
                url=url,
                image_url=image_url,
                author=author,
                published_at=published_at,
                raw_json={
                    "source": "web",
                    "selector_type": selector_type,
                    "extracted_at": datetime.now(timezone.utc).isoformat(),
                },
            )
            items.append(item)

        return page_title, items


# Singleton instance
web_connector = WebConnector()
