-- SMART FREIGHT NTT: master-data consistency migration
-- Safe for PostgreSQL. Run once against the production database before using
-- tenant-aware Customer/Job selectors.

ALTER TABLE IF EXISTS customers
    ADD COLUMN IF NOT EXISTS tenant_id TEXT DEFAULT 'default';

ALTER TABLE IF EXISTS shipments
    ADD COLUMN IF NOT EXISTS tenant_id TEXT DEFAULT 'default';

CREATE INDEX IF NOT EXISTS idx_customers_tenant_company
    ON customers (tenant_id, company_name);

CREATE INDEX IF NOT EXISTS idx_shipments_tenant_job
    ON shipments (tenant_id, job_no);

-- Keep existing rows usable in the current single-tenant deployment.
UPDATE customers SET tenant_id = COALESCE(NULLIF(tenant_id, ''), 'default') WHERE tenant_id IS NULL OR tenant_id = '';
UPDATE shipments SET tenant_id = COALESCE(NULLIF(tenant_id, ''), 'default') WHERE tenant_id IS NULL OR tenant_id = '';

-- Canonical operational terminology going forward:
-- carrier = carrier/liner master value
-- vessel  = mother vessel value
-- feeder  = not used as a second vessel master field
-- UI should stop writing duplicate legacy values unless an existing PDF/DB
-- compatibility path explicitly requires them.
