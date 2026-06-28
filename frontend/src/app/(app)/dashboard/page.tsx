"use client";

import React, { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { useTenantStore } from "@/store/tenant-store";
import toast from "react-hot-toast";
import {
  AlertTriangle,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Download,
  Filter,
  Mail,
  RefreshCw,
  Rocket,
  Settings,
  Sparkles,
  Users,
  Zap,
} from "lucide-react";

interface Campaign {
  id: string;
  name: string;
  type: string;
  status: string;
  created_at: string;
  emails_sent?: number;
}

export default function DashboardPage() {
  const { agentName, integrations, fetchTenantSettings } = useTenantStore();
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [loadingCampaigns, setLoadingCampaigns] = useState(false);
  const displayName = useMemo(() => (agentName || "Agent").trim(), [agentName]);
  const initials = useMemo(
    () => displayName.split(" ").map((part) => part[0]).join("").slice(0, 2).toUpperCase() || "AI",
    [displayName]
  );

  useEffect(() => {
    fetchTenantSettings();
    fetchCampaigns();
  }, [fetchTenantSettings]);

  const fetchCampaigns = async () => {
    setLoadingCampaigns(true);
    try {
      const res = await api.get("/campaigns");
      setCampaigns(res.data.campaigns);
    } catch (e) {
      console.error("Failed to load campaigns:", e);
    } finally {
      setLoadingCampaigns(false);
    }
  };

  const handleSyncNow = async () => {
    toast.promise(
      new Promise((resolve) => setTimeout(resolve, 1500)),
      {
        loading: "Syncing data pipelines...",
        success: "Multi-tenant sync complete!",
        error: "Sync failed.",
      }
    );
  };

  return (
    <div className="p-6 space-y-6 max-w-[1600px] mx-auto animate-in fade-in duration-500">
      {/* Agent Persona Hero Card */}
      <section className="bg-[#111113] border border-[#27272A] rounded-xl p-6 relative overflow-hidden group">
        <div className="absolute top-0 left-0 w-1 h-full bg-[#E8A020]" />
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="flex items-center gap-6">
            <div className="w-20 h-20 rounded-2xl bg-[#18181B] border border-[#27272A] flex items-center justify-center text-3xl font-bold text-[#E8A020] transition-transform duration-500 group-hover:scale-105 shadow-[0_0_15px_rgba(232,160,32,0.15)]">
              {initials}
            </div>
            <div>
              <h2 className="font-display-lg text-xl font-semibold text-[#e5e2e3]">
                {displayName} Persona
              </h2>
              <div className="flex items-center gap-4 mt-2">
                <div className="flex items-center gap-1.5 px-2 py-0.5 bg-green-500/10 rounded border border-green-500/20">
                  <span className="w-1.5 h-1.5 bg-green-500 rounded-full animate-pulse" />
                  <span className="font-data-mono text-[10px] text-green-400 uppercase font-bold tracking-tight">
                    Connected
                  </span>
                </div>
                <div className="flex items-center gap-2 text-xs text-[#d7c3ae]/70">
                  <span className="font-data-mono">
                    Gmail {integrations.gmail ? <span className="text-[#E8A020]">✓</span> : <span className="opacity-50">✗</span>}
                  </span>
                  <span className="text-[#27272A]">|</span>
                  <span className="font-data-mono">
                    Slack {integrations.slack ? <span className="text-[#E8A020]">✓</span> : <span className="opacity-50">✗</span>}
                  </span>
                </div>
              </div>
            </div>
          </div>
          <div className="flex flex-wrap gap-3">
            <button
              onClick={handleSyncNow}
              className="bg-[#E8A020] text-[#291800] h-10 w-10 rounded-lg font-bold hover:brightness-110 active:scale-[0.98] transition-all flex items-center justify-center text-sm cursor-pointer"
            >
              <Zap className="h-5 w-5" />
              <span className="sr-only">Sync Now</span>
            </button>
            <Link
              href="/settings"
              className="border border-[#27272A] text-[#e5e2e3] h-10 w-10 rounded-lg font-medium hover:bg-[#353436]/50 transition-all text-sm flex items-center justify-center"
            >
              <Settings className="h-5 w-5" />
              <span className="sr-only">Edit Persona</span>
            </Link>
          </div>
        </div>
      </section>

      {/* Stats Row (Bento Style) */}
      <section className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="bg-[#111113] border border-[#27272A] rounded-xl p-5 hover:bg-[#353436]/20 transition-all">
          <div className="flex items-center justify-between mb-3">
            <span className="font-label-caps text-label-caps text-[#d7c3ae]/70 uppercase text-xs">Customers Loaded</span>
            <Users className="h-5 w-5 text-[#E8A020]/50" />
          </div>
          <div className="font-data-mono text-2xl font-bold text-[#e5e2e3]">12,842</div>
          <div className="mt-2 flex items-center gap-1 min-h-[16px]">
            <span className="text-green-400 text-[10px] font-data-mono">+4.2%</span>
            <span className="text-[#d7c3ae]/40 text-[10px]">vs last month</span>
          </div>
        </div>

        <div className="bg-[#111113] border border-[#27272A] rounded-xl p-5 hover:bg-[#353436]/20 transition-all">
          <div className="flex items-center justify-between mb-3">
            <span className="font-label-caps text-label-caps text-[#d7c3ae]/70 uppercase text-xs">Campaigns Sent</span>
            <Rocket className="h-5 w-5 text-[#E8A020]/50" />
          </div>
          <div className="font-data-mono text-2xl font-bold text-[#e5e2e3]">
            {loadingCampaigns ? "..." : campaigns.length}
          </div>
          <div className="mt-2 flex items-center gap-1 min-h-[16px]">
            <span className="text-[#E8A020] text-[10px] font-data-mono">
              {campaigns.filter((c) => c.status === "active").length} Active
            </span>
            <span className="text-[#d7c3ae]/40 text-[10px]">concurrently</span>
          </div>
        </div>

        <div className="bg-[#111113] border border-[#27272A] rounded-xl p-5 hover:bg-[#353436]/20 transition-all">
          <div className="flex items-center justify-between mb-3">
            <span className="font-label-caps text-label-caps text-[#d7c3ae]/70 uppercase text-xs">Deliverability</span>
            <Mail className="h-5 w-5 text-[#E8A020]/50" />
          </div>
          <div className="font-data-mono text-2xl font-bold text-[#e5e2e3]">99.8%</div>
          <div className="mt-2 flex items-center gap-1 min-h-[16px]">
            <span className="text-green-400 text-[10px] font-data-mono">Active</span>
            <span className="text-[#d7c3ae]/40 text-[10px]">automated sequence</span>
          </div>
        </div>

        <div className="bg-[#111113] border border-[#27272A] rounded-xl p-5 hover:bg-[#353436]/20 transition-all">
          <div className="flex items-center justify-between mb-3">
            <span className="font-label-caps text-label-caps text-[#d7c3ae]/70 uppercase text-xs">Avg Churn Risk</span>
            <AlertTriangle className="h-5 w-5 text-[#E8A020]/50" />
          </div>
          <div className="font-data-mono text-2xl font-bold text-[#E8A020]">12.4%</div>
          <div className="mt-2 flex items-center gap-1 min-h-[16px]">
            <span className="text-red-400 text-[10px] font-data-mono">-2.1%</span>
            <span className="text-[#d7c3ae]/40 text-[10px]">lower than Q3</span>
          </div>
        </div>
      </section>

      {/* Campaign History Table Section */}
      <section className="bg-[#111113] border border-[#27272A] rounded-xl overflow-hidden">
        <div className="p-6 border-b border-[#27272A] flex items-center justify-between">
          <div>
            <h3 className="font-headline-md text-lg text-[#e5e2e3]">Campaign History</h3>
            <p className="text-xs text-[#d7c3ae]/50">Overview of recent outreach activities and performance</p>
          </div>
          <div className="flex gap-2">
            <button className="h-9 w-9 border border-[#27272A] rounded hover:bg-[#353436]/50 transition-colors flex items-center justify-center">
              <Filter className="h-4 w-4" />
              <span className="sr-only">Filter</span>
            </button>
            <button className="h-9 w-9 border border-[#27272A] rounded hover:bg-[#353436]/50 transition-colors flex items-center justify-center">
              <Download className="h-4 w-4" />
              <span className="sr-only">Download</span>
            </button>
            <button
              onClick={fetchCampaigns}
              className="h-9 w-9 border border-[#27272A] rounded hover:bg-[#353436]/50 transition-colors flex items-center justify-center"
            >
              <RefreshCw className="h-4 w-4" />
              <span className="sr-only">Refresh</span>
            </button>
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="bg-[#0e0e0f]/50">
                <th className="px-6 py-4 font-label-caps text-[#d7c3ae] uppercase tracking-wider">Name</th>
                <th className="px-6 py-4 font-label-caps text-[#d7c3ae] uppercase tracking-wider">Type</th>
                <th className="px-6 py-4 font-label-caps text-[#d7c3ae] uppercase tracking-wider">Status</th>
                <th className="px-6 py-4 font-label-caps text-[#d7c3ae] uppercase tracking-wider text-right">Emails Sent</th>
                <th className="px-6 py-4 font-label-caps text-[#d7c3ae] uppercase tracking-wider text-right">Date</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#27272A]/30">
              {loadingCampaigns ? (
                <tr>
                  <td colSpan={5} className="text-center py-8 font-data-mono text-[#d7c3ae]/40">
                    Querying database records...
                  </td>
                </tr>
              ) : campaigns.length === 0 ? (
                <tr>
                  <td colSpan={5} className="text-center py-8 font-data-mono text-[#d7c3ae]/40">
                    No campaign records found. Chat with {displayName} to launch one!
                  </td>
                </tr>
              ) : (
                campaigns.map((c) => (
                  <tr
                    key={c.id}
                    className="hover:bg-[#1A1A1C] transition-all duration-200 group cursor-pointer hover:translate-x-1"
                  >
                    <td className="px-6 py-4">
                      <div className="font-bold text-[#e5e2e3] group-hover:text-[#E8A020] transition-colors">
                        {c.name}
                      </div>
                      <div className="text-[10px] text-[#d7c3ae]/40 font-data-mono">
                        ID: {c.id.substring(0, 8).toUpperCase()}
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <span className="text-[#e5e2e3] uppercase tracking-tighter text-[10px]">
                        {c.type}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <div className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-[#E8A020]/10 border border-[#E8A020]/20">
                        <span className="w-1 h-1 bg-[#E8A020] rounded-full" />
                        <span className="font-data-mono text-[9px] text-[#E8A020] uppercase font-bold">
                          {c.status || "active"}
                        </span>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-right font-data-mono text-[#e5e2e3]">
                      {c.emails_sent ?? "—"}
                    </td>
                    <td className="px-6 py-4 text-right text-[#d7c3ae]/70">
                      {new Date(c.created_at).toLocaleDateString()}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
        <div className="p-4 bg-[#0e0e0f]/30 border-t border-[#27272A] flex items-center justify-between text-[10px] font-data-mono text-[#d7c3ae]/50">
          <span>Showing {campaigns.length} Campaigns</span>
          <div className="flex gap-2">
            <button className="h-7 w-7 border border-[#27272A] rounded hover:bg-[#353436]/50 transition-all flex items-center justify-center">
              <ChevronLeft className="h-4 w-4" />
              <span className="sr-only">Previous</span>
            </button>
            <button className="h-7 w-7 border border-[#27272A] rounded hover:bg-[#353436]/50 transition-all flex items-center justify-center">
              <ChevronRight className="h-4 w-4" />
              <span className="sr-only">Next</span>
            </button>
          </div>
        </div>
      </section>

      {/* Activity Feed & AI Insights */}
      <section className="grid grid-cols-1 xl:grid-cols-3 gap-6 pb-6">
        <div className="xl:col-span-2 bg-[#111113] border border-[#27272A] rounded-xl p-6">
          <h4 className="font-headline-md text-lg text-[#e5e2e3] mb-6">Recent Activity</h4>
          <div className="space-y-6">
            <div className="flex gap-4">
              <div className="w-2 mt-2 h-2 rounded-full bg-[#d7c3ae]/30 flex-shrink-0" />
              <div>
                <p className="text-sm font-medium text-[#e5e2e3]">Campaign "Enterprise Lead Gen" reached 1,000 deliveries</p>
                <p className="text-[10px] mt-1 font-data-mono uppercase tracking-wider">
                  <span className="text-[#d7c3ae]/60">2 minutes ago • </span>
                  <span className="text-[#E8A020] font-bold">System</span>
                </p>
              </div>
            </div>
            <div className="flex gap-4">
              <div className="w-2 mt-2 h-2 rounded-full bg-[#d7c3ae]/30 flex-shrink-0" />
              <div>
                <p className="text-sm font-medium text-[#e5e2e3]">{displayName} synced 420 new leads from LinkedIn Sales Nav</p>
                <p className="text-[10px] mt-1 font-data-mono uppercase tracking-wider">
                  <span className="text-[#d7c3ae]/60">45 minutes ago • </span>
                  <span className="text-[#E8A020] font-bold">Agent Persona</span>
                </p>
              </div>
            </div>
            <div className="flex gap-4">
              <div className="w-2 mt-2 h-2 rounded-full bg-[#d7c3ae]/30 flex-shrink-0" />
              <div>
                <p className="text-sm font-medium text-[#e5e2e3]">Billing cycle completed. Invoice INV-2023-098 issued.</p>
                <p className="text-[10px] mt-1 font-data-mono uppercase tracking-wider">
                  <span className="text-[#d7c3ae]/60">3 hours ago • </span>
                  <span className="text-[#E8A020] font-bold">Billing</span>
                </p>
              </div>
            </div>
          </div>
        </div>

        <div className="bg-[#111113] border border-[#27272A] rounded-xl p-6 relative">
          <div className="absolute top-0 left-0 w-1 h-full bg-[#3ac2ff]" />
          <div className="flex items-center gap-2 mb-4">
            <Sparkles className="h-5 w-5 text-[#3ac2ff]" />
            <h4 className="font-headline-md text-lg text-[#e5e2e3]">Smart Insight</h4>
          </div>
          <p className="text-sm mb-4 leading-relaxed text-[#e5e2e3]">
            <span className="text-[#E8A020] font-bold">Churn Risk Alert:</span> Accounts in the "Basic" tier have shown a 15% drop in login frequency over the last 7 days.
          </p>
          <div className="bg-[#0e0e0f] p-4 rounded border border-[#27272A] border-dashed">
            <p className="text-xs font-semibold mb-2 text-[#e5e2e3]">{displayName}&apos;s Recommendation:</p>
            <p className="text-xs text-[#d7c3ae]/70 italic">
              &quot;I can draft a personal check-in sequence for the top 20 at-risk accounts. Should I proceed?&quot;
            </p>
            <Link
              href="/chat"
              className="mt-4 w-full py-2 bg-[#e5e2e3] text-[#0A0A0B] font-bold rounded hover:opacity-90 transition-all text-xs flex items-center justify-center cursor-pointer"
            >
              <CheckCircle2 className="h-4 w-4" />
              <span className="sr-only">Approve and Act</span>
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}
