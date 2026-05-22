"""SQLite database connection and initialization."""
import sqlite3
from pathlib import Path
from config import DB_PATH

SCHEMA = """
-- ===== CRM / Customer Database =====
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
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_customers_company ON customers(company_name);
CREATE INDEX IF NOT EXISTS idx_customers_taxid ON customers(tax_id);


-- ===== Quotation =====
CREATE TABLE IF NOT EXISTS quotations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
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
    status TEXT DEFAULT 'Draft' CHECK(status IN ('Draft','Sent','Accepted','Rejected','Expired')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_quotations_customer ON quotations(customer_id);
CREATE INDEX IF NOT EXISTS idx_quotations_date ON quotations(quotation_date);


CREATE TABLE IF NOT EXISTS quotation_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
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
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    booking_no TEXT UNIQUE NOT NULL,
    job_type TEXT NOT NULL CHECK(job_type IN ('SE','SI','AE','AI','TE','TI')),
    customer_id INTEGER REFERENCES customers(id),
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
    closing_time TEXT,
    cargo_type TEXT CHECK(cargo_type IN ('FCL','LCL','AIR','TRUCK','')),
    commodity TEXT,
    quantity TEXT,
    remark TEXT,
    quotation_id INTEGER REFERENCES quotations(id),
    status TEXT DEFAULT 'Proceed' CHECK(status IN ('Proceed','Finished','Closed','Canceled')),
    created_by TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_bookings_status ON bookings(status);
CREATE INDEX IF NOT EXISTS idx_bookings_customer ON bookings(customer_id);


-- ===== Shipments (Job) =====
CREATE TABLE IF NOT EXISTS shipments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_no TEXT UNIQUE NOT NULL,
    job_type TEXT NOT NULL CHECK(job_type IN ('SE','SI','AE','AI','TE','TI')),
    booking_id INTEGER REFERENCES bookings(id),
    booking_no TEXT,
    customer_id INTEGER REFERENCES customers(id),
    customer_name TEXT,
    shipper TEXT,
    consignee TEXT,
    notify_party TEXT,
    brand TEXT,
    commodity TEXT,
    combine_commodity TEXT,
    cargo_type TEXT CHECK(cargo_type IN ('FCL','LCL','AIR','TRUCK','')),
    full_or_half TEXT,
    pick_up_date DATE,
    stuffing_date DATE,
    return_date DATE,
    etd DATE,
    eta DATE,
    container_no TEXT,
    seal_no TEXT,
    container_size TEXT,
    weight_origin TEXT,
    weight_port TEXT,
    carrier TEXT,
    m_vessel TEXT,
    feeder TEXT,
    pol TEXT,
    por TEXT,
    pod TEXT,
    final_destination TEXT,
    transhipment_port TEXT,
    bl_no TEXT,
    bl_status TEXT,
    closing_time TEXT,
    overnight_trucking INTEGER DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'Proceed'
        CHECK(status IN ('Proceed','Finished','Closed','Canceled')),
    invoice_no TEXT,
    customer_paid INTEGER DEFAULT 0,
    dn_type TEXT,
    dn_no TEXT,
    remark TEXT,
    created_by TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_shipments_job_type ON shipments(job_type);
CREATE INDEX IF NOT EXISTS idx_shipments_status ON shipments(status);
CREATE INDEX IF NOT EXISTS idx_shipments_etd ON shipments(etd);
CREATE INDEX IF NOT EXISTS idx_shipments_carrier ON shipments(carrier);
CREATE INDEX IF NOT EXISTS idx_shipments_customer ON shipments(customer_id);


-- ===== Shipment Milestones =====
CREATE TABLE IF NOT EXISTS shipment_milestones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    shipment_id INTEGER NOT NULL REFERENCES shipments(id) ON DELETE CASCADE,
    milestone_code TEXT NOT NULL,
    milestone_name TEXT NOT NULL,
    occurred_at TIMESTAMP,
    note TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_milestones_shipment ON shipment_milestones(shipment_id);


-- ===== Financial Documents =====
CREATE TABLE IF NOT EXISTS invoices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_no TEXT UNIQUE NOT NULL,
    doc_type TEXT NOT NULL CHECK(doc_type IN ('INV','BN','CN','DN','SOA')),
    shipment_id INTEGER REFERENCES shipments(id),
    job_no TEXT,
    customer_id INTEGER REFERENCES customers(id),
    customer_name TEXT,
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
    payment_status TEXT DEFAULT 'Unpaid' CHECK(payment_status IN ('Unpaid','Partial','Paid','Cancelled')),
    payment_date DATE,
    ref_doc_no TEXT,
    remark TEXT,
    created_by TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_invoices_customer ON invoices(customer_id);
CREATE INDEX IF NOT EXISTS idx_invoices_status ON invoices(payment_status);
CREATE INDEX IF NOT EXISTS idx_invoices_shipment ON invoices(shipment_id);


CREATE TABLE IF NOT EXISTS invoice_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_id INTEGER NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
    description TEXT NOT NULL,
    quantity REAL DEFAULT 1,
    unit_price REAL DEFAULT 0,
    amount REAL DEFAULT 0,
    sort_order INTEGER DEFAULT 0
);


-- ===== Document Counter (for invoice numbering) =====
CREATE TABLE IF NOT EXISTS doc_counters (
    doc_type TEXT NOT NULL,
    yymm TEXT NOT NULL,
    last_running INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (doc_type, yymm)
);


-- ===== Users (RBAC) =====
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    full_name TEXT,
    email TEXT,
    role TEXT NOT NULL CHECK(role IN ('admin','sales','cs','operation','accounting')),
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


-- ===== Activity Log =====
CREATE TABLE IF NOT EXISTS activity_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES users(id),
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


def get_connection() -> sqlite3.Connection:
    """Return a new SQLite connection with foreign keys enabled."""
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_database() -> None:
    """Create all tables if they do not exist + ensure default users."""
    with get_connection() as conn:
        conn.executescript(SCHEMA)
        # Migrate older shipments table: add new columns if missing
        _ensure_columns(conn, "shipments", {
            "shipper": "TEXT",
            "consignee": "TEXT",
            "notify_party": "TEXT",
            "cargo_type": "TEXT",
            "m_vessel": "TEXT",
            "feeder": "TEXT",
            "por": "TEXT",
            "final_destination": "TEXT",
            "transhipment_port": "TEXT",
            "bl_no": "TEXT",
            "closing_time": "TEXT",
            "booking_id": "INTEGER",
            "customer_id": "INTEGER",
            "created_by": "TEXT",
        })
        # Seed default users if no users exist
        _seed_default_users(conn)


def _ensure_columns(conn, table, columns: dict):
    """Add columns to existing table if they don't exist (for migration)."""
    existing = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}
    for col, ddl in columns.items():
        if col not in existing:
            try:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {ddl}")
            except sqlite3.OperationalError:
                pass


def _seed_default_users(conn):
    """Create default users on first run."""
    import hashlib
    count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    if count > 0:
        return
    
    defaults = [
        ("admin", "admin123", "System Admin", "admin"),
        ("sales", "sales123", "Sales Demo", "sales"),
        ("cs", "cs123", "CS Demo", "cs"),
        ("operation", "ops123", "Operation Demo", "operation"),
        ("accounting", "acc123", "Accounting Demo", "accounting"),
    ]
    for username, pwd, full_name, role in defaults:
        hashed = hashlib.sha256(pwd.encode()).hexdigest()
        conn.execute(
            "INSERT INTO users (username, password_hash, full_name, role) VALUES (?,?,?,?)",
            (username, hashed, full_name, role)
        )
