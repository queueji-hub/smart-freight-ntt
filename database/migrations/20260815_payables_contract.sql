-- Phase 30: Payables/Vendor contract required by vendor_manager.py and ap_manager.py.
-- Additive only; no historical data is removed.

CREATE TABLE IF NOT EXISTS vendors (
    id SERIAL PRIMARY KEY,
    tenant_id TEXT NOT NULL DEFAULT 'default',
    vendor_code TEXT NOT NULL,
    legal_name TEXT NOT NULL,
    tax_id TEXT,
    country TEXT,
    currency TEXT DEFAULT 'THB',
    status TEXT DEFAULT 'Active',
    created_by TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (tenant_id, vendor_code)
);

CREATE INDEX IF NOT EXISTS idx_vendors_tenant_name
    ON vendors(tenant_id, legal_name);

CREATE TABLE IF NOT EXISTS ap_vouchers (
    id SERIAL PRIMARY KEY,
    tenant_id TEXT NOT NULL DEFAULT 'default',
    vendor_id INTEGER NOT NULL REFERENCES vendors(id),
    job_no TEXT,
    invoice_no TEXT NOT NULL,
    invoice_date DATE,
    due_date DATE,
    currency TEXT DEFAULT 'THB',
    exchange_rate NUMERIC(15,6) DEFAULT 1,
    subtotal NUMERIC(15,2) DEFAULT 0,
    tax NUMERIC(15,2) DEFAULT 0,
    total NUMERIC(15,2) DEFAULT 0,
    status TEXT DEFAULT 'DRAFT',
    created_by TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_ap_vouchers_tenant_job
    ON ap_vouchers(tenant_id, job_no);

CREATE INDEX IF NOT EXISTS idx_ap_vouchers_tenant_status
    ON ap_vouchers(tenant_id, status);
