"use client";

import React, { useRef, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import axios from "axios";
import { api } from "@/lib/api";
import { useAuthStore } from "@/store/auth-store";
import { useTenantStore } from "@/store/tenant-store";
import {
  ArrowLeft,
  Bot,
  Building2,
  CheckCircle2,
  ChevronRight,
  FileUp,
  SlidersHorizontal,
  Sparkles,
  ScrollText,
  X,
  Trash2,
  Loader2,
  AlertCircle,
  FileText,
} from "lucide-react";
import toast from "react-hot-toast";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type FileUploadStatus = "pending" | "uploading" | "mapping" | "confirming" | "done" | "error";

interface UploadedFile {
  id: string;
  file: File;
  status: FileUploadStatus;
  progress: number;
  error?: string;
  // Results from /csv/upload
  uploadSessionId?: string;
  sourceType?: string;
  joinKey?: string | null;
  totalRows?: number;
  mappedColumns?: Record<string, string>;
  droppedColumns?: string[];
  reasoning?: string;
  // Results from /csv/confirm
  customersInserted?: number;
  customersUpdated?: number;
  totalCustomers?: number;
}

const getErrorMessage = (error: unknown, fallback: string) => {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    return typeof detail === "string" ? detail : fallback;
  }
  return error instanceof Error ? error.message : fallback;
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

interface OnboardingFlowProps {
  initialOrgName?: string;
  initialAgentName?: string;
  initialBackstory?: string;
  initialTone?: string;
  initialSchemaDef?: Record<string, unknown> | null;
  onComplete?: () => void;
  onCancel?: () => void;
  completeLabel?: string;
}

export default function OnboardingFlow({
  initialOrgName = "BandhanAI",
  initialAgentName = "Ralph",
  initialBackstory = "",
  initialTone = "Professional, helpful, and data-driven.",
  initialSchemaDef = null,
  onComplete,
  onCancel,
  completeLabel = "Complete Onboarding",
}: OnboardingFlowProps) {
  const router = useRouter();
  const setOrgId = useAuthStore((state) => state.setOrgId);
  const setSettings = useTenantStore((state) => state.setSettings);

  const [step, setStep] = useState(1);
  const [orgName, setOrgName] = useState(initialOrgName);
  const [agentName, setAgentName] = useState(initialAgentName);
  const [backstory, setBackstory] = useState(initialBackstory);
  const [tone, setTone] = useState(initialTone);
  const [saving, setSaving] = useState(false);

  // Multi-file upload state
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([]);
  const [isDragActive, setIsDragActive] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Check if any file completed successfully
  const hasSuccessfulUpload = uploadedFiles.some((f) => f.status === "done");
  const isAnyProcessing = uploadedFiles.some(
    (f) => f.status === "uploading" || f.status === "mapping" || f.status === "confirming"
  );

  // ------- Step 1: Agent Persona -------

  const handleStep1Submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!orgName.trim() || !agentName.trim()) {
      toast.error("Organization name and agent name are required.");
      return;
    }

    setSaving(true);
    try {
      toast.loading("Configuring your agent workspace...", { id: "onboarding-step1" });
      const res = await api.post("/auth/register-tenant", {
        org_name: orgName,
        agent_name: agentName,
        backstory,
        tone_instructions: tone,
      });

      toast.success("Agent persona saved.", { id: "onboarding-step1" });
      setOrgId(res.data.org_id);
      setSettings({
        orgName,
        agentName,
        backstory,
        toneInstructions: tone,
      });
      setStep(2);
    } catch (e: unknown) {
      toast.error(getErrorMessage(e, "Setup failed. Please try again."), {
        id: "onboarding-step1",
      });
    } finally {
      setSaving(false);
    }
  };

  // ------- Step 2: Multi-File CSV Upload -------

  const updateFile = useCallback(
    (id: string, updates: Partial<UploadedFile>) => {
      setUploadedFiles((prev) =>
        prev.map((f) => (f.id === id ? { ...f, ...updates } : f))
      );
    },
    []
  );

  const processFile = useCallback(
    async (uploadEntry: UploadedFile) => {
      const { id, file } = uploadEntry;

      // Step 1+2: Upload + LLM schema detection
      updateFile(id, { status: "uploading", progress: 20 });

      try {
        const formData = new FormData();
        formData.append("file", file);

        updateFile(id, { status: "mapping", progress: 50 });

        const uploadRes = await api.post("/csv/upload", formData, {
          headers: { "Content-Type": "multipart/form-data" },
        });

        const {
          upload_session_id,
          source_type,
          join_key,
          total_rows,
          mapped_columns,
          dropped_columns,
          reasoning,
        } = uploadRes.data;

        updateFile(id, {
          status: "confirming",
          progress: 75,
          uploadSessionId: upload_session_id,
          sourceType: source_type,
          joinKey: join_key,
          totalRows: total_rows,
          mappedColumns: mapped_columns,
          droppedColumns: dropped_columns,
          reasoning: reasoning,
        });

        // Step 4+5: Auto-confirm (accept LLM mapping as-is)
        const confirmRes = await api.post("/csv/confirm", {
          upload_session_id,
        });

        updateFile(id, {
          status: "done",
          progress: 100,
          customersInserted: confirmRes.data.customers_inserted,
          customersUpdated: confirmRes.data.customers_updated,
          totalCustomers: confirmRes.data.total_customers,
        });

        toast.success(`${file.name} imported successfully.`);
      } catch (err: unknown) {
        const msg = getErrorMessage(err, `Failed to process ${file.name}`);
        updateFile(id, { status: "error", progress: 0, error: msg });
        toast.error(msg);
      }
    },
    [updateFile]
  );

  const addFiles = useCallback(
    (files: FileList | File[]) => {
      const newEntries: UploadedFile[] = [];

      for (const file of Array.from(files)) {
        if (!file.name.toLowerCase().endsWith(".csv")) {
          toast.error(`${file.name} is not a CSV file. Skipped.`);
          continue;
        }

        // Prevent duplicate filenames
        const alreadyAdded = uploadedFiles.some(
          (f) => f.file.name === file.name && f.status !== "error"
        );
        if (alreadyAdded) {
          toast.error(`${file.name} is already added.`);
          continue;
        }

        const entry: UploadedFile = {
          id: crypto.randomUUID(),
          file,
          status: "pending",
          progress: 0,
        };

        newEntries.push(entry);
      }

      if (newEntries.length === 0) return;

      setUploadedFiles((prev) => [...prev, ...newEntries]);

      // Process each new file
      for (const entry of newEntries) {
        processFile(entry);
      }
    },
    [uploadedFiles, processFile]
  );

  const removeFile = useCallback((id: string) => {
    setUploadedFiles((prev) => prev.filter((f) => f.id !== id));
  }, []);

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragActive(e.type === "dragenter" || e.type === "dragover");
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragActive(false);

    if (e.dataTransfer.files?.length) {
      addFiles(e.dataTransfer.files);
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files?.length) {
      addFiles(e.target.files);
      // Reset input so the same file can be selected again
      e.target.value = "";
    }
  };

  const handleCompleteSetup = () => {
    toast.success("Agent setup complete.");
    if (onComplete) {
      onComplete();
      return;
    }
    router.push("/dashboard");
  };

  // ------- Status helpers -------

  const statusLabel = (status: FileUploadStatus): string => {
    switch (status) {
      case "pending":
        return "Queued";
      case "uploading":
        return "Uploading...";
      case "mapping":
        return "AI mapping columns...";
      case "confirming":
        return "Importing data...";
      case "done":
        return "Imported";
      case "error":
        return "Failed";
    }
  };

  const statusColor = (status: FileUploadStatus): string => {
    switch (status) {
      case "done":
        return "text-emerald-400";
      case "error":
        return "text-red-400";
      default:
        return "text-[#E8A020]";
    }
  };

  // ------- Render -------

  return (
    <div className="w-full max-w-[800px] z-10 space-y-6">
      <div>
        <div className="flex items-center justify-between mb-4 gap-4">
          <div className="flex flex-col">
            <span className="font-label-caps text-label-caps text-[#E8A020] mb-1 uppercase tracking-widest">
              {step === 1 ? "Setup Configuration" : "Data Integration"}
            </span>
            <h1 className="font-display-lg text-2xl font-bold">
              {step === 1 ? "Agent Persona" : "Customer Import"}
            </h1>
          </div>
          <div className="flex items-center gap-3">
            <span className="font-data-mono text-data-mono text-[#d7c3ae]/70">
              STEP 0{step} / 02
            </span>
            {onCancel && (
              <button
                onClick={onCancel}
                className="text-[#d7c3ae]/70 hover:text-[#e5e2e3] transition-colors"
                type="button"
                aria-label="Close onboarding setup"
              >
                <X className="h-5 w-5" />
              </button>
            )}
          </div>
        </div>
        <div className="h-1 w-full bg-[#353436] rounded-full overflow-hidden">
          <div
            className="h-full bg-[#E8A020] transition-all duration-500 ease-in-out"
            style={{ width: step === 1 ? "50%" : "100%" }}
          />
        </div>
      </div>

      <div className="bg-[#111113]/85 backdrop-blur-md border border-[#27272A] rounded-xl p-8 flex flex-col min-h-[480px]">
        {step === 1 ? (
          <form onSubmit={handleStep1Submit} className="flex-1 flex flex-col gap-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <label className="block font-label-caps text-label-caps text-[#d7c3ae] uppercase">
                  Organization Name
                </label>
                <div className="relative">
                  <Building2 className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[#E8A020]" />
                  <input
                    type="text"
                    required
                    placeholder="e.g. Bandhan Retails"
                    value={orgName}
                    onChange={(e) => setOrgName(e.target.value)}
                    className="w-full bg-[#09090B] border border-[#27272A] rounded p-3 pl-10 text-sm focus:outline-none focus:border-[#E8A020] focus:ring-1 focus:ring-[#E8A020] transition-all"
                  />
                </div>
              </div>
              <div className="space-y-2">
                <label className="block font-label-caps text-label-caps text-[#d7c3ae] uppercase">
                  Agent Persona Name
                </label>
                <div className="relative">
                  <Bot className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[#E8A020]" />
                  <input
                    type="text"
                    required
                    placeholder="e.g. Priya"
                    value={agentName}
                    onChange={(e) => setAgentName(e.target.value)}
                    className="w-full bg-[#09090B] border border-[#27272A] rounded p-3 pl-10 text-sm focus:outline-none focus:border-[#E8A020] focus:ring-1 focus:ring-[#E8A020] transition-all"
                  />
                </div>
              </div>
            </div>

            <div className="space-y-2 flex-grow flex flex-col">
              <label className="flex items-center gap-2 font-label-caps text-label-caps text-[#d7c3ae] uppercase">
                <ScrollText className="h-3.5 w-3.5 text-[#E8A020]" />
                Backstory & Domain Context
              </label>
              <div className="relative flex-grow flex">
                <Sparkles className="absolute left-4 top-4 h-4 w-4 text-[#E8A020]" />
                <textarea
                  required
                  placeholder="Describe the agent's personality, domain expertise, and how it should respond to customers."
                  value={backstory}
                  onChange={(e) => setBackstory(e.target.value)}
                  className="w-full flex-grow bg-[#09090B] border border-[#27272A] rounded p-4 pl-11 text-sm focus:outline-none focus:border-[#E8A020] focus:ring-1 focus:ring-[#E8A020] transition-all resize-none min-h-[160px]"
                />
              </div>
            </div>

            <div className="space-y-2">
              <label className="flex items-center gap-2 font-label-caps text-label-caps text-[#d7c3ae] uppercase">
                <SlidersHorizontal className="h-3.5 w-3.5 text-[#E8A020]" />
                Agent Tone Guidelines
              </label>
              <div className="relative">
                <SlidersHorizontal className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[#E8A020]" />
                <input
                  type="text"
                  required
                  value={tone}
                  onChange={(e) => setTone(e.target.value)}
                  className="w-full bg-[#09090B] border border-[#27272A] rounded p-3 pl-10 text-sm focus:outline-none focus:border-[#E8A020] focus:ring-1 focus:ring-[#E8A020] transition-all"
                />
              </div>
            </div>

            <div className="flex justify-end pt-4 border-t border-[#27272A]/50">
              <button
                type="submit"
                disabled={saving}
                className="bg-[#E8A020] text-[#291800] px-8 py-3 rounded font-bold hover:brightness-110 active:scale-[0.98] transition-all flex items-center gap-2 cursor-pointer disabled:opacity-60"
              >
                <span>{saving ? "Saving..." : "Save & Continue"}</span>
                <ChevronRight className="h-4 w-4" />
              </button>
            </div>
          </form>
        ) : (
          <div className="flex-1 flex flex-col gap-5">
            {/* Drop zone — always visible */}
            <div
              onDragEnter={handleDrag}
              onDragOver={handleDrag}
              onDragLeave={handleDrag}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              className={`border-2 border-dashed rounded-xl p-6 flex flex-col items-center justify-center bg-[#0e0e0f] cursor-pointer transition-all duration-300 group ${
                uploadedFiles.length > 0 ? "min-h-[140px]" : "min-h-[200px]"
              } ${
                isDragActive
                  ? "border-[#E8A020] bg-[#E8A020]/10"
                  : "border-[#27272A] hover:border-[#E8A020] hover:bg-[#E8A020]/5"
              } ${isAnyProcessing ? "pointer-events-none opacity-70" : ""}`}
            >
              <input
                type="file"
                ref={fileInputRef}
                className="hidden"
                accept=".csv"
                multiple
                onChange={handleFileSelect}
              />
              <div className="mb-2 flex h-10 w-10 items-center justify-center rounded bg-[#2a2a2b] border border-[#27272A] text-[#E8A020] transition-colors group-hover:border-[#E8A020]/50 group-hover:bg-[#E8A020]/10">
                <FileUp className="h-5 w-5" />
              </div>
              <p className="font-headline-md text-sm text-[#d7c3ae] group-hover:text-[#e5e2e3]">
                {uploadedFiles.length > 0 ? "Add more CSV files" : "Upload CSV files"}
              </p>
              <p className="text-xs text-[#d7c3ae]/50 mt-1">
                Drag & drop or click to select — multiple files supported
              </p>
            </div>

            {/* File cards */}
            {uploadedFiles.length > 0 && (
              <div className="space-y-3 max-h-[320px] overflow-y-auto pr-1 custom-scrollbar">
                {uploadedFiles.map((entry) => (
                  <div
                    key={entry.id}
                    className={`bg-[#0e0e0f] border rounded-lg p-4 transition-all duration-300 ${
                      entry.status === "done"
                        ? "border-emerald-500/30"
                        : entry.status === "error"
                        ? "border-red-500/30"
                        : "border-[#27272A]"
                    }`}
                  >
                    {/* Header row */}
                    <div className="flex items-center justify-between gap-3">
                      <div className="flex items-center gap-3 min-w-0">
                        <div
                          className={`flex-shrink-0 h-9 w-9 rounded flex items-center justify-center ${
                            entry.status === "done"
                              ? "bg-emerald-500/10 text-emerald-400"
                              : entry.status === "error"
                              ? "bg-red-500/10 text-red-400"
                              : "bg-[#2a2a2b] text-[#E8A020]"
                          }`}
                        >
                          {entry.status === "done" ? (
                            <CheckCircle2 className="h-4 w-4" />
                          ) : entry.status === "error" ? (
                            <AlertCircle className="h-4 w-4" />
                          ) : entry.status === "pending" ? (
                            <FileText className="h-4 w-4" />
                          ) : (
                            <Loader2 className="h-4 w-4 animate-spin" />
                          )}
                        </div>
                        <div className="min-w-0">
                          <p className="text-sm font-semibold text-[#e5e2e3] truncate">
                            {entry.file.name}
                          </p>
                          <p className={`text-xs font-mono ${statusColor(entry.status)}`}>
                            {statusLabel(entry.status)}
                            {entry.totalRows != null && entry.status !== "error" && (
                              <span className="text-[#d7c3ae]/50 ml-2">
                                {entry.totalRows.toLocaleString()} rows
                              </span>
                            )}
                          </p>
                        </div>
                      </div>

                      {/* Remove button */}
                      {(entry.status === "done" || entry.status === "error") && (
                        <button
                          onClick={() => removeFile(entry.id)}
                          className="text-[#d7c3ae]/40 hover:text-red-400 transition-colors flex-shrink-0"
                          type="button"
                          aria-label={`Remove ${entry.file.name}`}
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      )}
                    </div>

                    {/* Progress bar (while processing) */}
                    {entry.status !== "done" && entry.status !== "error" && entry.progress > 0 && (
                      <div className="mt-3">
                        <div className="h-1 w-full bg-[#353436] rounded-full overflow-hidden">
                          <div
                            className="bg-[#E8A020] h-full transition-all duration-500 ease-out"
                            style={{ width: `${entry.progress}%` }}
                          />
                        </div>
                      </div>
                    )}

                    {/* Error message */}
                    {entry.status === "error" && entry.error && (
                      <p className="mt-2 text-xs text-red-400/80 font-mono">{entry.error}</p>
                    )}

                    {/* Success summary */}
                    {entry.status === "done" && (
                      <div className="mt-3 flex items-center gap-4 text-xs font-mono text-[#d7c3ae]/70">
                        {entry.customersInserted != null && (
                          <span>
                            <span className="text-emerald-400 font-bold">
                              {entry.customersInserted}
                            </span>{" "}
                            inserted
                          </span>
                        )}
                        {(entry.customersUpdated ?? 0) > 0 && (
                          <span>
                            <span className="text-[#E8A020] font-bold">
                              {entry.customersUpdated}
                            </span>{" "}
                            updated
                          </span>
                        )}
                        {entry.totalCustomers != null && (
                          <span className="ml-auto text-[#d7c3ae]/50">
                            Total: {entry.totalCustomers.toLocaleString()}
                          </span>
                        )}
                      </div>
                    )}

                    {/* Schema mapping preview (collapsible detail for done files) */}
                    {entry.status === "done" && entry.mappedColumns && (
                      <details className="mt-3 group/detail">
                        <summary className="text-xs text-[#d7c3ae]/50 cursor-pointer hover:text-[#E8A020] transition-colors select-none">
                          View column mapping ({Object.keys(entry.mappedColumns).length} fields)
                        </summary>
                        <div className="mt-2 bg-[#111113] border border-[#27272A] rounded overflow-hidden">
                          <table className="w-full text-left border-collapse">
                            <thead>
                              <tr className="bg-[#201f20] border-b border-[#27272A]">
                                <th className="p-2 font-label-caps text-[10px] text-[#d7c3ae] uppercase">
                                  Source Column
                                </th>
                                <th className="p-2 font-label-caps text-[10px] text-[#d7c3ae] uppercase">
                                  Mapped To
                                </th>
                              </tr>
                            </thead>
                            <tbody className="font-data-mono text-xs text-[#e5e2e3]">
                              {Object.entries(entry.mappedColumns).map(([orig, semantic]) => (
                                <tr
                                  key={orig}
                                  className="border-b border-[#27272A]/30 hover:bg-[#353436]/20"
                                >
                                  <td className="p-2 text-[#d7c3ae]">{orig}</td>
                                  <td className="p-2">
                                    <span className="px-1.5 py-0.5 bg-[#2a2a2b] border border-[#27272A] rounded text-[#E8A020] text-[10px] font-bold">
                                      {semantic}
                                    </span>
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </details>
                    )}
                  </div>
                ))}
              </div>
            )}

            {/* Footer */}
            <div className="mt-auto pt-5 border-t border-[#27272A]/50 flex justify-between items-center">
              <button
                onClick={() => setStep(1)}
                className="text-[#d7c3ae] hover:text-[#e5e2e3] font-bold text-xs uppercase flex items-center gap-2 cursor-pointer"
                type="button"
              >
                <ArrowLeft className="h-4 w-4" />
                Back
              </button>

              <button
                onClick={handleCompleteSetup}
                disabled={!hasSuccessfulUpload || isAnyProcessing}
                className="bg-[#E8A020] text-[#291800] px-8 py-3 rounded font-bold hover:brightness-110 active:scale-[0.98] transition-all flex items-center gap-2 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
                type="button"
              >
                <span>{isAnyProcessing ? "Processing..." : completeLabel}</span>
                {isAnyProcessing ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <CheckCircle2 className="h-4 w-4" />
                )}
              </button>
            </div>
          </div>
        )}
      </div>

      <div className="flex items-center gap-4 p-4 border-l-2 border-[#E8A020] bg-[#0e0e0f]/50 rounded-r">
        <Sparkles className="h-5 w-5 shrink-0 text-[#E8A020]" />
        <p className="font-body-sm text-xs text-[#d7c3ae] italic">
          &quot;I will calibrate your dynamic CRM schemas and construct your agent persona using these
          inputs.&quot; <span className="text-[#E8A020] font-bold">{agentName}AI</span>
        </p>
      </div>
    </div>
  );
}
