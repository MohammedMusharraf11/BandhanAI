"use client";

import React, { useEffect, useState } from "react";
import axios from "axios";
import { api } from "@/lib/api";
import OnboardingFlow from "@/components/onboarding/onboarding-flow";
import { useTenantStore } from "@/store/tenant-store";
import { Bot, Database, Edit3, Link2 } from "lucide-react";
import toast from "react-hot-toast";

const getErrorMessage = (error: unknown, fallback: string) => {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    return typeof detail === "string" ? detail : fallback;
  }

  return error instanceof Error ? error.message : fallback;
};

export default function SettingsPage() {
  const {
    orgName,
    agentName,
    backstory,
    toneInstructions,
    schemaDef,
    integrations,
    fetchTenantSettings,
  } = useTenantStore();

  const [showPersonaEditor, setShowPersonaEditor] = useState(false);

  useEffect(() => {
    fetchTenantSettings();
  }, [fetchTenantSettings]);

  const handleConnectGmail = async () => {
    try {
      toast.loading("Initiating Google Secure Connect...", { id: "oauth" });
      const res = await api.get("/auth/gmail/connect");
      toast.success("Redirecting to Google authorization...", { id: "oauth" });
      window.location.href = res.data.auth_url;
    } catch (e: unknown) {
      toast.error(getErrorMessage(e, "Failed to trigger Gmail OAuth connection."), {
        id: "oauth",
      });
    }
  };

  const handleConnectSlack = async () => {
    try {
      toast.loading("Initiating Slack App Connect...", { id: "oauth" });
      const res = await api.get("/auth/slack/connect");
      toast.success("Redirecting to Slack authorization...", { id: "oauth" });
      window.location.href = res.data.auth_url;
    } catch (e: unknown) {
      toast.error(getErrorMessage(e, "Failed to trigger Slack OAuth connection."), {
        id: "oauth",
      });
    }
  };

  const handlePersonaComplete = async () => {
    setShowPersonaEditor(false);
    await fetchTenantSettings();
  };

  return (
    <>
      <div className="p-6 pb-12 max-w-4xl mx-auto space-y-8 animate-in fade-in duration-500">
        <div>
          <h2 className="font-display-lg text-2xl font-bold text-[#e5e2e3]">
            Workspace Settings
          </h2>
          <p className="text-xs text-[#d7c3ae]/70 mt-1">
            Manage your agent persona, customer schema, and external communication tools.
          </p>
        </div>

        <div className="grid grid-cols-1 gap-6">
          <section className="bg-[#111113] border border-[#27272A] rounded-xl p-6">
            <div className="flex items-start justify-between gap-6">
              <div>
                <h3 className="font-headline-md text-sm font-bold text-[#e5e2e3] mb-2 flex items-center gap-2">
                  <Bot className="h-4 w-4 text-[#E8A020]" />
                  Agent Persona
                </h3>
                <p className="text-xs text-[#d7c3ae]/60 max-w-xl">
                  {agentName} is configured as the active growth partner for {orgName}.
                </p>
                {backstory && (
                  <p className="text-xs text-[#d7c3ae]/70 mt-3 line-clamp-2">{backstory}</p>
                )}
              </div>
              <button
                onClick={() => setShowPersonaEditor(true)}
                className="shrink-0 bg-[#E8A020] text-[#291800] px-5 py-2.5 rounded font-bold hover:brightness-110 active:scale-[0.98] transition-all text-xs cursor-pointer flex items-center gap-2"
                type="button"
              >
                <Edit3 className="h-4 w-4" />
                Edit agent persona
              </button>
            </div>

            <div className="mt-5 grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="bg-[#0e0e0f] border border-[#27272A] rounded p-4">
                <p className="font-label-caps text-label-caps text-[#d7c3ae]/70 uppercase">
                  Agent Name
                </p>
                <p className="text-sm font-bold text-[#e5e2e3] mt-1">{agentName}</p>
              </div>
              <div className="bg-[#0e0e0f] border border-[#27272A] rounded p-4">
                <p className="font-label-caps text-label-caps text-[#d7c3ae]/70 uppercase">
                  Tone Guidelines
                </p>
                <p className="text-sm text-[#e5e2e3] mt-1">
                  {toneInstructions || "Not configured"}
                </p>
              </div>
            </div>
          </section>

          <section className="bg-[#111113] border border-[#27272A] rounded-xl p-6">
            <h3 className="font-headline-md text-sm font-bold text-[#e5e2e3] mb-2 flex items-center gap-2">
              <Link2 className="h-4 w-4 text-[#E8A020]" />
              Tools & Integrations
            </h3>
            <p className="text-xs text-[#d7c3ae]/50 mb-6">
              Authorized accounts are securely encrypted at rest.
            </p>

            <div className="space-y-4">
              <div className="bg-[#0e0e0f] border border-[#27272A] p-4 flex items-center justify-between hover:bg-[#353436]/10 transition-colors rounded-lg gap-4">
                <div className="flex items-center gap-4">
                  <div className="w-10 h-10 rounded bg-[#1c1b1c] border border-[#27272A] flex items-center justify-center font-bold text-[#E8A020]">
                    G
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <h4 className="font-bold text-[#e5e2e3]">Google Gmail Integration</h4>
                      {integrations.gmail ? (
                        <span className="bg-green-500/10 text-green-400 px-2 py-0.5 rounded text-[9px] font-data-mono uppercase font-bold border border-green-500/20">
                          Connected
                        </span>
                      ) : (
                        <span className="bg-[#2a2a2b] text-[#d7c3ae]/50 px-2 py-0.5 rounded text-[9px] font-data-mono uppercase font-bold border border-[#27272A]">
                          Disconnected
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-[#d7c3ae]/70 mt-1">
                      Allows {agentName} to compose and dispatch campaign sequences via Gmail.
                    </p>
                  </div>
                </div>
                {integrations.gmail ? (
                  <button
                    disabled
                    className="px-4 py-2 border border-[#27272A] text-green-400/40 rounded text-xs font-semibold"
                    type="button"
                  >
                    Linked
                  </button>
                ) : (
                  <button
                    onClick={handleConnectGmail}
                    className="px-4 py-2 bg-[#E8A020] text-[#291800] rounded font-bold hover:brightness-110 active:scale-[0.98] transition-all text-xs cursor-pointer"
                    type="button"
                  >
                    Connect
                  </button>
                )}
              </div>

              <div className="bg-[#0e0e0f] border border-[#27272A] p-4 flex items-center justify-between hover:bg-[#353436]/10 transition-colors rounded-lg gap-4">
                <div className="flex items-center gap-4">
                  <div className="w-10 h-10 rounded bg-[#1c1b1c] border border-[#27272A] flex items-center justify-center font-bold text-[#E8A020]">
                    S
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <h4 className="font-bold text-[#e5e2e3]">Slack Workspace Bot</h4>
                      {integrations.slack ? (
                        <span className="bg-green-500/10 text-green-400 px-2 py-0.5 rounded text-[9px] font-data-mono uppercase font-bold border border-green-500/20">
                          Connected
                        </span>
                      ) : (
                        <span className="bg-[#2a2a2b] text-[#d7c3ae]/50 px-2 py-0.5 rounded text-[9px] font-data-mono uppercase font-bold border border-[#27272A]">
                          Disconnected
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-[#d7c3ae]/70 mt-1">
                      Allows {agentName} to push campaign alerts and summaries into Slack.
                    </p>
                  </div>
                </div>
                {integrations.slack ? (
                  <button
                    disabled
                    className="px-4 py-2 border border-[#27272A] text-green-400/40 rounded text-xs font-semibold"
                    type="button"
                  >
                    Linked
                  </button>
                ) : (
                  <button
                    onClick={handleConnectSlack}
                    className="px-4 py-2 bg-[#E8A020] text-[#291800] rounded font-bold hover:brightness-110 active:scale-[0.98] transition-all text-xs cursor-pointer"
                    type="button"
                  >
                    Connect
                  </button>
                )}
              </div>
            </div>
          </section>

          {schemaDef && (
            <section className="bg-[#111113] border border-[#27272A] rounded-xl p-6">
              <h3 className="font-headline-md text-sm font-bold text-[#e5e2e3] mb-4 flex items-center gap-2">
                <Database className="h-4 w-4 text-[#E8A020]" />
                CRM Database Schema
              </h3>

              <div className="bg-[#0e0e0f] border border-[#27272A] rounded overflow-hidden">
                <table className="w-full text-left border-collapse text-xs">
                  <thead className="bg-[#201f20]">
                    <tr className="border-b border-[#27272A]">
                      <th className="p-3 font-label-caps text-[#d7c3ae] uppercase">
                        Spreadsheet Header
                      </th>
                      <th className="p-3 font-label-caps text-[#d7c3ae] uppercase">
                        Mapped Semantic Type
                      </th>
                      <th className="p-3 font-label-caps text-[#d7c3ae] uppercase">
                        AI Column Purpose
                      </th>
                    </tr>
                  </thead>
                  <tbody className="font-data-mono text-[11px] text-[#e5e2e3] divide-y divide-[#27272A]/50">
                    {Object.entries(schemaDef).map(([col, field]) => (
                      <tr key={col}>
                        <td className="p-3 font-bold">{col}</td>
                        <td className="p-3">
                          <span className="px-2 py-0.5 bg-[#E8A020]/15 text-[#E8A020] rounded border border-[#E8A020]/30 font-bold uppercase text-[10px]">
                            {field.canonical_type}
                          </span>
                        </td>
                        <td className="p-3 text-[#d7c3ae]/70">{field.description}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          )}
        </div>
      </div>

      {showPersonaEditor && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-start justify-center overflow-y-auto p-6">
          <div className="w-full min-h-full flex items-center justify-center py-8">
            <OnboardingFlow
              initialOrgName={orgName}
              initialAgentName={agentName}
              initialBackstory={backstory}
              initialTone={toneInstructions || "Professional, helpful, and data-driven."}
              initialSchemaDef={schemaDef}
              onCancel={() => setShowPersonaEditor(false)}
              onComplete={handlePersonaComplete}
              completeLabel="Save setup"
            />
          </div>
        </div>
      )}
    </>
  );
}
