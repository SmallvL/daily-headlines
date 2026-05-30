import { AuthSession } from "../../shared/api/auth";
import { apiRequest } from "../../shared/api/client";

export type TableStats = {
  table_name: string;
  record_count: number;
  estimated_size_kb: number;
  oldest_record: string | null;
  newest_record: string | null;
};

export type StorageStats = {
  db_path: string;
  db_size_mb: number;
  tables: TableStats[];
  total_records: number;
};

export type RetentionConfig = {
  id: number;
  table_name: string;
  max_age_days: number | null;
  max_records: number | null;
  keep_saved: boolean;
  enabled: boolean;
  last_purge_at: string | null;
  last_purge_count: number | null;
};

export type PurgePreview = {
  table_name: string;
  records_to_delete: number;
  oldest_to_keep: string | null;
  criteria: string;
};

export type PurgeResult = {
  table_name: string;
  deleted_count: number;
  duration_ms: number;
};

export type PurgeAllResult = {
  results: PurgeResult[];
  total_deleted: number;
  db_size_before_mb: number;
  db_size_after_mb: number;
  vacuum_performed: boolean;
};

export type MaintenanceResult = {
  action: string;
  success: boolean;
  details: Record<string, unknown>;
};

export async function getStorageStats(session: AuthSession): Promise<StorageStats> {
  return apiRequest("/api/data-mgmt/stats", { token: session.accessToken });
}

export async function listRetentionConfigs(session: AuthSession): Promise<RetentionConfig[]> {
  return apiRequest("/api/data-mgmt/retention-configs", { token: session.accessToken });
}

export async function updateRetentionConfig(
  session: AuthSession,
  tableName: string,
  updates: Partial<Pick<RetentionConfig, "max_age_days" | "max_records" | "keep_saved" | "enabled">>,
): Promise<RetentionConfig> {
  return apiRequest(`/api/data-mgmt/retention-configs/${tableName}`, {
    method: "PUT",
    token: session.accessToken,
    body: JSON.stringify(updates),
  });
}

export async function previewPurge(
  session: AuthSession,
  tableName?: string,
): Promise<PurgePreview[]> {
  const qs = tableName ? `?table_name=${tableName}` : "";
  return apiRequest(`/api/data-mgmt/purge/preview${qs}`, {
    method: "POST",
    token: session.accessToken,
  });
}

export async function executePurge(
  session: AuthSession,
  tableName?: string,
  vacuum = true,
): Promise<PurgeAllResult> {
  const params = new URLSearchParams();
  if (tableName) params.set("table_name", tableName);
  params.set("vacuum", String(vacuum));
  return apiRequest(`/api/data-mgmt/purge/execute?${params.toString()}`, {
    method: "POST",
    token: session.accessToken,
  });
}

export async function runVacuum(session: AuthSession): Promise<MaintenanceResult> {
  return apiRequest("/api/data-mgmt/vacuum", {
    method: "POST",
    token: session.accessToken,
  });
}

export function getExportUrl(session: AuthSession, fmt: string, tables?: string): string {
  const base = "/api/data-mgmt/export";
  const params = new URLSearchParams();
  params.set("fmt", fmt);
  if (tables) params.set("tables", tables);
  return `${base}?${params.toString()}`;
}
