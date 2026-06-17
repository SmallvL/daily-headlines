# Plugin System Specification & Bilibili Verification

## Overview

Standardize the plugin system for third-party site authentication and content subscription. Each website (Bilibili, Weibo, Xiaohongshu, Toutiao, etc.) implements the `SourcePlugin` interface and is auto-discovered by the registry. This spec documents the architecture, existing plugins, and the verification plan to ensure Bilibili works end-to-end.

## Plugin Architecture

### Directory Structure

```
apps/api/app/plugins/
├── base/
│   ├── __init__.py        # SourcePlugin ABC, dataclasses, AuthMethod enum
│   └── registry.py         # PluginRegistry singleton, auto_discover_plugins()
├── bilibili/               # Bilibili plugin (reference implementation)
│   ├── __init__.py          # Plugin = BilibiliPlugin
│   ├── plugin.py            # SourcePlugin subclass
│   ├── auth.py              # QR code + cookie auth
│   └── parser.py            # Content parsing
├── weibo/                   # Weibo plugin
├── xiaohongshu/             # Xiaohongshu plugin
└── toutiao/                 # Toutiao plugin
```

### SourcePlugin Interface

```python
class SourcePlugin(ABC):
    plugin_id: str                    # "bilibili"
    display_name: str                 # "哔哩哔哩"
    description: str                  # "B站动态、视频、文章等内容订阅"
    icon_url: Optional[str]           # favicon URL
    supported_auth_methods: List[AuthMethod]  # [QRCODE, COOKIE]
    default_source_type: str          # "api"

    @abstractmethod
    async def authenticate(self, method, credentials, callback) -> AuthResult
    @abstractmethod
    async def check_qrcode_status(self, session_id) -> QRCodeStatus
    @abstractmethod
    async def fetch_feed(self, credentials, config, cursor, limit) -> ParseResult
    @abstractmethod
    async def validate_credentials(self, credentials) -> bool

    # Optional
    async def get_auth_config_schema(self) -> Dict
    async def refresh_credentials(self, credentials) -> Optional[Dict]
    async def get_subscription_types(self) -> List[Dict]
    async def get_user_info(self, credentials) -> Optional[Dict]
```

### Key Dataclasses

- `AuthResult`: success, credentials, error, qrcode_url, qrcode_image, auth_url, expires_in
- `QRCodeStatus`: status (PENDING/SCANNED/CONFIRMED/EXPIRED/CANCELLED), credentials, user_info
- `ParseResult`: success, items: List[FeedItem], error, has_more, next_cursor, total_count
- `FeedItem`: title, url, summary, content, image_url, author, published_at, source_id, tags, extra

## Adding a New Plugin

1. Create `app/plugins/<name>/` directory
2. Create `__init__.py` with `Plugin = <Name>Plugin`
3. Create `plugin.py` extending `SourcePlugin`
4. Create `auth.py` with platform-specific authentication
5. Create `parser.py` with content parsing logic
6. Plugin is auto-discovered on next server start

## Bilibili Plugin Verification

### End-to-End Flow

1. **Plugin discovery**: `GET /api/plugins` returns all 4 plugins
2. **Auth init**: `POST /api/plugins/bilibili/auth/init?method=qrcode` returns QR code
3. **QR polling**: `GET /api/plugins/bilibili/auth/qrcode/status?session_id=xxx` polls scan status
4. **Source creation**: `POST /api/sources` with plugin auth config
5. **Feed fetch**: `POST /api/sources/{id}/fetch-now` triggers authenticated feed fetch
6. **Scheduled fetch**: Scheduler picks up due sources with plugin auth

### Verification Steps

1. API endpoints respond correctly (tested via pytest)
2. Plugin metadata returns correct supported_auth_methods, subscription_types
3. Auth init returns proper QR code response structure
4. Invalid auth methods return proper error codes
5. Unauthenticated access returns 401
6. Source creation with plugin auth stores credentials correctly
7. Feed fetch handles timeout and network errors gracefully

## Plugin Template

A minimal plugin template file is provided at `docs/sources/plugin-template.md` for easy extension.
