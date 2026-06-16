import { AuthSession } from "./auth";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

export async function uploadLoginBackground(
  session: AuthSession,
  file: File,
): Promise<{ url: string }> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE_URL}/api/upload/login-background`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${session.accessToken}`,
    },
    body: formData,
  });

  const payload = (await response.json()) as {
    data?: { url: string };
    error?: { message: string };
  };

  if (!response.ok || payload.error) {
    throw new Error(payload.error?.message ?? "上传失败");
  }

  if (!payload.data?.url) {
    throw new Error("上传响应缺少 URL");
  }

  return payload.data;
}
