"use client";

import { useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import { supabase } from "@/lib/supabase";
import { useAuthStore } from "@/store/auth-store";

export default function AuthStateSync({ children }: { children: React.ReactNode }) {
  const setSession = useAuthStore((state) => state.setSession);
  const setLoading = useAuthStore((state) => state.setLoading);
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    // 1. Initial check
    const syncSession = async () => {
      setLoading(true);
      const { data: { session } } = await supabase.auth.getSession();
      setSession(session);
      
      // If we got access token on hash (implicit flow), Supabase JS SDK handles it automatically.
      // If we are on /login with an active session, let's push them to dashboard.
      if (session && (pathname === "/login" || pathname === "/signup" || pathname === "/")) {
        router.push("/dashboard");
      }
      setLoading(false);
    };
    
    syncSession();

    // 2. Real-time auth listener
    const { data: { subscription } } = supabase.auth.onAuthStateChange((event, session) => {
      setSession(session);
      setLoading(false);
      
      if (session && (pathname === "/login" || pathname === "/signup" || pathname === "/")) {
        router.push("/dashboard");
      }
    });

    return () => {
      subscription.unsubscribe();
    };
  }, [setSession, setLoading, router, pathname]);

  return <>{children}</>;
}
