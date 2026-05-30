# Agent 接手说明

更新时间：2026-05-28

## 当前项目状态

项目是“我的每日头条”个人信息源聚合平台，当前已完成基础 monorepo、FastAPI 后端、React/Ant Design 前端、RSS/API 信息源、信息流、搜索过滤、保存搜索、用户条目状态、定时抓取配置、抓取日志和单进程 APScheduler 到期任务执行。

当前默认技术栈：

- 后端：Python、FastAPI、SQLAlchemy、Alembic、SQLite。
- 前端：React、TypeScript、Vite、Ant Design、TanStack Query。
- 调度：APScheduler，默认关闭，通过环境变量启用。
- 搜索：当前是数据库 fallback，Meilisearch 仍是后续目标。

## 目录结构

```text
apps/
  api/              FastAPI 后端
  web/              React 前端
docs/
  DEVELOPMENT_PLAN.md
  SOFTWARE_DESIGN.md
  PROGRESS_BOARD.md
  AGENT_HANDOFF.md
infra/
  docker-compose.yml
```

## 后端启动

```bash
cd apps/api
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8015
```

启用单进程调度器：

```bash
SCHEDULER_ENABLED=true SCHEDULER_INTERVAL_SECONDS=60 uvicorn app.main:app --host 0.0.0.0 --port 8015
```

Windows PowerShell 本地启动示例：

```powershell
cd apps/api
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
alembic upgrade head
$env:SCHEDULER_ENABLED="true"
$env:SCHEDULER_INTERVAL_SECONDS="60"
uvicorn app.main:app --reload --port 8015
```

## 前端启动

```bash
cd apps/web
npm install
VITE_API_BASE_URL=http://127.0.0.1:8015 npm run dev -- --host 0.0.0.0 --port 5180
```

Windows PowerShell 本地启动示例：

```powershell
cd apps/web
npm install
$env:VITE_API_BASE_URL="http://127.0.0.1:8015"
npm run dev -- --host 0.0.0.0 --port 5180
```

默认开发登录：

- 用户名：`admin`
- 密码：`admin123`

## 验证命令

后端：

```bash
cd apps/api
python -m ruff check .
python -m pytest
```

前端：

```bash
cd apps/web
npm run lint
npm run build
```

## 已实现模块

- `auth`：开发管理员登录、Bearer token、当前用户。
- `users`：当前用户资料。
- `sources`：RSS/API 信息源创建、测试预览、软删除、手动抓取、定时配置、抓取日志。
- `connectors`：RSS connector、基础 JSON API connector。
- `feed`：信息流查询、关键词/来源/图片/收藏/已读/隐藏过滤、收藏/已读/隐藏状态。
- `search`：保存搜索 CRUD，支持过滤条件回放。
- `scheduler`：APScheduler 单进程到期任务扫描，复用 sources 抓取服务。
- 前端：登录页、应用壳、信息流页、信息源页、主题切换、基础多语言资源。

## 重要边界

- 不要把第三方站点特殊逻辑写进核心模块，应通过 connector/template 扩展。
- 当前调度器是单进程方案，不具备多节点锁；部署多 API 进程时必须只让一个进程启用 `SCHEDULER_ENABLED=true`。
- 当前搜索仍走数据库查询，不是 Meilisearch。
- 当前认证是开发期简化实现，不适合作为生产安全边界。
- SQLite 适合当前开发阶段，后续 MySQL 兼容需要单独验证。

## 推荐下一步

1. 增加抓取失败重试和退避字段，复用 `source_fetch_logs`。
2. 增加管理端“任务日志总览”页面，不只展示第一个信息源的日志。
3. 接入 Meilisearch，建立 `SearchIndexer` 接口并让 feed item 变更触发索引。
4. 完成用户偏好持久化，包括主题、语言、默认视图。
5. 开始 v0.5 RBAC/管理后台：用户、角色、组和公共信息源模板。
6. 后续实现 v0.9 Agent token 与数据接出。

## 修改原则

- 小步提交，每次变更跑后端 ruff/pytest 和前端 lint/build。
- 后端模块之间通过 service 调用，避免跨模块直接读写内部表。
- 新数据库字段必须新增 Alembic migration，不要修改已存在 migration。
- 前端优先使用 Ant Design，不混用其他 UI 组件库。
- 进度变化同步更新 `docs/PROGRESS_BOARD.md`。
