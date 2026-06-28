import { create } from "zustand";
import { User, Session } from "@supabase/supabase-js";
import { supabase } from "@/lib/supabase";

interface AuthState {
  user: User | null;
  session: Session | null;
  token: string | null;
  orgId: string | null;
  loading: boolean;
  setSession: (session: Session | null) => void;
  setOrgId: (orgId: string | null) => void;
  setLoading: (loading: boolean) => void;
  logout: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  session: null,
  token: null,
  orgId: null,
  loading: true,
  setSession: (session) =>
    set({
      session,
      user: session?.user ?? null,
      token: session?.access_token ?? null,
    }),
  setOrgId: (orgId) => set({ orgId }),
  setLoading: (loading) => set({ loading }),
  logout: async () => {
    await supabase.auth.signOut();
    set({ user: null, session: null, token: null, orgId: null });
  },
}));
