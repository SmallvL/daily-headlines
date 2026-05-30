import { AuthSession } from "../../shared/api/auth";
import { apiRequest } from "../../shared/api/client";

export type AuthMethod = "none" | "cookie" | "token" | "qrcode" | "oauth" | "custom";

export interface SourcePlugin {
  id: string;
  name: string;
  description: string;
  icon_url: string | null;
  auth_methods: AuthMethod[];
  source_type: string;
}

export interface PluginDetail extends SourcePlugin {
  auth_schema: Record<string, unknown>;
  subscription_types: Array<{
    id: string;
    name: string;
    description: string;
  }>;
}

export interface AuthInitResult {
  success: boolean;
  auth_method: string;
  qrcode_image?: string;  // Base64 data URL
  qrcode_url?: string;
  session_id?: string;
  expires_in?: number;
  has_credentials?: boolean;
}

export interface QRCodeStatus {
  status: "pending" | "scanned" | "confirmed" | "expired" | "cancelled";
  success: boolean;
  error?: string;
  user_info?: {
    username: string;
    avatar: string;
    uid: string;
    [key: string]: string;
  };
  credentials?: Record<string, unknown>;
  has_credentials?: boolean;
}

export interface ValidateResult {
  valid: boolean;
  user_info: {
    username: string;
    avatar: string;
    uid: string;
    [key: string]: string;
  } | null;
}

export interface PluginFeedResult {
  items: Array<{
    title: string;
    url: string;
    summary: string | null;
    content: string | null;
    image_url: string | null;
    author: string | null;
    published_at: string | null;
    source_id: string | null;
    tags: string[];
    extra: Record<string, unknown>;
  }>;
  has_more: boolean;
  next_cursor: string | null;
  total_count: number;
}

export const pluginsApi = {
  /** List all available plugins */
  list(session: AuthSession): Promise<SourcePlugin[]> {
    return apiRequest<SourcePlugin[]>("/api/plugins", { token: session.accessToken });
  },

  /** Get plugin details */
  get(session: AuthSession, pluginId: string): Promise<PluginDetail> {
    return apiRequest<PluginDetail>(`/api/plugins/${pluginId}`, { token: session.accessToken });
  },

  /** Initialize authentication (returns QR code image for qrcode method) */
  initAuth(
    session: AuthSession,
    pluginId: string,
    method: string,
    credentials?: Record<string, unknown>
  ): Promise<AuthInitResult> {
    const params = new URLSearchParams({ method });
    return apiRequest<AuthInitResult>(`/api/plugins/${pluginId}/auth/init?${params}`, {
      method: "POST",
      token: session.accessToken,
      body: JSON.stringify(credentials ?? {}),
    });
  },

  /** Poll QR code scan status */
  checkQRCodeStatus(session: AuthSession, pluginId: string, sessionId: string): Promise<QRCodeStatus> {
    const params = new URLSearchParams({ session_id: sessionId });
    return apiRequest<QRCodeStatus>(`/api/plugins/${pluginId}/auth/qrcode/status?${params}`, {
      token: session.accessToken,
    });
  },

  /** Validate credentials */
  validate(
    session: AuthSession,
    pluginId: string,
    credentials: Record<string, unknown>
  ): Promise<ValidateResult> {
    return apiRequest<ValidateResult>(`/api/plugins/${pluginId}/auth/validate`, {
      method: "POST",
      token: session.accessToken,
      body: JSON.stringify(credentials),
    });
  },

  /** Fetch feed preview */
  fetchFeed(
    session: AuthSession,
    pluginId: string,
    credentials: Record<string, unknown>,
    config?: Record<string, unknown>,
    cursor?: string,
    limit?: number
  ): Promise<PluginFeedResult> {
    return apiRequest<PluginFeedResult>(`/api/plugins/${pluginId}/fetch`, {
      method: "POST",
      token: session.accessToken,
      body: JSON.stringify({ credentials, config, cursor, limit }),
    });
  },
};
