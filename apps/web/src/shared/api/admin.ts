import { AuthSession } from "./auth";
import { apiRequest } from "./client";

// ── Types ──

export type AdminUser = {
  id: string;
  username: string;
  email: string | null;
  display_name: string;
  role: string;
  status: string;
  last_login_at: string | null;
  created_at: string | null;
};

export type UserListPage = {
  items: AdminUser[];
  total: number;
};

export type UserGroup = {
  id: string;
  name: string;
  description: string | null;
  member_count: number;
  created_by: string;
  created_at: string | null;
};

export type GroupMember = {
  user_id: string;
  username: string;
  display_name: string;
  joined_at: string | null;
};

export type GroupDetail = {
  id: string;
  name: string;
  description: string | null;
  members: GroupMember[];
  created_by: string;
  created_at: string | null;
};

export type SourceTemplate = {
  id: string;
  name: string;
  type: string;
  endpoint: string;
  config: Record<string, unknown>;
  description: string | null;
  created_by: string;
  created_at: string | null;
};

export type PushSubscription = {
  id: string;
  user_id: string;
  template_id: string;
  template_name: string;
  source_id: string | null;
  status: string;
  pushed_by: string;
  created_at: string | null;
};

export type AuditLog = {
  id: string;
  actor_id: string;
  action: string;
  resource_type: string;
  resource_id: string | null;
  details: Record<string, unknown>;
  created_at: string | null;
};

export type AuditLogPage = {
  items: AuditLog[];
  total: number;
  page: number;
  page_size: number;
};

// ── User Management ──

export function listAdminUsers(
  session: AuthSession,
  q?: string
): Promise<UserListPage> {
  const qs = q ? `?q=${encodeURIComponent(q)}` : "";
  return apiRequest<UserListPage>(`/api/admin/users${qs}`, {
    token: session.accessToken,
  });
}

export function updateUserRole(
  session: AuthSession,
  userId: string,
  role: string
): Promise<AdminUser> {
  return apiRequest<AdminUser>(`/api/admin/users/${userId}/role`, {
    method: "PATCH",
    token: session.accessToken,
    body: JSON.stringify({ role }),
  });
}

export function updateUserStatus(
  session: AuthSession,
  userId: string,
  status: string
): Promise<AdminUser> {
  return apiRequest<AdminUser>(`/api/admin/users/${userId}/status`, {
    method: "PATCH",
    token: session.accessToken,
    body: JSON.stringify({ status }),
  });
}

export function createUser(
  session: AuthSession,
  payload: {
    username: string;
    password: string;
    display_name: string;
    email?: string;
    role?: string;
  }
): Promise<AdminUser> {
  return apiRequest<AdminUser>("/api/admin/users", {
    method: "POST",
    token: session.accessToken,
    body: JSON.stringify(payload),
  });
}

// ── Group Management ──

export function listGroups(session: AuthSession): Promise<UserGroup[]> {
  return apiRequest<UserGroup[]>("/api/admin/groups", {
    token: session.accessToken,
  });
}

export function getGroup(
  session: AuthSession,
  groupId: string
): Promise<GroupDetail> {
  return apiRequest<GroupDetail>(`/api/admin/groups/${groupId}`, {
    token: session.accessToken,
  });
}

export function createGroup(
  session: AuthSession,
  payload: { name: string; description?: string }
): Promise<UserGroup> {
  return apiRequest<UserGroup>("/api/admin/groups", {
    method: "POST",
    token: session.accessToken,
    body: JSON.stringify(payload),
  });
}

export function deleteGroup(
  session: AuthSession,
  groupId: string
): Promise<{ deleted: boolean }> {
  return apiRequest<{ deleted: boolean }>(`/api/admin/groups/${groupId}`, {
    method: "DELETE",
    token: session.accessToken,
  });
}

export function addGroupMembers(
  session: AuthSession,
  groupId: string,
  userIds: string[]
): Promise<GroupDetail> {
  return apiRequest<GroupDetail>(`/api/admin/groups/${groupId}/members`, {
    method: "POST",
    token: session.accessToken,
    body: JSON.stringify({ user_ids: userIds }),
  });
}

export function removeGroupMember(
  session: AuthSession,
  groupId: string,
  userId: string
): Promise<{ removed: boolean }> {
  return apiRequest<{ removed: boolean }>(
    `/api/admin/groups/${groupId}/members/${userId}`,
    { method: "DELETE", token: session.accessToken }
  );
}

// ── Source Templates ──

export function listTemplates(
  session: AuthSession
): Promise<SourceTemplate[]> {
  return apiRequest<SourceTemplate[]>("/api/admin/templates", {
    token: session.accessToken,
  });
}

export function createTemplate(
  session: AuthSession,
  payload: {
    name: string;
    type: string;
    endpoint: string;
    config?: Record<string, unknown>;
    description?: string;
  }
): Promise<SourceTemplate> {
  return apiRequest<SourceTemplate>("/api/admin/templates", {
    method: "POST",
    token: session.accessToken,
    body: JSON.stringify(payload),
  });
}

export function deleteTemplate(
  session: AuthSession,
  templateId: string
): Promise<{ deleted: boolean }> {
  return apiRequest<{ deleted: boolean }>(
    `/api/admin/templates/${templateId}`,
    { method: "DELETE", token: session.accessToken }
  );
}

export function pushTemplate(
  session: AuthSession,
  templateId: string,
  targetType: string,
  targetIds: string[]
): Promise<PushSubscription[]> {
  return apiRequest<PushSubscription[]>(
    `/api/admin/templates/${templateId}/push`,
    {
      method: "POST",
      token: session.accessToken,
      body: JSON.stringify({ target_type: targetType, target_ids: targetIds }),
    }
  );
}

// ── Push Subscriptions (user side) ──

export function listMyPushes(
  session: AuthSession
): Promise<PushSubscription[]> {
  return apiRequest<PushSubscription[]>("/api/admin/pushes/mine", {
    token: session.accessToken,
  });
}

export function actOnPush(
  session: AuthSession,
  pushId: string,
  action: "accept" | "ignore"
): Promise<PushSubscription> {
  return apiRequest<PushSubscription>(`/api/admin/pushes/${pushId}`, {
    method: "PATCH",
    token: session.accessToken,
    body: JSON.stringify({ action }),
  });
}

// ── Audit Logs ──

export function listAuditLogs(
  session: AuthSession,
  params: { action?: string; resource_type?: string; page?: number; page_size?: number } = {}
): Promise<AuditLogPage> {
  const searchParams = new URLSearchParams();
  if (params.action) searchParams.set("action", params.action);
  if (params.resource_type) searchParams.set("resource_type", params.resource_type);
  if (params.page) searchParams.set("page", String(params.page));
  if (params.page_size) searchParams.set("page_size", String(params.page_size));
  const qs = searchParams.toString();
  return apiRequest<AuditLogPage>(`/api/admin/audit-logs${qs ? `?${qs}` : ""}`, {
    token: session.accessToken,
  });
}
