# 导航布局改造 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将导航从 `activePage` 状态驱动改为 React Router 嵌套路由，同步打磨 Header/Sider 视觉与响应式适配。

**Architecture:** App.tsx 使用 `<Route element={<ProtectedRoute />}>` 包裹所有受保护页面，`AppShell` 使用 `<Outlet />` 替换 `{children}`，通过 `useLocation()` 驱动菜单高亮和页面标题。

**Tech Stack:** React Router v6（Layout Route、Outlet、useNavigate、useLocation）、Ant Design 5 Layout

---

## File Structure

| 文件 | 责任 |
|------|------|
| `apps/web/src/app/App.tsx` | 删除 `activePage` state 和 `content` 变量，改为嵌套 Route 结构 |
| `apps/web/src/app/AppShell.tsx` | 用 `<Outlet />` 替换 children，用 `useNavigate()/useLocation()` 替换 props |
| `apps/web/src/styles.css` | 更新 Header 样式、移除重复规则 |

---

## Task 1: App.tsx 路由化改造

**Files:**
- Modify: `apps/web/src/app/App.tsx`

- [ ] **Step 1.1: 重写 App.tsx 的路由结构**

删除以下内容：
- `useState` 中的 `activePage` 和 `setActivePage`
- 整个 `content` 变量（约 30 行 if/else 链）
- `handlePreferenceChange` 中的 `setActivePage("dashboard")` 调用

新增 ProtectedRoute 内联组件和嵌套 Route：

```typescript
// apps/web/src/app/App.tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ConfigProvider, theme } from "antd";
import zhCN from "antd/locale/zh_CN";
import enUS from "antd/locale/en_US";
import { useMemo, useState } from "react";
import { BrowserRouter, Navigate, Outlet, Route, Routes, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { AppShell } from "./AppShell";
import { LoginPage } from "../modules/auth/LoginPage";
import { DashboardPage } from "../modules/dashboard/DashboardPage";
import { SourcesPage } from "../modules/sources/SourcesPage";
import { FetchLogsPage } from "../modules/sources/FetchLogsPage";
import { UsersPage } from "../modules/admin/UsersPage";
import { GroupsPage } from "../modules/admin/GroupsPage";
import { TemplatesPage } from "../modules/admin/TemplatesPage";
import { AuditLogsPage } from "../modules/admin/AuditLogsPage";
import DataMgmtPage from "../modules/admin/DataMgmtPage";
import { AgentPage } from "../modules/agent/AgentPage";
import { AgentTokensPage } from "../modules/agent_tokens/AgentTokensPage";
import { SettingsPage } from "../modules/settings/SettingsPage";
import { AuthSession } from "../shared/api/auth";
import { UserPreference } from "../shared/api/preferences";

const queryClient = new QueryClient();

function ProtectedRoute({ session }: { session: AuthSession | null }) {
  if (!session) return <Navigate to="/login" replace />;
  return <Outlet />;
}

function NotFound() {
  return <div style={{ padding: 48, textAlign: "center" }}>404 — Page Not Found</div>;
}

export function App() {
  const { i18n } = useTranslation();
  const navigate = useNavigate();
  const [session, setSession] = useState<AuthSession | null>(() => {
    const token = localStorage.getItem("access_token");
    return token ? { accessToken: token } : null;
  });
  const [isDarkMode, setIsDarkMode] = useState(() => {
    const savedTheme = localStorage.getItem("theme");
    if (savedTheme === "dark") return true;
    if (savedTheme === "system") {
      return window.matchMedia("(prefers-color-scheme: dark)").matches;
    }
    return false;
  });
  const [antdLocale, setAntdLocale] = useState(i18n.language === "en-US" ? enUS : zhCN);

  const themeConfig = useMemo(
    () => ({
      algorithm: isDarkMode ? theme.darkAlgorithm : theme.defaultAlgorithm,
      token: {
        borderRadius: 6,
        colorPrimary: "#1677ff",
      },
    }),
    [isDarkMode]
  );

  function handleLogin(nextSession: AuthSession) {
    localStorage.setItem("access_token", nextSession.accessToken);
    setSession(nextSession);
    navigate("/feed");
  }

  function handleLogout() {
    localStorage.removeItem("access_token");
    setSession(null);
  }

  function handlePreferenceChange(pref: UserPreference) {
    if (pref.theme === "dark") {
      setIsDarkMode(true);
      localStorage.setItem("theme", "dark");
    } else if (pref.theme === "light") {
      setIsDarkMode(false);
      localStorage.setItem("theme", "light");
    } else {
      const isDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
      setIsDarkMode(isDark);
      localStorage.setItem("theme", "system");
    }
    setAntdLocale(pref.language === "en-US" ? enUS : zhCN);
  }

  const isAdmin = !!session;

  return (
    <QueryClientProvider client={queryClient}>
      <ConfigProvider locale={antdLocale} theme={themeConfig}>
        <Routes>
          <Route
            path="/login"
            element={
              session ? <Navigate to="/feed" replace /> : <LoginPage onLogin={handleLogin} />
            }
          />
          <Route element={<ProtectedRoute session={session} />}>
            <Route element={<AppShell session={session} isDarkMode={isDarkMode} isAdmin={isAdmin} onThemeChange={setIsDarkMode} onLogout={handleLogout} />}>
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
      </ConfigProvider>
    </QueryClientProvider>
  );
}
```

注意：`BrowserRouter` 需要移到 `main.tsx` 中（因为 `App` 组件内部现在调用了 `useNavigate` 和 `useRoutes`，它们必须在 Router 的上下文中）。修改 `main.tsx`：

```typescript
// apps/web/src/main.tsx
import { BrowserRouter } from "react-router-dom";
// ...
root.render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>
);
```

- [ ] **Step 1.2: 运行前端类型检查**

Run:
```bash
cd apps/web && npx tsc -b --noEmit
```

Expected: 无类型错误。

- [ ] **Step 1.3: Commit**

```bash
git add apps/web/src/main.tsx apps/web/src/app/App.tsx
git commit -m "refactor(routing): replace activePage with nested routes"
```

---

## Task 2: AppShell 重构

**Files:**
- Modify: `apps/web/src/app/AppShell.tsx`

- [ ] **Step 2.1: 重写 AppShell**

```typescript
// apps/web/src/app/AppShell.tsx
import {
  ApiOutlined,
  AuditOutlined,
  DashboardOutlined,
  DatabaseOutlined,
  FileTextOutlined,
  KeyOutlined,
  LogoutOutlined,
  MoonOutlined,
  RobotOutlined,
  SafetyOutlined,
  SettingOutlined,
  SunOutlined,
  TeamOutlined,
  UserOutlined,
} from "@ant-design/icons";
import { Button, Layout, Menu, Space, Switch, Typography, theme } from "antd";
import { Outlet, useLocation, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { AppLogo } from "../shared/components/AppLogo";
import { AuthSession } from "../shared/api/auth";

const { Header, Sider, Content } = Layout;

type AppShellProps = {
  session: AuthSession;
  isDarkMode: boolean;
  isAdmin: boolean;
  onThemeChange: (value: boolean) => void;
  onLogout: () => void;
};

const routeMeta: Record<string, { i18nKey: string }> = {
  "/feed":             { i18nKey: "feed.title" },
  "/sources":          { i18nKey: "sources.title" },
  "/fetch-logs":       { i18nKey: "taskLogs.title" },
  "/agent":            { i18nKey: "agent.title" },
  "/agent-tokens":     { i18nKey: "agent.title" },
  "/settings":         { i18nKey: "settings.title" },
  "/admin/users":      { i18nKey: "admin.users.title" },
  "/admin/groups":     { i18nKey: "admin.groups.title" },
  "/admin/templates":  { i18nKey: "admin.templates.title" },
  "/admin/audit":      { i18nKey: "admin.audit.title" },
  "/admin/data-mgmt":  { i18nKey: "admin.groups.title" },
};

const pathToMenuKey: Record<string, string> = {
  "/feed": "dashboard",
  "/sources": "sources",
  "/fetch-logs": "fetch-logs",
  "/agent": "agent",
  "/agent-tokens": "agent-tokens",
  "/settings": "settings",
  "/admin/users": "admin-users",
  "/admin/groups": "admin-groups",
  "/admin/templates": "admin-templates",
  "/admin/audit": "admin-audit",
  "/admin/data-mgmt": "data-mgmt",
};

export function AppShell({
  session,
  isDarkMode,
  isAdmin,
  onThemeChange,
  onLogout,
}: AppShellProps) {
  const { t } = useTranslation();
  const location = useLocation();
  const navigate = useNavigate();
  const { token } = theme.useToken();
  const siderTheme = isDarkMode ? "dark" : "light";

  const currentPath = location.pathname;
  const currentMeta = Object.entries(routeMeta).find(([path]) =>
    currentPath.startsWith(path)
  );
  const pageTitle = currentMeta ? t(currentMeta[1].i18nKey) : t("common.appName");
  const selectedKey = pathToMenuKey[currentPath] || "dashboard";

  const menuItems = [
    { key: "dashboard", icon: <DashboardOutlined />, label: t("nav.feed") },
    { key: "sources", icon: <ApiOutlined />, label: t("nav.sources") },
    { key: "fetch-logs", icon: <FileTextOutlined />, label: t("nav.taskLogs") },
    { key: "agent", icon: <RobotOutlined />, label: t("nav.aiAgent") },
    { key: "agent-tokens", icon: <KeyOutlined />, label: "Agent Token" },
    { key: "settings", icon: <SettingOutlined />, label: t("nav.settings") },
    ...(isAdmin
      ? [
          { type: "divider" as const },
          { key: "admin-users", icon: <UserOutlined />, label: t("nav.userManagement") },
          { key: "admin-groups", icon: <TeamOutlined />, label: t("nav.groupManagement") },
          { key: "admin-templates", icon: <SafetyOutlined />, label: t("nav.publicTemplates") },
          { key: "admin-audit", icon: <AuditOutlined />, label: t("nav.auditLogs") },
          { key: "data-mgmt", icon: <DatabaseOutlined />, label: t("settings.title") },
        ]
      : []),
  ];

  const menuKeyToPath: Record<string, string> = {
    "dashboard": "/feed",
    "sources": "/sources",
    "fetch-logs": "/fetch-logs",
    "agent": "/agent",
    "agent-tokens": "/agent-tokens",
    "settings": "/settings",
    "admin-users": "/admin/users",
    "admin-groups": "/admin/groups",
    "admin-templates": "/admin/templates",
    "admin-audit": "/admin/audit",
    "data-mgmt": "/admin/data-mgmt",
  };

  return (
    <Layout className="app-shell">
      <Sider
        width={232}
        breakpoint="lg"
        collapsedWidth={72}
        theme={siderTheme}
        style={{
          background: token.colorBgContainer,
          borderInlineEnd: `1px solid ${token.colorBorderSecondary}`,
        }}
      >
        <div className="brand">
          <AppLogo />
          <Typography.Text strong className="brand-text">
            {t("common.appName")}
          </Typography.Text>
        </div>
        <Menu
          theme={siderTheme}
          mode="inline"
          selectedKeys={[selectedKey]}
          onClick={({ key }) => {
            const path = menuKeyToPath[key];
            if (path) navigate(path);
          }}
          items={menuItems}
        />
      </Sider>
      <Layout>
        <Header className="app-header">
          <Typography.Title level={4} className="page-title" style={{ margin: 0 }}>
            {pageTitle}
          </Typography.Title>
          <Space>
            <Switch
              checked={isDarkMode}
              checkedChildren={<MoonOutlined />}
              unCheckedChildren={<SunOutlined />}
              onChange={onThemeChange}
              aria-label={t("settings.theme")}
            />
            <Button icon={<LogoutOutlined />} onClick={onLogout}>
              {t("common.logout")}
            </Button>
          </Space>
        </Header>
        <Content className="app-content">
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
}
```

- [ ] **Step 2.2: 运行前端类型检查**

Run:
```bash
cd apps/web && npx tsc -b --noEmit
```

Expected: 无类型错误。

- [ ] **Step 2.3: Commit**

```bash
git add apps/web/src/app/AppShell.tsx
git commit -m "refactor(appshell): replace children with Outlet, use useNavigate/useLocation"
```

---

## Task 3: CSS 打磨

**Files:**
- Modify: `apps/web/src/styles.css`

- [ ] **Step 3.1: 更新 Header 样式，移除重复规则**

当前 `styles.css` 中有两套 `.app-header` / `.app-main` 规则（line 85-103 和 line 114-135）。保留后一套（带分隔线的），删除前一套。同时给 Header 加白色背景。

```css
/* apps/web/src/styles.css */

/* 删除 lines 85-103 的 .app-header 和 .app-main */
/* 保留 lines 114-135 的版本，更新如下： */

.app-header {
  display: flex;
  gap: 16px;
  align-items: center;
  justify-content: space-between;
  height: 64px;
  padding: 0 24px;
  background: var(--color-bg-container, #fff);
  border-bottom: 1px solid var(--color-border-subtle);
}

.app-header .page-title {
  margin: 0 !important;
  font-weight: 600;
}

.app-main {
  padding: 24px;
  overflow-y: auto;
}
```

同时更新 `.app-content` 样式（添加 max-width 限制）：

```css
/* 如果不存在，添加到 styles.css */
/* 如果已存在，更新 */
.app-content {
  padding: 24px;
  overflow-y: auto;
  max-width: 1400px;
  width: 100%;
}
```

- [ ] **Step 3.2: 运行前端类型检查**

Run:
```bash
cd apps/web && npx tsc -b --noEmit
```

Expected: 无类型错误。

- [ ] **Step 3.3: Commit**

```bash
git add apps/web/src/styles.css
git commit -m "style(layout): polish app-header, remove duplicate CSS rules"
```

---

## Task 4: 验证

- [ ] **Step 4.1: 确认无回归**

手动验证：
1. 启动后端 + 前端
2. 访问 `http://localhost:5173/login` — 登录页正常工作
3. 登录后自动跳转到 `/feed` — DashboardPage 显示
4. 点击侧栏各个菜单 — URL 变化、页面正确切换
5. 浏览器前进/后退 — 页面正确切换
6. 直接访问 `/sources`、`/settings`、`/admin/users` — 正确渲染
7. 无 session 时直接访问受保护路径 → 重定向到 `/login`
8. 已登录时访问 `/login` → 重定向到 `/feed`
9. 访问不存在的路径 → 404 显示

