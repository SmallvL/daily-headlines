const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";
const REQUEST_TIMEOUT = 30_000; // 30 seconds

export type ApiResponse<T> = {
  data: T | null;
  error: { code: string; message: string; details?: Record<string, unknown> } | null;
  request_id?: string | null;
};

function getErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof Error) return error.message;
  if (typeof error === "string") return error;
  return fallback;
}

export async function apiRequest<T>(
  path: string,
  options: RequestInit & { token?: string } = {}
): Promise<T> {
  const { token, ...requestOptions } = options;

  // Add timeout
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT);

  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      ...requestOptions,
      signal: controller.signal,
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...requestOptions.headers
      }
    });

    clearTimeout(timeoutId);

    // Parse JSON with error handling
    let payload: ApiResponse<T>;
    try {
      payload = (await response.json()) as ApiResponse<T>;
    } catch {
      throw new Error(
        `服务器返回了无效的响应 (${response.status} ${response.statusText})`
      );
    }

    if (!response.ok || payload.error) {
      throw new Error(payload.error?.message ?? `请求失败: ${response.status}`);
    }

    if (payload.data === null) {
      throw new Error("响应数据为空");
    }

    return payload.data;
  } catch (error) {
    clearTimeout(timeoutId);

    if (error instanceof DOMException && error.name === "AbortError") {
      throw new Error("请求超时，请检查网络连接后重试");
    }

    throw new Error(getErrorMessage(error, "网络请求失败"));
  }
}
