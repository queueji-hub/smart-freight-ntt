-- Phase 30: Profitability / Job Cost tenant-safe contract.
-- Additive only; existing cost and profit records are preserved.

ALTER TABLE job_costs
    ADD COLUMN IF NOT EXISTS tenant_id TEXT DEFAULT 'default',
    ADD COLUMN IF NOT EXISTS cost_status TEXT DEFAULT 'ESTIMATED';

ALTER TABLE profit_sheets
    ADD COLUMN IF NOT EXISTS tenant_id TEXT DEFAULT 'default';

UPDATE job_costs
SET tenant_id = 'default'
WHERE tenant_id IS NULL OR btrim(tenant_id) = '';

UPDATE job_costs
SET cost_status = 'ESTIMATED'
WHERE cost_status IS NULL OR btrim(cost_status) = '';

UPDATE profit_sheets
SET tenant_id = 'default'
WHERE tenant_id IS NULL OR btrim(tenant_id) = '';

CREATE INDEX IF NOT EXISTS idx_job_costs_tenant_shipment
    ON job_costs(tenant_id, shipment_id);

CREATE INDEX IF NOT EXISTS idx_job_costs_tenant_status
    ON job_costs(tenant_id, cost_type, cost_status);

CREATE INDEX IF NOT EXISTS idx_profit_sheets_tenant_shipment
    ON profit_sheets(tenant_id, shipment_id);
