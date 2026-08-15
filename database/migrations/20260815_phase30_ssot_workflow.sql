-- Phase 30: additive SSOT/workflow compatibility migration.
-- Existing text columns are intentionally retained for legacy records.
-- New writes should populate *_id columns; text remains a compatibility/display field.

ALTER TABLE quotations
    ADD COLUMN IF NOT EXISTS customer_id BIGINT,
    ADD COLUMN IF NOT EXISTS sales_id BIGINT,
    ADD COLUMN IF NOT EXISTS approval_status TEXT DEFAULT 'Draft';

ALTER TABLE bookings
    ADD COLUMN IF NOT EXISTS sales_id BIGINT,
    ADD COLUMN IF NOT EXISTS approval_status TEXT DEFAULT 'Draft';

ALTER TABLE invoices
    ADD COLUMN IF NOT EXISTS tenant_id TEXT DEFAULT 'default',
    ADD COLUMN IF NOT EXISTS approval_status TEXT DEFAULT 'Draft';

ALTER TABLE bills_of_lading
    ADD COLUMN IF NOT EXISTS tenant_id TEXT DEFAULT 'default',
    ADD COLUMN IF NOT EXISTS approval_status TEXT DEFAULT 'Draft';

CREATE INDEX IF NOT EXISTS idx_quotations_tenant_customer
    ON quotations(tenant_id, customer_id);

CREATE INDEX IF NOT EXISTS idx_quotations_tenant_sales
    ON quotations(tenant_id, sales_id);

CREATE INDEX IF NOT EXISTS idx_bookings_tenant_customer
    ON bookings(tenant_id, customer_id);

CREATE INDEX IF NOT EXISTS idx_bookings_tenant_sales
    ON bookings(tenant_id, sales_id);

CREATE INDEX IF NOT EXISTS idx_invoices_tenant_customer
    ON invoices(tenant_id, customer_id);

CREATE INDEX IF NOT EXISTS idx_bills_of_lading_tenant_job
    ON bills_of_lading(tenant_id, job_no);

UPDATE quotations
SET approval_status = 'Draft'
WHERE approval_status IS NULL OR btrim(approval_status) = '';

UPDATE bookings
SET approval_status = 'Draft'
WHERE approval_status IS NULL OR btrim(approval_status) = '';

UPDATE invoices
SET approval_status = 'Draft'
WHERE approval_status IS NULL OR btrim(approval_status) = '';

UPDATE bills_of_lading
SET approval_status = 'Draft'
WHERE approval_status IS NULL OR btrim(approval_status) = '';
