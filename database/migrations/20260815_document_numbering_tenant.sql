-- Phase 30: tenant-safe document numbering.
-- The numbering service already expects tenant_id in document_counters.
-- This migration makes the production schema match that contract.

ALTER TABLE document_counters
    ADD COLUMN IF NOT EXISTS tenant_id TEXT DEFAULT 'default';

UPDATE document_counters
SET tenant_id = 'default'
WHERE tenant_id IS NULL OR btrim(tenant_id) = '';

ALTER TABLE document_counters
    DROP CONSTRAINT IF EXISTS document_counters_pkey;

ALTER TABLE document_counters
    ADD CONSTRAINT document_counters_pkey
    PRIMARY KEY (tenant_id, doc_type, yymm);

CREATE INDEX IF NOT EXISTS idx_document_counters_tenant
    ON document_counters(tenant_id, doc_type, yymm);
