# Bugfix Master Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans. Tasks use checkbox (`- [ ]`) syntax.

**Goal:** Fix ~170 bugs across security, API, frontend, database, i18n, performance, and DevOps

**Architecture:** 5 phases, ordered by risk/impact. Each phase is self-contained and independently testable.

**Tech Stack:** Python/FastAPI/SQLAlchemy, React 18/TypeScript/Ant Design, SQLite

---

## Phase 0: Critical Security & Crash Fixes

### Task 0.1: XSS sanitization on source name

**Files:**
- Modify: `apps/api/app/modules/sources/schemas.py`
- Modify: `apps/web/src/modules/sources/SourcesPage.tsx`

- [ ] **Step 1: Backend — Sanitize source name on input**

In `schemas.py`, `SourceCreate.name` field, add a validator:
```python
import re
from pydantic import field_validator

@field_validator("name")
@classmethod
def sanitize_name(cls, v: str) -> str:
    return v.strip()[:160]
```

- [ ] **Step 2: Frontend — Escape output in card**

In `SourcesPage.tsx`, wrap `source.name` with `{escapedName}` or use React's built-in escaping (verify existing usage — React escapes by default, but ensure it's in text content not dangerouslySetInnerHTML). Search for `dangerouslySetInnerHTML` across the codebase and remove any usage.

- [ ] **Step 3: Test**

```bash
DEV_ADMIN_PASSWORD=admin123 JWT_SECRET=test-secret PYTHONPATH=$PWD pytest tests/ -v --tb=short
```

- [ ] **Step 4: Commit**

```bash
git add -A && git commit -m "fix: sanitize source name to prevent XSS"
```

### Task 0.2: Add GET /api/sources/{id} endpoint

**Files:**
- Modify: `apps/api/app/modules/sources/router.py`
- Modify: `apps/api/app/modules/sources/service.py`

- [ ] **Step 1: Add service method**

In `service.py`, add:
```python
def get_source(self, db: Session, current_user: CurrentUser, source_id: str) -> SourceRead:
    source = self._get_owned_source(db, current_user, source_id)
    return self._to_read(source)
```

- [ ] **Step 2: Add route**

In `router.py`, add:
```python
@router.get("/{source_id}", response_model=ApiResponse[SourceRead])
def get_source(source_id: str, current_user: CurrentUserDep, db: SessionDep) -> ApiResponse[SourceRead]:
    return success_response(service.get_source(db, current_user, source_id))
```

- [ ] **Step 3: Fix trailing slash issue**

In `main.py`, add a middleware to strip trailing slashes from API routes, or add a redirect:
```python
@app.middleware("http")
async def strip_trailing_slash(request: Request, call_next):
    path = request.url.path
    if len(path) > 1 and path.endswith("/") and path.startswith("/api"):
        new_path = path.rstrip("/")
        if new_path:
            return RedirectResponse(url=str(request.url.replace(path=new_path)), status_code=307)
    return await call_next(request)
```

- [ ] **Step 4: Commit**

### Task 0.3: Fix data management API path

**Files:**
- Modify: `apps/web/src/modules/admin/DataMgmtPage.tsx`

- [ ] **Step 1: Find the API call to `/api/data-mgmt/overview` and replace with `/api/data-mgmt/stats`**

- [ ] **Step 2: Commit**

### Task 0.4: Return proper error on bad fetch instead of 500

**Files:**
- Modify: `apps/api/app/modules/sources/service.py`

- [ ] **Step 1: Wrap fetch in try/except and return proper error**

In the `_fetch_source_items` method or the calling code, catch `Exception` and convert to `HTTPException(400, detail=str(e))` instead of letting it propagate as 500.

- [ ] **Step 2: Commit**

### Task 0.5: Fix CORS preflight (OPTIONS) response

**Files:**
- Modify: `apps/api/app/main.py`

- [ ] **Step 1: Add CORS middleware if not present**

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

- [ ] **Step 2: Commit**

---

## Phase 1: Backend API hardening

### Task 1.1: Return proper HTTP status codes (201, 204)

**Files:**
- Modify: `apps/api/app/modules/sources/router.py`

- [ ] **Step 1: Change POST to return 201**

```python
@router.post("", response_model=ApiResponse[SourceRead], status_code=201)
```

- [ ] **Step 2: Change DELETE to return 204**

```python
@router.delete("/{source_id}", status_code=204)
def delete_source(...):
    service.delete_source(db, current_user, source_id)
    return Response(status_code=204)
```

- [ ] **Step 3: Commit**

### Task 1.2: Add basic rate limiting

**Files:**
- Create: `apps/api/app/core/rate_limit.py`
- Modify: `apps/api/app/main.py`

- [ ] **Step 1: Create rate limit middleware**

```python
import time
from collections import defaultdict

class RateLimiter:
    def __init__(self, max_requests=60, window_seconds=60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: dict[str, list[float]] = defaultdict(list)

    def is_allowed(self, key: str) -> bool:
        now = time.time()
        self.requests[key] = [t for t in self.requests[key] if now - t < self.window_seconds]
        if len(self.requests[key]) >= self.max_requests:
            return False
        self.requests[key].append(now)
        return True
```

- [ ] **Step 2: Apply to login endpoint**

- [ ] **Step 3: Commit**

### Task 1.3: Add cascade deletes and DB indexes

**Files:**
- Modify: `apps/api/app/models/*.py`

- [ ] **Step 1: Add ON DELETE CASCADE to Subscription.source_id relationship**

- [ ] **Step 2: Add explicit indexes on foreign keys**

- [ ] **Step 3: Add migration script**

- [ ] **Step 4: Commit**

### Task 1.4: Localize error messages

**Files:**
- Modify: `apps/api/app/core/errors.py` (if exists) or error handling in routes

- [ ] **Step 1: Create error message catalog in both languages**

- [ ] **Step 2: Detect Accept-Language header and return localized messages**

- [ ] **Step 3: Commit**

---

## Phase 2: Frontend i18n completion

### Task 2.1: Translate remaining hardcoded Chinese strings

**Files:**
- Modify: `apps/web/src/modules/sources/SourcesPage.tsx`
- Modify: `apps/web/src/modules/dashboard/DashboardPage.tsx`
- Modify: `apps/web/src/i18n/locales/en-US.json`
- Modify: `apps/web/src/i18n/locales/zh-CN.json`

- [ ] **Step 1: DAY_LABELS → i18n keys**
- [ ] **Step 2: STATUS_LABELS → i18n keys**
- [ ] **Step 3: formatScheduleLabel → use t()**
- [ ] **Step 4: buildScheduleSummary → use t()**
- [ ] **Step 5: authTypeLabel → use t()**
- [ ] **Step 6: sourceTypeLabel → use t()**
- [ ] **Step 7: Dashboard '加载中...' → t()**
- [ ] **Step 8: Dashboard empty state → t()**
- [ ] **Step 9: Dashboard '未命名搜索' → t()**
- [ ] **Step 10: Commit**

### Task 2.2: Dynamic HTML lang attribute

**Files:**
- Modify: `apps/web/index.html`
- Modify: `apps/web/src/main.tsx`

- [ ] **Step 1: Remove hardcoded lang from index.html**
- [ ] **Step 2: Set document.documentElement.lang on i18n language change**
- [ ] **Step 3: Commit**

---

## Phase 3: Frontend UX/Performance

### Task 3.1: Add ErrorBoundary

**Files:**
- Create: `apps/web/src/shared/components/ErrorBoundary.tsx`
- Modify: `apps/web/src/app/App.tsx`

- [ ] **Step 1: Create ErrorBoundary component**
- [ ] **Step 2: Wrap route pages in ErrorBoundary**
- [ ] **Step 3: Commit**

### Task 3.2: Add React.memo to feed item renderers

**Files:**
- Modify: `apps/web/src/modules/dashboard/DashboardPage.tsx`

- [ ] **Step 1: Wrap renderGridCard, renderListItem, renderCompactRow in useCallback/memo**
- [ ] **Step 2: Commit**

### Task 3.3: Add debounced search

**Files:**
- Modify: `apps/web/src/modules/dashboard/DashboardPage.tsx`

- [ ] **Step 1: Create useDebounce hook or import from library**
- [ ] **Step 2: Apply to search input**
- [ ] **Step 3: Commit**

### Task 3.4: Add loading skeletons and error retry

**Files:**
- Modify: `apps/web/src/modules/dashboard/DashboardPage.tsx`

- [ ] **Step 1: Replace Spin with Ant Design Skeleton**
- [ ] **Step 2: Add retry button on error**
- [ ] **Step 3: Commit**

### Task 3.5: Add pagination to admin tables

**Files:**
- Modify: `apps/web/src/modules/admin/UsersPage.tsx`
- Modify: `apps/web/src/modules/admin/GroupsPage.tsx`

- [ ] **Step 1: Add Ant Design Pagination component**
- [ ] **Step 2: Wire up backend pagination params**
- [ ] **Step 3: Commit**

---

## Phase 4: DevOps & Infra

### Task 4.1: Dockerfile + docker-compose

**Files:**
- Create: `Dockerfile`
- Create: `docker-compose.yml`
- Create: `.dockerignore`
- Create: `.env.example`

### Task 4.2: Frontend meta tags

**Files:**
- Modify: `apps/web/index.html`

- [ ] **Step 1: Add favicon**
- [ ] **Step 2: Add meta description, OG tags**
- [ ] **Step 3: Create public/ directory with favicon**
- [ ] **Step 4: Commit**

### Task 4.3: CI/CD pipeline

**Files:**
- Create: `.github/workflows/ci.yml`

---

## Phase 5: Frontend Tests

### Task 5.1: Set up testing framework
### Task 5.2: Write component tests
### Task 5.3: Write API integration tests
