# Dashboard Visual Polish

## Overview

Apply visual polish to the DashboardPage (feed reader) to align it with the login page's modern visual language. Uses B站-style card design as reference: clean white cards with soft shadows, overlay badges on cover images, compact information layout, and subtle entrance animations via framer-motion.

## Background Gradient

- Light mode: `linear-gradient(135deg, #f8f9fc 0%, #f0f2f8 100%)` applied to `.dashboard-page`
- Dark mode: keep existing solid dark background (no gradient in dark mode)
- The `app-content` max-width (1400px) already centers the page; the gradient fills the full content area

## Toolbar

- Wrap toolbar in a white card container (`border-radius: 12px`, `box-shadow: 0 1px 4px rgba(0,0,0,0.06)`)
- Search input: `border-radius: 10px`, subtle border, focus ring via Ant Design
- Segmented view switcher: keep Ant Design Segmented default (already clean)
- Filter + "新增信息源" buttons: keep existing Ant Design Button styles
- Bottom visual separation: the card shadow against the gray background is sufficient

## Grid Cards (primary view mode)

- `border-radius: 12px` (was 10px)
- Remove hard border (`border: none`), use `box-shadow: 0 2px 8px rgba(0,0,0,0.06)`
- Hover: `box-shadow` deepens to `0 6px 20px rgba(0,0,0,0.10)`, `translateY(-2px)`
- Cover area (16:9 aspect ratio) with overlay badges:
  - Source name badge: bottom-left, `rgba(0,0,0,0.55)` background, white text, `border-radius: 4px`
  - Time badge: bottom-right, same style as source badge
  - On real images, the existing `cover-source-tag` CSS class is kept (same positioning)
- Info area:
  - Compact padding: `10px 12px` (was 12px 14px)
  - Title: 14px, 600 weight, max 2 lines with ellipsis
  - Remove summary line from card body (it's already omitted in current layout for grid view)
  - Bottom row: source name (left, 12px, gray) + action icons (right)
- Read state: card-level `opacity: 0.5` (was 0.6) + action icons opacity 0.5
- Empty cover: keep existing gradient placeholder with first character + source name

## List View

- Thumbnail: width 160px (was 200px), aspect-ratio maintained, `border-radius: 8px` (was 6px)
- Title + summary + meta layout unchanged
- Hover: `background: var(--color-bg-hover, #f8f9fc)` (subtle highlight)
- Divider (`border-bottom`) kept

## Compact View

- Minimal changes: only adjust spacing/padding to match the visual rhythm
- Source + time inline layout unchanged
- Hover: same subtle background as list view

## Animations (framer-motion)

### Grid view (item entrance)

```tsx
// Container
<motion.div
  variants={{
    hidden: {},
    visible: { transition: { staggerChildren: 0.06 } }
  }}
  initial="hidden"
  animate="visible"
>
  {items.map(renderGridCard)}
</motion.div>

// Each card
<motion.div
  variants={{
    hidden: { opacity: 0, y: 20 },
    visible: { opacity: 1, y: 0, transition: { duration: 0.35, ease: "easeOut" } }
  }}
>
```

### List / Compact view

Same `fadeInUp` variant per item, but no stagger (simple fadeIn only to avoid visual overload with many items). Use `damping: true` approach where each item gets a slight delay based on index.

### Card hover

```tsx
whileHover={{ scale: 1.02 }}
transition={{ type: "spring", stiffness: 300, damping: 20 }}
```

## Source Filter Bar

- Keep existing pill button style (`border-radius: 16px`, 12px font, 28px height)
- Keep horizontal scroll with thin scrollbar
- No visual changes needed; the existing style already matches the new direction

## Filter Drawer

- Keep existing Ant Design Drawer
- No visual changes needed; default Ant Design styling is sufficient
- The Drawer is functional UI, not in the main visual flow

## CSS Changes

Files to modify:
- `apps/web/src/styles.css` — update/add `.dashboard-page`, `.dashboard-card`, `.dashboard-card-cover`, `.dashboard-card-body`, `.dashboard-feed-grid`, `.dashboard-list-thumb`, `.dashboard-list-item`, `.dashboard-compact-row`, `.dashboard-toolbar`, `.dashboard-feed-list`, `.dashboard-feed-compact` CSS rules
- `apps/web/src/modules/dashboard/DashboardPage.tsx` — add framer-motion wrappers, update card/list/compact renderers

## No Backend Changes

This is purely a frontend visual polish. No API, database, or backend changes required.

## Out of Scope

- Responsive drawer navigation for mobile (deferred)
- Splitting large DashboardPage component
- i18n coverage improvements
- Filter drawer redesign
- SourcesPage or other page optimizations
