import { AuthSession } from "./auth";
import { apiRequest } from "./client";

// ── Types ──

export type ApiFormat = "openai" | "anthropic";

export type LlmProvider = {
  id: string;
  name: string;
  base_url: string;
  api_key_masked: string;
  model: string;
  api_format: ApiFormat;
  is_default: boolean;
  enabled: boolean;
  created_at: string | null;
};

export type LlmProviderCreate = {
  name: string;
  base_url: string;
  api_key: string;
  model: string;
  api_format?: ApiFormat;
  is_default?: boolean;
};

export type AgentDraft = {
  id: string;
  user_id: string;
  provider_id: string;
  prompt_md: string;
  status: string;
  source_draft_json: string;
  error_message: string | null;
  llm_model: string;
  llm_tokens_used: number;
  llm_cost: number;
  created_at: string | null;
  updated_at: string | null;
};

export type SourceDraft = {
  name: string;
  type: "rss" | "api" | "web";
  endpoint: string;
  config: Record<string, string>;
  schedule_enabled: boolean;
  schedule_interval_minutes: number | null;
  // Added by confirm endpoint
  source_id?: string;
  source_name?: string;
  source_type?: string;
  draft_id?: string;
};

// ── API ──

export async function listProviders(session: AuthSession): Promise<LlmProvider[]> {
  const res = await apiRequest<{ items: LlmProvider[] }>(
    "/api/agent/providers",
    { token: session.accessToken },
  );
  return res.items;
}

export async function createProvider(
  session: AuthSession,
  data: LlmProviderCreate,
): Promise<LlmProvider> {
  return apiRequest<LlmProvider>("/api/agent/providers", {
    method: "POST",
    token: session.accessToken,
    body: JSON.stringify(data),
  });
}

export async function deleteProvider(
  session: AuthSession,
  providerId: string,
): Promise<void> {
  await apiRequest<{ deleted: boolean }>(
    `/api/agent/providers/${providerId}`,
    { method: "DELETE", token: session.accessToken },
  );
}

export async function listDrafts(
  session: AuthSession,
  limit = 20,
  offset = 0,
): Promise<{ items: AgentDraft[]; total: number }> {
  return apiRequest<{ items: AgentDraft[]; total: number }>(
    `/api/agent/drafts?limit=${limit}&offset=${offset}`,
    { token: session.accessToken },
  );
}

export async function generateDraft(
  session: AuthSession,
  data: { provider_id: string; prompt_md: string },
): Promise<AgentDraft> {
  return apiRequest<AgentDraft>("/api/agent/drafts/generate", {
    method: "POST",
    token: session.accessToken,
    body: JSON.stringify(data),
  });
}

export async function updateDraft(
  session: AuthSession,
  draftId: string,
  data: { source_draft_json?: string; status?: string },
): Promise<AgentDraft> {
  return apiRequest<AgentDraft>(`/api/agent/drafts/${draftId}`, {
    method: "PATCH",
    token: session.accessToken,
    body: JSON.stringify(data),
  });
}

export async function confirmDraft(
  session: AuthSession,
  draftId: string,
  sourceDraftJson: string,
): Promise<SourceDraft> {
  return apiRequest<SourceDraft>(`/api/agent/drafts/${draftId}/confirm`, {
    method: "POST",
    token: session.accessToken,
    body: JSON.stringify({ source_draft_json: sourceDraftJson }),
  });
}

export async function deleteDraft(
  session: AuthSession,
  draftId: string,
): Promise<void> {
  await apiRequest<{ deleted: boolean }>(
    `/api/agent/drafts/${draftId}`,
    { method: "DELETE", token: session.accessToken },
  );
}
