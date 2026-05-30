import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ConfigProvider, theme } from "antd";
import zhCN from "antd/locale/zh_CN";
import enUS from "antd/locale/en_US";
import { useMemo, useState } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
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

export function App() {
  const { i18n } = useTranslation();
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
  const [activePage, setActivePage] = useState("dashboard");
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
  }

  function handleLogout() {
    localStorage.removeItem("access_token");
    setSession(null);
    setActivePage("dashboard");
  }

  function handlePreferenceChange(pref: UserPreference) {
    // Update theme
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
    // Update locale
    setAntdLocale(pref.language === "en-US" ? enUS : zhCN);
  }

  // Dev admin always has admin role; real RBAC can be added later
  const isAdmin = !!session;

  const content =
    activePage === "sources" && session ? (
      <SourcesPage session={session} />
    ) : activePage === "fetch-logs" && session ? (
      <FetchLogsPage session={session} />
    ) : activePage === "admin-users" && session ? (
      <UsersPage session={session} />
    ) : activePage === "admin-groups" && session ? (
      <GroupsPage session={session} />
    ) : activePage === "admin-templates" && session ? (
      <TemplatesPage session={session} />
    ) : activePage === "admin-audit" && session ? (
      <AuditLogsPage session={session} />
    ) : activePage === "data-mgmt" && session ? (
      <DataMgmtPage session={session} />
    ) : activePage === "agent" && session ? (
      <AgentPage session={session} onCreateSource={() => setActivePage("sources")} />
    ) : activePage === "agent-tokens" && session ? (
      <AgentTokensPage session={session} />
    ) : activePage === "settings" && session ? (
      <SettingsPage session={session} onPreferenceChange={handlePreferenceChange} />
    ) : session ? (
      <DashboardPage
        session={session}
        onCreateSource={() => setActivePage("sources")}
      />
    ) : null;

  return (
    <QueryClientProvider client={queryClient}>
      <ConfigProvider locale={antdLocale} theme={themeConfig}>
        <BrowserRouter>
          <Routes>
            <Route
              path="/login"
              element={
                session ? (
                  <Navigate to="/" replace />
                ) : (
                  <LoginPage onLogin={handleLogin} />
                )
              }
            />
            <Route
              path="/*"
              element={
                session ? (
                  <AppShell
                    activePage={activePage}
                    isDarkMode={isDarkMode}
                    isAdmin={isAdmin}
                    onPageChange={setActivePage}
                    onThemeChange={setIsDarkMode}
                    onLogout={handleLogout}
                  >
                    {content}
                  </AppShell>
                ) : (
                  <Navigate to="/login" replace />
                )
              }
            />
          </Routes>
        </BrowserRouter>
      </ConfigProvider>
    </QueryClientProvider>
  );
}
