"use client";

import React, { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import Link from "next/link";
import { supabase } from "@/lib/supabase";
import { useAuthStore } from "@/store/auth-store";
import { useTenantStore } from "@/store/tenant-store";
import toast, { Toaster } from "react-hot-toast";
import {
  HelpCircle,
  LayoutDashboard,
  MessageSquare,
  Search,
  Bell,
  Settings,
  LogOut,
} from "lucide-react";

export default function AppLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const router = useRouter();
  const { session, user, loading, logout } = useAuthStore();
  const { agentName, fetchTenantSettings } = useTenantStore();

  useEffect(() => {
    if (!loading) {
      if (!session) {
        router.push("/login");
      } else {
        fetchTenantSettings();
      }
    }
  }, [session, loading, router, fetchTenantSettings]);

  // Loading state placeholder matching dark mode
  if (loading) {
    return (
      <div className="min-h-screen bg-[#0A0A0B] text-[#e5e2e3] flex flex-col items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <div className="w-8 h-8 border-t-2 border-b-2 border-[#E8A020] rounded-full animate-spin" />
          <span className="font-data-mono text-label-caps tracking-widest text-[#d7c3ae]">
            Loading BandhanAI...
          </span>
        </div>
      </div>
    );
  }

  // If session check complete but not logged in, wait for redirection
  if (!session) return null;

  // Onboarding page has its own full screen canvas (no sidebar)
  if (pathname === "/onboarding") {
    return (
      <div className="min-h-screen bg-[#0A0A0B] text-[#e5e2e3] relative">
        <Toaster position="top-right" toastOptions={{ style: { background: "#111113", color: "#e5e2e3", border: "1px solid #27272A" } }} />
        {children}
      </div>
    );
  }

  const handleLogout = async () => {
    try {
      await logout();
      toast.success("Logged out successfully");
      router.push("/login");
    } catch (e: any) {
      toast.error("Logout failed: " + e.message);
    }
  };

  const navItems = [
    { name: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
    { name: "Chat", href: "/chat", icon: MessageSquare },
    { name: "Settings", href: "/settings", icon: Settings },
  ];

  return (
    <div className="flex min-h-screen bg-[#0A0A0B] text-[#e5e2e3]">
      <Toaster position="top-right" toastOptions={{ style: { background: "#111113", color: "#e5e2e3", border: "1px solid #27272A" } }} />
      
      {/* SideNavBar Component */}
      <aside className="w-[240px] h-screen fixed left-0 top-0 bg-[#0A0A0B] border-r border-[#27272A] flex flex-col py-6 px-4 z-20">
        <div className="mb-8">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-[#E8A020]/10 border border-[#E8A020]/30 flex items-center justify-center text-[#E8A020] font-bold">
              B
            </div>
            <div>
              <h1 className="font-display-lg text-lg font-bold text-[#E8A020] leading-none">BandhanAI</h1>
              <p className="font-data-mono text-[10px] text-[#d7c3ae] uppercase tracking-widest mt-1">Enterprise CRM</p>
            </div>
          </div>
        </div>

        <nav className="flex-1 space-y-1">
          {navItems.map((item) => {
            const isActive = pathname === item.href;
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center gap-3 px-3 py-2 rounded-lg transition-colors duration-200 cursor-pointer active:scale-95 ${
                  isActive
                    ? "text-[#E8A020] font-bold bg-[#353436]"
                    : "text-[#d7c3ae] font-medium hover:bg-[#353436]/50"
                }`}
              >
                <Icon className="h-5 w-5" />
                <span className="font-body-base text-sm">{item.name}</span>
              </Link>
            );
          })}
        </nav>

        {/* User profile / Logout action */}
        <div className="mt-auto pt-4 border-t border-[#27272A]">
          <div className="flex items-center justify-between px-2 mb-3">
            <div className="flex items-center gap-3 overflow-hidden">
              <div className="w-8 h-8 rounded-full bg-[#353436] border border-[#27272A] flex items-center justify-center font-bold text-xs text-[#E8A020]">
                {agentName.substring(0, 2).toUpperCase()}
              </div>
              <div className="overflow-hidden">
                <p className="text-sm font-bold truncate">{agentName}</p>
                <p className="text-[10px] text-[#d7c3ae] truncate">AI Growth Partner</p>
              </div>
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="w-full flex items-center gap-3 px-3 py-2 text-[#ffb4ab] font-medium hover:bg-red-500/10 rounded-lg transition-colors duration-200 cursor-pointer text-xs"
          >
            <LogOut className="h-4 w-4" />
            <span>Sign Out</span>
          </button>
        </div>
      </aside>

      {/* Main Canvas Area */}
      <div className="flex-1 ml-[240px] flex flex-col min-h-screen relative">
        {/* TopAppBar Component */}
        <header className="h-16 fixed top-0 right-0 left-[240px] z-10 bg-[#0A0A0B] border-b border-[#27272A] flex justify-between items-center px-6">
          <div className="flex items-center gap-4 flex-1">
            <div className="relative w-full max-w-md group">
              <Search className="h-5 w-5 absolute left-3 top-1/2 -translate-y-1/2 text-[#d7c3ae]" />
              <input
                className="w-full bg-[#0e0e0f] border border-[#27272A] rounded-lg py-2 pl-10 pr-4 text-xs focus:outline-none focus:ring-1 focus:ring-[#E8A020] transition-all text-[#e5e2e3] placeholder-[#d7c3ae]/40"
                placeholder="Search campaigns or CRM database..."
                type="text"
              />
            </div>
          </div>
          
          <div className="flex items-center gap-6">
            <button className="relative text-[#d7c3ae] hover:text-[#e5e2e3] transition-colors cursor-pointer">
              <Bell className="h-5 w-5" />
              <span className="absolute top-0 right-0 w-2 h-2 bg-[#F5A623] rounded-full" />
            </button>
            <button className="text-[#d7c3ae] hover:text-[#e5e2e3] transition-colors cursor-pointer">
              <HelpCircle className="h-5 w-5" />
            </button>
            <div className="h-8 w-[1px] bg-[#27272A]" />
            <div className="w-8 h-8 rounded bg-[#2a2a2b] border border-[#27272A] flex items-center justify-center text-xs font-bold text-[#e5e2e3]">
              {user?.email?.substring(0, 2).toUpperCase() || "ME"}
            </div>
          </div>
        </header>

        {/* Content canvas */}
        <main className="flex-grow pt-16">{children}</main>
      </div>
    </div>
  );
}
