"""SQLite database connection and initialization."""
import sqlite3
from pathlib import Path
from config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_name TEXT NOT NULL,
    contact_person TEXT,
    tel TEXT,
    email TEXT,
    address TEXT,
    tax_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

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
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

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

CREATE TABLE IF NOT EXISTS job_counters (
    job_type TEXT NOT NULL,
    yymm TEXT NOT NULL,
    last_running INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (job_type, yymm)
);

CREATE TABLE IF NOT EXISTS shipments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_no TEXT UNIQUE NOT NULL,
    job_type TEXT NOT NULL CHECK(job_type IN ('SE','SI','AE','AI','TE','TI')),
    booking_no TEXT,
    customer_name TEXT,
    brand TEXT,
    commodity TEXT,
    combine_commodity TEXT,
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
    pol TEXT,
    pod TEXT,
    bl_status TEXT,
    overnight_trucking INTEGER DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'In-Progress'
        CHECK(status IN ('In-Progress','Finished','Cancelled','SOC','On-Hold')),
    invoice_no TEXT,
    customer_paid INTEGER DEFAULT 0,
    dn_type TEXT,
    dn_no TEXT,
    remark TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_shipments_job_type ON shipments(job_type);
CREATE INDEX IF NOT EXISTS idx_shipments_status ON shipments(status);
CREATE INDEX IF NOT EXISTS idx_shipments_etd ON shipments(etd);
CREATE INDEX IF NOT EXISTS idx_shipments_carrier ON shipments(carrier);

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
"""


def get_connection() -> sqlite3.Connection:
    """Return a new SQLite connection with foreign keys enabled."""
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_database() -> None:
    """Create all tables if they do not exist."""
    with get_connection() as conn:
        conn.executescript(SCHEMA)
