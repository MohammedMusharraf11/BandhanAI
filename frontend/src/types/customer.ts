export interface Customer {
  customer_id: number;
  org_id: string;
  email?: string;
  data: Record<string, any>;
  created_at: string;
}
