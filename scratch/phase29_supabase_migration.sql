-- =========================================================
-- PHASE 29: SUPABASE PRODUCTION SCHEMA RECONCILIATION
-- Idempotent, safe, and non-destructive schema additions
-- =========================================================

-- 1. Alter existing tables to add tenant_id columns safely
ALTER TABLE bookings ADD COLUMN IF NOT EXISTS tenant_id TEXT DEFAULT 'default';
ALTER TABLE quotations ADD COLUMN IF NOT EXISTS tenant_id TEXT DEFAULT 'default';

-- 2. Add missing columns to bookings table
ALTER TABLE bookings ADD COLUMN IF NOT EXISTS vessel TEXT;
ALTER TABLE bookings ADD COLUMN IF NOT EXISTS voyage TEXT;
ALTER TABLE bookings ADD COLUMN IF NOT EXISTS package_qty INTEGER;
ALTER TABLE bookings ADD COLUMN IF NOT EXISTS package_unit TEXT;
ALTER TABLE bookings ADD COLUMN IF NOT EXISTS measurement_cbm NUMERIC(15,2);
ALTER TABLE bookings ADD COLUMN IF NOT EXISTS gross_weight NUMERIC(15,2);
ALTER TABLE bookings ADD COLUMN IF NOT EXISTS container_summary TEXT;
ALTER TABLE bookings ADD COLUMN IF NOT EXISTS freight_term TEXT;
ALTER TABLE bookings ADD COLUMN IF NOT EXISTS quotation_no TEXT;
ALTER TABLE bookings ADD COLUMN IF NOT EXISTS job_no TEXT;
ALTER TABLE bookings ADD COLUMN IF NOT EXISTS revision_no INTEGER DEFAULT 0;
ALTER TABLE bookings ADD COLUMN IF NOT EXISTS is_current INTEGER DEFAULT 1;
ALTER TABLE bookings ADD COLUMN IF NOT EXISTS previous_booking_id INTEGER;
ALTER TABLE bookings ADD COLUMN IF NOT EXISTS revision_reason TEXT;
ALTER TABLE bookings ADD COLUMN IF NOT EXISTS revised_by TEXT;
ALTER TABLE bookings ADD COLUMN IF NOT EXISTS revised_at TIMESTAMP;

-- 3. Add missing columns to quotations table
ALTER TABLE quotations ADD COLUMN IF NOT EXISTS customer_address TEXT;
ALTER TABLE quotations ADD COLUMN IF NOT EXISTS customer_email TEXT;
ALTER TABLE quotations ADD COLUMN IF NOT EXISTS salesperson TEXT;
ALTER TABLE quotations ADD COLUMN IF NOT EXISTS shipper TEXT;
ALTER TABLE quotations ADD COLUMN IF NOT EXISTS consignee TEXT;
ALTER TABLE quotations ADD COLUMN IF NOT EXISTS origin TEXT;
ALTER TABLE quotations ADD COLUMN IF NOT EXISTS destination TEXT;
ALTER TABLE quotations ADD COLUMN IF NOT EXISTS freight_term TEXT;
ALTER TABLE quotations ADD COLUMN IF NOT EXISTS hs_code TEXT;
ALTER TABLE quotations ADD COLUMN IF NOT EXISTS quantity NUMERIC(15,2) DEFAULT 0;
ALTER TABLE quotations ADD COLUMN IF NOT EXISTS package_type TEXT;
ALTER TABLE quotations ADD COLUMN IF NOT EXISTS weight_kg NUMERIC(15,2) DEFAULT 0;
ALTER TABLE quotations ADD COLUMN IF NOT EXISTS volume_cbm NUMERIC(15,2) DEFAULT 0;
ALTER TABLE quotations ADD COLUMN IF NOT EXISTS container_type TEXT;
ALTER TABLE quotations ADD COLUMN IF NOT EXISTS container_quantity INTEGER DEFAULT 0;
ALTER TABLE quotations ADD COLUMN IF NOT EXISTS is_dg BOOLEAN DEFAULT FALSE;
ALTER TABLE quotations ADD COLUMN IF NOT EXISTS customer_id INTEGER REFERENCES customers(id);

-- 4. Add missing columns to quotation_items table
ALTER TABLE quotation_items ADD COLUMN IF NOT EXISTS basis TEXT;
ALTER TABLE quotation_items ADD COLUMN IF NOT EXISTS quantity NUMERIC(15,3) DEFAULT 1;
ALTER TABLE quotation_items ADD COLUMN IF NOT EXISTS unit_rate NUMERIC(15,2) DEFAULT 0;
ALTER TABLE quotation_items ADD COLUMN IF NOT EXISTS amount NUMERIC(15,2) DEFAULT 0;

-- 5. Add missing columns to shipments table
ALTER TABLE shipments ADD COLUMN IF NOT EXISTS place_of_receipt TEXT;
ALTER TABLE shipments ADD COLUMN IF NOT EXISTS transshipment_port TEXT;
ALTER TABLE shipments ADD COLUMN IF NOT EXISTS place_of_delivery TEXT;
ALTER TABLE shipments ADD COLUMN IF NOT EXISTS vessel TEXT;
ALTER TABLE shipments ADD COLUMN IF NOT EXISTS voyage TEXT;
ALTER TABLE shipments ADD COLUMN IF NOT EXISTS freight_term TEXT;
ALTER TABLE shipments ADD COLUMN IF NOT EXISTS package_quantity INTEGER;
ALTER TABLE shipments ADD COLUMN IF NOT EXISTS package_type TEXT;
ALTER TABLE shipments ADD COLUMN IF NOT EXISTS cbm NUMERIC(15,2);
ALTER TABLE shipments ADD COLUMN IF NOT EXISTS gross_weight NUMERIC(15,2);
ALTER TABLE shipments ADD COLUMN IF NOT EXISTS actual_departure DATE;
ALTER TABLE shipments ADD COLUMN IF NOT EXISTS actual_arrival DATE;

-- 6. Create booking_revisions table (with tenant_id column)
CREATE TABLE IF NOT EXISTS booking_revisions (
    id SERIAL PRIMARY KEY,
    booking_no TEXT NOT NULL,
    revision_no INTEGER NOT NULL,
    revised_by TEXT,
    revised_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    revision_reason TEXT,
    snapshot TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    tenant_id TEXT DEFAULT 'default'
);

-- Ensure tenant_id exists on booking_revisions if the table already existed
ALTER TABLE booking_revisions ADD COLUMN IF NOT EXISTS tenant_id TEXT DEFAULT 'default';

-- 7. Create bills_of_lading table
CREATE TABLE IF NOT EXISTS bills_of_lading (
    id SERIAL PRIMARY KEY,
    bl_no TEXT UNIQUE NOT NULL,
    job_no TEXT NOT NULL,
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
    number_of_originals TEXT,
    freight_term TEXT,
    freight_payable_at TEXT,
    marks_numbers TEXT,
    package_qty INTEGER DEFAULT 0,
    package_type TEXT,
    description_of_goods TEXT,
    gross_weight NUMERIC(15,2) DEFAULT 0,
    measurement_cbm NUMERIC(15,2) DEFAULT 0,
    hs_code TEXT,
    remarks TEXT,
    special_instructions TEXT,
    bl_type TEXT DEFAULT 'Original',
    status TEXT DEFAULT 'Draft',
    created_by TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 8. Create bl_containers table (Junction table)
CREATE TABLE IF NOT EXISTS bl_containers (
    id SERIAL PRIMARY KEY,
    bl_id INTEGER NOT NULL REFERENCES bills_of_lading(id) ON DELETE CASCADE,
    container_id INTEGER NOT NULL REFERENCES containers(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(bl_id, container_id)
);
