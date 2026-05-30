# 进度看板

更新时间：2026-05-29（v1.1 插件化认证完成）

## 当前阶段

v0.1 基础骨架已完成，v0.2 信息源 MVP 已具备 RSS/API 源闭环，v0.3 搜索与过滤 MVP 已具备主要交互，v0.4 定时采集基础能力已完成，v0.5 管理后台已完成，v0.6 Scrapling 爬虫源已完成，v0.7 AI Agent 源已完成，v0.8 多语言与主题已完成，v0.9 Agent Token 与数据接出已完成，v1.0 稳定版已完成，v1.1 插件化认证系统已完成。

已建立可部署的生产级系统，包括 Docker Compose 部署、MySQL 兼容、安全加固、监控指标、OPML 导入导出和备份恢复文档。新增插件化认证系统，支持 B站/微博/小红书/今日头条的二维码扫码登录。

## 看板

| 状态 | 任务 | Owner | 验收标准 |
| --- | --- | --- | --- |
| Done | 产品计划文档 | Documentation | `docs/DEVELOPMENT_PLAN.md` 已落盘 |
| Done | 软件设计文档 | Documentation | `docs/SOFTWARE_DESIGN.md` 已落盘 |
| Done | v0.1 基础骨架 | Backend Foundation / Frontend Foundation | 后端和前端最小应用可启动 |
| Done | 后端 FastAPI 骨架 | Backend Foundation Agent | `/api/health`、`/api/auth/login`、`/api/auth/me` 已实现 |
| Done | 前端 React/Ant Design 骨架 | Frontend Foundation Agent | 登录页、应用壳、工作台空状态已实现 |
| Done | 认证 MVP 占位 | Auth RBAC Agent | 支持开发管理员登录和当前用户接口 |
| Done | 数据库迁移初始化 | Backend Foundation Agent | Alembic 可创建基础表 |
| Done | 信息源 MVP | Source Agent | 支持 RSS/API 源创建、测试预览和手动抓取 |
| Done | 首页信息流 | Feed UI Agent | 能展示已抓取 RSS/API 条目列表 |
| Done | 搜索与过滤 MVP | Search Agent / Feed UI Agent | 支持关键词搜索、来源类型过滤、图片过滤、收藏过滤和保存搜索 |
| Done | 定时采集 MVP | Scheduler Agent / Source Agent | 信息源可配置定时抓取间隔、启停状态、查看抓取日志，并由单进程调度器执行到期任务 |
| Done | 抓取失败重试与退避 | Backend Agent | 失败时 attempt < max_attempts 自动设置 next_retry_at（指数退避），调度器扫描重试 |
| Done | 全局任务日志 API | Backend Agent | `GET /api/sources/fetch-logs` 支持按 source/status/trigger 过滤和分页 |
| Done | 任务日志总览页面 | Frontend Agent | 侧边栏"任务日志"入口，表格展示所有源的抓取日志，支持过滤和分页 |
| Done | DB 认证 + JWT | Backend Agent | 登录验证数据库用户，JWT token，PBKDF2-SHA256 密码哈希，启动时种子管理员 |
| Done | 用户管理 API | Backend Agent | `POST /api/admin/users` 创建用户，`PATCH .../role` 和 `PATCH .../status` 角色/状态切换 |
| Done | 组管理 API | Backend Agent | 用户组 CRUD、成员添加/移除、组级推送支持 |
| Done | 公共信息源模板 API | Backend Agent | 模板 CRUD、推送到用户或组、用户接受/忽略推送自动创建源 |
| Done | 审计日志 API | Backend Agent | `GET /api/admin/audit-logs` 按操作/资源类型过滤和分页 |
| Done | 用户管理页面 | Frontend Agent | 表格展示真实用户数据，搜索、创建用户弹窗、角色/状态开关 |
| Done | 组管理页面 | Frontend Agent | 创建组、删除组、查看/添加/移除成员 |
| Done | 公共模板页面 | Frontend Agent | 创建/删除模板、推送到用户或组 |
| Done | 审计日志页面 | Frontend Agent | 操作/资源类型过滤、分页表格 |
| Done | Web 爬虫连接器 | Backend Agent | CSS/XPath 选择器提取、域名安全限制、`<time>` 属性优先 |
| Done | 网页爬虫源类型 | Backend Agent | `SourceType` 新增 `"web"`，路由到 web connector |
| Done | 网页爬虫表单 | Frontend Agent | 选择器类型切换（CSS/XPath）、9 个选择器字段、域名白名单 |
| Done | 浏览器验证 v0.6 | QA Agent | 测试预览 3 条新闻 ✅、保存信息源 ✅、手动抓取入库 ✅、信息流展示 ✅ |
| Done | AI Agent 源后端 | Backend Agent | LLM Provider CRUD、OpenAI/Anthropic 双格式、草稿生成/确认 API |
| Done | AI Agent 源前端 | Frontend Agent | Provider 管理、需求输入、AI 生成草稿、JSON 编辑、预览确认 |
| Done | 浏览器验证 v0.7 | QA Agent | Provider 创建 ✅、AI 草稿生成 ✅、api_format 字段 ✅、草稿确认 ✅ |
| Done | i18n 国际化 | Frontend Agent | react-i18next + zh-CN/en-US 语言包，登录页/侧边栏/设置页全部 i18n |
| Done | 用户偏好 API | Backend Agent | user_preferences 表，GET/PATCH /api/preferences，语言/主题/默认视图 |
| Done | 设置页面 | Frontend Agent | 语言切换、主题切换（亮/暗/系统）、默认视图切换 |
| Done | 浏览器验证 v0.8 | QA Agent | 登录页英文 ✅、侧边栏英文 ✅、设置页 ✅、语言切换 ✅、暗色主题 ✅ |
| Done | Agent Token 后端 | Backend Agent | agent_tokens 表、Token CRUD API、SHA-256 hash 存储、scope 授权 |
| Done | 数据导出 API | Backend Agent | /api/agent-tokens/export，支持 JSON/CSV 格式，按条件过滤 |
| Done | Token 管理页面 | Frontend Agent | Token 列表、创建 Token（明文一次性显示）、吊销 Token |
| Done | 浏览器验证 v0.9 | QA Agent | Token 创建 ✅、导出 JSON ✅、导出 CSV ✅、Token 页面 ✅ |
| Done | 安全加固 | Backend Agent | 启动时校验 JWT_SECRET/密码/CORS/root 运行，结构化错误中间件 |
| Done | 增强健康检查 | Backend Agent | /api/health 带数据库连通性检测，/api/metrics 请求统计 |
| Done | 权限审计 | Backend Agent | 全量端点审计，修复 /sources/test 缺失认证，新增 AdminDep 依赖 |
| Done | 结构化日志 | Backend Agent | 请求日志中间件，request_id，响应时间，跳过 health/metrics 噪音 |
| Done | Docker Compose 部署 | DevOps Agent | API Dockerfile + Frontend Dockerfile + Nginx + MySQL + Meilisearch |
| Done | MySQL 兼容验证 | Backend Agent | 全量迁移审计，修复 alembic/env.py 模型导入，MySQL 8.0+ 兼容 |
| Done | OPML 导入导出 | Backend Agent | OPML XML 解析导入，RSS 源导出为 OPML 文件 |
| Done | 备份恢复脚本 | DevOps Agent | scripts/backup.sh + scripts/restore.sh 自动备份 MySQL |
| Done | 部署文档 | Documentation Agent | docs/DEPLOYMENT.md 完整部署指南（Docker/手动/备份/监控） |
| Done | 浏览器验证 v1.0 | QA Agent | 后端测试 6/6 ✅、ruff lint ✅、版本号 1.0.0 ✅ |

## 本轮开发记录

- 2026-05-28：开始 v0.1 基础骨架开发，创建 monorepo 目录、后端 FastAPI 骨架、前端 React/Ant Design 骨架。
- 2026-05-28：新增开发期管理员登录、当前用户接口、React 登录页、应用壳、主题切换和工作台空状态。
- 2026-05-28：新增 Alembic 配置和首个 `users` migration；后端 pytest/ruff、前端 lint/build 均通过。
- 2026-05-28：启动本地 API `8011` 和 Web `5176`，浏览器验证登录到工作台流程通过。
- 2026-05-28：修复登录页在暗色主题下卡片固定白底导致表单文字不可见的问题。
- 2026-05-28：修复窄屏下工作台 header 固定高度导致主题切换和退出按钮压住搜索栏的问题。
- 2026-05-28：修复亮色模式下侧边栏仍使用暗色 Sider、品牌文字显示不协调的问题。
- 2026-05-28：优化工作台 header 响应式断点，避免平板宽度下标题和操作区纵向堆叠产生大块空白。
- 2026-05-28：将折叠侧栏顶部品牌改为 SVG 图标，展开时显示图标加文字，折叠时只显示图标。
- 2026-05-28：推进 v0.2，新增 `sources/subscriptions/feed_items` 表、RSS connector、信息源 API、手动抓取 API 和真实首页 feed API。
- 2026-05-28：新增前端信息源页面，支持 RSS 测试预览、保存、手动抓取；首页改为读取真实 feed 数据。
- 2026-05-28：补齐标准 JSON API 源，支持 `items_path` 和字段映射；前端信息源表单支持 RSS/API 切换。
- 2026-05-28：补充信息源软删除 API 和前端删除按钮；首页"新增信息源"按钮可直接切到信息源页面。
- 2026-05-28：进入 v0.3 搜索与过滤 MVP，后端 feed 查询支持 `q/source_type/has_image`，前端搜索框和过滤抽屉接入真实查询。
- 2026-05-28：新增 `saved_searches` 表和保存搜索 API，前端过滤抽屉支持保存当前条件和加载已保存搜索。
- 2026-05-28：新增 `user_item_states` 表和收藏/已读/隐藏状态 API，前端收藏按钮和"只看收藏"过滤接入真实状态。
- 2026-05-28：前端信息流补齐"标记已读""隐藏"和"显示隐藏项"过滤，后端列表默认排除隐藏条目并支持显式包含。
- 2026-05-28：补齐阅读状态过滤，保存搜索支持收藏、已读和显示隐藏项条件的持久化与回放。
- 2026-05-28：进入 v0.4 定时采集基础能力，新增信息源定时字段、schedule 更新 API、创建表单定时配置和列表启停入口。
- 2026-05-28：新增 `source_fetch_logs` 表和抓取日志 API，手动抓取会记录成功/失败、新增数、跳过数和错误信息，前端信息源页展示最近抓取日志。
- 2026-05-28：接入 APScheduler 单进程后台执行循环，`SCHEDULER_ENABLED=true` 时定期扫描 `next_fetch_at` 已到期的信息源并执行抓取，复用抓取日志。
- 2026-05-28：v0.4 补全 — 新增 `source_fetch_logs` 重试字段（attempt/max_attempts/next_retry_at），失败时指数退避自动重试，调度器同时扫描重试任务。
- 2026-05-28：v0.4 补全 — 新增全局抓取日志 API `GET /api/sources/fetch-logs`，支持按 source/status/trigger 过滤和分页。
- 2026-05-28：v0.4 补全 — 新增前端"任务日志"页面，表格展示所有信息源的抓取日志，支持按信息源、状态、触发方式过滤。
- 2026-05-28：v0.5 — 新增 migration 0008 创建管理后台表（user_groups、user_group_members、source_templates、push_subscriptions、audit_logs），users 表新增 role 字段。
- 2026-05-28：v0.5 — 改造 auth service：从内存 token 升级为 JWT + PBKDF2-SHA256 密码哈希，启动时种子管理员用户到数据库。
- 2026-05-28：v0.5 — 新增用户管理 API（创建用户、角色/状态切换）、组管理 API（CRUD、成员管理）、公共模板 API（CRUD、推送到用户/组）、审计日志 API。
- 2026-05-28：v0.5 — 新增前端 4 个管理页面：用户管理（搜索、创建、角色/状态开关）、组管理、公共模板、审计日志，侧边栏管理员可见。
- 2026-05-28：v0.5 — 浏览器验证：用户管理页面显示真实 DB 数据（admin 管理员 + testuser 普通用户），创建用户、角色切换均正常。
- 2026-05-28：v0.6 — 新增 `app/modules/connectors/web.py` 网页爬虫连接器，基于 beautifulsoup4 + lxml，支持 CSS/XPath 选择器、域名安全限制、`<time>` 属性优先解析。
- 2026-05-28：v0.6 — `SourceType` 新增 `"web"`，`source_service` 路由到 web connector，前端 SourcesPage 增加「网页爬虫」类型和 9 个选择器表单字段。
- 2026-05-28：v0.6 — 浏览器验证：测试预览返回 3 条新闻 ✅、保存信息源 ✅、手动抓取入库 3 条 ✅、信息流页面展示正确 ✅。
- 2026-05-28：v0.6 — 第三方平台验证：V2EX ✅(10条)、新浪新闻 ✅(5条)、IT之家 ✅(10条)、少数派 ✅(10条)、虎扑 ✅(10条)、GitHub Trending ✅(10条)，6/8 平台通过共 55 条。
- 2026-05-28：v0.6 — 端到端完整流程：IT之家入库 20 条 ✅、V2EX 入库 20 条 ✅、信息流展示 43 条 ✅。
- 2026-05-28：v0.6 — 改进 User-Agent 为 Chrome 浏览器标识，添加 Accept/Accept-Language 头，禁用 SSL 验证。
- 2026-05-29：v0.7 — 新增 LLM Provider 和 AgentDraft 模型，创建 migration 0009（llm_providers + agent_drafts 表）。
- 2026-05-29：v0.7 — 新增 Agent 模块（schemas/service/router），支持 Provider CRUD、LLM 调用、草稿生成/编辑/确认/删除。
- 2026-05-29：v0.7 — 新增 api_format 字段（openai/anthropic），call_llm 支持两种 API 格式，创建 migration 0010。
- 2026-05-29：v0.7 — 修复 CurrentUser 对象用 dict 访问的 bug（user["id"] → user.id，6处）。
- 2026-05-29：v0.7 — 浏览器验证：Provider 创建 ✅、AI 草稿生成（mimo-v2.5）✅、api_format 显示 ✅、草稿确认 ✅。
- 2026-05-29：v0.7 — MiMo API 测试：OpenAI 格式完全兼容，返回 1957 tokens 的 V2EX 爬虫配置；Anthropic 格式待真实 Claude API 验证。
- 2026-05-29：v0.8 — 安装 react-i18next + i18next-browser-languagedetector，创建 zh-CN/en-US 完整语言包（200+ 词条）。
- 2026-05-29：v0.8 — 创建 user_preferences 表（migration 0011），实现 GET/PATCH /api/preferences API。
- 2026-05-29：v0.8 — 创建 SettingsPage 前端页面，支持语言/主题/默认视图切换，Segmented 组件交互。
- 2026-05-29：v0.8 — App.tsx 集成 antd locale 切换（zhCN/enUS），主题持久化到 localStorage。
- 2026-05-29：v0.8 — 登录页/侧边栏/设置页全部迁移至 i18n，浏览器验证中英文切换实时生效。
- 2026-05-29：v0.9 — 创建 agent_tokens 表（migration 0012），实现 Token CRUD API（创建/列表/吊销），SHA-256 hash 存储。
- 2026-05-29：v0.9 — 实现 Token 认证中间件（Bearer token → hash 匹配），scope 权限检查，过期时间处理。
- 2026-05-29：v0.9 — 实现数据导出 API（/api/agent-tokens/export），支持 JSON/CSV 格式，按 query/source_type 过滤。
- 2026-05-29：v0.9 — 创建 AgentTokensPage 前端页面，Token 列表、创建弹窗（明文一次性显示）、吊销确认。
- 2026-05-29：v0.9 — 浏览器验证：Token 创建 ✅、导出 3 条 JSON ✅、导出 2 条 CSV ✅、Token 页面显示 ✅。
- 2026-05-29：v1.0 — 安全加固：新增 `app/core/security.py` 启动时校验 JWT_SECRET/密码/CORS/root 运行，`app/core/errors.py` 结构化错误处理中间件。
- 2026-05-29：v1.0 — 增强健康检查：新增 `app/modules/health/router.py`，/api/health 带数据库连通性检测，/api/metrics 请求统计（请求数/错误数/平均响应时间）。
- 2026-05-29：v1.0 — 权限审计：全量审计 8 个 router 40+ 端点，修复 `POST /sources/test` 缺失认证（安全漏洞），新增 `AdminDep` 路由级管理员权限依赖。
- 2026-05-29：v1.0 — Docker Compose 部署：API Dockerfile + requirements.txt，Frontend Dockerfile（多阶段构建 + nginx），docker-compose.yml（MySQL 8.0 + Meilisearch + API + Web），.env.example。
- 2026-05-29：v1.0 — MySQL 兼容验证：全量审计 12 个迁移文件，MySQL 8.0+ 兼容，修复 alembic/env.py 补齐所有 15 个模型导入。
- 2026-05-29：v1.0 — OPML 导入导出：新增 `app/modules/sources/opml.py`，OPML XML 解析导入（支持 UTF-8/GBK 编码），RSS 源导出为 OPML 文件。
- 2026-05-29：v1.0 — 备份恢复：`scripts/backup.sh` 自动备份 MySQL + Meilisearch，`scripts/restore.sh` 一键恢复。
- 2026-05-29：v1.0 — 部署文档：`docs/DEPLOYMENT.md` 完整部署指南（Docker/手动/备份/监控/安全建议/常见问题）。
- 2026-05-29：v1.0 — 版本号升级至 1.0.0，后端测试 6/6 通过，ruff lint 通过。
- 2026-05-29：v1.1 — 插件化认证系统：创建 `app/plugins/` 插件框架（基类 SourcePlugin + 注册表 PluginRegistry），支持自动发现和注册。
- 2026-05-29：v1.1 — 实现 4 个平台插件：哔哩哔哩（动态/信息流/专栏）、微博（关注动态/我的微博）、小红书（关注/推荐/用户笔记）、今日头条（推荐/用户文章）。
- 2026-05-29：v1.1 — 每个插件支持二维码扫码登录和 Cookie 认证两种方式，含完整的认证流程（生成二维码 → 轮询状态 → 获取凭证）。
- 2026-05-29：v1.1 — 新增插件 API 路由 `/api/plugins/`，支持列出插件、获取详情、初始化认证、轮询二维码状态、验证凭证、预览抓取。
- 2026-05-29：v1.1 — 前端插件组件：QRCodeLogin（二维码登录 Modal，带倒计时和状态轮询）、PluginSelector（平台选择卡片网格）。
- 2026-05-29：v1.1 — SourcesPage 集成：认证方式新增「扫码登录」选项，选择平台后显示「扫码登录」按钮，弹出二维码 Modal。
- 2026-05-29：v1.1 — 修复 Bug：Form.useWatch 无法追踪嵌套对象 → 改用 useState；路由双前缀；插件注册表扫描路径。
- 2026-05-29：v1.1 — 浏览器验证：登录 ✅、信息源页面 ✅、插件选择器 ✅、平台选择 ✅、二维码 Modal ✅。
- 2026-05-29：v1.1 — 后端测试 16/16 通过（含 10 个插件测试），前端构建成功，零回归。

## 风险和备注

- v0.2 当前支持 RSS 和基础 JSON API 源；API 认证、分页、游标仍留到后续版本。
- v0.3 当前使用数据库 fallback 搜索；Meilisearch 索引和更复杂的查询表达式留到后续迭代。
- v0.4 当前完成调度配置持久化、UI、抓取日志和单进程 APScheduler 执行循环；失败重试已接入（指数退避，最多3次），全局任务日志总览页面已接入；多节点锁尚未接入。
- v0.5 当前完成 DB 认证、JWT、用户/组/模板/推送/审计管理；推送接受后自动创建源和订阅；角色仅 admin/user 两级。
- v0.6 当前完成网页爬虫连接器（CSS/XPath）、域名安全限制、`<time>` 属性优先解析；使用 beautifulsoup4 + lxml 替代 Scrapling（PyPI 不可访问）；已验证 6 个第三方平台（V2EX、新浪新闻、IT之家、少数派、虎扑、GitHub Trending）；SPA 平台（知乎、掘金、虎嗅等）不支持，需 JS 渲染。
- Agent token 与数据接出已进入设计文档，计划在 v0.9 实现。
- v0.7 当前完成 AI Agent 源：LLM Provider 管理（OpenAI/Anthropic 双格式）、Markdown 需求输入、AI 生成信息源草稿、JSON 编辑预览、确认创建源；已验证 mimo-v2.5 OpenAI 格式；Anthropic 格式代码已实现但未用真实 API 验证。
