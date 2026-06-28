-- ============================================================================
-- Migration 004: CSV Pipeline Tables + Customers Unique Constraint
-- Run AFTER migration 003_customers.sql
-- ============================================================================

-- Tracks every CSV file uploaded by a tenant
CREATE TABLE IF NOT EXISTS public.data_sources (
  source_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id uuid NOT NULL REFERENCES public.tenants(org_id) ON DELETE CASCADE,
  file_name text NOT NULL,
  source_type text,
  row_count integer,
  status text DEFAULT 'processing',
  error_message text,
  uploaded_at timestamp DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_data_sources_org_id ON public.data_sources(org_id);

-- Stores the LLM column mapping decision for each upload
CREATE TABLE IF NOT EXISTS public.schema_mappings (
  mapping_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  source_id uuid NOT NULL REFERENCES public.data_sources(source_id) ON DELETE CASCADE,
  org_id uuid NOT NULL REFERENCES public.tenants(org_id) ON DELETE CASCADE,
  original_columns jsonb NOT NULL,
  mapped_columns jsonb NOT NULL,
  join_key text,
  dropped_columns jsonb,
  created_at timestamp DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_schema_mappings_org_id ON public.schema_mappings(org_id);
CREATE INDEX IF NOT EXISTS idx_schema_mappings_source_id ON public.schema_mappings(source_id);

-- Unique constraint on customers for email-based upsert deduplication
-- This allows: INSERT ... ON CONFLICT (org_id, email) DO UPDATE
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'customers_org_email_unique'
  ) THEN
    ALTER TABLE public.customers
      ADD CONSTRAINT customers_org_email_unique UNIQUE (org_id, email);
  END IF;
END $$;
