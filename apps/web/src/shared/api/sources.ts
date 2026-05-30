import { AuthSession } from "./auth";
import { apiRequest } from "./client";
import { FeedItem } from "./feed";

export type AuthType = "none" | "cookie" | "bearer" | "api_key" | "custom_headers" | "qrcode" | "plugin";

export type AuthConfig = {
  auth_type: AuthType;
  cookies?: string | null;
  token?: string | null;
  header_name?: string | null;
  api_key?: string | null;
  headers?: Record<string, string> | null;
  plugin_id?: string | null;
  plugin_credentials?: Record<string, any> | null;
  plugin_config?: Record<string, any> | null;
  // Masked fields from server
  has_cookies?: boolean;
  has_token?: boolean;
  has_api_key?: boolean;
};

export type Source = {
  id: string;
  name: string;
  type: string;
  endpoint: string;
  status: string;
  last_fetch_at: string | null;
  schedule_enabled: boolean;
  schedule_mode: "interval" | "cron";
  schedule_interval_minutes: number | null;
  cron_expression: string | null;
  cron_days_of_week: string | null;
  cron_hour: number | null;
  cron_minute: number | null;
  next_fetch_at: string | null;
  created_at: string | null;
  auth_type: AuthType;
  has_auth: boolean;
  plugin_id?: string | null;
  plugin_name?: string | null;
  plugin_user_info?: Record<string, string> | null;
};

export type SourcePayload = {
  name: string;
  type: "rss" | "api" | "web";
  endpoint: string;
  config?: {
    title_path?: string;
    items_path?: string;
    mappings?: Record<string, string>;
    // Web crawler fields
    selector_type?: "css" | "xpath";
    item_selector?: string;
    title_selector?: string;
    url_selector?: string;
    summary_selector?: string;
    image_selector?: string;
    author_selector?: string;
    date_selector?: string;
    allowed_domains?: string[];
  };
  auth?: AuthConfig;
  schedule_enabled?: boolean;
  schedule_mode?: "interval" | "cron";
  schedule_interval_minutes?: number | null;
  cron_expression?: string | null;
  cron_days_of_week?: string | null;
  cron_hour?: number | null;
  cron_minute?: number | null;
};

export type SourceTestResult = {
  title: string | null;
  items: FeedItem[];
};

export type FetchResult = {
  log_id: string;
  inserted: number;
  skipped: number;
  items: FeedItem[];
};

export type SourceFetchLog = {
  id: string;
  source_id: string;
  trigger: string;
  status: string;
  inserted_count: number;
  skipped_count: number;
  error_message: string | null;
  attempt: number;
  max_attempts: number;
  next_retry_at: string | null;
  started_at: string;
  finished_at: string | null;
};

export type FetchLogPage = {
  items: SourceFetchLog[];
  total: number;
  page: number;
  page_size: number;
};

export type SourceTemplate = {
  name: string;
  type: "rss" | "api" | "web";
  endpoint: string;
  config?: Record<string, unknown>;
  auth_type?: AuthType;
  schedule_enabled?: boolean;
  schedule_mode?: "interval" | "cron";
  schedule_interval_minutes?: number | null;
  cron_expression?: string | null;
  cron_days_of_week?: string | null;
  cron_hour?: number | null;
  cron_minute?: number | null;
};

export function listSources(session: AuthSession): Promise<Source[]> {
  return apiRequest<Source[]>("/api/sources", { token: session.accessToken });
}

export function createSource(session: AuthSession, payload: SourcePayload): Promise<Source> {
  return apiRequest<Source>("/api/sources", {
    method: "POST",
    token: session.accessToken,
    body: JSON.stringify(payload)
  });
}

export function testSource(session: AuthSession, payload: SourcePayload): Promise<SourceTestResult> {
  return apiRequest<SourceTestResult>("/api/sources/test", {
    method: "POST",
    token: session.accessToken,
    body: JSON.stringify(payload)
  });
}

export function fetchSourceNow(session: AuthSession, sourceId: string): Promise<FetchResult> {
  return apiRequest<FetchResult>(`/api/sources/${sourceId}/fetch-now`, {
    method: "POST",
    token: session.accessToken
  });
}

export function deleteSource(session: AuthSession, sourceId: string): Promise<void> {
  return apiRequest<void>(`/api/sources/${sourceId}`, {
    method: "DELETE",
    token: session.accessToken
  });
}

export function updateSource(
  session: AuthSession,
  sourceId: string,
  data: Partial<Pick<SourcePayload, "name" | "type" | "endpoint" | "config" | "auth">>
): Promise<Source> {
  return apiRequest<Source>(`/api/sources/${sourceId}`, {
    method: "PATCH",
    token: session.accessToken,
    body: JSON.stringify(data)
  });
}

export function updateSourceSchedule(
  session: AuthSession,
  sourceId: string,
  data: {
    schedule_enabled: boolean;
    schedule_mode: "interval" | "cron";
    schedule_interval_minutes: number | null;
    cron_expression: string | null;
    cron_days_of_week: string | null;
    cron_hour: number | null;
    cron_minute: number | null;
  }
): Promise<Source> {
  return apiRequest<Source>(`/api/sources/${sourceId}/schedule`, {
    method: "PATCH",
    token: session.accessToken,
    body: JSON.stringify(data)
  });
}

export function listSourceFetchLogs(
  session: AuthSession,
  sourceId: string
): Promise<SourceFetchLog[]> {
  return apiRequest<SourceFetchLog[]>(`/api/sources/${sourceId}/fetch-logs`, {
    token: session.accessToken
  });
}

export function listAllFetchLogs(
  session: AuthSession,
  params: {
    source_id?: string;
    status?: string;
    trigger?: string;
    page?: number;
    page_size?: number;
  } = {}
): Promise<FetchLogPage> {
  const searchParams = new URLSearchParams();
  if (params.source_id) searchParams.set("source_id", params.source_id);
  if (params.status) searchParams.set("status", params.status);
  if (params.trigger) searchParams.set("trigger", params.trigger);
  if (params.page) searchParams.set("page", String(params.page));
  if (params.page_size) searchParams.set("page_size", String(params.page_size));
  const qs = searchParams.toString();
  return apiRequest<FetchLogPage>(`/api/sources/fetch-logs${qs ? `?${qs}` : ""}`, {
    token: session.accessToken
  });
}

export function exportSourceTemplate(session: AuthSession, sourceId: string): Promise<SourceTemplate> {
  return apiRequest<SourceTemplate>(`/api/sources/${sourceId}/export-template`, {
    token: session.accessToken
  });
}

export function importSourceTemplate(session: AuthSession, template: SourceTemplate): Promise<Source> {
  return apiRequest<Source>("/api/sources/import-template", {
    method: "POST",
    token: session.accessToken,
    body: JSON.stringify(template)
  });
}
