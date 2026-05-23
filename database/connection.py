"""Supabase (PostgreSQL) database connection and initialization with SQLite compatibility layer."""
import psycopg2
import psycopg2.extras
import streamlit as st

# ปรับปรุงโครงสร้าง SCHEMA ให้เข้ากับ PostgreSQL (เปลี่ยน AUTOINCREMENT เป็น SERIAL)
RAW_SCHEMA = """
-- ===== CRM / Customer Database =====
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
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_customers_company ON customers(company_name);
CREATE INDEX IF NOT EXISTS idx_customers_taxid ON customers(tax_id);


-- ===== Quotation =====
CREATE TABLE IF NOT EXISTS quotations (
    id SERIAL PRIMARY KEY,
    quotation_no TEXT UNIQUE NOT NULL,
    job_type TEXT NOT NULL CHECK(job_type IN ('SE','SI','AE','AI','TE','TI')),
    customer_id INTEGER REFERENCES customers(id),
    customer_name TEXT,
    shipper_cnee TEXT,
    carrier TEXT,
    pol TEXT,
    pod TEXT,
    service_type TEXT,
    attention TEXT,
    tel TEXT,
    incoterm TEXT,
    commodity TEXT,
    weight TEXT,
    quantity_desc TEXT,
    payment_term TEXT DEFAULT '30 Days',
    quotation_date DATE NOT NULL,
    validity_date DATE NOT NULL,
    subject TEXT,
    terms_conditions TEXT,
    prepared_by TEXT,
    status TEXT DEFAULT 'Draft',
    cargo_type TEXT,
    container_size TEXT,
    estimated_cost REAL DEFAULT 0,
    selling_price REAL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_quotations_customer ON quotations(customer_id);
CREATE INDEX IF NOT EXISTS idx_quotations_date ON quotations(quotation_date);


CREATE TABLE IF NOT EXISTS quotation_items (
    id SERIAL PRIMARY KEY,
    quotation_id INTEGER NOT NULL REFERENCES quotations(id) ON DELETE CASCADE,
    description TEXT NOT NULL,
    currency TEXT NOT NULL DEFAULT 'USD',
    price REAL NOT NULL,
    unit TEXT,
    remark TEXT,
    sort_order INTEGER DEFAULT 0
);


-- ===== Job Number Counter =====
CREATE TABLE IF NOT EXISTS job_counters (
    job_type TEXT NOT NULL,
    yymm TEXT NOT NULL,
    last_running INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (job_type, yymm)
);


-- ===== Booking Confirmation =====
CREATE TABLE IF NOT EXISTS bookings (
    id SERIAL PRIMARY KEY,
    booking_no TEXT UNIQUE NOT NULL,
    job_type TEXT NOT NULL,
    customer_id INTEGER REFERENCES customers(id),
    customer_name TEXT,
    shipper TEXT,
    consignee TEXT,
    notify_party TEXT,
    pol TEXT, por TEXT, pod TEXT,
    final_destination TEXT,
    transhipment_port TEXT,
    cy_date DATE, cy_place TEXT,
    cfs_date DATE, cfs_place TEXT,
    customer_return_date DATE,
    return_place TEXT,
    etd DATE, eta DATE,
    carrier TEXT, m_vessel TEXT, feeder TEXT, liner TEXT,
    closing_time TEXT,
    cargo_type TEXT,
    commodity TEXT, quantity TEXT, remark TEXT,
    quotation_id INTEGER REFERENCES quotations(id),
    status TEXT DEFAULT 'Proceed',
    created_by TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_bookings_status ON bookings(status);
CREATE INDEX IF NOT EXISTS idx_bookings_customer ON bookings(customer_id);


-- ===== Shipments (Job) =====
CREATE TABLE IF NOT EXISTS shipments (
    id SERIAL PRIMARY KEY,
    job_no TEXT UNIQUE NOT NULL,
    job_type TEXT NOT NULL,
    booking_id INTEGER, booking_no TEXT,
    customer_id INTEGER, customer_name TEXT,
    shipper TEXT, consignee TEXT, notify_party TEXT,
    brand TEXT, commodity TEXT, combine_commodity TEXT,
    cargo_type TEXT, full_or_half TEXT,
    pick_up_date DATE, stuffing_date DATE, return_date DATE,
    etd DATE, eta DATE,
    container_no TEXT, seal_no TEXT, container_size TEXT,
    weight_origin TEXT, weight_port TEXT,
    carrier TEXT, m_vessel TEXT, feeder TEXT,
    pol TEXT, por TEXT, pod TEXT,
    final_destination TEXT, transhipment_port TEXT,
    bl_no TEXT, bl_status TEXT, closing_time TEXT,
    overnight_trucking INTEGER DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'Proceed',
    invoice_no TEXT, customer_paid INTEGER DEFAULT 0,
    dn_type TEXT, dn_no TEXT, remark TEXT,
    created_by TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_shipments_job_type ON shipments(job_type);
CREATE INDEX IF NOT EXISTS idx_shipments_status ON shipments(status);
CREATE INDEX IF NOT EXISTS idx_shipments_etd ON shipments(etd);
CREATE INDEX IF NOT EXISTS idx_shipments_carrier ON shipments(carrier);


-- ===== Shipment Milestones =====
CREATE TABLE IF NOT EXISTS shipment_milestones (
    id SERIAL PRIMARY KEY,
    shipment_id INTEGER NOT NULL REFERENCES shipments(id) ON DELETE CASCADE,
    milestone_code TEXT NOT NULL,
    milestone_name TEXT NOT NULL,
    occurred_at TIMESTAMP,
    note TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


-- ===== Financial Documents =====
CREATE TABLE IF NOT EXISTS invoices (
    id SERIAL PRIMARY KEY,
    doc_no TEXT UNIQUE NOT NULL,
    doc_type TEXT NOT NULL,
    shipment_id INTEGER, job_no TEXT,
    customer_id INTEGER, customer_name TEXT,
    issue_date DATE NOT NULL,
    due_date DATE,
    currency TEXT DEFAULT 'THB',
    subtotal REAL DEFAULT 0,
    vat_rate REAL DEFAULT 7,
    vat_amount REAL DEFAULT 0,
    wht_rate REAL DEFAULT 0,
    wht_amount REAL DEFAULT 0,
    total_amount REAL DEFAULT 0,
    paid_amount REAL DEFAULT 0,
    outstanding REAL DEFAULT 0,
    payment_status TEXT DEFAULT 'Unpaid',
    payment_date DATE,
    ref_doc_no TEXT,
    remark TEXT,
    created_by TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_invoices_customer ON invoices(customer_id);
CREATE INDEX IF NOT EXISTS idx_invoices_status ON invoices(payment_status);


CREATE TABLE IF NOT EXISTS invoice_items (
    id SERIAL PRIMARY KEY,
    invoice_id INTEGER NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
    description TEXT NOT NULL,
    quantity REAL DEFAULT 1,
    unit_price REAL DEFAULT 0,
    amount REAL DEFAULT 0,
    tax_type TEXT DEFAULT 'VAT 7%',
    wht_type TEXT DEFAULT 'None',
    sort_order INTEGER DEFAULT 0
);


-- ===== Document Counter =====
CREATE TABLE IF NOT EXISTS doc_counters (
    doc_type TEXT NOT NULL,
    yymm TEXT NOT NULL,
    last_running INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (doc_type, yymm)
);


-- ===== Users (RBAC) =====
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    full_name TEXT,
    email TEXT,
    role TEXT NOT NULL,
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


-- ===== Activity Log =====
CREATE TABLE IF NOT EXISTS activity_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER,
    username TEXT,
    action TEXT NOT NULL,
    entity_type TEXT,
    entity_id TEXT,
    details TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_logs_user ON activity_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_logs_created ON activity_logs(created_at);
"""

MIGRATIONS = {}

# =====================================================================
#  SQLite to PostgreSQL Compatibility Layers (ฉนวนแปลงคำสั่งเพื่อความปลอดภัย)
# =====================================================================

class SQLiteCursorWrapper:
    def __init__(self, pg_cursor):
        self._cursor = pg_cursor

    def execute(self, query, params=None):
        # แปลงตัวแปรคำถามจาก ? เป็น %s ให้เข้ากับ PostgreSQL 
        if "?" in query:
            query = query.replace("?", "%s")
        self._cursor.execute(query, params)
        return self

    def fetchall(self):
        return self._cursor.fetchall()

    def fetchone(self):
        return self._cursor.fetchone()

    def __getattr__(self, name):
        return getattr(self._cursor, name)

class SQLiteConnectionWrapper:
    def __init__(self, pg_conn):
        self._conn = pg_conn

    def cursor(self):
        # ใช้ RealDictCursor เพื่อส่งค่ากลับไปเป็น Dict คล้าย Row Factory ของ SQLite
        cursor = self._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        return SQLiteCursorWrapper(cursor)

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.rollback()
        else:
            self.commit()

# =====================================================================
def get_connection():
    """สร้างการเชื่อมต่อกับ PostgreSQL (Supabase) และห่อด้วย Wrapper"""
    try:
        # ดึงค่าคอนฟิกจาก Streamlit Secrets
        db_secrets = st.secrets["connections"]["postgresql"]
        
        pg_conn = psycopg2.connect(
            host=db_secrets["host"],
            database=db_secrets["database"],
            user=db_secrets["user"],
            password=db_secrets["password"],
            port=db_secrets["port"]
        )
        # ส่งกลับในรูปแบบ Wrapper เพื่อให้ใช้งานร่วมกับโค้ด SQLite เดิมได้
        return SQLiteConnectionWrapper(pg_conn)
    except Exception as e:
        st.error(f"❌ ไม่สามารถเชื่อมต่อฐานข้อมูลได้: {e}")
        raise e

def init_database():
    """สร้างตารางในฐานข้อมูลเริ่มต้นหากยังไม่มี"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(RAW_SCHEMA)
        conn.commit()
    except Exception as e:
        conn.rollback()
        st.error(f"❌ เกิดข้อผิดพลาดในการรัน Schema: {e}")
    finally:
        conn.close()