/**
 * Image proxy helper — wraps external image URLs through the backend proxy
 * to bypass hotlink protection (403 from B站/IT之家 etc.).
 */

const PROXY_BASE = "/api/proxy/image";

/**
 * Returns the proxied URL for an external image.
 * If the URL is already local or empty, returns it as-is.
 */
export function proxiedImageUrl(url: string | null | undefined): string | null {
  if (!url) return null;

  // Already proxied or local
  if (url.startsWith("/api/") || url.startsWith("data:")) return url;

  // Only proxy http/https external URLs
  if (url.startsWith("http://") || url.startsWith("https://")) {
    return `${PROXY_BASE}?url=${encodeURIComponent(url)}`;
  }

  return url;
}
