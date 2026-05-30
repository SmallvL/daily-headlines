# 数据管理方案 v1.1

## 现状分析

### 数据库概况
- **引擎**: SQLite (`daily_headlines.db`)
- **表数量**: 17 张
- **当前大小**: ~476KB（开发阶段）

### 数据增长分类

| 类别 | 表名 | 增长速度 | 风险 |
|------|------|----------|------|
| 📰 内容数据 | `feed_items` | **高速** (含 raw_json) | 存储膨胀 |
| 👤 用户状态 | `user_item_states` | 中速 | 关联 feed_items |
| 📋 抓取日志 | `source_fetch_logs` | 中速 | 可快速堆积 |
| 🔒 审计日志 | `audit_logs` | 低速 | 合规保留 |
| 🤖 Agent 草稿 | `agent_drafts` | 低速 | 含大 JSON |
| ⚙️ 配置数据 | 其余 12 张表 | 极低 | 无风险 |

### 问题
1. **无 TTL/过期机制** — 所有数据永久保留
2. **无自动清理** — 无 cron、无后台任务
3. **raw_json 膨胀** — feed_items 每条含完整原始 JSON
4. **无 VACUUM** — SQLite 删除后不自动回收空间
5. **无导出能力** — 无法备份/迁移数据
6. **无存储监控** — 无法感知数据增长

---

## 设计方案

### 一、数据保留策略（Retention Policy）

每张可增长表独立配置保留策略：

```yaml
feed_items:
  max_age_days: 90       # 保留最近 90 天
  max_per_source: 500    # 每个信源最多 500 条
  keep_saved: true       # 收藏的条目永不删除

user_item_states:
  cascade_from_feed: true  # 随 feed_items 级联清理

source_fetch_logs:
  max_age_days: 30       # 保留最近 30 天

audit_logs:
  max_age_days: 180      # 保留最近 180 天（合规）

agent_drafts:
  max_age_days: 30       # 保留最近 30 天
  keep_status: ["active"] # 仅清理 completed/failed
```

### 二、存储统计（Storage Stats）

提供 API 返回：
- 每张表的记录数
- 每张表的估算大小
- 数据库总大小
- 最旧/最新记录时间
- 增长趋势（可选）

### 三、数据清理（Purge）

- **手动触发**: 管理员在前端点击"立即清理"
- **自动触发**: 应用启动时检查是否需要清理（每日最多一次）
- **级联清理**: feed_items 删除时级联清理 user_item_states
- **安全机制**: 清理前预览影响范围，确认后执行

### 四、数据导出（Export）

支持格式：
- **JSON**: 完整结构化数据，适合备份/迁移
- **CSV**: 扁平表格，适合 Excel 分析

导出范围：
- 全量导出
- 按信源导出
- 按时间范围导出

### 五、SQLite 优化

- **WAL 模式**: 提升并发读写性能
- **定期 VACUUM**: 清理后回收空间
- **PRAGMA 分析**: 优化查询计划

### 六、前端数据管理页面

新增 `Settings > 数据管理` 子页面：
1. **存储概览卡片**: 数据库大小、总记录数、各表统计
2. **保留策略配置**: 可调整每张表的保留天数/条数
3. **清理操作区**: 预览+执行清理
4. **导出功能**: 选择范围和格式导出
5. **SQLite 优化**: VACUUM 按钮 + 状态显示

---

## 实施计划

| 阶段 | 内容 | 文件 |
|------|------|------|
| 1 | Migration: data_retention_configs 表 | `alembic/versions/0016_*` |
| 2 | 后端: 数据管理 service（stats + purge + export） | `app/modules/data_mgmt/` |
| 3 | 后端: API 路由（stats/config/purge/export） | `app/modules/data_mgmt/router.py` |
| 4 | 前端: 数据管理页面 | `apps/web/src/modules/admin/DataMgmtPage.tsx` |
| 5 | 前端: 路由注册 + 菜单集成 | `AppShell.tsx` |
| 6 | 测试 | `tests/test_data_mgmt.py` + 浏览器 |
