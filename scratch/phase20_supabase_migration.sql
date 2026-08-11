-- =========================================================
-- PHASE 20: SUPABASE PRODUCTION SCHEMA MIGRATION
-- Safely applies D74-D90 additions to a Pre-D74 Database
-- =========================================================

-- 1. Document Management Tables
CREATE TABLE IF NOT EXISTS documents (
    id SERIAL PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    document_no TEXT NOT NULL,
    document_type TEXT NOT NULL,
    document_category TEXT NOT NULL,
    document_date TEXT,
    description TEXT,
    status TEXT DEFAULT 'Draft',
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by TEXT
);
CREATE INDEX IF NOT EXISTS idx_documents_tenant ON documents(tenant_id);
CREATE INDEX IF NOT EXISTS idx_documents_no ON documents(document_no);

CREATE TABLE IF NOT EXISTS document_versions (
    id SERIAL PRIMARY KEY,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL,
    original_file_name TEXT NOT NULL,
    mime_type TEXT,
    file_size INTEGER,
    storage_key TEXT NOT NULL,
    storage_provider TEXT DEFAULT 'LOCAL',
    file_hash TEXT,
    uploaded_by TEXT,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_doc_versions_doc_id ON document_versions(document_id);

CREATE TABLE IF NOT EXISTS document_links (
    id SERIAL PRIMARY KEY,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by TEXT
);
CREATE INDEX IF NOT EXISTS idx_doc_links_doc_id ON document_links(document_id);
CREATE INDEX IF NOT EXISTS idx_doc_links_entity ON document_links(entity_type, entity_id);

CREATE TABLE IF NOT EXISTS document_counters (
    tenant_id TEXT NOT NULL,
    prefix TEXT NOT NULL,
    yymm TEXT NOT NULL,
    last_running INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (tenant_id, prefix, yymm)
);

-- 2. New Operational & Physical Document Tables
CREATE TABLE IF NOT EXISTS shipment_milestones (
    id SERIAL PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    shipment_id INTEGER REFERENCES shipments(id),
    milestone_code TEXT,
    milestone_name TEXT,
    planned_date TIMESTAMP,
    actual_date TIMESTAMP,
    status TEXT DEFAULT 'PENDING',
    responsible_user TEXT,
    remarks TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS regulatory_submissions (
    id SERIAL PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    submission_type TEXT,
    country TEXT,
    authority TEXT,
    job_no TEXT,
    hbl_no TEXT,
    mbl_no TEXT,
    container_no TEXT,
    submission_reference TEXT,
    submission_date TIMESTAMP,
    cut_off_date TIMESTAMP,
    submitted_by TEXT,
    status TEXT DEFAULT 'DRAFT',
    response TEXT,
    error_msg TEXT,
    version INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS transport_orders (
    id SERIAL PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    transport_order_no TEXT UNIQUE NOT NULL,
    order_type TEXT DEFAULT 'TRUCKING',
    job_no TEXT,
    customer_name TEXT,
    vendor_name TEXT,
    pickup_location TEXT,
    delivery_location TEXT,
    pickup_time TIMESTAMP,
    delivery_time TIMESTAMP,
    truck_type TEXT,
    vehicle_no TEXT,
    driver_name TEXT,
    container_no TEXT,
    cargo_details TEXT,
    special_instructions TEXT,
    status TEXT DEFAULT 'DRAFT',
    pod_received BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS physical_documents (
    id SERIAL PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    job_no TEXT,
    document_type TEXT,
    is_original BOOLEAN DEFAULT TRUE,
    quantity INTEGER DEFAULT 1,
    received_from TEXT,
    received_date TIMESTAMP,
    storage_location TEXT,
    released_to TEXT,
    released_date TIMESTAMP,
    courier_name TEXT,
    tracking_no TEXT,
    returned_date TIMESTAMP,
    destroyed_date TIMESTAMP,
    barcode TEXT,
    remarks TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Finance & Sales
CREATE TABLE IF NOT EXISTS commissions (
    id SERIAL PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    job_no TEXT,
    sales_person TEXT,
    basis TEXT,
    rate NUMERIC(5,2),
    commission_amount NUMERIC(15,2),
    status TEXT DEFAULT 'DRAFT',
    calculated_at TIMESTAMP,
    approved_by TEXT,
    paid_at TIMESTAMP,
    remarks TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS vendors (
    id SERIAL PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    vendor_code TEXT UNIQUE NOT NULL,
    vendor_name TEXT NOT NULL,
    tax_id TEXT,
    address TEXT,
    contact_name TEXT,
    contact_email TEXT,
    contact_phone TEXT,
    payment_terms_days INTEGER DEFAULT 30,
    status TEXT DEFAULT 'ACTIVE',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ap_vouchers (
    id SERIAL PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    voucher_no TEXT UNIQUE NOT NULL,
    vendor_id INTEGER REFERENCES vendors(id),
    job_no TEXT,
    voucher_date DATE,
    due_date DATE,
    currency TEXT DEFAULT 'THB',
    exchange_rate NUMERIC(10,5) DEFAULT 1.00000,
    subtotal NUMERIC(15,2) DEFAULT 0,
    vat_amount NUMERIC(15,2) DEFAULT 0,
    wht_amount NUMERIC(15,2) DEFAULT 0,
    total_amount NUMERIC(15,2) DEFAULT 0,
    status TEXT DEFAULT 'DRAFT',
    remarks TEXT,
    created_by TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. Audit & Logs
CREATE TABLE IF NOT EXISTS email_log (
    id SERIAL PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    job_no TEXT,
    sender TEXT,
    recipient TEXT,
    subject TEXT,
    status TEXT,
    error_msg TEXT,
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS document_templates (
    id SERIAL PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    template_code TEXT UNIQUE NOT NULL,
    template_name TEXT NOT NULL,
    document_type TEXT NOT NULL,
    content_html TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 5. Safe Column Alterations
ALTER TABLE shipments ADD COLUMN IF NOT EXISTS reporting_date DATE;
ALTER TABLE shipments ADD COLUMN IF NOT EXISTS reporting_month TEXT;
ALTER TABLE shipments ADD COLUMN IF NOT EXISTS reporting_year TEXT;
ALTER TABLE shipments ADD COLUMN IF NOT EXISTS financial_status TEXT DEFAULT 'Open';
ALTER TABLE shipments ADD COLUMN IF NOT EXISTS document_status TEXT;
ALTER TABLE shipments ADD COLUMN IF NOT EXISTS mode TEXT DEFAULT 'Sea';
ALTER TABLE shipments ADD COLUMN IF NOT EXISTS closed_at TIMESTAMP;
ALTER TABLE shipments ADD COLUMN IF NOT EXISTS closed_by TEXT;

ALTER TABLE job_costs ADD COLUMN IF NOT EXISTS cost_status TEXT DEFAULT 'ESTIMATED';
