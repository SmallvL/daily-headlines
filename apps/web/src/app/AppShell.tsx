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

const pathToKey: Record<string, string> = {
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

const keyToPath: Record<string, string> = {
  dashboard: "/feed",
  sources: "/sources",
  "fetch-logs": "/fetch-logs",
  agent: "/agent",
  "agent-tokens": "/agent-tokens",
  settings: "/settings",
  "admin-users": "/admin/users",
  "admin-groups": "/admin/groups",
  "admin-templates": "/admin/templates",
  "admin-audit": "/admin/audit",
  "data-mgmt": "/admin/data-mgmt",
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
  "/admin/data-mgmt":  { i18nKey: "admin.dataMgmt.title" },
};

type AppShellProps = {
  session: AuthSession | null;
  isDarkMode: boolean;
  isAdmin: boolean;
  onThemeChange: (value: boolean) => void;
  onLogout: () => void;
};

export function AppShell({
  isDarkMode,
  isAdmin,
  onThemeChange,
  onLogout,
}: AppShellProps) {
  const { t } = useTranslation();
  const { token } = theme.useToken();
  const navigate = useNavigate();
  const location = useLocation();
  const siderTheme = isDarkMode ? "dark" : "light";

  const selectedKey = pathToKey[location.pathname] || "dashboard";

  const currentPath = location.pathname;
  const currentMeta = Object.entries(routeMeta).find(([path]) =>
    currentPath.startsWith(path)
  );
  const pageTitle = currentMeta ? t(currentMeta[1].i18nKey) : t("common.appName");

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
          { key: "data-mgmt", icon: <DatabaseOutlined />, label: "数据管理" },
        ]
      : []),
  ];

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
            const path = keyToPath[key];
            if (path) navigate(path);
          }}
          items={menuItems}
        />
      </Sider>
      <Layout>
        <Header className="app-header">
          <Typography.Title level={4} style={{ margin: 0 }}>
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
