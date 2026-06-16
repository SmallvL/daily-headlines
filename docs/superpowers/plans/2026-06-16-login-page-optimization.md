# 登录页视觉优化 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将登录页升级为极简专业的悬浮居中卡片，并支持用户在设置页上传/清除登录页背景图；默认使用浅灰渐变背景。

**Architecture:** 后端扩展 `user_preferences` 表与 API 以保存 `login_background_url`；新增独立的上传接口将背景图保存到 `uploads/` 目录并挂载为静态文件。前端安装 `framer-motion` 实现入场动效，重构 `LoginPage` 读取偏好并动态切换背景，在 `SettingsPage` 新增背景图上传/清除卡片。

**Tech Stack:** React 18 + TypeScript + Ant Design 5 + Vite + Framer Motion；FastAPI + SQLAlchemy + Alembic + SQLite。

---

## File Structure

### 后端变更

| 文件 | 责任 |
|------|------|
| `apps/api/app/modules/preferences/models.py` | 在 `UserPreference` 模型新增 `login_background_url` 字段 |
| `apps/api/app/modules/preferences/schemas.py` | 在 `UserPreferenceRead` / `UserPreferenceUpdate` 新增该字段 |
| `apps/api/app/modules/preferences/service.py` | `_to_read` 与默认值处理包含新字段 |
| `apps/api/app/core/config.py` | 新增上传目录与静态 URL 路径配置 |
| `apps/api/app/main.py` | 挂载 `/uploads` 静态文件路由 |
| `apps/api/app/modules/upload/router.py`（新建） | 提供 `/api/upload/login-background` 文件上传接口 |
| `apps/api/alembic/versions/0017_add_login_background_url.py`（新建） | 数据库迁移脚本 |
| `apps/api/tests/test_preferences.py`（新建） | 偏好设置与上传相关测试 |

### 前端变更

| 文件 | 责任 |
|------|------|
| `apps/web/package.json` | 新增依赖 `framer-motion` |
| `apps/web/src/shared/api/preferences.ts` | 扩展 `UserPreference` / `UserPreferenceUpdate` 类型 |
| `apps/web/src/shared/api/upload.ts`（新建） | 封装背景图上传 API |
| `apps/web/src/modules/auth/LoginPage.tsx` | 重构为悬浮居中卡片，读取背景图偏好，应用动效 |
| `apps/web/src/modules/settings/SettingsPage.tsx` | 新增"登录页背景"配置卡片 |

---

## Task 1: 后端模型扩展

**Files:**
- Modify: `apps/api/app/modules/preferences/models.py`
- Modify: `apps/api/app/modules/preferences/schemas.py`
- Modify: `apps/api/app/modules/preferences/service.py`

### Step 1.1: 修改模型

在 `UserPreference` 表中新增 `login_background_url` 字段：

```python
# apps/api/app/modules/preferences/models.py
from sqlalchemy import DateTime, String, func, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class UserPreference(Base):
    __tablename__ = "user_preferences"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True, unique=True
    )
    language: Mapped[str] = mapped_column(
        String(10), nullable=False, default="zh-CN"
    )
    theme: Mapped[str] = mapped_column(
        String(20), nullable=False, default="light"
    )
    default_view: Mapped[str] = mapped_column(
        String(20), nullable=False, default="list"
    )
    login_background_url: Mapped[str | None] = mapped_column(
        Text, nullable=True, default=None
    )
    created_at: Mapped[str] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[str] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
```

### Step 1.2: 修改 schema

```python
# apps/api/app/modules/preferences/schemas.py
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

Language = Literal["zh-CN", "en-US"]
Theme = Literal["light", "dark", "system"]
DefaultView = Literal["list", "grid", "compact"]


class UserPreferenceRead(BaseModel):
    user_id: str
    language: Language
    theme: Theme
    default_view: DefaultView
    login_background_url: str | None = None
    updated_at: datetime | None


class UserPreferenceUpdate(BaseModel):
    language: Language | None = None
    theme: Theme | None = None
    default_view: DefaultView | None = None
    login_background_url: str | None = Field(default=None)
```

### Step 1.3: 修改 service

```python
# apps/api/app/modules/preferences/service.py
import uuid

from sqlalchemy.orm import Session

from app.modules.auth.schemas import CurrentUser
from app.modules.preferences.models import UserPreference
from app.modules.preferences.schemas import UserPreferenceRead, UserPreferenceUpdate


def _to_read(p: UserPreference) -> UserPreferenceRead:
    return UserPreferenceRead(
        user_id=p.user_id,
        language=p.language,
        theme=p.theme,
        default_view=p.default_view,
        login_background_url=p.login_background_url,
        updated_at=p.updated_at,
    )


def get_or_create_preference(db: Session, user: CurrentUser) -> UserPreferenceRead:
    pref = (
        db.query(UserPreference)
        .filter(UserPreference.user_id == user.id)
        .first()
    )
    if not pref:
        pref = UserPreference(
            id=uuid.uuid4().hex[:16],
            user_id=user.id,
            language="zh-CN",
            theme="light",
            default_view="list",
            login_background_url=None,
        )
        db.add(pref)
        db.commit()
        db.refresh(pref)
    return _to_read(pref)


def update_preference(
    db: Session, user: CurrentUser, data: UserPreferenceUpdate
) -> UserPreferenceRead:
    pref = (
        db.query(UserPreference)
        .filter(UserPreference.user_id == user.id)
        .first()
    )
    if not pref:
        pref = UserPreference(
            id=uuid.uuid4().hex[:16],
            user_id=user.id,
        )
        db.add(pref)

    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(pref, k, v)

    db.commit()
    db.refresh(pref)
    return _to_read(pref)
```

### Step 1.4: 新增公开读取端点

在 `preferences/router.py` 中新增 `/login-background` 公开端点，使未登录的登录页也能获取 admin 设置的背景图：

```python
# apps/api/app/modules/preferences/router.py
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.modules.auth.router import CurrentUserDep
from app.modules.preferences import service as pref_service
from app.modules.preferences.schemas import UserPreferenceRead, UserPreferenceUpdate
from app.modules.users.models import User
from app.shared.responses import ApiResponse

router = APIRouter()

DbDep = Annotated[Session, Depends(get_db)]


@router.get("", response_model=ApiResponse[UserPreferenceRead])
def get_preference(
    db: DbDep,
    user: CurrentUserDep,
):
    """Get current user's preferences."""
    result = pref_service.get_or_create_preference(db, user)
    return ApiResponse(data=result)


@router.patch("", response_model=ApiResponse[UserPreferenceRead])
def update_preference(
    data: UserPreferenceUpdate,
    db: DbDep,
    user: CurrentUserDep,
):
    """Update current user's preferences."""
    result = pref_service.update_preference(db, user, data)
    return ApiResponse(data=result)


@router.get("/login-background", response_model=ApiResponse[str | None])
def get_login_background(db: DbDep):
    """Public endpoint: get login page background URL from admin preference."""
    admin = db.query(User).filter(User.username == settings.dev_admin_username).first()
    if not admin:
        return ApiResponse(data=None)
    pref = pref_service.get_or_create_preference(db, admin)
    return ApiResponse(data=pref.login_background_url)
```

### Step 1.5: Commit

```bash
git add apps/api/app/modules/preferences/models.py \
        apps/api/app/modules/preferences/schemas.py \
        apps/api/app/modules/preferences/service.py \
        apps/api/app/modules/preferences/router.py
git commit -m "feat(preferences): add login_background_url field and public endpoint"
```

---

## Task 2: Alembic 迁移

**Files:**
- Create: `apps/api/alembic/versions/0017_add_login_background_url.py`

### Step 2.1: 编写迁移

```python
# apps/api/alembic/versions/0017_add_login_background_url.py
"""add login_background_url to user_preferences

Revision ID: 0017
Revises: 0016
Create Date: 2026-06-16
"""

from alembic import op
import sqlalchemy as sa

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "user_preferences",
        sa.Column("login_background_url", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("user_preferences", "login_background_url")
```

### Step 2.2: 应用迁移

Run:
```bash
cd apps/api
alembic upgrade head
```

Expected: `0017_add_login_background_url.py` 执行成功，数据库新增字段。

### Step 2.3: Commit

```bash
git add apps/api/alembic/versions/0017_add_login_background_url.py
git commit -m "feat(db): add migration for login_background_url"
```

---

## Task 3: 上传接口

**Files:**
- Create: `apps/api/app/modules/upload/router.py`
- Modify: `apps/api/app/main.py`
- Modify: `apps/api/app/core/config.py`

### Step 3.1: 新增上传目录配置

```python
# apps/api/app/core/config.py
import os
from dataclasses import dataclass, field
from pathlib import Path


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "My Daily Headlines API")
    app_version: str = os.getenv("APP_VERSION", "1.0.0")
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./daily_headlines.db")
    cors_origins: list[str] = field(
        default_factory=lambda: _split_csv(
            os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
        )
    )
    dev_admin_username: str = os.getenv("DEV_ADMIN_USERNAME", "admin")
    dev_admin_password: str = os.getenv("DEV_ADMIN_PASSWORD", "")
    jwt_secret: str = os.getenv("JWT_SECRET", "")
    jwt_algorithm: str = "HS256"
    jwt_expire_hours: int = int(os.getenv("JWT_EXPIRE_HOURS", "72"))
    scheduler_enabled: bool = os.getenv("SCHEDULER_ENABLED", "false").lower() == "true"
    scheduler_interval_seconds: int = int(os.getenv("SCHEDULER_INTERVAL_SECONDS", "60"))
    uploads_dir: Path = field(
        default_factory=lambda: Path(os.getenv("UPLOADS_DIR", "./uploads")).resolve()
    )
    uploads_url_path: str = os.getenv("UPLOADS_URL_PATH", "/uploads")


settings = Settings()
```

### Step 3.2: 创建上传路由

```python
# apps/api/app/modules/upload/router.py
import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.modules.auth.router import CurrentUserDep
from app.shared.responses import ApiResponse

router = APIRouter()

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB


@router.post("/login-background", response_model=ApiResponse[dict])
def upload_login_background(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: CurrentUserDep = None,
):
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise ValueError("仅支持 JPEG/PNG/WebP/GIF 图片")

    uploads_dir = settings.uploads_dir
    uploads_dir.mkdir(parents=True, exist_ok=True)

    ext = Path(file.filename or "bg.jpg").suffix.lower()
    if ext not in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
        ext = ".jpg"

    filename = f"login-bg-{user.id}-{uuid.uuid4().hex[:8]}{ext}"
    file_path = uploads_dir / filename

    with file_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Basic size check after write
    if file_path.stat().st_size > MAX_FILE_SIZE:
        file_path.unlink()
        raise ValueError("图片大小不能超过 5MB")

    url = f"{settings.uploads_url_path}/{filename}"
    return ApiResponse(data={"url": url})
```

### Step 3.3: 注册上传路由

```python
# apps/api/app/main.py
# 在现有 import 下新增
from app.modules.upload.router import router as upload_router

# 在 router include 区域新增
app.include_router(upload_router, prefix="/api/upload", tags=["upload"])
```

### Step 3.4: Commit

```bash
git add apps/api/app/core/config.py \
        apps/api/app/modules/upload/router.py \
        apps/api/app/main.py
git commit -m "feat(upload): add login background upload endpoint"
```

---

## Task 4: 挂载 uploads 静态文件

**Files:**
- Modify: `apps/api/app/main.py`

### Step 4.1: 在 SPA 静态文件之前挂载 uploads

```python
# apps/api/app/main.py
# 在 app.include_router(...) 之后、SPA 静态文件之前新增
create_uploads_dir = settings.uploads_dir
if not create_uploads_dir.exists():
    create_uploads_dir.mkdir(parents=True, exist_ok=True)

app.mount(
    settings.uploads_url_path,
    StaticFiles(directory=str(settings.uploads_dir)),
    name="uploads",
)
```

### Step 4.2: Commit

```bash
git add apps/api/app/main.py
git commit -m "feat(static): mount uploads directory"
```

---

## Task 5: 前端 preferences API 扩展

**Files:**
- Modify: `apps/web/src/shared/api/preferences.ts`
- Create: `apps/web/src/shared/api/upload.ts`

### Step 5.1: 扩展类型

```typescript
// apps/web/src/shared/api/preferences.ts
import { AuthSession } from "./auth";
import { apiRequest } from "./client";

export type Language = "zh-CN" | "en-US";
export type Theme = "light" | "dark" | "system";
export type DefaultView = "list" | "grid" | "compact";

export type UserPreference = {
  user_id: string;
  language: Language;
  theme: Theme;
  default_view: DefaultView;
  login_background_url: string | null;
  updated_at: string | null;
};

export type UserPreferenceUpdate = {
  language?: Language;
  theme?: Theme;
  default_view?: DefaultView;
  login_background_url?: string | null;
};

export async function getPreference(
  session: AuthSession,
): Promise<UserPreference> {
  return apiRequest<UserPreference>("/api/preferences", {
    token: session.accessToken,
  });
}

export async function updatePreference(
  session: AuthSession,
  data: UserPreferenceUpdate,
): Promise<UserPreference> {
  return apiRequest<UserPreference>("/api/preferences", {
    method: "PATCH",
    token: session.accessToken,
    body: JSON.stringify(data),
  });
}

export async function getLoginBackground(): Promise<string | null> {
  return apiRequest<string | null>("/api/preferences/login-background");
}
```

### Step 5.2: 创建上传 API

```typescript
// apps/web/src/shared/api/upload.ts
import { AuthSession } from "./auth";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

export async function uploadLoginBackground(
  session: AuthSession,
  file: File,
): Promise<{ url: string }> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE_URL}/api/upload/login-background`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${session.accessToken}`,
    },
    body: formData,
  });

  const payload = (await response.json()) as {
    data?: { url: string };
    error?: { message: string };
  };

  if (!response.ok || payload.error) {
    throw new Error(payload.error?.message ?? "上传失败");
  }

  if (!payload.data?.url) {
    throw new Error("上传响应缺少 URL");
  }

  return payload.data;
}
```

### Step 5.3: Commit

```bash
git add apps/web/src/shared/api/preferences.ts \
        apps/web/src/shared/api/upload.ts
git commit -m "feat(api): extend preferences and add upload client"
```

---

## Task 6: 安装 framer-motion

**Files:**
- Modify: `apps/web/package.json`
- Modify: `apps/web/package-lock.json`（通过 npm install 自动生成）

### Step 6.1: 安装依赖

Run:
```bash
cd apps/web
npm install framer-motion
```

### Step 6.2: Commit

```bash
git add apps/web/package.json apps/web/package-lock.json
git commit -m "chore(deps): add framer-motion"
```

---

## Task 7: 重构 LoginPage

**Files:**
- Modify: `apps/web/src/modules/auth/LoginPage.tsx`

### Step 7.1: 重写 LoginPage

```tsx
// apps/web/src/modules/auth/LoginPage.tsx
import { LockOutlined, UserOutlined } from "@ant-design/icons";
import { Alert, Button, Form, Input, Typography } from "antd";
import { motion } from "framer-motion";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { AuthSession, login } from "../../shared/api/auth";
import { getLoginBackground } from "../../shared/api/preferences";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";
const DEFAULT_GRADIENT = "linear-gradient(135deg, #f5f7fa 0%, #e4e7f1 100%)";

type LoginValues = {
  username: string;
  password: string;
};

type LoginPageProps = {
  onLogin: (session: AuthSession) => void;
};

export function LoginPage({ onLogin }: LoginPageProps) {
  const { t } = useTranslation();
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [backgroundUrl, setBackgroundUrl] = useState<string | null>(null);

  useEffect(() => {
    getLoginBackground()
      .then((url) => setBackgroundUrl(url))
      .catch(() => setBackgroundUrl(null));
  }, []);

  async function handleFinish(values: LoginValues) {
    setError(null);
    setIsSubmitting(true);
    try {
      const session = await login(values);
      onLogin(session);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("auth.loginFailed"));
    } finally {
      setIsSubmitting(false);
    }
  }

  const backgroundStyle = backgroundUrl
    ? {
        backgroundImage: `url(${API_BASE_URL}${backgroundUrl})`,
        backgroundSize: "cover",
        backgroundPosition: "center",
      }
    : { background: DEFAULT_GRADIENT };

  const cardBackground = backgroundUrl
    ? "rgba(255, 255, 255, 0.96)"
    : "#ffffff";

  return (
    <main
      style={{
        minHeight: "100vh",
        display: "grid",
        placeItems: "center",
        padding: 24,
        ...backgroundStyle,
      }}
    >
      <motion.section
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.45, ease: "easeOut" }}
        style={{
          width: "100%",
          maxWidth: 360,
          padding: "40px 32px",
          borderRadius: 20,
          background: cardBackground,
          boxShadow: backgroundUrl
            ? "0 20px 60px rgba(0, 0, 0, 0.12)"
            : "0 20px 60px rgba(0, 0, 0, 0.08)",
          backdropFilter: backgroundUrl ? "blur(8px)" : undefined,
          textAlign: "center",
        }}
      >
        <div
          style={{
            width: 48,
            height: 48,
            borderRadius: 12,
            background: "linear-gradient(135deg, #1677ff 0%, #36cfc9 100%)",
            margin: "0 auto 16px",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            color: "#fff",
            fontSize: 24,
          }}
        >
          📰
        </div>
        <Typography.Title level={3} style={{ margin: "0 0 4px" }}>
          {t("common.appName")}
        </Typography.Title>
        <Typography.Paragraph
          type="secondary"
          style={{ marginBottom: 28, fontSize: 13 }}
        >
          {t("auth.loginSlogan")}
        </Typography.Paragraph>

        {error ? (
          <Alert
            type="error"
            message={error}
            showIcon
            style={{ marginBottom: 16, textAlign: "left" }}
          />
        ) : null}

        <Form<LoginValues>
          layout="vertical"
          initialValues={{ username: "", password: "" }}
          onFinish={handleFinish}
        >
          <Form.Item
            label={t("auth.username")}
            name="username"
            rules={[{ required: true, message: t("auth.username") }]}
          >
            <Input
              prefix={<UserOutlined />}
              autoComplete="username"
              size="large"
              style={{ borderRadius: 10 }}
            />
          </Form.Item>
          <Form.Item
            label={t("auth.password")}
            name="password"
            rules={[{ required: true, message: t("auth.password") }]}
          >
            <Input.Password
              prefix={<LockOutlined />}
              autoComplete="current-password"
              size="large"
              style={{ borderRadius: 10 }}
            />
          </Form.Item>
          <motion.div whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}>
            <Button
              type="primary"
              htmlType="submit"
              loading={isSubmitting}
              block
              size="large"
              style={{ borderRadius: 10 }}
            >
              {t("auth.loginButton")}
            </Button>
          </motion.div>
        </Form>
      </motion.section>
    </main>
  );
}
```

### Step 7.2: 新增 i18n 文案

在中文和英文语言包中新增 `auth.loginSlogan`：

```json
// apps/web/src/i18n/locales/zh-CN.json
{
  "auth": {
    "loginSlogan": "汇聚你关心的内容"
  }
}
```

```json
// apps/web/src/i18n/locales/en-US.json
{
  "auth": {
    "loginSlogan": "Aggregate the content you care about"
  }
}
```

### Step 7.3: 运行前端类型检查

Run:
```bash
cd apps/web
npx tsc -b --noEmit
```

Expected: 无类型错误。

### Step 7.4: Commit

```bash
git add apps/web/src/modules/auth/LoginPage.tsx \
        apps/web/src/i18n/locales/zh-CN.json \
        apps/web/src/i18n/locales/en-US.json
git commit -m "feat(auth): redesign login page with floating card and motion"
```

---

## Task 8: SettingsPage 背景图配置

**Files:**
- Modify: `apps/web/src/modules/settings/SettingsPage.tsx`

### Step 8.1: 新增背景图设置卡片

在 `SettingsPage` 中新增导入与处理函数：

```typescript
import {
  CheckOutlined,
  GlobalOutlined,
  MoonOutlined,
  SunOutlined,
  DesktopOutlined,
  UnorderedListOutlined,
  AppstoreOutlined,
  CompressOutlined,
  SettingOutlined,
  PictureOutlined,
  DeleteOutlined,
  UploadOutlined,
} from "@ant-design/icons";
import {
  Card,
  Col,
  Row,
  Segmented,
  Space,
  Typography,
  message,
  Button,
  Upload,
} from "antd";
import type { UploadChangeParam } from "antd/es/upload";
import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { AuthSession } from "../../shared/api/auth";
import {
  DefaultView,
  Language,
  Theme,
  UserPreference,
  getPreference,
  updatePreference,
} from "../../shared/api/preferences";
import { uploadLoginBackground } from "../../shared/api/upload";
```

新增 `handleUpload` 与 `handleClearBackground`：

```typescript
  const handleUploadChange = async (info: UploadChangeParam) => {
    const { file } = info;
    if (file.status === "uploading") {
      return;
    }
    if (file.status === "done") {
      message.success("背景图已上传");
    }
  };

  const customUpload = async (options: {
    file: File;
    onSuccess?: (value: unknown) => void;
    onError?: (error: Error) => void;
  }) => {
    try {
      const { url } = await uploadLoginBackground(session, options.file);
      const pref = await updatePreference(session, { login_background_url: url });
      setPreference(pref);
      onPreferenceChange?.(pref);
      options.onSuccess?.({ url });
    } catch (e) {
      message.error(e instanceof Error ? e.message : "上传失败");
      options.onError?.(e instanceof Error ? e : new Error("上传失败"));
    }
  };

  const handleClearBackground = async () => {
    try {
      const pref = await updatePreference(session, { login_background_url: null });
      setPreference(pref);
      onPreferenceChange?.(pref);
      message.success("已恢复默认背景");
    } catch (e) {
      message.error(t("settings.saveFailed"));
    }
  };
```

在 Row 中新增背景图配置卡片（放在语言/主题/视图卡片之后）：

```tsx
        <Col xs={24} md={12}>
          <Card
            title={
              <Space>
                <PictureOutlined />
                登录页背景
              </Space>
            }
            styles={{ body: { padding: "20px 24px" } }}
            style={{ borderRadius: "var(--radius-md)", height: "100%" }}
          >
            <Text type="secondary" style={{ display: "block", marginBottom: 16 }}>
              自定义登录页背景图，留空则使用默认渐变。
            </Text>
            {preference.login_background_url ? (
              <Space direction="vertical" style={{ width: "100%" }}>
                <div
                  style={{
                    width: "100%",
                    height: 100,
                    borderRadius: 8,
                    backgroundImage: `url(${import.meta.env.VITE_API_BASE_URL ?? ""}${preference.login_background_url})`,
                    backgroundSize: "cover",
                    backgroundPosition: "center",
                    border: "1px solid var(--color-border-subtle)",
                  }}
                />
                <Button icon={<DeleteOutlined />} danger onClick={handleClearBackground}>
                  清除背景图
                </Button>
              </Space>
            ) : (
              <Upload
                accept="image/jpeg,image/png,image/webp,image/gif"
                customRequest={customUpload}
                onChange={handleUploadChange}
                showUploadList={false}
              >
                <Button icon={<UploadOutlined />}>上传背景图</Button>
              </Upload>
            )}
          </Card>
        </Col>
```

### Step 8.2: 运行前端类型检查

Run:
```bash
cd apps/web
npx tsc -b --noEmit
```

Expected: 无类型错误。

### Step 8.3: Commit

```bash
git add apps/web/src/modules/settings/SettingsPage.tsx
git commit -m "feat(settings): add login background upload/clear UI"
```

---

## Task 9: 后端测试与验证

**Files:**
- Create: `apps/api/tests/test_preferences.py`

### Step 9.1: 编写偏好设置测试

```python
# apps/api/tests/test_preferences.py
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def login_admin() -> str:
    response = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]["access_token"]


def test_get_preference_includes_login_background_url(test_db):
    token = login_admin()
    response = client.get(
        "/api/preferences",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert "login_background_url" in data
    assert data["login_background_url"] is None


def test_update_login_background_url(test_db):
    token = login_admin()
    response = client.patch(
        "/api/preferences",
        headers={"Authorization": f"Bearer {token}"},
        json={"login_background_url": "/uploads/login-bg-test.jpg"},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["login_background_url"] == "/uploads/login-bg-test.jpg"

    response = client.get(
        "/api/preferences",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.json()["data"]["login_background_url"] == "/uploads/login-bg-test.jpg"


def test_clear_login_background_url(test_db):
    token = login_admin()
    client.patch(
        "/api/preferences",
        headers={"Authorization": f"Bearer {token}"},
        json={"login_background_url": "/uploads/login-bg-test.jpg"},
    )
    response = client.patch(
        "/api/preferences",
        headers={"Authorization": f"Bearer {token}"},
        json={"login_background_url": None},
    )
    assert response.status_code == 200
    assert response.json()["data"]["login_background_url"] is None


def test_public_login_background_endpoint(test_db):
    token = login_admin()
    client.patch(
        "/api/preferences",
        headers={"Authorization": f"Bearer {token}"},
        json={"login_background_url": "/uploads/login-bg-public.jpg"},
    )

    response = client.get("/api/preferences/login-background")
    assert response.status_code == 200
    assert response.json()["data"] == "/uploads/login-bg-public.jpg"
```

### Step 9.2: 运行测试

Run:
```bash
cd apps/api
pytest tests/test_preferences.py -v
```

Expected: 4 tests pass。

### Step 9.3: 运行完整后端测试套件

Run:
```bash
cd apps/api
pytest tests/ -v
```

Expected: 全部通过（无回归）。

### Step 9.4: Commit

```bash
git add apps/api/tests/test_preferences.py
git commit -m "test(preferences): add login_background_url tests"
```

---

## Task 10: 端到端验证

### Step 10.1: 启动后端

```bash
cd apps/api
source .venv/bin/activate
uvicorn app.main:app --reload --port 8015
```

### Step 10.2: 启动前端

```bash
cd apps/web
npm run dev
```

### Step 10.3: 手动验证

1. 访问 `http://localhost:5173/login`，确认：
   - 显示悬浮居中卡片
   - 默认背景为浅灰渐变
   - 卡片有入场动效
2. 登录后进入设置页，上传背景图，然后退出登录回到登录页，确认：
   - 登录页背景变为上传的图片
   - 卡片半透明并带有毛玻璃效果
3. 在设置页清除背景图，退出登录，确认背景恢复默认渐变。

---

## Self-Review Checklist

- [ ] Spec coverage: 所有设计文档中的验收标准都对应到具体任务。
- [ ] Placeholder scan: 无 TBD/TODO/"实现 later"。
- [ ] Type consistency: `login_background_url` 在前端、后端、数据库中的命名一致。
- [ ] Scope: 本计划仅覆盖登录页优化与背景图配置，导航布局改造不在本次范围。
