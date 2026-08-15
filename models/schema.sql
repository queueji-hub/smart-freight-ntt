-- =====================================================
-- SMART FREIGHT NTT
-- CANONICAL POSTGRESQL PRODUCTION SCHEMA
-- =====================================================

-- Production DDL changes are additive and belong in database/migrations/*.sql.
-- Keep this file as the canonical baseline; do not replace it with migration fragments.

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT DEFAULT 'user',
    full_name TEXT,
    email TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);

CREATE TABLE IF NOT EXISTS sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    token TEXT UNIQUE NOT NULL,
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(token);

CREATE TABLE IF NOT EXISTS customers (
    id SERIAL PRIMARY KEY,
    company_name TEXT NOT NULL,
    contact_person TEXT,
    tel TEXT,
    email TEXT,
    address TEXT,
    tax_id TEXT,
    credit_terms_days INTEGER DEFAULT 30,
    notes TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_customers_company_name ON customers(company_name);

CREATE TABLE IF NOT EXISTS quotations (
    id SERIAL PRIMARY KEY,
    quotation_no TEXT UNIQUE NOT NULL,
    job_type TEXT,
    customer_id INTEGER REFERENCES customers(id),
    customer_name TEXT,
    customer_address TEXT,
    customer_email TEXT,
    attention TEXT,
    tel TEXT,
    salesperson TEXT,
    shipper TEXT,
    consignee TEXT,
    service_type TEXT,
    origin TEXT,
    pol TEXT,
    transshipment_port TEXT,
    pod TEXT,
    destination TEXT,
    carrier TEXT,
    quotation_date DATE,
    validity_date DATE,
    payment_term TEXT,
    incoterm TEXT,
    freight_term TEXT,
    commodity TEXT,
    hs_code TEXT,
    quantity NUMERIC(15,2) DEFAULT 0,
    package_type TEXT,
    weight_kg NUMERIC(15,2) DEFAULT 0,
    volume_cbm NUMERIC(15,2) DEFAULT 0,
    container_type TEXT,
    container_quantity INTEGER DEFAULT 0,
    is_dg BOOLEAN DEFAULT FALSE,
    subject TEXT,
    terms_conditions TEXT,
    status TEXT DEFAULT 'ACTIVE',
    created_by TEXT,
    updated_by TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_quotations_no ON quotations(quotation_no);

CREATE TABLE IF NOT EXISTS quotation_items (
    id SERIAL PRIMARY KEY,
    quotation_id INTEGER REFERENCES quotations(id) ON DELETE CASCADE,
    description TEXT,
    currency TEXT DEFAULT 'USD',
    basis TEXT,
    quantity NUMERIC(15,3) DEFAULT 1,
    unit TEXT,
    unit_rate NUMERIC(15,2) DEFAULT 0,
    amount NUMERIC(15,2) DEFAULT 0,
    price NUMERIC(15,2) DEFAULT 0,
    remark TEXT,
    sort_order INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS invoices (
    id SERIAL PRIMARY KEY,
    doc_no TEXT UNIQUE NOT NULL,
    doc_type TEXT,
    shipment_id INTEGER,
    job_no TEXT,
    customer_id INTEGER,
    customer_name TEXT,
    issue_date DATE,
    due_date DATE,
    currency TEXT DEFAULT 'THB',
    subtotal NUMERIC(15,2) DEFAULT 0,
    vat_rate NUMERIC(5,2) DEFAULT 0,
    vat_amount NUMERIC(15,2) DEFAULT 0,
    wht_amount NUMERIC(15,2) DEFAULT 0,
    total_amount NUMERIC(15,2) DEFAULT 0,
    outstanding NUMERIC(15,2) DEFAULT 0,
    payment_status TEXT DEFAULT 'Unpaid',
    ref_doc_no TEXT,
    remark TEXT,
    created_by TEXT,
    advance_amount NUMERIC(15,2) DEFAULT 0,
    wht_1_amount NUMERIC(15,2) DEFAULT 0,
    wht_3_amount NUMERIC(15,2) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_invoices_doc_no ON invoices(doc_no);
CREATE INDEX IF NOT EXISTS idx_invoices_customer ON invoices(customer_name);

CREATE TABLE IF NOT EXISTS invoice_items (
    id SERIAL PRIMARY KEY,
    invoice_id INTEGER REFERENCES invoices(id) ON DELETE CASCADE,
    description TEXT,
    quantity NUMERIC(15,2) DEFAULT 1,
    unit_price NUMERIC(15,2) DEFAULT 0,
    amount NUMERIC(15,2) DEFAULT 0,
    tax_type TEXT,
    wht_type TEXT,
    sort_order INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS invoice_payments (
    id SERIAL PRIMARY KEY,
    invoice_id INTEGER REFERENCES invoices(id) ON DELETE CASCADE,
    doc_no TEXT,
    payment_amount NUMERIC(15,2) DEFAULT 0,
    payment_method TEXT,
    payment_reference TEXT,
    payment_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS shipments (
    id SERIAL PRIMARY KEY,
    job_no TEXT UNIQUE NOT NULL,
    status TEXT DEFAULT 'Proceed',
    job_type TEXT,
    booking_no TEXT,
    customer_id INTEGER REFERENCES customers(id),
    customer_name TEXT,
    notify_party TEXT,
    sales_person TEXT,
    operations_owner TEXT,
    customer_reference TEXT,
    quotation_no TEXT,
    shipper TEXT,
    consignee TEXT,
    cargo_type TEXT,
    carrier TEXT,
    place_of_receipt TEXT,
    pol TEXT,
    transshipment_port TEXT,
    pod TEXT,
    place_of_delivery TEXT,
    final_destination TEXT,
    origin_country TEXT,
    destination_country TEXT,
    etd DATE,
    eta DATE,
    actual_departure DATE,
    actual_arrival DATE,
    mbl_no TEXT,
    hbl_no TEXT,
    bl_no TEXT,
    invoice_no TEXT,
    vessel TEXT,
    voyage TEXT,
    incoterm TEXT,
    service_type TEXT,
    freight_term TEXT,
    commodity TEXT,
    hs_code TEXT,
    package_type TEXT,
    package_quantity INTEGER DEFAULT 0,
    gross_weight NUMERIC(15,2) DEFAULT 0,
    net_weight NUMERIC(15,2) DEFAULT 0,
    cbm NUMERIC(15,2) DEFAULT 0,
    chargeable_weight NUMERIC(15,2) DEFAULT 0,
    is_dg BOOLEAN DEFAULT FALSE,
    is_temp_controlled BOOLEAN DEFAULT FALSE,
    special_cargo_remarks TEXT,
    customs_declaration_no TEXT,
    customs_status TEXT,
    customs_broker TEXT,
    customs_clearance_date DATE,
    customer_paid BOOLEAN DEFAULT FALSE,
    remark TEXT,
    created_by TEXT,
    updated_by TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_shipments_job_no ON shipments(job_no);
CREATE INDEX IF NOT EXISTS idx_shipments_booking_no ON shipments(booking_no);
CREATE INDEX IF NOT EXISTS idx_shipments_etd ON shipments(etd);
CREATE INDEX IF NOT EXISTS idx_shipments_eta ON shipments(eta);

CREATE TABLE IF NOT EXISTS job_counters (
    job_type TEXT NOT NULL,
    yymm TEXT NOT NULL,
    last_running INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (job_type, yymm)
);
CREATE TABLE IF NOT EXISTS doc_counters (
    doc_type TEXT NOT NULL,
    yymm TEXT NOT NULL,
    last_running INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (doc_type, yymm)
);

CREATE TABLE IF NOT EXISTS shipment_milestones (
    id SERIAL PRIMARY KEY,
    shipment_id INTEGER REFERENCES shipments(id) ON DELETE CASCADE,
    job_no TEXT NOT NULL,
    milestone_code TEXT NOT NULL,
    milestone_name TEXT NOT NULL,
    event_date TIMESTAMP NOT NULL,
    location TEXT,
    remark TEXT,
    created_by TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_shipment_milestones_job_no ON shipment_milestones(job_no);

CREATE TABLE IF NOT EXISTS bookings (
    id SERIAL PRIMARY KEY,
    tenant_id TEXT DEFAULT 'default',
    booking_no TEXT UNIQUE NOT NULL,
    job_type TEXT,
    customer_id INTEGER,
    customer_name TEXT,
    shipper TEXT,
    consignee TEXT,
    notify_party TEXT,
    pol TEXT,
    por TEXT,
    pod TEXT,
    final_destination TEXT,
    transhipment_port TEXT,
    cy_date DATE,
    cy_place TEXT,
    cfs_date DATE,
    cfs_place TEXT,
    customer_return_date DATE,
    return_place TEXT,
    etd DATE,
    eta DATE,
    carrier TEXT,
    m_vessel TEXT,
    feeder TEXT,
    liner TEXT,
    vessel TEXT,
    voyage TEXT,
    closing_time TIMESTAMP,
    cargo_type TEXT,
    container_summary TEXT,
    gross_weight NUMERIC(15,2),
    measurement_cbm NUMERIC(15,2),
    package_qty INTEGER,
    quantity INTEGER,
    package_unit TEXT,
    commodity TEXT,
    freight_term TEXT,
    status TEXT DEFAULT 'Proceed',
    remark TEXT,
    quotation_id INTEGER,
    quotation_no TEXT,
    job_no TEXT,
    revision_no INTEGER DEFAULT 0,
    is_current INTEGER DEFAULT 1,
    previous_booking_id INTEGER,
    revision_reason TEXT,
    revised_by TEXT,
    revised_at TIMESTAMP,
    created_by TEXT,
    updated_by TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_bookings_booking_no ON bookings(booking_no);
CREATE INDEX IF NOT EXISTS idx_bookings_etd ON bookings(etd);
CREATE INDEX IF NOT EXISTS idx_bookings_eta ON bookings(eta);

CREATE TABLE IF NOT EXISTS booking_revisions (
    id SERIAL PRIMARY KEY,
    booking_no TEXT NOT NULL,
    revision_no INTEGER NOT NULL,
    revised_by TEXT,
    revised_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    revision_reason TEXT,
    snapshot TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

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

CREATE TABLE IF NOT EXISTS containers (
    id SERIAL PRIMARY KEY,
    shipment_id INTEGER NOT NULL REFERENCES shipments(id) ON DELETE CASCADE,
    job_no TEXT NOT NULL,
    bl_no TEXT,
    container_no TEXT NOT NULL,
    container_size TEXT DEFAULT '40HC',
    container_type TEXT DEFAULT 'GP',
    seal_no TEXT,
    vgm_kg NUMERIC(15,2) DEFAULT 0,
    vgm_method TEXT DEFAULT 'Method 1',
    gross_weight NUMERIC(15,2) DEFAULT 0,
    net_weight NUMERIC(15,2) DEFAULT 0,
    tare_weight NUMERIC(15,2) DEFAULT 0,
    max_payload NUMERIC(15,2) DEFAULT 0,
    volume_cbm NUMERIC(15,2) DEFAULT 0,
    soc_coc TEXT DEFAULT 'COC',
    temp_setting NUMERIC(5,2),
    temp_unit TEXT DEFAULT 'C',
    vent_setting TEXT,
    genset_no TEXT,
    oog_length_cm NUMERIC(10,2) DEFAULT 0,
    oog_width_cm NUMERIC(10,2) DEFAULT 0,
    oog_height_cm NUMERIC(10,2) DEFAULT 0,
    un_number TEXT,
    imo_class TEXT,
    status TEXT DEFAULT 'Loaded',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(shipment_id, container_no)
);
CREATE INDEX IF NOT EXISTS idx_containers_job_no ON containers(job_no);

CREATE TABLE IF NOT EXISTS bl_containers (
    id SERIAL PRIMARY KEY,
    bl_id INTEGER NOT NULL REFERENCES bills_of_lading(id) ON DELETE CASCADE,
    container_id INTEGER NOT NULL REFERENCES containers(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(bl_id, container_id)
);

CREATE TABLE IF NOT EXISTS job_costs (
    id SERIAL PRIMARY KEY,
    shipment_id INTEGER NOT NULL REFERENCES shipments(id) ON DELETE CASCADE,
    cost_type TEXT NOT NULL,
    category TEXT,
    description TEXT,
    supplier TEXT,
    quantity NUMERIC(15,2) DEFAULT 1,
    unit_price NUMERIC(15,2) DEFAULT 0,
    amount NUMERIC(15,2) DEFAULT 0,
    currency TEXT DEFAULT 'THB',
    exchange_rate NUMERIC(10,5) DEFAULT 1.00000,
    amount_thb NUMERIC(15,2) DEFAULT 0,
    remark TEXT,
    created_by TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS profit_sheets (
    id SERIAL PRIMARY KEY,
    shipment_id INTEGER NOT NULL,
    sheet_no TEXT UNIQUE NOT NULL,
    total_ar NUMERIC(15,2) DEFAULT 0,
    total_ap NUMERIC(15,2) DEFAULT 0,
    net_profit NUMERIC(15,2) DEFAULT 0,
    profit_margin NUMERIC(5,2) DEFAULT 0,
    prepared_by TEXT,
    reviewed_by TEXT,
    reviewed_at TIMESTAMP,
    approved_by TEXT,
    approved_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS fx_rates (
    id SERIAL PRIMARY KEY,
    currency TEXT NOT NULL,
    rate_to_thb NUMERIC(15,4) NOT NULL,
    effective_date DATE NOT NULL,
    source TEXT DEFAULT 'manual',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(currency, effective_date)
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER,
    tenant_id TEXT,
    entity TEXT,
    entity_id TEXT,
    action TEXT,
    details TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
