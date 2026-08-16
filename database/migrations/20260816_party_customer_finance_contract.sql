-- Phase 30 production contract: canonical Customer/Party finance controls.
-- Additive/idempotent. No historical columns are removed.

ALTER TABLE customers ADD COLUMN IF NOT EXISTS tenant_id TEXT DEFAULT 'default';
ALTER TABLE customers ADD COLUMN IF NOT EXISTS customer_code VARCHAR(5);
ALTER TABLE customers ADD COLUMN IF NOT EXISTS display_name TEXT;
ALTER TABLE customers ADD COLUMN IF NOT EXISTS billing_name TEXT;
ALTER TABLE customers ADD COLUMN IF NOT EXISTS billing_address TEXT;
ALTER TABLE customers ADD COLUMN IF NOT EXISTS billing_country_code VARCHAR(2);
ALTER TABLE customers ADD COLUMN IF NOT EXISTS credit_limit NUMERIC(18,2) DEFAULT 0;
ALTER TABLE customers ADD COLUMN IF NOT EXISTS credit_currency VARCHAR(3) DEFAULT 'THB';
ALTER TABLE customers ADD COLUMN IF NOT EXISTS payment_term_code TEXT;
ALTER TABLE customers ADD COLUMN IF NOT EXISTS credit_status TEXT DEFAULT 'NORMAL';
ALTER TABLE customers ADD COLUMN IF NOT EXISTS credit_hold BOOLEAN DEFAULT FALSE;
ALTER TABLE customers ADD COLUMN IF NOT EXISTS updated_by TEXT;

UPDATE customers
SET tenant_id='default'
WHERE tenant_id IS NULL OR btrim(tenant_id)='';

UPDATE customers
SET display_name=company_name
WHERE display_name IS NULL OR btrim(display_name)='';

UPDATE customers
SET billing_name=company_name
WHERE billing_name IS NULL OR btrim(billing_name)='';

CREATE UNIQUE INDEX IF NOT EXISTS uq_customers_tenant_code
ON customers(tenant_id, customer_code)
WHERE customer_code IS NOT NULL AND btrim(customer_code)<>'';

CREATE INDEX IF NOT EXISTS idx_customers_tenant_active
ON customers(tenant_id, is_active);

CREATE INDEX IF NOT EXISTS idx_customers_tenant_due_control
ON customers(tenant_id, credit_status, credit_hold);

ALTER TABLE users ADD COLUMN IF NOT EXISTS tenant_id TEXT DEFAULT 'default';
UPDATE users SET tenant_id='default' WHERE tenant_id IS NULL OR btrim(tenant_id)='';
CREATE INDEX IF NOT EXISTS idx_users_tenant_role ON users(tenant_id, role, is_active);

ALTER TABLE invoices ADD COLUMN IF NOT EXISTS tenant_id TEXT DEFAULT 'default';
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS payment_term_code TEXT;
UPDATE invoices SET tenant_id='default' WHERE tenant_id IS NULL OR btrim(tenant_id)='';
CREATE INDEX IF NOT EXISTS idx_invoices_tenant_customer_due
ON invoices(tenant_id, customer_id, due_date);

ALTER TABLE ap_vouchers ADD COLUMN IF NOT EXISTS payment_term_code TEXT;
CREATE INDEX IF NOT EXISTS idx_ap_vouchers_tenant_due
ON ap_vouchers(tenant_id, vendor_id, due_date);
