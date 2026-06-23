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
import { Button, Layout, Menu, Space, Tooltip, Typography, theme } from "antd";
import type { MenuProps } from "antd";
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

  const handleMenuClick: MenuProps["onClick"] = ({ key }) => {
    const path = keyToPath[key];
    if (path) navigate(path);
  };

  const menuItems: MenuProps["items"] = [
    {
      type: "group",
      label: <Typography.Text type="secondary" style={{ fontSize: 12 }}>{t("nav.groupMain")}</Typography.Text>,
      children: [
        { key: "dashboard", icon: <DashboardOutlined />, label: t("nav.feed") },
      ],
    },
    {
      type: "group",
      label: <Typography.Text type="secondary" style={{ fontSize: 12 }}>{t("nav.groupSources")}</Typography.Text>,
      children: [
        { key: "sources", icon: <ApiOutlined />, label: t("nav.sources") },
        { key: "fetch-logs", icon: <FileTextOutlined />, label: t("nav.taskLogs") },
      ],
    },
    {
      type: "group",
      label: <Typography.Text type="secondary" style={{ fontSize: 12 }}>{t("nav.groupAi")}</Typography.Text>,
      children: [
        { key: "agent", icon: <RobotOutlined />, label: t("nav.aiAgent") },
        { key: "agent-tokens", icon: <KeyOutlined />, label: t("nav.agentTokens") },
      ],
    },
    {
      type: "group",
      label: <Typography.Text type="secondary" style={{ fontSize: 12 }}>{t("nav.groupSettings")}</Typography.Text>,
      children: [
        { key: "settings", icon: <SettingOutlined />, label: t("nav.settings") },
      ],
    },
    ...(isAdmin
      ? [
          {
            type: "group" as const,
            label: <Typography.Text type="secondary" style={{ fontSize: 12 }}>{t("nav.groupAdmin")}</Typography.Text>,
            children: [
              { key: "admin-users", icon: <UserOutlined />, label: t("nav.userManagement") },
              { key: "admin-groups", icon: <TeamOutlined />, label: t("nav.groupManagement") },
              { key: "admin-templates", icon: <SafetyOutlined />, label: t("nav.publicTemplates") },
              { key: "admin-audit", icon: <AuditOutlined />, label: t("nav.auditLogs") },
              { key: "data-mgmt", icon: <DatabaseOutlined />, label: t("nav.dataManagement") },
            ],
          },
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
        className={`app-sider ${isDarkMode ? "app-sider-dark" : ""}`}
        style={{
          background: isDarkMode ? "#0d1117" : token.colorBgContainer,
          borderInlineEnd: `1px solid ${isDarkMode ? "#1f2937" : token.colorBorderSecondary}`,
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
          onClick={handleMenuClick}
          items={menuItems}
          style={{ padding: "0 8px" }}
        />
      </Sider>
      <Layout>
        <Header className="app-header">
          <Typography.Title level={4} style={{ margin: 0 }}>
            {pageTitle}
          </Typography.Title>
          <Space>
            <Tooltip title={isDarkMode ? "切换到浅色模式" : "切换到深色模式"}>
              <Button
                type="text"
                shape="circle"
                size="large"
                icon={
                  isDarkMode
                    ? <SunOutlined style={{ fontSize: 18, color: "#fbbf24" }} />
                    : <MoonOutlined style={{ fontSize: 18, color: "#6366f1" }} />
                }
                onClick={() => onThemeChange(!isDarkMode)}
                aria-label={t("settings.theme")}
                className="theme-toggle-btn"
              />
            </Tooltip>
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
