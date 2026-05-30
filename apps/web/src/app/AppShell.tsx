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
import { ReactNode } from "react";
import { useTranslation } from "react-i18next";

import { AppLogo } from "../shared/components/AppLogo";

const { Header, Sider, Content } = Layout;

type AppShellProps = {
  children: ReactNode;
  activePage: string;
  isDarkMode: boolean;
  isAdmin: boolean;
  onPageChange: (page: string) => void;
  onThemeChange: (value: boolean) => void;
  onLogout: () => void;
};

export function AppShell({
  children,
  activePage,
  isDarkMode,
  isAdmin,
  onPageChange,
  onThemeChange,
  onLogout,
}: AppShellProps) {
  const { t } = useTranslation();
  const { token } = theme.useToken();
  const siderTheme = isDarkMode ? "dark" : "light";

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
          selectedKeys={[activePage]}
          onClick={({ key }) => onPageChange(key)}
          items={menuItems}
        />
      </Sider>
      <Layout>
        <Header className="app-header">
          <Typography.Title level={4} className="page-title">
            {t("feed.title")}
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
        <Content className="app-content">{children}</Content>
      </Layout>
    </Layout>
  );
}
