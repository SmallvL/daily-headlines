import { AuthSession } from "./auth";
import { apiRequest } from "./client";

// ── Types ──

export type Language = "zh-CN" | "en-US";
export type Theme = "light" | "dark" | "system";
export type DefaultView = "list" | "grid" | "compact";

export type UserPreference = {
  user_id: string;
  language: Language;
  theme: Theme;
  default_view: DefaultView;
  login_background_url: string | null;
  updated_at: string | null;
};

export type UserPreferenceUpdate = {
  language?: Language;
  theme?: Theme;
  default_view?: DefaultView;
  login_background_url?: string | null;
};

// ── API ──

export async function getPreference(
  session: AuthSession,
): Promise<UserPreference> {
  return apiRequest<UserPreference>("/api/preferences", {
    token: session.accessToken,
  });
}

export async function updatePreference(
  session: AuthSession,
  data: UserPreferenceUpdate,
): Promise<UserPreference> {
  return apiRequest<UserPreference>("/api/preferences", {
    method: "PATCH",
    token: session.accessToken,
    body: JSON.stringify(data),
  });
}

export async function getLoginBackground(): Promise<string | null> {
  return apiRequest<string | null>("/api/preferences/login-background");
}
