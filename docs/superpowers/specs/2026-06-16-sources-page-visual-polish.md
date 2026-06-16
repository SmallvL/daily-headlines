# Sources Page Visual Polish

## Overview

Apply visual polish to the SourcesPage to align it with the Dashboard's B站-style card design. Scope includes card styling, page background, form consistency, schedule UI polish, log section alignment, and covering visible hardcoded Chinese labels with i18n keys.

## Page Background

- Add micro gradient background consistent with Dashboard: `linear-gradient(135deg, #f8f9fc 0%, #f0f2f8 100%)` on the outer page container
- Dark mode: no gradient (override to `none`)

## Source Cards (source-card)

- `border-radius: 12px` (was `var(--radius-md)` ≈ 8px)
- Remove hard `border: 1px solid var(--color-border-subtle)`
- Add `box-shadow: 0 2px 8px rgba(0,0,0,0.06)` matching Dashboard grid cards
- Hover: `box-shadow: 0 6px 20px rgba(0,0,0,0.10)`, `transform: translateY(-2px)`
- `.source-card-editing`: keep existing highlight (blue border + ring)
- Card grid gap: 16px → 18px (align with Dashboard)

## Form Section

- The create/edit form area is already wrapped in Ant Design `Card` — keep existing styling
- `.source-form-card` inherits the border-radius updates from card variables
- The Modal for edit source: add `style={{ borderRadius: 12 }}` on Modal body

## Schedule UI

- Keep existing schedule-day-btn, schedule-time-preset, schedule-summary CSS classes
- These already use custom CSS with proper styling — no visual changes needed
- The schedule section sits inside the form card, which inherits the card visual updates

## Fetch Logs Timeline

- Keep existing `.source-log-section`, `.log-timeline`, `.log-item` CSS
- Already uses proper spacing, dots, and status colors — no visual changes needed
- The section sits within the page's gradient background

## i18n Coverage (visible labels only)

Add i18n keys for hardcoded Chinese strings visible to users:

Current text → i18n key → translations

| Location | Current text | i18n key | en | zh-CN |
|----------|-------------|----------|----|-------|
| Source card header | "新增信息源" | sources.add | Add Source | 新增信息源 |
| Source card header | "导入模板" | sources.import | Import Template | 导入模板 |
| Source card actions | "编辑" | sources.edit | Edit | 编辑 |
| Source card actions | "删除" | sources.delete | Delete | 删除 |
| Source card actions | "导出模板" | sources.export | Export Template | 导出模板 |
| Source card actions | "立即抓取" | sources.fetchNow | Fetch Now | 立即抓取 |
| Source card actions | "定时设置" | sources.schedule | Schedule | 定时设置 |
| Section header | "我的信息源" | sources.mySources | My Sources | 我的信息源 |
| Form section | "新建信息源" OR "编辑信息源" | sources.create / sources.edit | Create Source / Edit Source | 新建信息源 / 编辑信息源 |
| Log section header | "抓取日志" | sources.fetchLogs | Fetch Logs | 抓取日志 |
| Modal confirm | "确认删除" / "确定要删除该信息源吗？" | sources.deleteConfirm / sources.deleteMessage | Confirm Delete / Are you sure you want to delete this source? | 确认删除 / 确定要删除该信息源吗？ |
| Empty state | "暂无信息源" | sources.empty | No sources yet | 暂无信息源 |
| Test result header | "预览结果" | sources.preview | Preview | 预览结果 |
| Various tooltips | "删除" / "收藏" / "标记已读" / "隐藏" | Already i18n'd? Check for hardcoded ones | | |

Only add visible labels. Do not translate backend error messages, placeholder text, or internal console.log statements.

## Out of Scope

- Component splitting (SourcesPage stays at ~1200 lines)
- Full i18n coverage of all strings
- Backend changes
- Responsive drawer navigation
- Schedule UI redesign (keep existing layout, only inherit card styles)
- Fetch log timeline redesign (keep existing style)
