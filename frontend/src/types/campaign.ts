export interface Campaign {
  id: string;
  name: string;
  type: string;
  description?: string;
  status: "draft" | "active" | "completed";
  created_at: string;
}

export interface CampaignEmail {
  id: number;
  campaign_id: string;
  customer_id?: number;
  email: string;
  subject: string;
  body: string;
  sent_at: string;
  status: string;
  opened: boolean;
}
