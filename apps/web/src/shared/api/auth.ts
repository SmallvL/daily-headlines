import { apiRequest } from "./client";

export type AuthSession = {
  accessToken: string;
};

type LoginResponse = {
  access_token: string;
  token_type: string;
};

export async function login(payload: { username: string; password: string }): Promise<AuthSession> {
  const data = await apiRequest<LoginResponse>("/api/auth/login", {
    method: "POST",
    body: JSON.stringify(payload)
  });

  return { accessToken: data.access_token };
}
