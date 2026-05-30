import { AuthSession } from "./auth";
import { apiRequest } from "./client";

// ── Types ──

export type AgentToken = {
  id: string;
  name: string;
  prefix: string;
  scopes: string[];
  enabled: boolean;
  last_used_at: string | null;
  expires_at: string | null;
  created_at: string | null;
  revoked_at: string | null;
};

export type AgentTokenCreated = {
  id: string;
  name: string;
  token: string; // 只在创建时返回
  prefix: string;
  scopes: string[];
  expires_at: string | null;
  created_at: string | null;
};

export type AgentTokenCreate = {
  name: string;
  scopes?: string[];
  expires_in_days?: number;
};

// ── API ──

export async function listTokens(
  session: AuthSession,
): Promise<AgentToken[]> {
  const res = await apiRequest<{ items: AgentToken[] }>(
    "/api/agent-tokens/tokens",
    { token: session.accessToken },
  );
  return res.items;
}

export async function createToken(
  session: AuthSession,
  data: AgentTokenCreate,
): Promise<AgentTokenCreated> {
  return apiRequest<AgentTokenCreated>("/api/agent-tokens/tokens", {
    method: "POST",
    token: session.accessToken,
    body: JSON.stringify(data),
  });
}

export async function revokeToken(
  session: AuthSession,
  tokenId: string,
): Promise<void> {
  await apiRequest<{ revoked: boolean }>(
    `/api/agent-tokens/tokens/${tokenId}`,
    { method: "DELETE", token: session.accessToken },
  );
}
