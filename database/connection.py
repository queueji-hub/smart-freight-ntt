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
    id INTEGER PRIMARY KEY AUTOINCREMENT,
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
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    shipment_id INTEGER NOT NULL REFERENCES shipments(id) ON DELETE CASCADE,
    milestone_code TEXT NOT NULL,
    milestone_name TEXT NOT NULL,
    occurred_at TIMESTAMP,
    note TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


-- ===== Financial Documents =====
CREATE TABLE IF NOT EXISTS invoices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
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
    id INTEGER PRIMARY KEY AUTOINCREMENT,
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
    id INTEGER PRIMARY KEY AUTOINCREMENT,
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
    id INTEGER PRIMARY KEY AUTOINCREMENT,
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


# Migration definitions: tables and columns to add for older databases
MIGRATIONS = {
    "customers": {
        "credit_terms_days": "INTEGER DEFAULT 30",
        "notes": "TEXT",
        "is_active": "INTEGER DEFAULT 1",
        "updated_at": "TIMESTAMP",
    },
    "quotations": {
        "status": "TEXT DEFAULT 'Draft'",
        "cargo_type": "TEXT",
        "container_size": "TEXT",
        "estimated_cost": "REAL DEFAULT 0",
        "selling_price": "REAL DEFAULT 0",
    },
    "invoices": {
        "advance_amount": "REAL DEFAULT 0",
        "non_vat_amount": "REAL DEFAULT 0",
        "wht_1_amount": "REAL DEFAULT 0",
        "wht_3_amount": "REAL DEFAULT 0",
    },
    "invoice_items": {
        "tax_type": "TEXT DEFAULT 'VAT 7%'",
        "wht_type": "TEXT DEFAULT 'None'",
    },
    "shipments": {
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
    },
    "users": {
        "is_active": "INTEGER DEFAULT 1",
        "email": "TEXT",
        "full_name": "TEXT",
    },
}


def get_connection() -> sqlite3.Connection:
    """Return a new SQLite connection with foreign keys enabled."""
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    
    # Auto-schedule push to GitHub when commits happen (Streamlit Cloud persistence)
    try:
        from managers.db_persistence import schedule_push
        # Only schedule on commit (write operations)
        original_commit = conn.commit
        def _commit_with_push():
            original_commit()
            schedule_push()
        conn.commit = _commit_with_push
    except Exception:
        pass
    
    return conn


def init_database() -> None:
    """Create all tables + run migrations + seed default users.
    
    On first call: pull latest DB from GitHub if configured.
    """
    # Pull from GitHub before any local DB operations
    try:
        from managers.db_persistence import pull_db_from_github
        pull_db_from_github()
    except Exception:
        pass
    
    with get_connection() as conn:
        # Create new tables (won't affect existing ones)
        conn.executescript(SCHEMA)
        
        # Run migrations: add missing columns to existing tables
        for table, columns in MIGRATIONS.items():
            _ensure_columns(conn, table, columns)
        
        # Seed default users (idempotent)
        _seed_default_users(conn)


def _ensure_columns(conn, table: str, columns: dict) -> None:
    """Add missing columns. Skips if table doesn't exist or column already exists."""
    try:
        existing = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}
    except sqlite3.OperationalError:
        return
    if not existing:
        # Table doesn't exist
        return
    for col, ddl in columns.items():
        if col not in existing:
            try:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {ddl}")
            except sqlite3.OperationalError:
                # Column might already exist or DDL incompatible
                pass


def _seed_default_users(conn) -> None:
    """Create or update default users with secure passwords."""
    import hashlib
    
    defaults = [
        ("admin", "Admin@2026!", "System Admin", "admin"),
        ("sales", "Sales@2026!", "Sales Demo", "sales"),
        ("cs", "Cs@2026!", "CS Demo", "cs"),
        ("operation", "Ops@2026!", "Operation Demo", "operation"),
        ("accounting", "Acc@2026!", "Accounting Demo", "accounting"),
    ]
    
    # Old weak passwords to replace if found (for existing DBs)
    old_passwords = {
        "admin": "admin123", "sales": "sales123", "cs": "cs123",
        "operation": "ops123", "accounting": "acc123",
    }
    
    try:
        existing_users = {row[0]: row[1] for row in
                          conn.execute("SELECT username, password_hash FROM users")}
    except Exception:
        existing_users = {}
    
    for username, pwd, full_name, role in defaults:
        new_hash = hashlib.sha256(pwd.encode()).hexdigest()
        old_hash = hashlib.sha256(old_passwords[username].encode()).hexdigest()
        
        if username not in existing_users:
            # New user — insert
            try:
                conn.execute(
                    "INSERT INTO users (username, password_hash, full_name, role, is_active) "
                    "VALUES (?,?,?,?,1)",
                    (username, new_hash, full_name, role)
                )
            except Exception:
                pass
        elif existing_users[username] == old_hash:
            # User has old weak password — upgrade
            try:
                conn.execute(
                    "UPDATE users SET password_hash=? WHERE username=?",
                    (new_hash, username)
                )
            except Exception:
                pass
