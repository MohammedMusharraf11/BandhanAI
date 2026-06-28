import { useAuthStore } from "@/store/auth-store";

export function useAuth() {
  const { user, session, token, orgId, loading } = useAuthStore();
  return { user, session, token, orgId, loading };
}
