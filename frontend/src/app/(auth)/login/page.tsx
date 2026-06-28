"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { supabase } from "@/lib/supabase";
import { api } from "@/lib/api";
import { useAuthStore } from "@/store/auth-store";
import toast, { Toaster } from "react-hot-toast";
import { Mail, Lock, ArrowRight } from "lucide-react"; // Import Lucide icons

export default function LoginPage() {
  const router = useRouter();
  const setSession = useAuthStore((state) => state.setSession);

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);

  // Mouse tracking position for interactive glow
  const [glowPos, setGlowPos] = useState({ x: 0, y: 0 });

  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    setGlowPos({
      x: e.clientX - rect.left,
      y: e.clientY - rect.top,
    });
  };

  const handleGoogleLogin = async () => {
    try {
      toast.loading("Connecting with Google...", { id: "oauth" });
      const { error } = await supabase.auth.signInWithOAuth({
        provider: "google",
        options: {
          redirectTo: `${window.location.origin}/api/auth/callback?next=/onboarding`,
        },
      });
      if (error) {
        toast.error(error.message, { id: "oauth" });
      }
    } catch (e: any) {
      toast.error("OAuth initiation failed", { id: "oauth" });
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password) {
      toast.error("Please fill in all fields");
      return;
    }

    setLoading(true);
    try {
      const { data, error } = await supabase.auth.signInWithPassword({
        email,
        password,
      });

      if (error) {
        toast.error(error.message);
        setLoading(false);
        return;
      }

      if (data.session) {
        setSession(data.session);

        try {
          // Verify tenant configuration
          await api.get("/settings/integrations", {
            headers: { Authorization: `Bearer ${data.session.access_token}` },
          });
          toast.success("Welcome back!");
          router.push("/dashboard");
        } catch (e: any) {
          if (e.response && e.response.status === 404) {
            toast.success("Welcome! Let's set up your workspace.");
            router.push("/onboarding");
          } else {
            toast.success("Login successful.");
            router.push("/dashboard");
          }
        }
      }
    } catch (e: any) {
      toast.error("Authentication failed: " + (e.message || "Unknown error"));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      onMouseMove={handleMouseMove}
      className="w-full h-screen bg-[#0A0A0B] text-[#e5e2e3] relative overflow-hidden flex flex-col items-center justify-center p-4 select-none"
    >
      <Toaster
        position="top-right"
        toastOptions={{
          style: {
            background: "#111113",
            color: "#e5e2e3",
            border: "1px solid #27272A",
          },
        }}
      />
      
      {/* Dynamic Cursor-Tracking Glow */}
      <div
        className="absolute inset-0 pointer-events-none opacity-35 transition-opacity duration-300"
        style={{
          background: `radial-gradient(600px circle at ${glowPos.x}px ${glowPos.y}px, rgba(245, 166, 35, 0.35), transparent 75%)`,
        }}
      />

      <main className="w-full max-w-[400px] flex flex-col items-center z-10">
        
        {/* Logo Section */}
        <div className="mb-6 flex flex-col items-center gap-1 animate-in fade-in duration-500">
          <div className="w-12 h-12 bg-[#E8A020] flex items-center justify-center mb-3 rounded-lg shadow-[0_0_20px_rgba(245,166,35,0.25)]">
            <svg
              className="w-7 h-7 text-[#291800]"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.5"
              viewBox="0 0 24 24"
              xmlns="http://www.w3.org/2000/svg"
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 21a9.004 9.004 0 008.716-6.747M12 21a9.004 9.004 0 01-8.716-6.747M12 21c2.485 0 4.5-4.03 4.5-9S14.485 3 12 3m0 18c-2.485 0-4.5-4.03-4.5-9s2.015-9 4.5-9m0 0a9.003 9.003 0 018.716 6.747M12 3a9.003 9.003 0 00-8.716 6.747" />
            </svg>
          </div>
          <h1 className="font-display-lg text-2xl font-bold text-[#e5e2e3] tracking-tight">
            BandhanAI
          </h1>
          <p className="text-[11px] text-[#d7c3ae]/50 text-center">
            AI-powered CRM for modern commerce
          </p>
        </div>

        {/* Authentication Card */}
        <div className="w-full bg-[#111113]/90 backdrop-blur border border-[#27272A] p-6 shadow-2xl rounded-lg animate-in fade-in duration-700">
          <div className="mb-4">
            <h2 className="text-lg font-bold text-[#e5e2e3] mb-0.5">Sign in</h2>
            <p className="text-[11px] text-[#d7c3ae]/70">
              Enter your credentials to access your workspace.
            </p>
          </div>

          {/* Continue with Google Action */}
          <button
            onClick={handleGoogleLogin}
            type="button"
            className="w-full flex items-center justify-center gap-3 border border-[#27272A] bg-[#0e0e0f] py-2.5 mb-4 hover:bg-[#353436] transition-colors duration-200 cursor-pointer rounded"
          >
            <svg height="18" viewBox="0 0 24 24" width="18" xmlns="http://www.w3.org/2000/svg">
              <path
                d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                fill="#4285F4"
              ></path>
              <path
                d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                fill="#34A853"
              ></path>
              <path
                d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z"
                fill="#FBBC05"
              ></path>
              <path
                d="M12 5.38c1.62 0 3.06.56 4.21 1.66l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                fill="#EA4335"
              ></path>
            </svg>
            <span className="font-body-base font-medium text-[#e5e2e3] text-xs">
              Continue with Google
            </span>
          </button>

          {/* OR Divider */}
          <div className="flex items-center gap-4 mb-4 text-[#d7c3ae]/30">
            <div className="h-px bg-[#27272A] flex-1"></div>
            <span className="font-data-mono text-[9px] uppercase tracking-wider">or</span>
            <div className="h-px bg-[#27272A] flex-1"></div>
          </div>

          {/* Credentials Form */}
          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <div className="flex flex-col gap-1">
              <label
                className="font-label-caps text-[9px] text-[#d7c3ae]/80 uppercase ml-1"
                htmlFor="email"
              >
                Email Address
              </label>
              <div className="border border-[#27272A] bg-[#09090B] flex items-center px-3 py-1 text-sm rounded transition-colors focus-within:ring-1 focus-within:ring-[#E8A020]/30 focus-within:border-[#E8A020]">
                <Mail className="w-4 h-4 text-[#d7c3ae]/60 mr-3" />
                <input
                  className="bg-transparent border-none focus:ring-0 w-full text-[#e5e2e3] font-body-base placeholder-[#474649] py-2 focus:outline-none text-xs"
                  id="email"
                  type="email"
                  placeholder="name@company.com"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                />
              </div>
            </div>

            <div className="flex flex-col gap-1">
              <div className="flex justify-between items-center px-1">
                <label
                  className="font-label-caps text-[9px] text-[#d7c3ae]/80 uppercase"
                  htmlFor="password"
                >
                  Password
                </label>
                <a
                  className="font-label-caps text-[9px] text-[#d7c3ae]/50 hover:text-[#E8A020] transition-colors"
                  href="#"
                >
                  Forgot?
                </a>
              </div>
              <div className="border border-[#27272A] bg-[#09090B] flex items-center px-3 py-1 text-sm rounded transition-colors focus-within:ring-1 focus-within:ring-[#E8A020]/30 focus-within:border-[#E8A020]">
                <Lock className="w-4 h-4 text-[#d7c3ae]/60 mr-3" />
                <input
                  className="bg-transparent border-none focus:ring-0 w-full text-[#e5e2e3] font-body-base placeholder-[#474649] py-2 focus:outline-none text-xs"
                  id="password"
                  type="password"
                  placeholder="••••••••"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="mt-2 bg-[#E8A020] text-[#291800] font-bold py-2.5 rounded hover:brightness-110 active:scale-[0.98] transition-all duration-200 flex items-center justify-center gap-2 cursor-pointer text-xs"
            >
              {loading ? "Authenticating..." : "Login"}
              <ArrowRight className="w-4 h-4 text-[#291800]" />
            </button>
          </form>

          {/* Create account trigger */}
          <div className="mt-4 pt-3 border-t border-[#27272A]/50 flex justify-center text-xs">
            <p className="text-[#d7c3ae]/70 text-[11px]">
              Don&apos;t have an account?
              <Link
                href="/signup"
                className="text-[#E8A020] font-semibold hover:underline ml-1.5"
              >
                Create an account
              </Link>
            </p>
          </div>
        </div>

        {/* Footer Meta */}
        <footer className="mt-6 flex flex-col items-center gap-1.5">
          <span className="font-data-mono text-[9px] text-[#3F3F46] uppercase tracking-wider">
            v2.4.0-stable
          </span>
          <div className="flex gap-4">
            <a
              className="font-data-mono text-[9px] text-[#d7c3ae]/40 hover:text-[#e5e2e3] transition-colors"
              href="#"
            >
              Privacy
            </a>
            <a
              className="font-data-mono text-[9px] text-[#d7c3ae]/40 hover:text-[#e5e2e3] transition-colors"
              href="#"
            >
              Terms
            </a>
            <a
              className="font-data-mono text-[9px] text-[#d7c3ae]/40 hover:text-[#e5e2e3] transition-colors"
              href="#"
            >
              Status
            </a>
          </div>
        </footer>
      </main>
    </div>
  );
}
