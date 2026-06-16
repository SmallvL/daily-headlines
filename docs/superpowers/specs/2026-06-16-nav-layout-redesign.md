# 全局导航布局改造设计文档

**日期：** 2026-06-16
**范围：** `apps/web/src/app/AppShell.tsx` + `apps/web/src/app/App.tsx` + 相关 CSS
**目标：** 将导航从 `activePage` 状态驱动改为路由驱动，同步打磨视觉与响应式适配

---

## 背景

当前导航使用 `activePage` state 和 `if/else` 链控制页面渲染，URL 永远不会改变。存在以下问题：

1. 浏览器前进/后退无效，无法书签直达页面
2. 页面切换逻辑分散在 `App.tsx` 的 `content` 变量中，不易维护
3. 顶栏/侧栏视觉效果有改善空间
4. 小屏设备导航体验不理想

---

## 路由结构

使用 React Router v6 嵌套 Layout Route：

```
/login                     → LoginPage（无 AppShell 包裹，公开）
/                          → ProtectedRoute（鉴权守卫）
  /                        → AppShell（Layout Route，含 Sider + Header + Outlet）
    /feed                  → DashboardPage
    /sources               → SourcesPage
    /fetch-logs            → FetchLogsPage
    /agent                 → AgentPage
    /agent-tokens          → AgentTokensPage
    /settings              → SettingsPage
    /admin/users           → UsersPage
    /admin/groups          → GroupsPage
    /admin/templates       → TemplatesPage
    /admin/audit           → AuditLogsPage
    /admin/data-mgmt       → DataMgmtPage
    /                      → Navigate to /feed（默认页）
    *                      → 显示 404
```

### 路由映射表

页面标题从路由路径映射 i18n key：

```ts
const routeMeta: Record<string, { i18nKey: string }> = {
  "/feed":               { i18nKey: "feed.title" },
  "/sources":            { i18nKey: "sources.title" },
  "/fetch-logs":         { i18nKey: "taskLogs.title" },
  "/agent":              { i18nKey: "agent.title" },
  "/agent-tokens":       { i18nKey: "agent.tokens" },
  "/settings":           { i18nKey: "settings.title" },
  "/admin/users":        { i18nKey: "admin.users.title" },
  "/admin/groups":       { i18nKey: "admin.groups.title" },
  "/admin/templates":    { i18nKey: "admin.templates.title" },
  "/admin/audit":        { i18nKey: "admin.audit.title" },
  "/admin/data-mgmt":    { i18nKey: "admin.data" },
};
```

非匹配路径映射到 i18n key `"common.notFound"`。

---

## 组件变更

### App.tsx

**删除：**
- `activePage` state 和 `setActivePage`
- 整个 `content` 变量（~30 行的 if/else 链）
- `handlePreferenceChange` 中的 `setActivePage` 调用

**改为嵌套 Route 结构：**

```tsx
<Routes>
  <Route path="/login" element={session ? <Navigate to="/feed" /> : <LoginPage onLogin={handleLogin} />} />

  <Route element={<ProtectedRoute session={session} />}>
    <Route element={<AppShell session={session} isDarkMode={isDarkMode} isAdmin={isAdmin} onThemeChange={setIsDarkMode} onLogout={handleLogout} onPreferenceChange={handlePreferenceChange} />}>
      <Route path="/feed" element={<DashboardPage session={session} onCreateSource={() => navigate("/sources")} />} />
      <Route path="/sources" element={<SourcesPage session={session} />} />
      <Route path="/fetch-logs" element={<FetchLogsPage session={session} />} />
      <Route path="/agent" element={<AgentPage session={session} onCreateSource={() => navigate("/sources")} />} />
      <Route path="/agent-tokens" element={<AgentTokensPage session={session} />} />
      <Route path="/settings" element={<SettingsPage session={session} onPreferenceChange={handlePreferenceChange} />} />
      <Route path="/admin/users" element={<UsersPage session={session} />} />
      <Route path="/admin/groups" element={<GroupsPage session={session} />} />
      <Route path="/admin/templates" element={<TemplatesPage session={session} />} />
      <Route path="/admin/audit" element={<AuditLogsPage session={session} />} />
      <Route path="/admin/data-mgmt" element={<DataMgmtPage session={session} />} />
      <Route index element={<Navigate to="/feed" replace />} />
      <Route path="*" element={<NotFound />} />
    </Route>
  </Route>
</Routes>
```

### ProtectedRoute（新建）

简单鉴权守卫组件：

```tsx
function ProtectedRoute({ session }: { session: AuthSession | null }) {
  if (!session) return <Navigate to="/login" replace />;
  return <Outlet />;
}
```

### AppShell

**Props 变化：**
- 删除：`children`, `activePage`, `onPageChange`
- 删除：`ReactNode` import for `children`
- 删除：`onPreferenceChange`（SettingsPage 改为由 Route element 直接传入）

**注意：页面 props 传递方式**

所有页面组件的 props 接口保持不变。在 App.tsx 的 Route 定义中直接传入闭包中的 state/handler：

```tsx
<Route path="/settings" element={<SettingsPage session={session} onPreferenceChange={handlePreferenceChange} />} />
<Route path="/feed" element={<DashboardPage session={session} onCreateSource={() => navigate("/sources")} />} />
```

**内部逻辑变化：**
- 用 `<Outlet />` 替换 `{children}`
- 用 `useLocation().pathname` 计算 `selectedKeys`（通过路由路径到 menu key 的映射）
- 用 `useNavigate()` 替换 `onPageChange`
- 读取当前路径并设置页面标题

**侧栏：**
- 保持 232px 宽度，`lg` 断点折叠到 72px
- 品牌区（Logo + 应用名）
- 菜单项不变
- Admin 菜单在非 admin 时不显示

**顶栏：**
- 背景从 `transparent` 改为 `var(--color-bg-container)`（与内容区一致）
- 底部加 `1px solid var(--color-border-subtle)` 分隔线
- 左侧：当前页面标题
- 右侧：主题切换 + 用户名 + 退出按钮

**响应式：**
- `lg` 断点：Sider 自动折叠（已有）
- `md` 断点以下：Sider 切换为 Drawer，通过汉堡图标控制
- 小屏隐藏用户名文字，只显示图标

---

## CSS 变更

**styles.css 修改：**
- 更新 `.app-header` 样式：加背景色和边框
- 更新 `.app-content`：统一内边距
- 新增 `.app-header-right` 和 `.app-header-user` 样式
- 移除重复的 `.app-header`/`.app-main` 定义（有两套冲突的样式规则）

---

## 技术约束

- 保持 Ant Design 5 现有组件使用方式
- 不改变 `styles.css` 中的 CSS 变量系统
- 不引入新的第三方依赖
- 所有页面组件保持现有 props 接口不变

---

## 验收标准

- [ ] 登录后 `/feed` 默认展示 DashboardPage
- [ ] 侧栏点击切换页面，URL 同步变化
- [ ] 浏览器前进/后退正常工作
- [ ] 直接访问 `/sources`、`/settings` 等 URL 正确加载对应页面
- [ ] 无 session 时所有受保护路由重定向到 `/login`
- [ ] 已登录访问 `/login` 重定向到 `/feed`
- [ ] 顶栏显示当前页面标题
- [ ] 侧栏 collapsed 状态下图标 + tooltip 工作
- [ ] 小屏（<768px）Sider 切换为 Drawer
- [ ] 无回归：全部现有页面功能正常
