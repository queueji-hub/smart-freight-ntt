import streamlit as st
import psycopg2
import psycopg2.extras
from contextlib import contextmanager


import sqlite3
from pathlib import Path
from decimal import Decimal

# Register adapter for Decimal so local SQLite testing doesn't crash
sqlite3.register_adapter(Decimal, float)

class SQLiteCursorAdapter:
    def __init__(self, cur):
        self._cur = cur
        self._last_row = None

    def execute(self, query, params=None):
        q = query.replace("%s", "?")
        
        # SQLite does not support FOR UPDATE
        if "FOR UPDATE" in q.upper():
            q = q.replace("FOR UPDATE", "")
            q = q.replace("for update", "")
            
        # SQLite uses LIKE instead of ILIKE
        q = q.replace(" ILIKE ", " LIKE ")
        q = q.replace(" ilike ", " like ")
            
        if params is None:
            self._cur.execute(q)
        else:
            self._cur.execute(q, params)
            
        return self

    def fetchone(self):
        row = self._cur.fetchone()
        return dict(row) if row else None

    def fetchall(self):
        rows = self._cur.fetchall()
        return [dict(r) for r in rows]

    @property
    def rowcount(self):
        return self._cur.rowcount

    @property
    def description(self):
        return self._cur.description

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


class SQLiteConnAdapter:
    def __init__(self, sqlite_conn):
        self._conn = sqlite_conn

    def cursor(self):
        return SQLiteCursorAdapter(self._conn.cursor())

    def execute(self, query, params=None):
        cur = self.cursor()
        cur.execute(query, params)
        return cur

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()


# =========================================================
# DATABASE CONNECTION (WITH RESILIENT LOCAL FALLBACK)
# =========================================================
@contextmanager
def get_connection():
    """
    PostgreSQL connection manager for Supabase with automatic SQLite fallback.
    Yields exactly once and propagates exceptions cleanly.
    """
    app_env = st.secrets.get("APP_ENV", "development")
    postgres_conn = None

    try:
        host = st.secrets.get("DB_HOST", st.secrets.get("host", "localhost"))
        port = int(st.secrets.get("DB_PORT", st.secrets.get("port", 5432)))
        dbname = st.secrets.get("DB_NAME", st.secrets.get("database", "postgres"))
        user = st.secrets.get("DB_USER", st.secrets.get("user", "postgres"))
        password = st.secrets.get("DB_PASSWORD", st.secrets.get("password", ""))

        postgres_conn = psycopg2.connect(
            host=host,
            port=port,
            dbname=dbname,
            user=user,
            password=password,
            cursor_factory=psycopg2.extras.RealDictCursor,
            sslmode=st.secrets.get("sslmode", "require"),
            connect_timeout=3
        )
    except Exception as e:
        if app_env == "production":
            raise RuntimeError(f"PostgreSQL connection failed in production mode: {type(e).__name__} - {str(e)}") from e
        
        # Fall back to local SQLite database if PostgreSQL/Supabase is unreachable (dev only)
        db_file = Path(__file__).resolve().parent.parent / "data" / "smart_freight.db"
        db_file.parent.mkdir(exist_ok=True, parents=True)
        sqlite_conn = sqlite3.connect(db_file)
        sqlite_conn.row_factory = sqlite3.Row
        adapter = SQLiteConnAdapter(sqlite_conn)
        try:
            yield adapter
        except Exception:
            adapter.rollback()
            raise
        finally:
            adapter.close()
        return

    # If PostgreSQL connected successfully
    try:
        yield postgres_conn
    except Exception:
        if postgres_conn:
            postgres_conn.rollback()
        raise
    finally:
        if postgres_conn:
            postgres_conn.close()



# =========================================================
# SAFE QUERY EXECUTOR
# =========================================================
def execute_query(
    query,
    params=None,
    fetchone=False,
    fetchall=False,
    commit=False
):
    """
    Universal PostgreSQL executor
    """

    with get_connection() as conn:

        try:
            with conn.cursor() as cur:

                cur.execute(query, params)

                result = None

                if fetchone:
                    result = cur.fetchone()

                elif fetchall:
                    result = cur.fetchall()

                if commit:
                    conn.commit()

                return result

        except Exception:
            conn.rollback()
            raise


# =========================================================
# INIT DATABASE
# =========================================================
def init_database():
    """
    Initialize required tables
    """

    with get_connection() as conn:
        # Do not run SQLite-specific AUTOINCREMENT DDL against PostgreSQL.
        # PostgreSQL schema is managed via external migrations (e.g. models/schema.sql).
        if type(conn).__name__ != 'SQLiteConnAdapter':
            return


        try:
            with conn.cursor() as cur:

                # =====================================================
                # USERS
                # =====================================================
                cur.execute("""
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
                """)

                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_users_username
                    ON users(username)
                """)

                # =====================================================
                # SESSIONS
                # =====================================================
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS sessions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                        token TEXT UNIQUE NOT NULL,
                        expires_at TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                try:
                    cur.execute("ALTER TABLE sessions ADD COLUMN IF NOT EXISTS expires_at TIMESTAMP;")
                except Exception:
                    try:
                        cur.execute("ALTER TABLE sessions ADD COLUMN expires_at TIMESTAMP;")
                    except Exception:
                        pass

                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_sessions_token
                    ON sessions(token)
                """)

                # =====================================================
                # CUSTOMERS
                # =====================================================
                cur.execute("""
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
                        tenant_id TEXT DEFAULT 'default',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_customers_company_name
                    ON customers(company_name)
                """)

                # =====================================================
                # QUOTATIONS
                # =====================================================
                cur.execute("""
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
                        tenant_id TEXT DEFAULT 'default',
                        created_by TEXT,
                        updated_by TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                # Add missing data completeness columns safely
                alter_columns = [
                    "customer_address TEXT",
                    "customer_email TEXT",
                    "salesperson TEXT",
                    "shipper TEXT",
                    "consignee TEXT",
                    "service_type TEXT",
                    "origin TEXT",
                    "destination TEXT",
                    "incoterm TEXT",
                    "freight_term TEXT",
                    "hs_code TEXT",
                    "quantity NUMERIC(15,2) DEFAULT 0",
                    "package_type TEXT",
                    "weight_kg NUMERIC(15,2) DEFAULT 0",
                    "volume_cbm NUMERIC(15,2) DEFAULT 0",
                    "container_type TEXT",
                    "container_quantity INTEGER DEFAULT 0",
                    "is_dg BOOLEAN DEFAULT FALSE",
                    "customer_id INTEGER REFERENCES customers(id)"
                ]
                for col_def in alter_columns:
                    col_name = col_def.split()[0]
                    try:
                        cur.execute(f"ALTER TABLE quotations ADD COLUMN {col_def}")
                    except Exception as e:
                        pass # Column already exists or other error, safe to ignore for SQLite ALTER ADD

                cur.execute("""
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
                """)

                # Add V2 columns to quotation_items safely
                alter_item_columns = [
                    "basis TEXT",
                    "quantity NUMERIC(15,3) DEFAULT 1",
                    "unit_rate NUMERIC(15,2) DEFAULT 0",
                    "amount NUMERIC(15,2) DEFAULT 0"
                ]
                for col_def in alter_item_columns:
                    col_name = col_def.split()[0]
                    try:
                        cur.execute(f"ALTER TABLE quotation_items ADD COLUMN {col_def}")
                    except Exception as e:
                        pass

                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_quotations_no
                    ON quotations(quotation_no)
                """)

                # =====================================================
                # INVOICES
                # =====================================================
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS invoices (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        tenant_id TEXT DEFAULT 'default',
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
                        status TEXT DEFAULT 'OPEN',

                        ref_doc_no TEXT,
                        remark TEXT,

                        created_by TEXT,

                        advance_amount NUMERIC(15,2) DEFAULT 0,
                        wht_1_amount NUMERIC(15,2) DEFAULT 0,
                        wht_3_amount NUMERIC(15,2) DEFAULT 0,

                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_invoices_doc_no
                    ON invoices(doc_no)
                """)

                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_invoices_customer
                    ON invoices(customer_name)
                """)

                # =====================================================
                # INVOICE ITEMS
                # =====================================================
                cur.execute("""
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
                """)

                # =====================================================
                # INVOICE PAYMENTS
                # =====================================================
                cur.execute("""
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
                """)

                # =====================================================
                # SHIPMENTS
                # =====================================================
                cur.execute("""
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

                        tenant_id TEXT DEFAULT 'default',
                        reporting_date DATE,
                        reporting_month TEXT,
                        reporting_year TEXT,
                        financial_status TEXT DEFAULT 'Open',
                        document_status TEXT,
                        mode TEXT DEFAULT 'Sea',
                        closed_at TIMESTAMP,
                        closed_by TEXT,

                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_shipments_job_no
                    ON shipments(job_no)
                """)

                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_shipments_booking_no
                    ON shipments(booking_no)
                """)

                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_shipments_etd
                    ON shipments(etd)
                """)

                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_shipments_eta
                    ON shipments(eta)
                """)

                # =====================================================
                # JOB COUNTERS (FOR ID GENERATION)
                # =====================================================
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS job_counters (
                        job_type TEXT NOT NULL,
                        yymm TEXT NOT NULL,
                        last_running INTEGER NOT NULL DEFAULT 0,
                        PRIMARY KEY (job_type, yymm)
                    )
                """)

                # =====================================================
                # DOC COUNTERS (FOR INVOICE / AR ID GENERATION)
                # =====================================================
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS doc_counters (
                        doc_type TEXT NOT NULL,
                        yymm TEXT NOT NULL,
                        last_running INTEGER NOT NULL DEFAULT 0,
                        PRIMARY KEY (doc_type, yymm)
                    )
                """)

                # =====================================================
                # NEW DOCUMENT NUMBERING SYSTEM COUNTERS (P1.X)
                # =====================================================
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS document_counters (
                        tenant_id TEXT NOT NULL,
                        doc_type TEXT NOT NULL,
                        yymm TEXT NOT NULL,
                        last_running INTEGER NOT NULL DEFAULT 0,
                        PRIMARY KEY (tenant_id, doc_type, yymm)
                    )
                """)

                # =====================================================
                # SHIPMENT MILESTONES
                # =====================================================
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS shipment_milestones (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        shipment_id INTEGER REFERENCES shipments(id) ON DELETE CASCADE,
                        tenant_id TEXT DEFAULT 'default',
                        job_no TEXT,
                        milestone_code TEXT NOT NULL,
                        milestone_name TEXT NOT NULL,
                        event_date TIMESTAMP,
                        planned_date TIMESTAMP,
                        actual_date TIMESTAMP,
                        location TEXT,
                        remark TEXT,
                        remarks TEXT,
                        status TEXT DEFAULT 'Pending',
                        created_by TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_shipment_milestones_job_no
                    ON shipment_milestones(job_no)
                """)

                # =====================================================
                # BOOKINGS
                # =====================================================
                cur.execute("""
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
                """)

                # Add missing Booking revision fields safely
                alter_booking_columns = [
                    "revision_no INTEGER DEFAULT 0",
                    "is_current INTEGER DEFAULT 1",
                    "previous_booking_id INTEGER",
                    "revision_reason TEXT",
                    "revised_by TEXT",
                    "revised_at TIMESTAMP",
                    "quotation_no TEXT",
                    "job_no TEXT"
                ]
                for col_def in alter_booking_columns:
                    try:
                        cur.execute(f"ALTER TABLE bookings ADD COLUMN {col_def}")
                    except Exception:
                        pass

                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_bookings_booking_no
                    ON bookings(booking_no)
                """)

                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_bookings_etd
                    ON bookings(etd)
                """)

                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_bookings_eta
                    ON bookings(eta)
                """)

                # =====================================================
                # BOOKING REVISIONS
                # =====================================================
                cur.execute("""
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
                """)

                # =====================================================
                # BILLS OF LADING
                # =====================================================
                cur.execute("""
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
                """)

                # Add missing B/L fields safely
                alter_bl_columns = [
                    "shipment_id INTEGER",
                    "booking_no TEXT",
                    "place_of_receipt TEXT",
                    "port_of_loading TEXT",
                    "port_of_discharge TEXT",
                    "place_of_delivery TEXT",
                    "final_destination TEXT",
                    "etd DATE",
                    "eta DATE",
                    "bl_date DATE",
                    "place_of_issue TEXT",
                    "number_of_originals TEXT",
                    "freight_term TEXT",
                    "freight_payable_at TEXT",
                    "marks_numbers TEXT",
                    "package_qty INTEGER DEFAULT 0",
                    "package_type TEXT",
                    "description_of_goods TEXT",
                    "gross_weight NUMERIC(15,2) DEFAULT 0",
                    "measurement_cbm NUMERIC(15,2) DEFAULT 0",
                    "hs_code TEXT",
                    "remarks TEXT",
                    "special_instructions TEXT",
                    "created_by TEXT",
                    "updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
                ]
                for col_def in alter_bl_columns:
                    try:
                        cur.execute(f"ALTER TABLE bills_of_lading ADD COLUMN {col_def}")
                    except Exception:
                        pass
                
                # =====================================================
                # BL CONTAINERS (JUNCTION)
                # =====================================================
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS bl_containers (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        bl_id INTEGER NOT NULL REFERENCES bills_of_lading(id) ON DELETE CASCADE,
                        container_id INTEGER NOT NULL REFERENCES containers(id) ON DELETE CASCADE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(bl_id, container_id)
                    )
                """)

                # =====================================================
                # CONTAINERS
                # =====================================================
                cur.execute("""
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
                """)

                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_containers_job_no
                    ON containers(job_no)
                """)

                # =====================================================
                # JOB COSTS (P&L LEDGER LINES)
                # =====================================================
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS job_costs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        shipment_id INTEGER NOT NULL REFERENCES shipments(id) ON DELETE CASCADE,
                        tenant_id TEXT DEFAULT 'default',
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
                        cost_status TEXT DEFAULT 'ESTIMATED',
                        remark TEXT,
                        created_by TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                # =====================================================
                # PROFIT SHEETS
                # =====================================================
                cur.execute("""
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
                """)

                # =====================================================
                # FX RATES
                # =====================================================
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS fx_rates (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        currency TEXT NOT NULL,
                        rate_to_thb NUMERIC(15,4) NOT NULL,
                        effective_date DATE NOT NULL,
                        source TEXT DEFAULT 'manual',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(currency, effective_date)
                    )
                """)

                # =====================================================
                # AUDIT LOGS
                # =====================================================
                cur.execute("""
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
                """)

                # =====================================================
                # DOCUMENT MANAGEMENT
                # =====================================================
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS documents (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
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
                    )
                """)

                # =====================================================
                # EMAIL LOGS
                # =====================================================
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS email_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        tenant_id TEXT NOT NULL,
                        to_email TEXT,
                        cc TEXT,
                        subject TEXT,
                        body TEXT,
                        attachments TEXT,
                        status TEXT,
                        error TEXT,
                        sent_at TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        created_by TEXT
                    )
                """)

                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_documents_tenant 
                    ON documents(tenant_id)
                """)

                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_documents_no 
                    ON documents(document_no)
                """)

                cur.execute("""
                    CREATE TABLE IF NOT EXISTS document_versions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
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
                    )
                """)

                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_doc_versions_doc_id 
                    ON document_versions(document_id)
                """)

                cur.execute("""
                    CREATE TABLE IF NOT EXISTS document_links (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
                        entity_type TEXT NOT NULL,
                        entity_id TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        created_by TEXT
                    )
                """)

                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_doc_links_doc_id 
                    ON document_links(document_id)
                """)

                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_doc_links_entity 
                    ON document_links(entity_type, entity_id)
                """)

                # =====================================================
                # PHASE D61: VENDOR MASTER
                # =====================================================
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS vendors (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        tenant_id TEXT NOT NULL,
                        vendor_code TEXT NOT NULL,
                        legal_name TEXT NOT NULL,
                        tax_id TEXT,
                        country TEXT,
                        currency TEXT DEFAULT 'THB',
                        status TEXT DEFAULT 'Active',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        created_by TEXT,
                        UNIQUE (tenant_id, vendor_code)
                    )
                """)

                # =====================================================
                # PHASE D62: ACCOUNTS PAYABLE
                # =====================================================
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS ap_vouchers (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        tenant_id TEXT NOT NULL,
                        vendor_id INTEGER NOT NULL REFERENCES vendors(id),
                        job_no TEXT,
                        invoice_no TEXT NOT NULL,
                        invoice_date DATE NOT NULL,
                        due_date DATE,
                        currency TEXT DEFAULT 'THB',
                        exchange_rate NUMERIC(15,6) DEFAULT 1.0,
                        subtotal NUMERIC(15,2) DEFAULT 0,
                        tax NUMERIC(15,2) DEFAULT 0,
                        total NUMERIC(15,2) DEFAULT 0,
                        paid_amount NUMERIC(15,2) DEFAULT 0,
                        status TEXT DEFAULT 'DRAFT',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        created_by TEXT,
                        UNIQUE (tenant_id, vendor_id, invoice_no)
                    )
                """)

                # =====================================================
                # TRANSPORT ORDERS
                # =====================================================
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS transport_orders (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        tenant_id TEXT DEFAULT 'default',
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
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                # =====================================================
                # REGULATORY SUBMISSIONS
                # =====================================================
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS regulatory_submissions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        tenant_id TEXT DEFAULT 'default',
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
                    )
                """)

                # =====================================================
                # COMMISSIONS
                # =====================================================
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS commissions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        tenant_id TEXT DEFAULT 'default',
                        job_no TEXT,
                        sales_person TEXT,
                        basis TEXT,
                        rate NUMERIC(5,2) DEFAULT 0,
                        commission_amount NUMERIC(15,2) DEFAULT 0,
                        status TEXT DEFAULT 'DRAFT',
                        approved_by TEXT,
                        calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                conn.commit()

        except Exception:
            conn.rollback()
            raise

    # Ensure default user accounts exist and passwords match configuration
    ensure_default_users()


def ensure_default_users():
    """
    Ensures default admin and demo user accounts exist with updated passwords.
    Guarantees login success on fresh DBs, cloud deployments, or local SQLite fallbacks.
    """
    try:
        from managers.auth_manager import hash_password
        default_users = [
            ("admin", "Admin@2026!", "Administrator", "admin@nattayaraat.com", "admin"),
            ("sales", "Sales@2026!", "Sales Team", "sales@nattayaraat.com", "sales"),
            ("cs", "Cs@2026!", "Customer Service", "cs@nattayaraat.com", "operation"),
            ("operation", "Ops@2026!", "Operations Team", "ops@nattayaraat.com", "operation"),
            ("accounting", "Acc@2026!", "Accounting Team", "acc@nattayaraat.com", "accounting"),
        ]

        with get_connection() as conn:
            with conn.cursor() as cur:
                for username, password, full_name, email, role in default_users:
                    pw_hash = hash_password(password)
                    cur.execute("""
                        INSERT INTO users (username, password_hash, full_name, email, role, is_active)
                        VALUES (%s, %s, %s, %s, %s, 1)
                        ON CONFLICT (username) DO UPDATE SET password_hash = EXCLUDED.password_hash, role = EXCLUDED.role
                    """, (username, pw_hash, full_name, email, role))
                conn.commit()
    except Exception as e:
        print(f"[WARN] ensure_default_users failed: {str(e)}")