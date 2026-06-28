"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { supabase } from "@/lib/supabase";
import toast, { Toaster } from "react-hot-toast";
import { User, Mail, Lock, ArrowRight } from "lucide-react"; // Import Lucide icons

export default function SignupPage() {
  const router = useRouter();

  const [name, setName] = useState("");
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
          redirectTo: `${window.location.origin}/api/auth/callback`,
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
    if (!name || !email || !password) {
      toast.error("Please fill in all fields");
      return;
    }

    setLoading(true);
    try {
      // Register via Supabase signup
      const { error } = await supabase.auth.signUp({
        email,
        password,
        options: {
          data: {
            full_name: name,
          },
        },
      });

      if (error) {
        toast.error(error.message);
        setLoading(false);
        return;
      }

      toast.success("Account created successfully! Redirecting to login portal...");
      setTimeout(() => {
        router.push("/login");
      }, 2000);
    } catch (e: any) {
      toast.error("Registration failed: " + (e.message || "Unknown error"));
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

      <main className="w-full max-w-[420px] flex flex-col items-center z-10">
        
        {/* Logo Section */}
        <div className="flex flex-col items-center mb-6 animate-in fade-in duration-500">
          <div className="w-12 h-12 bg-[#F5A623] flex items-center justify-center mb-3 rounded-lg shadow-[0_0_20px_rgba(245,166,35,0.25)]">
            <svg
              className="w-7 h-7 text-[#0A0A0B]"
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
          <p className="text-[11px] text-[#d7c3ae]/60 text-center mt-0.5">
            AI-powered CRM for modern commerce
          </p>
        </div>

        {/* Registration Card */}
        <div className="w-full bg-[#111113]/90 backdrop-blur border border-[#1C1C1F] p-6 rounded-lg shadow-2xl animate-in fade-in duration-700">
          
          {/* Google Signup Action */}
          <button
            onClick={handleGoogleLogin}
            type="button"
            className="w-full flex items-center justify-center gap-3 py-2.5 bg-transparent border border-[#1C1C1F] hover:bg-[#353436]/50 rounded transition-all duration-200 cursor-pointer active:scale-[0.98] mb-5"
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
                d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                fill="#EA4335"
              ></path>
            </svg>
            <span className="font-body-base font-medium text-[#e5e2e3] text-xs">
              Continue with Google
            </span>
          </button>

          {/* OR Divider */}
          <div className="relative flex items-center mb-5">
            <div className="flex-grow border-t border-[#1C1C1F]"></div>
            <span className="px-3 font-data-mono text-[9px] uppercase tracking-wider text-[#d7c3ae]/30 bg-[#111113]">
              or
            </span>
            <div className="flex-grow border-t border-[#1C1C1F]"></div>
          </div>

          {/* Registration Credentials Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-1">
              <label
                className="font-label-caps text-[9px] text-[#d7c3ae]/85 uppercase ml-1"
                htmlFor="name"
              >
                Full Name
              </label>
              <div className="border border-[#1C1C1F] bg-[#09090B] flex items-center px-3 py-1 text-sm rounded transition-colors focus-within:ring-1 focus-within:ring-[#F5A623]/25 focus-within:border-[#F5A623]">
                <User className="w-4 h-4 text-[#d7c3ae]/60 mr-3" />
                <input
                  className="bg-transparent border-none focus:ring-0 w-full text-[#e5e2e3] font-body-base placeholder-[#474649] py-2 focus:outline-none text-xs"
                  id="name"
                  placeholder="Elias Thorne"
                  type="text"
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                />
              </div>
            </div>

            <div className="space-y-1">
              <label
                className="font-label-caps text-[9px] text-[#d7c3ae]/85 uppercase ml-1"
                htmlFor="email"
              >
                Work Email
              </label>
              <div className="border border-[#1C1C1F] bg-[#09090B] flex items-center px-3 py-1 text-sm rounded transition-colors focus-within:ring-1 focus-within:ring-[#F5A623]/25 focus-within:border-[#F5A623]">
                <Mail className="w-4 h-4 text-[#d7c3ae]/60 mr-3" />
                <input
                  className="bg-transparent border-none focus:ring-0 w-full text-[#e5e2e3] font-body-base placeholder-[#474649] py-2 focus:outline-none text-xs"
                  id="email"
                  placeholder="elias@company.ai"
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                />
              </div>
            </div>

            <div className="space-y-1">
              <label
                className="font-label-caps text-[9px] text-[#d7c3ae]/85 uppercase ml-1"
                htmlFor="password"
              >
                Password
              </label>
              <div className="border border-[#1C1C1F] bg-[#09090B] flex items-center px-3 py-1 text-sm rounded transition-colors focus-within:ring-1 focus-within:ring-[#F5A623]/25 focus-within:border-[#F5A623]">
                <Lock className="w-4 h-4 text-[#d7c3ae]/60 mr-3" />
                <input
                  className="bg-transparent border-none focus:ring-0 w-full text-[#e5e2e3] font-body-base placeholder-[#474649] py-2 focus:outline-none text-xs"
                  id="password"
                  placeholder="••••••••"
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
              </div>
            </div>

            <div className="pt-1">
              <button
                type="submit"
                disabled={loading}
                className="w-full bg-[#F5A623] py-2.5 rounded font-body-base font-bold text-[#0A0A0B] transition-all hover:bg-[#E8A020] active:scale-[0.97] flex items-center justify-center gap-1.5 group cursor-pointer text-xs"
              >
                {loading ? "Configuring Workspace..." : "Create Account"}
                <ArrowRight className="w-4 h-4 text-[#0A0A0B] group-hover:translate-x-0.5 transition-transform" />
              </button>
            </div>
          </form>

          {/* Terms */}
          <p className="mt-4 text-center font-body-sm text-[10px] text-[#474649] leading-relaxed">
            By clicking &quot;Create Account&quot;, you agree to our{" "}
            <a
              className="text-[#d7c3ae] hover:text-[#F5A623] underline-offset-4 underline decoration-[#1C1C1F] transition-colors"
              href="#"
            >
              Terms of Service
            </a>{" "}
            and{" "}
            <a
              className="text-[#d7c3ae] hover:text-[#F5A623] underline-offset-4 underline decoration-[#1C1C1F] transition-colors"
              href="#"
            >
              Privacy Policy
            </a>
            .
          </p>
        </div>

        {/* Redirect Footer Link */}
        <div className="mt-4 animate-in fade-in duration-1000 delay-300">
          <p className="font-body-base text-xs text-[#d7c3ae]/80">
            Already have an account?
            <Link
              href="/login"
              className="text-[#F5A623] font-bold ml-1.5 hover:text-[#E8A020] transition-colors focus:underline outline-none"
            >
              Sign in
            </Link>
          </p>
        </div>
      </main>
    </div>
  );
}
