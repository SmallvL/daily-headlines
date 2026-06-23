import { AuthSession } from "./auth";
import { apiRequest } from "./client";

export type UserProfile = {
  id: string;
  username: string;
  display_name: string;
  roles: string[];
  language: string;
  theme: string;
};

export function getUserProfile(session: AuthSession): Promise<UserProfile> {
  return apiRequest<UserProfile>("/api/users/me", {
    token: session.accessToken,
  });
}
