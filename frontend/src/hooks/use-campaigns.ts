import { useState, useEffect } from "react";
import { api } from "@/lib/api";

export function useCampaigns() {
  const [campaigns, setCampaigns] = useState([]);
  const [loading, setLoading] = useState(false);

  const fetchCampaigns = async () => {
    setLoading(true);
    try {
      const res = await api.get("/campaigns");
      setCampaigns(res.data.campaigns);
    } catch (e) {
      console.error("Failed to load campaigns inside hook:", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCampaigns();
  }, []);

  return { campaigns, loading, refetch: fetchCampaigns };
}
