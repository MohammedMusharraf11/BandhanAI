-- ============================================================================
-- Migration 002: Add org_id to Existing Tables + RLS Policies
-- Run AFTER migration 001_tenants.sql
-- ============================================================================

-- NOTE: If your tables already have data, you must first:
--   1. Create a default tenant row in public.tenants
--   2. Add the column as nullable: ALTER TABLE public.crm ADD COLUMN org_id UUID;
--   3. Backfill: UPDATE public.crm SET org_id = '<your-default-org-id>';
--   4. Then set NOT NULL: ALTER TABLE public.crm ALTER COLUMN org_id SET NOT NULL;
-- The statements below assume the tables are empty or have been backfilled.

-- Add org_id to crm
ALTER TABLE public.crm
    ADD COLUMN IF NOT EXISTS org_id UUID NOT NULL REFERENCES public.tenants(org_id);

-- Add org_id to marketing_campaigns
ALTER TABLE public.marketing_campaigns
    ADD COLUMN IF NOT EXISTS org_id UUID NOT NULL REFERENCES public.tenants(org_id);

-- Add org_id to campaigning_emails
ALTER TABLE public.campaigning_emails
    ADD COLUMN IF NOT EXISTS org_id UUID NOT NULL REFERENCES public.tenants(org_id);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_crm_org_id ON public.crm(org_id);
CREATE INDEX IF NOT EXISTS idx_campaigns_org_id ON public.marketing_campaigns(org_id);
CREATE INDEX IF NOT EXISTS idx_emails_org_id ON public.campaigning_emails(org_id);

-- Enable RLS and create policies
ALTER TABLE public.crm ENABLE ROW LEVEL SECURITY;
CREATE POLICY crm_tenant_policy ON public.crm
    FOR ALL USING (
        org_id IN (SELECT org_id FROM tenants WHERE owner_auth_uid = auth.uid())
    );

ALTER TABLE public.marketing_campaigns ENABLE ROW LEVEL SECURITY;
CREATE POLICY campaigns_tenant_policy ON public.marketing_campaigns
    FOR ALL USING (
        org_id IN (SELECT org_id FROM tenants WHERE owner_auth_uid = auth.uid())
    );

ALTER TABLE public.campaigning_emails ENABLE ROW LEVEL SECURITY;
CREATE POLICY emails_tenant_policy ON public.campaigning_emails
    FOR ALL USING (
        org_id IN (SELECT org_id FROM tenants WHERE owner_auth_uid = auth.uid())
    );
