# Dashboard Visual Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Apply visual polish to the DashboardPage — B站-style cards, soft shadows, overlay badges, framer-motion animations

**Architecture:** Pure frontend CSS + TSX changes. No backend/API changes. framer-motion already installed (v12.40.0). Two files touched: `styles.css` (CSS rules) and `DashboardPage.tsx` (motion wrappers + layout tweaks).

**Tech Stack:** React 18, TypeScript, Vite, Ant Design 5, framer-motion

---

### Task 1: CSS — Background gradient + toolbar card container

**Files:**
- Modify: `apps/web/src/styles.css`

- [ ] **Step 1: Update `.dashboard-page` with gradient background**

In `styles.css`, find `.dashboard-page` (around line 860) and add `background`:

```css
.dashboard-page {
  display: flex;
  flex-direction: column;
  gap: 20px;
  background: linear-gradient(135deg, #f8f9fc 0%, #f0f2f8 100%);
  padding: 20px;
  border-radius: 12px;
}
```

- [ ] **Step 2: Wrap toolbar in card container**

Update `.dashboard-toolbar`:

```css
.dashboard-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
  background: #fff;
  padding: 12px 16px;
  border-radius: 12px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}
```

For dark mode, add:

```css
html[data-theme="dark"] .dashboard-toolbar {
  background: var(--ant-color-bg-container);
}
```

- [ ] **Step 3: Commit**

```bash
git add apps/web/src/styles.css
git commit -m "style(dashboard): gradient background and toolbar card container"
```

---

### Task 2: CSS — Grid card visual update

**Files:**
- Modify: `apps/web/src/styles.css`

- [ ] **Step 1: Update `.dashboard-card` — remove border, add soft shadow**

Replace the existing `.dashboard-card` block (around line 980) with:

```css
.dashboard-card {
  background: var(--color-card-bg);
  border-radius: 12px;
  overflow: hidden;
  border: none;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  cursor: pointer;
  display: flex;
  flex-direction: column;
}

.dashboard-card:hover {
  box-shadow: 0 6px 20px rgba(0,0,0,0.10);
  transform: translateY(-2px);
}
```

- [ ] **Step 2: Update `.dashboard-card-body` — compact padding**

```css
.dashboard-card-body {
  padding: 10px 12px;
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
```

- [ ] **Step 3: Update `.dashboard-card-actions` — compact padding**

```css
.dashboard-card-actions {
  padding: 0 8px 8px;
  display: flex;
  justify-content: flex-end;
  gap: 4px;
}
```

- [ ] **Step 4: Add overlay badge CSS classes**

Add after `.cover-source-tag` block:

```css
.cover-badge {
  position: absolute;
  bottom: 8px;
  background: rgba(0,0,0,0.55);
  color: #fff;
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 4px;
  max-width: 50%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  line-height: 1.4;
}

.cover-badge-left {
  left: 8px;
}

.cover-badge-right {
  right: 8px;
}
```

- [ ] **Step 5: Update `.cover-source-tag` — reposition for overlay**

No changes needed — it's already positioned at bottom-left (8px 8px). The `cover-badge` classes will be used for the time badge on the right.

- [ ] **Step 6: Commit**

```bash
git add apps/web/src/styles.css
git commit -m "style(dashboard): modern cards with soft shadows and overlay badges"
```

---

### Task 3: CSS — List + compact view polish

**Files:**
- Modify: `apps/web/src/styles.css`

- [ ] **Step 1: Update `.dashboard-list-thumb` — resize + border-radius**

```css
.dashboard-list-thumb {
  width: 160px;
  min-height: 100px;
  border-radius: 8px;
  overflow: hidden;
  flex-shrink: 0;
  background: var(--color-bg-layout);
}
```

- [ ] **Step 2: Add hover state for list items**

Find `.dashboard-list-item` and add hover after the existing rule:

```css
.dashboard-list-item {
  display: flex;
  gap: 14px;
  padding: 14px 16px;
  margin: 0 -16px;
  border-radius: 8px;
  border-bottom: 1px solid var(--color-border-subtle);
  transition: background 0.2s, opacity 0.2s;
}

.dashboard-list-item:hover {
  background: var(--color-bg-hover, #f8f9fc);
}
```

- [ ] **Step 3: Add hover state for compact rows**

```css
.dashboard-compact-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  margin: 0 -12px;
  border-radius: 6px;
  border-bottom: 1px solid var(--color-border-subtle);
  transition: background 0.2s, opacity 0.2s;
}

.dashboard-compact-row:hover {
  background: var(--color-bg-hover, #f8f9fc);
}
```

- [ ] **Step 4: Commit**

```bash
git add apps/web/src/styles.css
git commit -m "style(dashboard): list and compact view hover states"
```

---

### Task 4: Dashboard TSX — framer-motion imports + animation containers

**Files:**
- Modify: `apps/web/src/modules/dashboard/DashboardPage.tsx`

- [ ] **Step 1: Add framer-motion import**

Add at the top of the file with other imports:

```tsx
import { motion } from "framer-motion";
```

- [ ] **Step 2: Add animation variant constants**

Add after the `type ViewMode = "grid" | "list" | "compact";` line:

```tsx
const cardVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: { duration: 0.35, ease: "easeOut", delay: i * 0.04 },
  }),
};

const containerVariants = {
  hidden: {},
  visible: {
    transition: { staggerChildren: 0.06 },
  },
};
```

- [ ] **Step 3: Wrap grid view with motion**

Replace the grid view render block (line ~610):

```tsx
{viewMode === "grid" && !feedQuery.isLoading && items.length > 0 ? (
  <motion.div
    className="dashboard-feed-grid"
    variants={containerVariants}
    initial="hidden"
    animate="visible"
  >
    {items.map((item, i) => (
      <motion.div
        key={item.id}
        variants={cardVariants}
        custom={i}
        whileHover={{ scale: 1.02 }}
        transition={{ type: "spring", stiffness: 300, damping: 20 }}
      >
        {renderGridCard(item)}
      </motion.div>
    ))}
  </motion.div>
) : ...}
```

- [ ] **Step 4: Wrap list view with motion**

Replace the list view block:

```tsx
{viewMode === "list" && !feedQuery.isLoading && items.length > 0 ? (
  <motion.div className="dashboard-feed-list" initial="hidden" animate="visible">
    {items.map((item, i) => (
      <motion.div
        key={item.id}
        variants={cardVariants}
        custom={i}
      >
        {renderListItem(item)}
      </motion.div>
    ))}
  </motion.div>
) : ...}
```

- [ ] **Step 5: Wrap compact view with motion**

Replace the compact view block:

```tsx
{viewMode === "compact" && !feedQuery.isLoading && items.length > 0 ? (
  <motion.div className="dashboard-feed-compact" initial="hidden" animate="visible">
    {items.map((item, i) => (
      <motion.div
        key={item.id}
        variants={cardVariants}
        custom={i}
      >
        {renderCompactRow(item)}
      </motion.div>
    ))}
  </motion.div>
) : ...}
```

- [ ] **Step 6: Commit**

```bash
git add apps/web/src/modules/dashboard/DashboardPage.tsx
git commit -m "feat(dashboard): add framer-motion entrance animations"
```

---

### Task 5: Dashboard TSX — Grid card overlay badges + styling

**Files:**
- Modify: `apps/web/src/modules/dashboard/DashboardPage.tsx`

- [ ] **Step 1: Update `renderGridCard` — move source/time to cover overlay, compact info body**

Replace the existing `renderGridCard` function (around line 332) with this updated version:

```tsx
const renderGridCard = (item: FeedItem) => {
  const readOpacity = item.is_read ? 0.5 : 1;
  return (
    <div
      key={item.id}
      className="dashboard-card"
      style={{ opacity: readOpacity }}
    >
      {/* Image with overlay badges */}
      <div className="dashboard-card-cover">
        {item.image_url ? (
          <img
            src={proxiedImageUrl(item.image_url) ?? undefined}
            alt=""
            loading="lazy"
            style={{ width: "100%", height: "100%", objectFit: "cover", display: "block" }}
            onError={(e) => {
              (e.target as HTMLImageElement).style.display = "none";
            }}
          />
        ) : (
          <div
            className="cover-placeholder"
            style={{ background: placeholderGradient(item.id) }}
          >
            <span className="cover-char">
              {item.title.charAt(0)}
            </span>
            <span className="cover-source">
              {item.source_name}
            </span>
          </div>
        )}
        <span className="cover-badge cover-badge-left">
          {item.source_name}
        </span>
        <span className="cover-badge cover-badge-right">
          {relativeTime(item.published_at ?? item.fetched_at)}
        </span>
      </div>

      {/* Body — compact, no summary */}
      <div className="dashboard-card-body">
        <Typography.Text
          strong
          ellipsis={{ tooltip: item.title }}
          style={{
            fontSize: 14,
            lineHeight: 1.5,
            cursor: item.url ? "pointer" : "default",
            display: "-webkit-box",
            WebkitLineClamp: 2,
            WebkitBoxOrient: "vertical",
            overflow: "hidden",
          }}
          onClick={() => {
            handleTitleClick(item);
            if (item.url) window.open(item.url, "_blank", "noopener,noreferrer");
          }}
        >
          {item.title}
        </Typography.Text>
      </div>

      {/* Actions */}
      <div className="dashboard-card-actions" style={{ opacity: item.is_read ? 0.5 : 1 }}>
        {renderActions(item)}
      </div>
    </div>
  );
};
```

Key changes:
1. Remove the `className="dashboard-card-cover"` child inline style for `readOpacity` (now at card level)
2. Add source badge + time badge as overlay elements inside cover
3. Remove summary from card body (already not shown in current grid view)
4. Compact info area with just title + actions
5. Remove the separate `renderTitle` call — inline the title directly

- [ ] **Step 2: Commit**

```bash
git add apps/web/src/modules/dashboard/DashboardPage.tsx
git commit -m "feat(dashboard): grid card overlay badges and compact layout"
```

---

### Task 6: Dashboard TSX — List/compact view polish

**Files:**
- Modify: `apps/web/src/modules/dashboard/DashboardPage.tsx`

- [ ] **Step 1: Update `renderListItem` — remove inline thumbnail width, use CSS class only**

The thumbnail size is now controlled by CSS (160px). Remove the inline `style={{ width: 200, ... }}` aspect from the thumb div if present — but looking at the current code (line 405), the list thumb already uses the CSS class `.dashboard-list-thumb` so no change needed there.

Just verify the existing list item renderer works with the new CSS. No code changes needed for the list view — CSS handles it.

- [ ] **Step 2: Update `renderCompactRow` — verify spacing**

Same — no TSX changes needed for compact row. CSS handles the hover state.

- [ ] **Step 3: Commit**

```bash
git add apps/web/src/modules/dashboard/DashboardPage.tsx
git commit -m "fix(dashboard): list and compact view minor polish"
```

---

### Task 7: Verification

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

- [ ] **Step 3: Backend tests**

```bash
cd apps/api && source .venv/bin/activate && DEV_ADMIN_PASSWORD=admin123 JWT_SECRET=test-secret PYTHONPATH=$PWD pytest tests/ -v --tb=short
```
Expected: 26 passed, 6 pre-existing errors in test_plugins.py (unrelated).

- [ ] **Step 4: Commit verification (if any fixes needed)**

If any type errors or build errors, fix them first, then:
```bash
git add -A && git commit -m "fix: address review feedback"
```

No commit if everything passes without changes — the previous tasks already committed working code.
