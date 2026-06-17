import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ConfigProvider, theme } from "antd";
import zhCN from "antd/locale/zh_CN";
import enUS from "antd/locale/en_US";
import { useEffect, useMemo, useState } from "react";
import { Navigate, Outlet, Route, Routes, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { getPreference } from "../shared/api/preferences";
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
import { ErrorBoundary } from "../shared/components/ErrorBoundary";
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
    const isDark = savedTheme === "dark" || (savedTheme === "system" && window.matchMedia("(prefers-color-scheme: dark)").matches);
    document.documentElement.setAttribute("data-theme", isDark ? "dark" : "light");
    return isDark;
  });
  const [antdLocale, setAntdLocale] = useState(i18n.language === "en-US" ? enUS : zhCN);

  useEffect(() => {
    document.documentElement.lang = i18n.language;
  }, [i18n.language]);

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

  // Fetch user preferences after login to apply theme/language
  useEffect(() => {
    if (!session) return;
    getPreference(session).then((pref) => {
      if (pref.theme === "dark") {
        setIsDarkMode(true);
        document.documentElement.setAttribute("data-theme", "dark");
      } else if (pref.theme === "light") {
        setIsDarkMode(false);
        document.documentElement.setAttribute("data-theme", "light");
      } else {
        const isDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
        setIsDarkMode(isDark);
        document.documentElement.setAttribute("data-theme", isDark ? "dark" : "light");
      }
      setAntdLocale(pref.language === "en-US" ? enUS : zhCN);
    }).catch(() => {});
  }, [session]);

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
    // Update theme
    if (pref.theme === "dark") {
      setIsDarkMode(true);
      localStorage.setItem("theme", "dark");
      document.documentElement.setAttribute("data-theme", "dark");
    } else if (pref.theme === "light") {
      setIsDarkMode(false);
      localStorage.setItem("theme", "light");
      document.documentElement.setAttribute("data-theme", "light");
    } else {
      const isDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
      setIsDarkMode(isDark);
      localStorage.setItem("theme", "system");
      document.documentElement.setAttribute("data-theme", isDark ? "dark" : "light");
    }
    // Update locale
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
              <Route path="/feed" element={<ErrorBoundary><DashboardPage session={session!} onCreateSource={() => navigate("/sources")} /></ErrorBoundary>} />
              <Route path="/sources" element={<ErrorBoundary><SourcesPage session={session!} /></ErrorBoundary>} />
              <Route path="/fetch-logs" element={<ErrorBoundary><FetchLogsPage session={session!} /></ErrorBoundary>} />
              <Route path="/agent" element={<ErrorBoundary><AgentPage session={session!} onCreateSource={() => navigate("/sources")} /></ErrorBoundary>} />
              <Route path="/agent-tokens" element={<ErrorBoundary><AgentTokensPage session={session!} /></ErrorBoundary>} />
              <Route path="/settings" element={<ErrorBoundary><SettingsPage session={session!} onPreferenceChange={handlePreferenceChange} /></ErrorBoundary>} />
              <Route path="/admin/users" element={<ErrorBoundary><UsersPage session={session!} /></ErrorBoundary>} />
              <Route path="/admin/groups" element={<ErrorBoundary><GroupsPage session={session!} /></ErrorBoundary>} />
              <Route path="/admin/templates" element={<ErrorBoundary><TemplatesPage session={session!} /></ErrorBoundary>} />
              <Route path="/admin/audit" element={<ErrorBoundary><AuditLogsPage session={session!} /></ErrorBoundary>} />
              <Route path="/admin/data-mgmt" element={<ErrorBoundary><DataMgmtPage session={session!} /></ErrorBoundary>} />
              <Route index element={<Navigate to="/feed" replace />} />
              <Route path="*" element={<ErrorBoundary><NotFound /></ErrorBoundary>} />
            </Route>
          </Route>
        </Routes>
      </ConfigProvider>
    </QueryClientProvider>
  );
}
