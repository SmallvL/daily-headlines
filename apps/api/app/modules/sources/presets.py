"""Source preset configurations for popular sites.

These presets allow users to quickly add common sources without
manually configuring selectors, mappings, or auth.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SourcePreset:
    id: str
    name: str
    description: str
    category: str
    type: str  # "rss" | "api" | "web"
    endpoint: str
    config: dict = field(default_factory=dict)
    auth_type: str = "none"
    icon: str = ""  # emoji or short text


# ── RSS Presets ──

_RSS_PRESETS = [
    SourcePreset(
        id="hn-rss",
        name="Hacker News",
        description="Hacker News front page (RSS)",
        category="科技",
        type="rss",
        endpoint="https://hnrss.org/frontpage",
        icon="📰",
    ),
    SourcePreset(
        id="hn-best-rss",
        name="Hacker News (Best)",
        description="Hacker News best stories (RSS)",
        category="科技",
        type="rss",
        endpoint="https://hnrss.org/best",
        icon="⭐",
    ),
    SourcePreset(
        id="hn-jobs-rss",
        name="Hacker News Jobs",
        description="Hacker News job postings (RSS)",
        category="招聘",
        type="rss",
        endpoint="https://hnrss.org/jobs",
        icon="💼",
    ),
    SourcePreset(
        id="github-trending-rss",
        name="GitHub Trending",
        description="GitHub trending repositories (RSS via mshibanami)",
        category="开发",
        type="rss",
        endpoint="https://mshibanami.github.io/GitHubTrendingRSS/daily/all.xml",
        icon="🐙",
    ),
    SourcePreset(
        id="techcrunch-rss",
        name="TechCrunch",
        description="TechCrunch technology news (RSS)",
        category="科技",
        type="rss",
        endpoint="https://techcrunch.com/feed/",
        icon="📱",
    ),
    SourcePreset(
        id="the-verge-rss",
        name="The Verge",
        description="The Verge technology news (RSS)",
        category="科技",
        type="rss",
        endpoint="https://www.theverge.com/rss/index.xml",
        icon="🎙️",
    ),
    SourcePreset(
        id="engadget-rss",
        name="Engadget",
        description="Engadget technology news (RSS)",
        category="科技",
        type="rss",
        endpoint="https://www.engadget.com/rss.xml",
        icon="🔌",
    ),
    SourcePreset(
        id="ars-technica-rss",
        name="Ars Technica",
        description="Ars Technica technology news (RSS)",
        category="科技",
        type="rss",
        endpoint="https://feeds.arstechnica.com/arstechnica/index",
        icon="🔬",
    ),
    SourcePreset(
        id="v2ex-rss",
        name="V2EX",
        description="V2EX community (RSS)",
        category="社区",
        type="rss",
        endpoint="https://www.v2ex.com/index.xml",
        icon="💬",
    ),
    SourcePreset(
        id="rsshub-trending",
        name="RSSHub Trending",
        description="RSSHub trending topics (RSS)",
        category="综合",
        type="rss",
        endpoint="https://rsshub.app/trending",
        icon="🔥",
    ),
]

# ── Web Scraper Presets (verified working selectors) ──

_WEB_PRESETS = [
    SourcePreset(
        id="hn-web",
        name="Hacker News (Web)",
        description="Hacker News front page (web scraping)",
        category="科技",
        type="web",
        endpoint="https://news.ycombinator.com/",
        config={
            "selector_type": "css",
            "item_selector": ".athing",
            "title_selector": ".titleline > a",
            "url_selector": ".titleline > a",
        },
        icon="📰",
    ),
    SourcePreset(
        id="v2ex-web",
        name="V2EX (Web)",
        description="V2EX tech tab (web scraping)",
        category="社区",
        type="web",
        endpoint="https://www.v2ex.com/?tab=tech",
        config={
            "selector_type": "css",
            "item_selector": ".cell.item",
            "title_selector": ".item_title a",
            "url_selector": ".item_title a",
            "author_selector": ".topic_info strong a",
        },
        icon="💬",
    ),
    SourcePreset(
        id="github-trending-web",
        name="GitHub Trending (Web)",
        description="GitHub trending repositories (web scraping)",
        category="开发",
        type="web",
        endpoint="https://github.com/trending",
        config={
            "selector_type": "css",
            "item_selector": "article.Box",
            "title_selector": "h2 a",
            "url_selector": "h2 a",
            "summary_selector": "p",
        },
        icon="🐙",
    ),
]

# ── API Presets ──

_API_PRESETS = [
    SourcePreset(
        id="jsonplaceholder",
        name="JSONPlaceholder Posts",
        description="Demo JSON API for testing (JSONPlaceholder)",
        category="测试",
        type="api",
        endpoint="https://jsonplaceholder.typicode.com/posts",
        config={
            "items_path": "",
            "mappings": {
                "id": "id",
                "title": "title",
                "summary": "body",
            },
        },
        icon="🧪",
    ),
]

ALL_PRESETS: list[SourcePreset] = _RSS_PRESETS + _WEB_PRESETS + _API_PRESETS

_PRESETS_BY_ID: dict[str, SourcePreset] = {p.id: p for p in ALL_PRESETS}


def list_presets() -> list[dict]:
    """Return all presets as serializable dicts."""
    return [
        {
            "id": p.id,
            "name": p.name,
            "description": p.description,
            "category": p.category,
            "type": p.type,
            "endpoint": p.endpoint,
            "config": p.config,
            "auth_type": p.auth_type,
            "icon": p.icon,
        }
        for p in ALL_PRESETS
    ]


def get_preset(preset_id: str) -> SourcePreset | None:
    """Get a preset by ID."""
    return _PRESETS_BY_ID.get(preset_id)


def preset_to_source_create(preset: SourcePreset, name: str | None = None) -> dict:
    """Convert a preset to a SourceCreate-compatible dict."""
    return {
        "name": name or preset.name,
        "type": preset.type,
        "endpoint": preset.endpoint,
        "config": preset.config,
        "auth": {"auth_type": preset.auth_type},
        "schedule_enabled": False,
    }
