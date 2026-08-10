# AGENT DATABASE AUDIT (Raw SQL extraction)

### .\core\audit.py
```sql
SELECT 
            a.id, a.user_id, a.tenant_id, a.entity, a.entity_id, a.action, a.details, a.timestamp,
            COALESCE(u.username, 'System') as username,
            COALESCE(u.full_name, 'System Operator') as full_name
        FROM audit_logs a
        LEFT JOIN users u ON a.user_id = u.id
        WHERE 1=1
```
```sql
INSERT INTO audit_logs (
                        user_id, 
                        tenant_id, 
                        entity, 
                        entity_id, 
                        action, 
                        details,
                        timestamp
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP);
```
### .\database\connection.py
```sql
CREATE TABLE IF NOT EXISTS bookings (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
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
                        created_by TEXT,
                        updated_by TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
```
```sql
CREATE TABLE IF NOT EXISTS quotation_items (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        quotation_id INTEGER REFERENCES quotations(id) ON DELETE CASCADE,
                        description TEXT,
                        currency TEXT DEFAULT 'USD',
                        price NUMERIC(15,2) DEFAULT 0,
                        unit TEXT,
                        remark TEXT,
                        sort_order INTEGER DEFAULT 0
                    )
```
```sql
CREATE TABLE IF NOT EXISTS invoice_items (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,

                        invoice_id INTEGER REFERENCES invoices(id) ON DELETE CASCADE,

                        description TEXT,

                        quantity NUMERIC(15,2) DEFAULT 1,
                        unit_price NUMERIC(15,2) DEFAULT 0,
                        amount NUMERIC(15,2) DEFAULT 0,

                        tax_type TEXT,
                        wht_type TEXT,

                        sort_order INTEGER DEFAULT 0
                    )
```
```sql
CREATE TABLE IF NOT EXISTS job_costs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
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
                    )
```
```sql
CREATE TABLE IF NOT EXISTS invoices (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,

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
                    )
```
```sql
CREATE TABLE IF NOT EXISTS job_counters (
                        job_type TEXT NOT NULL,
                        yymm TEXT NOT NULL,
                        last_running INTEGER NOT NULL DEFAULT 0,
                        PRIMARY KEY (job_type, yymm)
                    )
```
```sql
CREATE TABLE IF NOT EXISTS sessions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                        token TEXT UNIQUE NOT NULL,
                        expires_at TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
```
```sql
CREATE INDEX IF NOT EXISTS idx_bookings_eta
                    ON bookings(eta)
```
```sql
CREATE TABLE IF NOT EXISTS containers (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
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
                    )
```
```sql
CREATE TABLE IF NOT EXISTS shipment_milestones (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        shipment_id INTEGER REFERENCES shipments(id) ON DELETE CASCADE,
                        job_no TEXT NOT NULL,
                        milestone_code TEXT NOT NULL,
                        milestone_name TEXT NOT NULL,
                        event_date TIMESTAMP NOT NULL,
                        location TEXT,
                        remark TEXT,
                        created_by TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
```
```sql
CREATE INDEX IF NOT EXISTS idx_sessions_token
                    ON sessions(token)
```
```sql
CREATE INDEX IF NOT EXISTS idx_quotations_no
                    ON quotations(quotation_no)
```
```sql
CREATE INDEX IF NOT EXISTS idx_shipments_eta
                    ON shipments(eta)
```
```sql
CREATE TABLE IF NOT EXISTS fx_rates (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        currency TEXT NOT NULL,
                        rate_to_thb NUMERIC(15,4) NOT NULL,
                        effective_date DATE NOT NULL,
                        source TEXT DEFAULT 'manual',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(currency, effective_date)
                    )
```
```sql
CREATE INDEX IF NOT EXISTS idx_containers_job_no
                    ON containers(job_no)
```
```sql
CREATE INDEX IF NOT EXISTS idx_invoices_customer
                    ON invoices(customer_name)
```
```sql
CREATE TABLE IF NOT EXISTS booking_revisions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        booking_no TEXT NOT NULL,
                        revision_no INTEGER NOT NULL,
                        revised_by TEXT,
                        revised_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        revision_reason TEXT,
                        snapshot TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
```
```sql
CREATE TABLE IF NOT EXISTS bl_containers (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        bl_id INTEGER NOT NULL REFERENCES bills_of_lading(id) ON DELETE CASCADE,
                        container_id INTEGER NOT NULL REFERENCES containers(id) ON DELETE CASCADE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(bl_id, container_id)
                    )
```
```sql
CREATE TABLE IF NOT EXISTS doc_counters (
                        doc_type TEXT NOT NULL,
                        yymm TEXT NOT NULL,
                        last_running INTEGER NOT NULL DEFAULT 0,
                        PRIMARY KEY (doc_type, yymm)
                    )
```
```sql
CREATE TABLE IF NOT EXISTS bills_of_lading (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        bl_no TEXT UNIQUE NOT NULL,
                        job_no TEXT NOT NULL,
                        shipper TEXT,
                        consignee TEXT,
                        notify_party TEXT,
                        pol TEXT,
                        pod TEXT,
                        vessel TEXT,
                        voyage TEXT,
                        bl_type TEXT DEFAULT 'Original',
                        status TEXT DEFAULT 'Draft',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
```
```sql
CREATE INDEX IF NOT EXISTS idx_shipments_job_no
                    ON shipments(job_no)
```
```sql
CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE NOT NULL,
                        password_hash TEXT NOT NULL,
                        role TEXT DEFAULT 'user',
                        full_name TEXT,
                        email TEXT,
                        is_active BOOLEAN DEFAULT TRUE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
```
```sql
CREATE TABLE IF NOT EXISTS profit_sheets (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
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
                    )
```
```sql
CREATE TABLE IF NOT EXISTS shipments (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,

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
                    )
```
```sql
CREATE TABLE IF NOT EXISTS audit_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        tenant_id TEXT,
                        entity TEXT,
                        entity_id TEXT,
                        action TEXT,
                        details TEXT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
```
```sql
CREATE TABLE IF NOT EXISTS quotations (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        quotation_no TEXT UNIQUE NOT NULL,
                        job_type TEXT,
                        customer_name TEXT,
                        attention TEXT,
                        tel TEXT,
                        carrier TEXT,
                        pol TEXT,
                        pod TEXT,
                        quotation_date DATE,
                        validity_date DATE,
                        payment_term TEXT,
                        commodity TEXT,
                        subject TEXT,
                        terms_conditions TEXT,
                        status TEXT DEFAULT 'ACTIVE',
                        created_by TEXT,
                        updated_by TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
```
```sql
CREATE INDEX IF NOT EXISTS idx_shipment_milestones_job_no
                    ON shipment_milestones(job_no)
```
```sql
CREATE INDEX IF NOT EXISTS idx_bookings_etd
                    ON bookings(etd)
```
```sql
CREATE INDEX IF NOT EXISTS idx_users_username
                    ON users(username)
```
```sql
INSERT INTO users (username, password_hash, full_name, email, role, is_active)
                        VALUES (%s, %s, %s, %s, %s, 1)
                        ON CONFLICT (username) DO UPDATE SET password_hash = EXCLUDED.password_hash, role = EXCLUDED.role
```
```sql
CREATE TABLE IF NOT EXISTS customers (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
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
                    )
```
```sql
CREATE INDEX IF NOT EXISTS idx_invoices_doc_no
                    ON invoices(doc_no)
```
```sql
CREATE INDEX IF NOT EXISTS idx_bookings_booking_no
                    ON bookings(booking_no)
```
```sql
CREATE INDEX IF NOT EXISTS idx_shipments_etd
                    ON shipments(etd)
```
```sql
CREATE INDEX IF NOT EXISTS idx_customers_company_name
                    ON customers(company_name)
```
```sql
CREATE TABLE IF NOT EXISTS invoice_payments (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        invoice_id INTEGER REFERENCES invoices(id) ON DELETE CASCADE,
                        doc_no TEXT,
                        payment_amount NUMERIC(15,2) DEFAULT 0,
                        payment_method TEXT,
                        payment_reference TEXT,
                        payment_date DATE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
```
```sql
CREATE INDEX IF NOT EXISTS idx_shipments_booking_no
                    ON shipments(booking_no)
```
### .\managers\auth_manager.py
```sql
INSERT INTO users (username, password_hash, full_name, email, role, is_active)
                    VALUES (%s, %s, %s, %s, %s, %s)
```
```sql
UPDATE users SET role = %s WHERE LOWER(username) = %s
```
```sql
SELECT id, username, full_name, email, role, is_active FROM users WHERE LOWER(username) = %s LIMIT 1
```
```sql
SELECT id, username, password_hash, full_name, email, role, is_active 
                    FROM users 
                    WHERE LOWER(username) = %s 
                    LIMIT 1
```
```sql
UPDATE users SET password_hash = %s WHERE LOWER(username) = %s
```
```sql
UPDATE users SET is_active = %s WHERE LOWER(username) = %s
```
```sql
SELECT id, username, full_name, email, role, is_active FROM users ORDER BY username ASC
```
### .\managers\bl_manager.py
```sql
DELETE FROM bl_containers WHERE bl_id=%s AND container_id=%s
```
```sql
SELECT c.id, c.container_no, c.container_size, c.container_type,
                       c.seal_no, c.vgm_kg, c.tare_weight, c.gross_weight,
                       c.job_no, bc.id AS junction_id
                FROM   containers c
                JOIN   bl_containers bc ON c.id = bc.container_id
                WHERE  bc.bl_id = %s
                ORDER  BY c.container_no
```
```sql
Update editable fields on a DRAFT or SUBMITTED B/L.
    Validates numeric fields.
    Does NOT touch job/booking/quotation data.
```
```sql
SELECT * FROM bills_of_lading WHERE job_no = %s ORDER BY created_at ASC
```
```sql
INSERT INTO bills_of_lading (
```
```sql
UPDATE bills_of_lading SET status=%s, updated_at=CURRENT_TIMESTAMP WHERE id=%s
```
```sql
SELECT * FROM bills_of_lading WHERE bl_no = %s
```
```sql
SELECT job_no FROM containers WHERE id = %s
```
```sql
UPDATE bills_of_lading SET
```
```sql
INSERT INTO bl_containers (bl_id, container_id) VALUES (%s, %s)
```
```sql
SELECT * FROM bills_of_lading WHERE id = %s
```
```sql
Create a B/L from a Job.
    Prefills from Job. extra_data can override any prefilled field.
    Returns the new bl_id (INTEGER).
    Raises ValueError on duplicate B/L number or job lock.
```
```sql
DELETE FROM bills_of_lading WHERE id = %s
```
```sql
SELECT last_running FROM job_counters WHERE job_type=%s AND yymm=%s
```
```sql
Delete a DRAFT / SUBMITTED B/L.
    bl_containers rows are removed via ON DELETE CASCADE.
    Never removes Job containers.
```
```sql
INSERT INTO job_counters (job_type, yymm, last_running)
            VALUES (%s, %s, 1)
            ON CONFLICT (job_type, yymm)
            DO UPDATE SET last_running = job_counters.last_running + 1
```
### .\managers\booking_manager.py
```sql
UPDATE bookings
                SET revision_no = %s,
                    status = 'DRAFT',
                    revision_reason = %s,
                    revised_by = %s,
                    revised_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE booking_no = %s AND tenant_id = %s
```
```sql
Create booking from quotation
    SaaS version (tenant-safe + audit)
```
```sql
SELECT *
                FROM bookings
                WHERE booking_no=%s AND tenant_id=%s
```
```sql
SELECT * FROM booking_revisions
                WHERE booking_no = %s AND revision_no = %s
```
```sql
INSERT INTO shipments (
```
```sql
UPDATE bookings
                SET
```
```sql
DELETE FROM bookings 
                WHERE booking_no=%s AND tenant_id=%s
```
```sql
SELECT job_no FROM shipments WHERE booking_no = %s
```
```sql
INSERT INTO shipment_milestones 
                            (shipment_id, job_no, milestone_code, milestone_name, event_date, remark, created_by) 
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
```
```sql
UPDATE bookings SET status = %s, job_no = %s WHERE booking_no = %s AND tenant_id = %s AND status = 'CONFIRMED'
```
```sql
SELECT * FROM bookings WHERE booking_no = %s AND tenant_id = %s
```
```sql
INSERT INTO bookings (
                    tenant_id,
                    booking_no,
                    job_type,
                    customer_id,
                    customer_name,
                    shipper,
                    consignee,
                    notify_party,
                    pol,
                    por,
                    pod,
                    final_destination,
                    transhipment_port,
                    cy_date,
                    cy_place,
                    cfs_date,
                    cfs_place,
                    customer_return_date,
                    return_place,
                    etd,
                    eta,
                    carrier,
                    m_vessel,
                    feeder,
                    liner,
                    vessel,
                    voyage,
                    closing_time,
                    cargo_type,
                    container_summary,
                    gross_weight,
                    measurement_cbm,
                    package_qty,
                    quantity,
                    package_unit,
                    commodity,
                    freight_term,
                    remark,
                    quotation_id,
                    status,
                    created_by
                )
                VALUES (
                    %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                    %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                    %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                    %s,%s,%s,%s,%s,%s,%s,%s,%s,'DRAFT',%s
                )
```
```sql
INSERT INTO booking_revisions (
                    booking_no, revision_no, revised_by, revision_reason, snapshot
                )
                VALUES (%s, %s, %s, %s, %s)
```
```sql
SELECT id FROM shipment_milestones WHERE job_no = %s AND milestone_code = 'JOB_CREATED'
```
```sql
SELECT id, booking_no, revision_no, revised_by, revised_at, revision_reason, snapshot, created_at
                FROM booking_revisions
                WHERE booking_no = %s
                ORDER BY revision_no DESC
```
```sql
SELECT *
        FROM bookings
        WHERE tenant_id=%s
```
```sql
SELECT id FROM shipments WHERE job_no = %s
```
### .\managers\container_manager.py
```sql
SELECT id FROM shipments WHERE job_no=%s
```
```sql
DELETE FROM containers WHERE id=%s AND job_no=%s
```
```sql
INSERT INTO containers (
            shipment_id, job_no, bl_no, container_no, container_size, container_type,
            seal_no, vgm_kg, vgm_method, gross_weight, net_weight,
            tare_weight, max_payload, volume_cbm, soc_coc,
            temp_setting, temp_unit, vent_setting, genset_no,
            oog_length_cm, oog_width_cm, oog_height_cm, un_number, imo_class, status
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
```
```sql
SELECT * FROM containers WHERE 1=1
```
### .\managers\customer_manager.py
```sql
SELECT *
                FROM customers
                WHERE is_active = TRUE
                ORDER BY LOWER(company_name) ASC
```
```sql
INSERT INTO customers (
                    company_name,
                    contact_person,
                    tel,
                    email,
                    address,
                    tax_id,
                    credit_terms_days,
                    notes,
                    is_active
                )
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
```
```sql
UPDATE customers
                    SET contact_person = %s,
                        tel = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE company_name = %s
```
```sql
DELETE FROM customers
                WHERE id = %s
```
```sql
SELECT *
                FROM customers
                WHERE company_name ILIKE %s
                ORDER BY company_name
                LIMIT 10
```
```sql
UPDATE customers
                SET company_name=%s,
                    contact_person=%s,
                    tel=%s,
                    email=%s,
                    address=%s,
                    tax_id=%s,
                    credit_terms_days=%s,
                    notes=%s,
                    updated_at=CURRENT_TIMESTAMP
                WHERE company_name=%s
```
```sql
SELECT id
                FROM customers
                WHERE company_name = %s
```
```sql
SELECT *
                FROM customers
                WHERE id = %s
```
```sql
INSERT INTO customers (
                        company_name,
                        contact_person,
                        tel,
                        is_active
                    )
                    VALUES (%s, %s, %s, TRUE)
```
```sql
SELECT *
                FROM customers
                WHERE company_name ILIKE %s
                LIMIT 1
```
### .\managers\dashboard_manager.py
```sql
SELECT 
                        COUNT(*) as total,
                        SUM(CASE WHEN LOWER(status) = 'draft' THEN 1 ELSE 0 END) as draft,
                        SUM(CASE WHEN LOWER(status) = 'submitted' THEN 1 ELSE 0 END) as submitted,
                        SUM(CASE WHEN LOWER(status) = 'confirmed' THEN 1 ELSE 0 END) as confirmed,
                        SUM(CASE WHEN LOWER(status) = 'converted_to_job' OR LOWER(status) = 'converted to job' THEN 1 ELSE 0 END) as converted,
                        SUM(CASE WHEN revision_no > 0 THEN 1 ELSE 0 END) as revised,
                        SUM(CASE WHEN LOWER(status) = 'confirmed' AND (job_no IS NULL OR job_no = '') THEN 1 ELSE 0 END) as unconverted_confirmed
                    FROM bookings
```
```sql
SELECT COUNT(DISTINCT job_no) FROM bills_of_lading WHERE job_no IS NOT NULL AND job_no != ''
```
```sql
SELECT * FROM job_costs WHERE shipment_id = %s ORDER BY cost_type ASC, id ASC
```
```sql
SELECT * FROM invoices WHERE LOWER(job_no) = %s OR LOWER(customer_name) LIKE %s ORDER BY id DESC
```
```sql
SELECT * FROM bookings WHERE LOWER(booking_no) = %s LIMIT 1
```
```sql
SELECT * FROM bookings WHERE LOWER(booking_no) LIKE %s OR LOWER(customer_name) LIKE %s LIMIT 1
```
```sql
SELECT COUNT(DISTINCT job_no) FROM containers WHERE job_no IS NOT NULL AND job_no != ''
```
```sql
SELECT COUNT(*) FROM containers
```
```sql
SELECT a.*, COALESCE(u.username, 'System') as username
                        FROM audit_logs a
                        LEFT JOIN users u ON a.user_id = u.id
                        WHERE LOWER(a.entity_id) = %s OR LOWER(a.details) LIKE %s
                        ORDER BY a.timestamp DESC LIMIT 100
```
```sql
SELECT * FROM shipments
                    WHERE LOWER(job_no) LIKE %s OR LOWER(booking_no) LIKE %s OR LOWER(bl_no) LIKE %s OR LOWER(customer_name) LIKE %s
                    ORDER BY id DESC LIMIT 1
```
```sql
SELECT * FROM invoices WHERE LOWER(doc_no) LIKE %s OR LOWER(customer_name) LIKE %s
```
```sql
SELECT 
                        COUNT(*) as total,
                        SUM(CASE WHEN LOWER(status) = 'draft' THEN 1 ELSE 0 END) as draft,
                        SUM(CASE WHEN LOWER(status) = 'issued' THEN 1 ELSE 0 END) as issued,
                        SUM(CASE WHEN LOWER(status) = 'cancelled' THEN 1 ELSE 0 END) as cancelled
                    FROM bills_of_lading
```
```sql
SELECT 
                        COUNT(*) as total,
                        SUM(CASE WHEN LOWER(status) = 'draft' THEN 1 ELSE 0 END) as draft,
                        SUM(CASE WHEN LOWER(status) = 'active' THEN 1 ELSE 0 END) as active,
                        SUM(CASE WHEN LOWER(status) = 'converted' THEN 1 ELSE 0 END) as converted,
                        SUM(CASE WHEN LOWER(status) = 'expired' THEN 1 ELSE 0 END) as expired
                    FROM quotations
```
```sql
SELECT 
                        COUNT(*) as total,
                        SUM(CASE WHEN LOWER(status) = 'proceed' THEN 1 ELSE 0 END) as proceed,
                        SUM(CASE WHEN LOWER(status) = 'in_transit' OR LOWER(status) = 'in transit' THEN 1 ELSE 0 END) as in_transit,
                        SUM(CASE WHEN LOWER(status) = 'arrived' THEN 1 ELSE 0 END) as arrived,
                        SUM(CASE WHEN LOWER(status) = 'finished' THEN 1 ELSE 0 END) as finished,
                        SUM(CASE WHEN LOWER(status) = 'closed' THEN 1 ELSE 0 END) as closed,
                        SUM(CASE WHEN LOWER(status) = 'cancelled' OR LOWER(status) = 'canceled' THEN 1 ELSE 0 END) as cancelled
                    FROM shipments
```
```sql
SELECT * FROM quotations WHERE LOWER(quotation_no) LIKE %s OR LOWER(customer_name) LIKE %s LIMIT 1
```
### .\managers\doc_number.py
```sql
INSERT INTO doc_counters (doc_type, yymm, last_running)
            VALUES (%s, %s, 1)
            ON CONFLICT (doc_type, yymm) 
            DO UPDATE SET last_running = doc_counters.last_running + 1
            RETURNING last_running
```
### .\managers\email_manager.py
```sql
INSERT INTO email_log (to_email, cc, subject, body, attachments, status, sent_at, created_by)
                VALUES (%s, %s, %s, %s, %s, 'sent', %s, %s)
```
```sql
INSERT INTO email_log (to_email, cc, subject, body, attachments, status, error, created_by)
                VALUES (%s, %s, %s, %s, %s, 'failed', %s, %s)
```
```sql
INSERT INTO email_log (to_email, cc, subject, body, attachments, status, error, created_by)
                VALUES (%s, %s, %s, %s, %s, 'draft', 'SMTP not configured', %s)
```
```sql
SELECT * FROM email_log ORDER BY created_at DESC LIMIT %s
```
### .\managers\finance_manager.py
```sql
UPDATE invoices
            SET outstanding=%s,
                status=%s,
                updated_at=CURRENT_TIMESTAMP
            WHERE id=%s AND tenant_id=%s
```
```sql
SELECT *
            FROM invoices
            WHERE id=%s AND tenant_id=%s
```
```sql
INSERT INTO invoices (
                tenant_id,
                doc_no,
                doc_type,
                customer_name,
                issue_date,
                due_date,
                subtotal,
                vat_amount,
                wht_amount,
                total_amount,
                outstanding,
                status,
                created_by
            )
            VALUES (
                %s,%s,'INV',
                %s,%s,%s,
                %s,%s,%s,%s,
                %s,'OPEN',%s
            )
            RETURNING id
```
```sql
INSERT INTO invoice_items (
                    invoice_id,
                    description,
                    quantity,
                    unit_price,
                    amount,
                    tax_type,
                    wht_type,
                    sort_order
                )
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
```
```sql
SELECT outstanding
            FROM invoices
            WHERE id=%s AND tenant_id=%s
```
```sql
SELECT *
            FROM invoice_items
            WHERE invoice_id=%s
            ORDER BY sort_order
```
```sql
SELECT * FROM invoices WHERE tenant_id=%s
```
### .\managers\fx_manager.py
```sql
INSERT INTO fx_rates (currency, rate_to_thb, effective_date, source)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT(currency, effective_date) DO UPDATE
            SET rate_to_thb = EXCLUDED.rate_to_thb,
                source = EXCLUDED.source
            RETURNING id
```
```sql
SELECT * FROM fx_rates
```
```sql
SELECT rate_to_thb FROM fx_rates
            WHERE currency=%s AND effective_date <= %s
            ORDER BY effective_date DESC LIMIT 1
```
### .\managers\invoice_manager.py
```sql
INSERT INTO invoices (
                        doc_no, doc_type, customer_id, customer_name, job_no,
                        issue_date, due_date, currency, ref_doc_no, remark,
                        subtotal, vat_amount, wht_amount, total_amount,
                        outstanding, payment_status, created_by
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id;
```
```sql
INSERT INTO invoice_items (
                            invoice_id, description, quantity, unit_price,
                            amount, tax_type, wht_type, sort_order
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
```
```sql
SELECT 
                    doc_no, doc_type, customer_name, issue_date, due_date, 
                    currency, total_amount, total_amount AS grand_total, 
                    outstanding, payment_status AS status
                FROM invoices 
                ORDER BY id DESC;
```
```sql
INSERT INTO invoice_payments (
                        invoice_id, doc_no, payment_amount, payment_method, 
                        payment_reference, payment_date
                    )
                    VALUES (%s, %s, %s, %s, %s, %s);
```
```sql
SELECT id, total_amount, outstanding 
                    FROM invoices 
                    WHERE doc_no = %s 
                    FOR UPDATE;
```
```sql
UPDATE invoices
                    SET outstanding = %s,
                        payment_status = %s
                    WHERE id = %s;
```
### .\managers\job_manager.py
```sql
SELECT *
            FROM jobs
            WHERE job_no=%s AND tenant_id=%s
```
```sql
INSERT INTO jobs (
                tenant_id,
                job_no,
                job_type,
                booking_no,
                customer_name,
                shipper,
                consignee,
                cargo_type,
                carrier,
                pol,
                pod,
                etd,
                eta,
                status,
                created_by
            )
            VALUES (
                %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                %s,%s,%s,'OPEN',%s
            )
```
```sql
UPDATE jobs
            SET
```
```sql
SELECT *
        FROM jobs
        WHERE tenant_id=%s
```
```sql
UPDATE jobs
            SET status='CANCELLED'
            WHERE job_no=%s AND tenant_id=%s
```
```sql
UPDATE jobs
            SET status=%s,
                updated_at=CURRENT_TIMESTAMP
            WHERE job_no=%s AND tenant_id=%s
```
### .\managers\job_number.py
```sql
SELECT last_running FROM job_counters WHERE job_type=%s AND yymm=%s
```
```sql
INSERT INTO job_counters (job_type, yymm, last_running)
            VALUES (%s, %s, 1)
            ON CONFLICT (job_type, yymm) 
            DO UPDATE SET last_running = job_counters.last_running + 1
```
### .\managers\milestone_manager.py
```sql
INSERT INTO shipment_milestones (shipment_id, job_no, milestone_code, milestone_name, event_date, location, remark)
            VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id
```
```sql
SELECT COUNT(*) as cnt FROM shipment_milestones WHERE shipment_id=%s
```
```sql
DELETE FROM shipment_milestones WHERE id=%s AND job_no=%s
```
```sql
SELECT * FROM shipment_milestones
            WHERE job_no = %s
            ORDER BY event_date DESC, created_at DESC
```
```sql
SELECT 
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE event_date IS NOT NULL) as completed
            FROM shipment_milestones WHERE shipment_id=%s
```
```sql
UPDATE shipment_milestones SET event_date=%s, location=%s, remark=%s WHERE id=%s
```
```sql
INSERT INTO shipment_milestones (shipment_id, job_no, milestone_code, milestone_name, event_date)
                VALUES (%s, %s, %s, %s, NULL)
```
### .\managers\profit_manager.py
```sql
SELECT 
                    COALESCE(SUM(amount_thb) FILTER (WHERE cost_type='AR'), 0) as ar,
                    COALESCE(SUM(amount_thb) FILTER (WHERE cost_type='AP'), 0) as ap
                FROM job_costs WHERE shipment_id=%s
```
```sql
DELETE FROM job_costs WHERE id=%s
```
```sql
INSERT INTO profit_sheets (shipment_id, sheet_no, total_ar, total_ap, net_profit, profit_margin, prepared_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING *
```
```sql
SELECT * FROM job_costs WHERE shipment_id=%s ORDER BY id ASC
```
```sql
INSERT INTO job_costs (shipment_id, cost_type, category, description, supplier, 
                                       quantity, unit_price, amount, currency, amount_thb, remark, created_by)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id
```
```sql
UPDATE job_costs SET 
                category=%s, description=%s, supplier=%s, quantity=%s, unit_price=%s, 
                amount=%s, currency=%s, amount_thb=%s, remark=%s 
                WHERE id=%s
```
```sql
Update cost/revenue line with recalculation.
```
```sql
SELECT * FROM profit_sheets WHERE shipment_id=%s ORDER BY id DESC
```
```sql
Update review or approve status on a profit sheet.
```
```sql
UPDATE profit_sheets SET
```
```sql
Delete a cost line item by ID.
```
```sql
SELECT * FROM job_costs WHERE shipment_id=%s AND cost_type=%s ORDER BY id ASC
```
```sql
SELECT amount, currency FROM job_costs WHERE id=%s
```
### .\managers\quotation_manager.py
```sql
INSERT INTO quotations (
                        quotation_no, job_type, customer_name, attention, tel,
                        carrier, pol, pod, quotation_date, validity_date,
                        payment_term, commodity, subject, terms_conditions,
                        status, created_at,
                        customer_address, customer_email, salesperson,
                        shipper, consignee, service_type, origin, destination,
                        incoterm, freight_term, hs_code, quantity, package_type,
                        weight_kg, volume_cbm, container_type, container_quantity, is_dg
                    )
                    VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP,
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    );
```
```sql
UPDATE quotations SET
                        job_type = %s, customer_name = %s, attention = %s, tel = %s,
                        carrier = %s, pol = %s, pod = %s, quotation_date = %s,
                        validity_date = %s, payment_term = %s, commodity = %s,
                        subject = %s, terms_conditions = %s,
                        customer_address = %s, customer_email = %s, salesperson = %s,
                        shipper = %s, consignee = %s, service_type = %s, origin = %s, destination = %s,
                        incoterm = %s, freight_term = %s, hs_code = %s, quantity = %s, package_type = %s,
                        weight_kg = %s, volume_cbm = %s, container_type = %s, container_quantity = %s, is_dg = %s
                    WHERE id = %s;
```
```sql
SELECT * FROM quotations WHERE quotation_no = %s LIMIT 1;
```
```sql
SELECT id, description, currency, price, unit, remark,
                       basis, quantity, unit_rate, amount 
                FROM quotation_items 
                WHERE quotation_id = %s 
                ORDER BY sort_order ASC;
```
```sql
INSERT INTO quotation_items (
                            quotation_id, description, currency, price, unit, remark, sort_order,
                            basis, quantity, unit_rate, amount
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
```
```sql
SELECT id FROM quotations WHERE quotation_no = %s LIMIT 1;
```
```sql
SELECT 
                    quotation_no, job_type, customer_name, subject,
                    quotation_date, validity_date, status
                FROM quotations 
                ORDER BY id DESC;
```
```sql
DELETE FROM quotation_items WHERE quotation_id = %s;
```
### .\managers\quotation_number.py
```sql
SELECT quotation_no FROM quotations 
                WHERE quotation_no LIKE %s 
                ORDER BY quotation_no DESC LIMIT 1
```
### .\managers\session_manager.py
```sql
INSERT INTO sessions (
                            user_id,
                            token,
                            expires_at
                        )
                        VALUES (%s, %s, %s)
```
```sql
DELETE FROM sessions
                    WHERE token = %s
```
```sql
DELETE SESSION ERROR:
```
```sql
CREATE SESSION ERROR:
```
```sql
INSERT INTO sessions (
                            user_id,
                            token
                        )
                        VALUES (%s, %s)
```
### .\managers\shipment_manager.py
```sql
SELECT cost_type, amount, exchange_rate, amount_thb FROM job_costs WHERE shipment_id = %s
```
```sql
SELECT * FROM shipments WHERE job_no = %s
```
```sql
SELECT * FROM shipments WHERE 1=1
```
```sql
UPDATE shipments
                SET
```
```sql
SELECT status FROM shipments WHERE job_no = %s
```
```sql
DELETE FROM shipments WHERE job_no = %s
```
```sql
INSERT INTO shipments (
```
```sql
SELECT id FROM shipments WHERE job_no = %s
```
### .\managers\template_manager.py
```sql
UPDATE email_templates SET subject=%s, body=%s, updated_at=CURRENT_TIMESTAMP WHERE code=%s
```
```sql
Update template and commit changes.
```
### .\pdf\bl_pdf.py
```sql
SELECT * FROM bills_of_lading WHERE bl_no = %s
```
```sql
SELECT * FROM bookings WHERE booking_no = %s
```
```sql
SELECT * FROM shipments WHERE job_no = %s
```
### .\repositories\quotation_repo.py
```sql
SELECT * FROM quotation_items WHERE quotation_id=%s ORDER BY sort_order
```
```sql
INSERT INTO quotation_items (
                    quotation_id,
                    description,
                    price,
                    currency,
                    sort_order
                )
                VALUES (%s,%s,%s,%s,%s)
```
```sql
INSERT INTO quotations (
                job_type,
                customer_name,
                quotation_date
            )
            VALUES (%s, %s, %s)
            RETURNING id
```
```sql
SELECT * FROM quotations WHERE id=%s
```
### .\scratch\qa_p0_2_3_canonical_managers.py
```sql
INSERT INTO shipments (job_no, status) VALUES (%s, 'Proceed') RETURNING id
```
```sql
DELETE FROM shipments WHERE job_no = %s
```
### .\scripts\seed_shipments.py
```sql
INSERT INTO shipments (
                    job_no, job_type, booking_no, brand,
                    combine_commodity, pick_up_date, stuffing_date, return_date,
                    container_no, seal_no, carrier, pol, pod, container_size,
                    bl_status, status, invoice_no, remark
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
```
```sql
SELECT id FROM shipments WHERE job_no=?
```
### .\views\billing_view.py
```sql
Create Financial Document
```
```sql
Select Outstanding Invoice
```
```sql
Select the type of financial document to generate.
```
### .\views\bl_view.py
```sql
Select B/L Record to Inspect / Edit
```
```sql
Select Job Container to Link
```
```sql
Select Target B/L
```
```sql
Select Container to Unlink
```
### .\views\booking_view.py
```sql
Select Booking Record to Inspect / Edit
```
```sql
Select Target Booking
```
```sql
Select Historical Revision Version
```
### .\views\crm_view.py
```sql
Select Account
```
### .\views\finance.py
```sql
Create Invoice
```
```sql
Select customer
```
### .\views\fx_view.py
```sql
Select Unreconciled
```
### .\views\profit_view.py
```sql
Select Unreconciled
```
### .\views\quotation_view.py
```sql
Select Quotation
```
### .\views\shipment_view.py
```sql
Delete Milestone
```
```sql
Delete Container
```
```sql
Update Routing
```
```sql
Update Vessel
```
```sql
Select Milestone to Delete
```
```sql
Delete This B/L (Draft only)
```
```sql
Select container to unlink
```
```sql
Update Overview
```
```sql
Update Parties
```
```sql
Select container to link
```
```sql
Select Target Operational Job to Open
```
```sql
Select Container to Delete
```
```sql
Update Cargo
```
```sql
Create B/L (prefill from Job)
```
```sql
Select B/L to View / Edit
```
### .\views\tracking_view.py
```sql
Select Job ID to view routing details
```
### .\views\users_view.py
```sql
UPDATE users SET role = %s WHERE id = %s
```
```sql
UPDATE users SET role = ? WHERE id = ?
```
```sql
Select Target Corporate Account to Manage
```
