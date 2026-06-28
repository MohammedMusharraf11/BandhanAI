"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function RootPage() {
  const router = useRouter();

  useEffect(() => {
    // Automatically redirect root visitors to the dashboard
    router.replace("/dashboard");
  }, [router]);

  return (
    <div className="min-h-screen bg-[#0A0A0B] text-[#e5e2e3] flex flex-col items-center justify-center">
      <div className="flex flex-col items-center gap-4">
        <div className="w-8 h-8 border-t-2 border-b-2 border-[#E8A020] rounded-full animate-spin" />
        <span className="font-data-mono text-label-caps tracking-widest text-[#d7c3ae]">
          Redirecting to BandhanAI Workspace...
        </span>
      </div>
    </div>
  );
}
