export interface Tenant {
  org_id: string;
  owner_email: string;
  owner_auth_uid: string;
  org_name: string;
  agent_name: string;
  backstory?: string;
  tone_instructions?: string;
  schema_def?: Record<string, SchemaField>;
  created_at: string;
}

export interface SchemaField {
  canonical_type: string;
  description: string;
}

export interface Integrations {
  gmail: boolean;
  slack: boolean;
}
