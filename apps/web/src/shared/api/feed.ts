import { AuthSession } from "./auth";
import { apiRequest } from "./client";

export type FeedItem = {
  id: string;
  source_id: string;
  source_name: string;
  title: string;
  summary: string | null;
  url: string | null;
  image_url: string | null;
  author: string | null;
  published_at: string | null;
  fetched_at: string | null;
  is_read: boolean;
  is_saved: boolean;
  is_hidden: boolean;
};

export type FeedQuery = {
  q?: string;
  sourceType?: "rss" | "api";
  sourceId?: string;
  hasImage?: boolean;
  saved?: boolean;
  read?: boolean;
  includeHidden?: boolean;
  page?: number;
  pageSize?: number;
};

export type FeedListResponse = {
  items: FeedItem[];
  total: number;
  page: number;
  page_size: number;
};

export async function listFeedItems(session: AuthSession, query: FeedQuery = {}): Promise<FeedListResponse> {
  const params = new URLSearchParams();
  if (query.q) {
    params.set("q", query.q);
  }
  if (query.sourceType) {
    params.set("source_type", query.sourceType);
  }
  if (query.sourceId) {
    params.set("source_id", query.sourceId);
  }
  if (query.hasImage !== undefined) {
    params.set("has_image", String(query.hasImage));
  }
  if (query.saved !== undefined) {
    params.set("saved", String(query.saved));
  }
  if (query.read !== undefined) {
    params.set("read", String(query.read));
  }
  if (query.includeHidden !== undefined) {
    params.set("include_hidden", String(query.includeHidden));
  }
  if (query.page !== undefined) {
    params.set("page", String(query.page));
  }
  if (query.pageSize !== undefined) {
    params.set("page_size", String(query.pageSize));
  }
  const path = params.size ? `/api/feed/items?${params.toString()}` : "/api/feed/items";
  const data = await apiRequest<FeedListResponse>(path, {
    token: session.accessToken
  });

  return data;
}

export function saveFeedItem(session: AuthSession, itemId: string): Promise<unknown> {
  return apiRequest(`/api/feed/items/${itemId}/save`, {
    method: "POST",
    token: session.accessToken
  });
}

export function unsaveFeedItem(session: AuthSession, itemId: string): Promise<unknown> {
  return apiRequest(`/api/feed/items/${itemId}/save`, {
    method: "DELETE",
    token: session.accessToken
  });
}

export function readFeedItem(session: AuthSession, itemId: string): Promise<unknown> {
  return apiRequest(`/api/feed/items/${itemId}/read`, {
    method: "POST",
    token: session.accessToken
  });
}

export function hideFeedItem(session: AuthSession, itemId: string): Promise<unknown> {
  return apiRequest(`/api/feed/items/${itemId}/hide`, {
    method: "POST",
    token: session.accessToken
  });
}
