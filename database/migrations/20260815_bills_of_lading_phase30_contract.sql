-- Phase 30: Bills of Lading tenant/workflow contract.
-- Additive and idempotent; preserves existing B/L records.

CREATE TABLE IF NOT EXISTS bills_of_lading (
    id SERIAL PRIMARY KEY,
    tenant_id TEXT DEFAULT 'default',
    bl_no TEXT,
    job_no TEXT,
    shipment_id INTEGER,
    booking_no TEXT,
    shipper TEXT,
    consignee TEXT,
    notify_party TEXT,
    place_of_receipt TEXT,
    port_of_loading TEXT,
    port_of_discharge TEXT,
    place_of_delivery TEXT,
    final_destination TEXT,
    vessel TEXT,
    voyage TEXT,
    etd DATE,
    eta DATE,
    bl_date DATE,
    place_of_issue TEXT,
    number_of_originals INTEGER DEFAULT 3,
    freight_term TEXT,
    freight_payable_at TEXT,
    marks_numbers TEXT,
    package_qty NUMERIC(15,2) DEFAULT 0,
    package_type TEXT,
    description_of_goods TEXT,
    gross_weight NUMERIC(15,3) DEFAULT 0,
    measurement_cbm NUMERIC(15,3) DEFAULT 0,
    hs_code TEXT,
    remarks TEXT,
    special_instructions TEXT,
    bl_type TEXT DEFAULT 'HBL',
    status TEXT DEFAULT 'Draft',
    approval_status TEXT DEFAULT 'Draft',
    created_by TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE bills_of_lading
    ADD COLUMN IF NOT EXISTS tenant_id TEXT DEFAULT 'default',
    ADD COLUMN IF NOT EXISTS bl_no TEXT,
    ADD COLUMN IF NOT EXISTS job_no TEXT,
    ADD COLUMN IF NOT EXISTS shipment_id INTEGER,
    ADD COLUMN IF NOT EXISTS booking_no TEXT,
    ADD COLUMN IF NOT EXISTS shipper TEXT,
    ADD COLUMN IF NOT EXISTS consignee TEXT,
    ADD COLUMN IF NOT EXISTS notify_party TEXT,
    ADD COLUMN IF NOT EXISTS place_of_receipt TEXT,
    ADD COLUMN IF NOT EXISTS port_of_loading TEXT,
    ADD COLUMN IF NOT EXISTS port_of_discharge TEXT,
    ADD COLUMN IF NOT EXISTS place_of_delivery TEXT,
    ADD COLUMN IF NOT EXISTS final_destination TEXT,
    ADD COLUMN IF NOT EXISTS vessel TEXT,
    ADD COLUMN IF NOT EXISTS voyage TEXT,
    ADD COLUMN IF NOT EXISTS etd DATE,
    ADD COLUMN IF NOT EXISTS eta DATE,
    ADD COLUMN IF NOT EXISTS bl_date DATE,
    ADD COLUMN IF NOT EXISTS place_of_issue TEXT,
    ADD COLUMN IF NOT EXISTS number_of_originals INTEGER DEFAULT 3,
    ADD COLUMN IF NOT EXISTS freight_term TEXT,
    ADD COLUMN IF NOT EXISTS freight_payable_at TEXT,
    ADD COLUMN IF NOT EXISTS marks_numbers TEXT,
    ADD COLUMN IF NOT EXISTS package_qty NUMERIC(15,2) DEFAULT 0,
    ADD COLUMN IF NOT EXISTS package_type TEXT,
    ADD COLUMN IF NOT EXISTS description_of_goods TEXT,
    ADD COLUMN IF NOT EXISTS gross_weight NUMERIC(15,3) DEFAULT 0,
    ADD COLUMN IF NOT EXISTS measurement_cbm NUMERIC(15,3) DEFAULT 0,
    ADD COLUMN IF NOT EXISTS hs_code TEXT,
    ADD COLUMN IF NOT EXISTS remarks TEXT,
    ADD COLUMN IF NOT EXISTS special_instructions TEXT,
    ADD COLUMN IF NOT EXISTS bl_type TEXT DEFAULT 'HBL',
    ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'Draft',
    ADD COLUMN IF NOT EXISTS approval_status TEXT DEFAULT 'Draft',
    ADD COLUMN IF NOT EXISTS created_by TEXT,
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

UPDATE bills_of_lading
SET tenant_id = 'default'
WHERE tenant_id IS NULL OR btrim(tenant_id) = '';

CREATE INDEX IF NOT EXISTS idx_bills_of_lading_tenant_job
    ON bills_of_lading(tenant_id, job_no);

CREATE INDEX IF NOT EXISTS idx_bills_of_lading_tenant_created
    ON bills_of_lading(tenant_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_bills_of_lading_tenant_bl_no
    ON bills_of_lading(tenant_id, bl_no);
