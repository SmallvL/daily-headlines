# Sources Page Visual Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Apply B站-style visual polish to SourcesPage — card shadows/radius, page gradient, i18n for visible labels

**Architecture:** Pure frontend changes. Three files touched: `styles.css` (card styling), locale JSONs (i18n keys), `SourcesPage.tsx` (i18n replacement). No backend changes. framer-motion already installed (v12).

**Tech Stack:** React 18, TypeScript, Vite, Ant Design 5, react-i18next

---

### Task 1: CSS — Page background + source card visual update

**Files:**
- Modify: `apps/web/src/styles.css`

- [ ] **Step 1: Add gradient background to sources page**

In `styles.css`, find the existing source section CSS (around line 311). Add a wrapper class before the section. Since SourcesPage doesn't have a dedicated page container class, use `.source-page` class. But looking at the page render, there's no outer class. So add the gradient to the existing section approach:

Add after the dashboard page section (find `/* ── Dashboard Page ── */` and the rules around it):

```css
/* ── Sources Page ── */
.source-list-section {
  background: linear-gradient(135deg, #f8f9fc 0%, #f0f2f8 100%);
  padding: 20px;
  border-radius: 12px;
}
```

For dark mode, add in the `html[data-theme="dark"]` block:
```css
  .source-list-section {
    background: none;
  }
```

- [ ] **Step 2: Update `.source-card`**

Find (around line 318):
```css
.source-card {
  border-radius: var(--radius-md);
  transition: var(--transition);
  border: 1px solid var(--color-border-subtle);
  background: var(--color-card-bg);
}
```

Replace with:
```css
.source-card {
  border-radius: 12px;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
  background: var(--color-card-bg);
}
```

- [ ] **Step 3: Update `.source-card:hover`**

Find:
```css
.source-card:hover {
  border-color: var(--ant-color-primary-border);
  box-shadow: var(--color-card-shadow-hover);
}
```

Replace with:
```css
.source-card:hover {
  box-shadow: 0 6px 20px rgba(0,0,0,0.10);
  transform: translateY(-2px);
}
```

- [ ] **Step 4: Update `.source-cards-grid` gap**

```css
.source-cards-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 18px;
}
```

- [ ] **Step 5: Commit**

```bash
git add apps/web/src/styles.css && git commit -m "style(sources): card shadows and gradient background"
```

---

### Task 2: i18n — Add new locale keys

**Files:**
- Modify: `apps/web/src/i18n/locales/en-US.json`
- Modify: `apps/web/src/i18n/locales/zh-CN.json`

- [ ] **Step 1: Add keys to en-US.json**

Find the `"sources"` object (around line 69) and add after the existing keys (before the closing `}`):

```json
    "add": "Add Source",
    "import": "Import Template",
    "edit": "Edit",
    "delete": "Delete",
    "export": "Export Template",
    "fetchNow": "Fetch Now",
    "schedule": "Schedule",
    "create": "Create Source",
    "fetchLogs": "Fetch Logs",
    "deleteConfirm": "Confirm Delete",
    "deleteMessage": "Are you sure you want to delete this source?",
    "empty": "No sources yet",
    "preview": "Preview",
    "templateExport": "Export Template",
    "scheduleEnableTitle": "Enable Schedule",
    "scheduleDisableTitle": "Disable Schedule",
    "count": "{{count}} sources",
    "cancelEdit": "Cancel Edit",
    "updateSource": "Update Source"
```

- [ ] **Step 2: Add keys to zh-CN.json**

Find the `"sources"` object (around line 69) and add:

```json
    "add": "新增信息源",
    "import": "导入模板",
    "edit": "编辑",
    "delete": "删除",
    "export": "导出模板",
    "fetchNow": "立即抓取",
    "schedule": "定时设置",
    "create": "新建信息源",
    "fetchLogs": "抓取日志",
    "deleteConfirm": "确认删除",
    "deleteMessage": "确定要删除该信息源吗？",
    "empty": "暂无信息源",
    "preview": "预览",
    "templateExport": "导出模板",
    "scheduleEnableTitle": "启用定时",
    "scheduleDisableTitle": "关闭定时",
    "count": "{{count}} 个信息源",
    "cancelEdit": "取消编辑",
    "updateSource": "更新信息源"
```

- [ ] **Step 3: Commit**

```bash
git add apps/web/src/i18n/locales/en-US.json apps/web/src/i18n/locales/zh-CN.json && git commit -m "i18n(sources): add new locale keys"
```

---

### Task 3: TSX — Add useTranslation hook + replace hardcoded strings

**Files:**
- Modify: `apps/web/src/modules/sources/SourcesPage.tsx`

- [ ] **Step 1: Add useTranslation import**

Find the imports section and add after the last import:
```tsx
import { useTranslation } from "react-i18next";
```

- [ ] **Step 2: Add t() hook inside component**

Find the component function declaration:
```tsx
export function SourcesPage({ session }: SourcesPageProps) {
```

Add after the opening brace:
```tsx
  const { t } = useTranslation();
```

- [ ] **Step 3: Replace hardcoded strings with t() calls**

Use the Edit tool with `replaceAll` for each string replacement:

| Find text | Replace with | Notes |
|-----------|-------------|-------|
| `"编辑信息源"` | `t("sources.edit")` | In section header, line ~420 |
| `"添加信息源"` | `t("sources.create")` | In section header, line ~420 |
| `"导入模板"` (in header button) | `t("sources.import")` | Line ~427 |
| `"我的信息源"` | `t("sources.mySources")` | Line ~975 |
| `"暂无信息源"` | `t("sources.empty")` | Line ~988 |
| `"导入模板"` (in empty state) | `t("sources.import")` | Line ~991 |
| `"取消编辑"` | `t("sources.cancelEdit")` | Line ~938 |
| `"更新信息源"` | `t("sources.updateSource")` | Line ~928 |
| `"保存信息源"` | `t("sources.saveSource")` | Line ~928 |
| `"测试预览"` | `t("sources.testPreview")` | Line ~912 |
| `"导出模板"` (tooltip) | `t("sources.export")` | Line ~1076 |
| `"编辑"` (tooltip) | `t("sources.edit")` | Line ~1068 |
| `"手动抓取"` (tooltip + tag) | `t("sources.manualFetch")` | Line ~1084, ~1033 |
| `"关闭定时"` | `t("sources.scheduleDisableTitle")` | Line ~1096 |
| `"启用定时"` | `t("sources.scheduleEnableTitle")` | Line ~1096 |
| `"删除"` (tooltip) | `t("sources.delete")` | Line ~1120 |
| `"抓取日志"` | `t("sources.fetchLogs")` | Line ~1142 |
| `"预览"` | `t("sources.preview")` | Line ~952 |

- [ ] **Step 4: Replace formatted string with t()**

Find:
```tsx
{sourcesQuery.data?.length ?? 0} 个信息源
```

Replace with:
```tsx
{t("sources.count", { count: sourcesQuery.data?.length ?? 0 })}
```

- [ ] **Step 5: Verify TypeScript**

```bash
cd apps/web && npx tsc -b --noEmit
```

Fix any errors.

- [ ] **Step 6: Commit**

```bash
git add apps/web/src/modules/sources/SourcesPage.tsx && git commit -m "i18n(sources): replace hardcoded strings with translation keys"
```

---

### Task 4: Verification

**Files:**
- No file changes

- [ ] **Step 1: TypeScript check**

```bash
cd apps/web && npx tsc -b --noEmit
```
Expected: No errors.

- [ ] **Step 2: Vite build**

```bash
cd apps/web && npx vite build
```
Expected: Build succeeds.

- [ ] **Step 3: Commit if any fixes**

```bash
git add -A && git commit -m "fix: address review feedback"
```
