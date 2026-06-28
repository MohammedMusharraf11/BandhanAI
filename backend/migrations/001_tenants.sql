-- ============================================================================
-- Migration 001: Tenants & Integrations Tables
-- Run this migration FIRST before any other migrations.
-- ============================================================================

-- Master tenant record — one row per business owner
CREATE TABLE IF NOT EXISTS public.tenants (
    org_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_email TEXT NOT NULL UNIQUE,
    owner_auth_uid UUID NOT NULL UNIQUE,  -- maps to Supabase auth.users.id
    org_name TEXT NOT NULL,
    agent_name TEXT DEFAULT 'Ralph',
    backstory TEXT,
    tone_instructions TEXT,
    schema_def JSONB,                      -- populated by CSV upload (Phase 5)
    created_at TIMESTAMP DEFAULT now()
);

-- Integration credentials (encrypted with Fernet)
CREATE TABLE IF NOT EXISTS public.integrations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL UNIQUE REFERENCES public.tenants(org_id) ON DELETE CASCADE,
    gmail_access_token TEXT,       -- Fernet-encrypted
    gmail_refresh_token TEXT,      -- Fernet-encrypted
    gmail_token_expiry TIMESTAMP,
    slack_bot_token TEXT,          -- Fernet-encrypted
    slack_team_id TEXT,
    connected_at TIMESTAMP DEFAULT now()
);

-- RLS for tenants: owner can only see their own row
ALTER TABLE public.tenants ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenants_owner_policy ON public.tenants
    FOR ALL USING (owner_auth_uid = auth.uid());

-- RLS for integrations: scoped via tenant ownership
ALTER TABLE public.integrations ENABLE ROW LEVEL SECURITY;
CREATE POLICY integrations_owner_policy ON public.integrations
    FOR ALL USING (
        org_id IN (SELECT org_id FROM tenants WHERE owner_auth_uid = auth.uid())
    );
