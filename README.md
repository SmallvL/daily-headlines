# 我的每日头条

个人信息源聚合平台，支持 RSS、JSON API、网页爬虫和**插件化平台认证**（B站/微博/小红书/今日头条）。

## 项目结构

```text
apps/
  api/                  FastAPI 后端
    app/
      core/             配置、数据库、安全、错误处理、认证工具
      modules/
        auth/           认证（JWT 登录）
        sources/        信息源管理（CRUD、抓取、定时、认证配置）
        feed/           信息流（去重、分页、搜索、来源筛选）
        plugins/        插件系统 API 路由
        agent/          AI Agent 集成
        search/         全文搜索
        admin/          管理后台
        data_mgmt/      数据管理（保留策略、清理、统计）
      plugins/          插件系统核心
        base/           插件基类、注册表
        bilibili/       哔哩哔哩插件（二维码/Cookie 认证）
        weibo/          微博插件（二维码/Cookie 认证）
        xiaohongshu/    小红书插件（二维码/Cookie 认证）
        toutiao/        今日头条插件（二维码/Cookie 认证）
    tests/              后端测试
  web/                  React + Ant Design + TypeScript 前端
    src/
      features/plugins/ 插件前端组件
      modules/          页面模块
      shared/           共享 API、工具
docs/                   开发计划、设计文档
infra/                  基础设施配置
scripts/                启动脚本
```

## 功能特性

### 信息源管理
- **RSS 源** — 标准 RSS/Atom 订阅
- **JSON API** — 自定义字段映射的 REST API
- **网页爬虫** — CSS/XPath 选择器抓取网页内容
- **定时抓取** — 支持间隔模式和 Cron 表达式
- **导入/导出** — 模板化信息源配置
- **认证配置** — Cookie/Token/API Key 加密存储

### 插件化认证
- **二维码扫码登录** — B站、微博、小红书、今日头条
- **Cookie 认证** — 从浏览器复制 Cookie
- **Bearer Token / API Key** — 标准 API 认证
- **自定义 Header** — 灵活的请求头配置

### 信息流与 Dashboard
- **Feed 分页** — 无限滚动加载
- **来源筛选** — 按信源快速筛选 Feed
- **AI 摘要** — 自动提取文章摘要
- **图片代理** — 后端代理外部图片绕过防盗链

### 数据管理
- **保留策略** — 可配置数据保留天数（Feed/日志/Agent）
- **手动清理** — 预览后执行清理操作
- **数据统计** — 存储使用、数据量总览
- **一键重置** — 系统重置（需确认）

### AI Agent
- **API Token** — 独立的 Agent 认证体系，支持 scope 权限
- **OpenAI / Anthropic** — 兼容两种 API 格式
- **推理模型** — 支持 MiMo 等推理模型的 reasoning_content 解析

### 其他功能
- **全文搜索** — Meilisearch 驱动的搜索
- **用户管理** — 多用户、JWT 认证
- **主题切换** — 亮色/暗色主题
- **国际化** — 中英文支持

## 本地开发

### 后端

```bash
cd apps/api
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8015
```

### 前端

```bash
cd apps/web
npm install
npm run dev        # 开发服务器 (默认 5173)
npm run build      # 生产构建 → dist/
```

### 运行测试

```bash
cd apps/api
.venv/bin/pytest tests/ -v
```

## 插件系统

### 架构

```
app/plugins/base/         基类 (SourcePlugin) + 注册表 (PluginRegistry)
app/plugins/bilibili/     B站插件 (auth.py, parser.py, plugin.py)
app/plugins/weibo/        微博插件
app/plugins/xiaohongshu/  小红书插件
app/plugins/toutiao/      今日头条插件
```

### API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/plugins` | 列出所有插件 |
| GET | `/api/plugins/{id}` | 插件详情 + schema |
| POST | `/api/plugins/{id}/auth/init` | 初始化认证 |
| GET | `/api/plugins/{id}/auth/qrcode/status` | 轮询二维码状态 |
| POST | `/api/plugins/{id}/auth/validate` | 验证凭证 |
| POST | `/api/plugins/{id}/fetch` | 预览抓取 |

### 添加新插件

1. 创建 `app/plugins/{name}/` 目录
2. 实现 `__init__.py` 导出 `Plugin` 类
3. 继承 `SourcePlugin` 基类
4. 实现 `auth.py`（认证）、`parser.py`（解析）、`plugin.py`（主类）
5. 插件会被自动发现和注册

## 技术栈

- **后端**: FastAPI + SQLAlchemy + SQLite + Alembic
- **前端**: React + Ant Design + TypeScript + Vite
- **搜索**: Meilisearch (可选)
- **认证**: JWT + 插件化平台认证 + Fernet 加密

## 文档

- [开发计划](docs/DEVELOPMENT_PLAN.md)
- [进度看板](docs/PROGRESS_BOARD.md)
- [数据管理方案](docs/DATA_MANAGEMENT_PLAN.md)
- [部署指南](docs/DEPLOYMENT.md)
- [软件设计](docs/SOFTWARE_DESIGN.md)
- [API 文档](http://localhost:8015/docs) (Swagger UI)
