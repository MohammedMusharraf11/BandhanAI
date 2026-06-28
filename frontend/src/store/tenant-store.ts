import { create } from "zustand";
import { api } from "@/lib/api";
import { SchemaField } from "@/types/tenant";

interface TenantSettings {
  orgName: string;
  agentName: string;
  backstory: string;
  toneInstructions: string;
  schemaDef: Record<string, SchemaField> | null;
  integrations: {
    gmail: boolean;
    slack: boolean;
  };
  loading: boolean;
  fetchTenantSettings: () => Promise<void>;
  setSettings: (settings: Partial<TenantSettings>) => void;
}

export const useTenantStore = create<TenantSettings>((set) => ({
  orgName: "BandhanAI",
  agentName: "Ralph",
  backstory: "",
  toneInstructions: "",
  schemaDef: null,
  integrations: {
    gmail: false,
    slack: false,
  },
  loading: false,
  fetchTenantSettings: async () => {
    set({ loading: true });
    try {
      const res = await api.get("/settings/integrations");
      set({
        orgName: res.data.org_name || "BandhanAI",
        agentName: res.data.agent_name,
        backstory: res.data.backstory,
        toneInstructions: res.data.tone_instructions,
        schemaDef: res.data.schema_def,
        integrations: res.data.integrations,
      });
    } catch (e) {
      console.error("Failed to fetch tenant settings:", e);
    } finally {
      set({ loading: false });
    }
  },
  setSettings: (settings) => set((state) => ({ ...state, ...settings })),
}));
