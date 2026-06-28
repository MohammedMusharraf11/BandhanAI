-- ============================================================================
-- Migration 003: Dynamic Customer Data Table (JSONB)
-- Run AFTER migration 001_tenants.sql
-- ============================================================================

-- Dynamic customer data storage using JSONB
-- This table stores uploaded CSV customer data with flexible schema.
-- The actual column meanings are stored in tenants.schema_def (JSONB).
CREATE TABLE IF NOT EXISTS public.customers (
    customer_id BIGSERIAL PRIMARY KEY,
    org_id UUID NOT NULL REFERENCES public.tenants(org_id) ON DELETE CASCADE,
    email TEXT,           -- extracted from the JSONB data & indexed for fast lookup
    data JSONB NOT NULL,  -- all customer fields as a JSON blob
    created_at TIMESTAMP DEFAULT now()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_customers_org_id ON public.customers(org_id);
CREATE INDEX IF NOT EXISTS idx_customers_email ON public.customers(org_id, email);
CREATE INDEX IF NOT EXISTS idx_customers_data_gin ON public.customers USING GIN (data);

-- RLS
ALTER TABLE public.customers ENABLE ROW LEVEL SECURITY;
CREATE POLICY customers_tenant_policy ON public.customers
    FOR ALL USING (
        org_id IN (SELECT org_id FROM tenants WHERE owner_auth_uid = auth.uid())
    );
