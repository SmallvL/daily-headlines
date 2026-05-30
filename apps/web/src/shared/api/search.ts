import { AuthSession } from "./auth";
import { apiRequest } from "./client";
import { FeedQuery } from "./feed";

export type SavedSearch = {
  id: string;
  name: string;
  query: {
    q?: string | null;
    source_type?: "rss" | "api" | null;
    has_image?: boolean | null;
    saved?: boolean | null;
    read?: boolean | null;
    include_hidden?: boolean | null;
  };
  created_at: string | null;
};

function toApiQuery(query: FeedQuery) {
  return {
    q: query.q,
    source_type: query.sourceType,
    has_image: query.hasImage,
    saved: query.saved,
    read: query.read,
    include_hidden: query.includeHidden
  };
}

export function fromApiQuery(savedSearch: SavedSearch): FeedQuery {
  return {
    q: savedSearch.query.q ?? undefined,
    sourceType: savedSearch.query.source_type ?? undefined,
    hasImage: savedSearch.query.has_image ?? undefined,
    saved: savedSearch.query.saved ?? undefined,
    read: savedSearch.query.read ?? undefined,
    includeHidden: savedSearch.query.include_hidden ?? undefined
  };
}

export function listSavedSearches(session: AuthSession): Promise<SavedSearch[]> {
  return apiRequest<SavedSearch[]>("/api/search/saved-searches", {
    token: session.accessToken
  });
}

export function createSavedSearch(
  session: AuthSession,
  name: string,
  query: FeedQuery
): Promise<SavedSearch> {
  return apiRequest<SavedSearch>("/api/search/saved-searches", {
    method: "POST",
    token: session.accessToken,
    body: JSON.stringify({ name, query: toApiQuery(query) })
  });
}

export function deleteSavedSearch(
  session: AuthSession,
  searchId: string
): Promise<{ deleted: boolean }> {
  return apiRequest<{ deleted: boolean }>(`/api/search/saved-searches/${searchId}`, {
    method: "DELETE",
    token: session.accessToken
  });
}
