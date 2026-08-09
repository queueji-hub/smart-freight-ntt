import streamlit as st
import psycopg2
import psycopg2.extras
from contextlib import contextmanager


import sqlite3
from pathlib import Path

class SQLiteCursorAdapter:
    def __init__(self, cur):
        self._cur = cur
        self._last_row = None

    def execute(self, query, params=None):
        q = query.replace("%s", "?")
        ret_col = None
        if "RETURNING" in q.upper():
            parts = q.rsplit("RETURNING", 1)
            q = parts[0]
            ret_col = parts[1].strip().split()[0]

        if params is None:
            self._cur.execute(q)
        else:
            self._cur.execute(q, params)

        if ret_col:
            lastid = self._cur.lastrowid
            self._last_row = {ret_col: lastid, "id": lastid}
        else:
            self._last_row = None
        return self

    def fetchone(self):
        if self._last_row:
            return self._last_row
        row = self._cur.fetchone()
        return dict(row) if row else None

    def fetchall(self):
        rows = self._cur.fetchall()
        return [dict(r) for r in rows]

    @property
    def rowcount(self):
        return self._cur.rowcount

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
    """

    conn = None

    try:
        host = st.secrets.get("DB_HOST", st.secrets.get("host", "localhost"))
        port = int(st.secrets.get("DB_PORT", st.secrets.get("port", 5432)))
        dbname = st.secrets.get("DB_NAME", st.secrets.get("database", "postgres"))
        user = st.secrets.get("DB_USER", st.secrets.get("user", "postgres"))
        password = st.secrets.get("DB_PASSWORD", st.secrets.get("password", ""))

        conn = psycopg2.connect(
            host=host,
            port=port,
            dbname=dbname,
            user=user,
            password=password,
            cursor_factory=psycopg2.extras.RealDictCursor,
            sslmode=st.secrets.get("sslmode", "require"),
            connect_timeout=3
        )

        yield conn

    except Exception:
        # Fall back to local SQLite database if PostgreSQL/Supabase is unreachable
        db_file = Path(__file__).resolve().parent.parent / "data" / "smart_freight.db"
        db_file.parent.mkdir(exist_ok=True, parents=True)
        sqlite_conn = sqlite3.connect(db_file)
        sqlite_conn.row_factory = sqlite3.Row
        adapter = SQLiteConnAdapter(sqlite_conn)
        try:
            yield adapter
        finally:
            adapter.close()

    finally:
        if conn:
            conn.close()


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

        try:
            with conn.cursor() as cur:

                # =====================================================
                # USERS
                # =====================================================
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id SERIAL PRIMARY KEY,
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
                        id SERIAL PRIMARY KEY,
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
                        id SERIAL PRIMARY KEY,
                        company_name TEXT NOT NULL,
                        attention TEXT,
                        tel TEXT,
                        email TEXT,
                        address TEXT,
                        tax_id TEXT,
                        is_active BOOLEAN DEFAULT TRUE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
                        id SERIAL PRIMARY KEY,
                        quotation_no TEXT UNIQUE NOT NULL,
                        customer_name TEXT,
                        issue_date DATE,
                        validity_date DATE,

                        subtotal NUMERIC(15,2) DEFAULT 0,
                        vat_amount NUMERIC(15,2) DEFAULT 0,
                        total_amount NUMERIC(15,2) DEFAULT 0,

                        remark TEXT,
                        status TEXT DEFAULT 'Draft',

                        created_by TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_quotations_no
                    ON quotations(quotation_no)
                """)

                # =====================================================
                # INVOICES
                # =====================================================
                cur.execute("""
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
                        id SERIAL PRIMARY KEY,

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
                # SHIPMENTS
                # =====================================================
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS shipments (
                        id SERIAL PRIMARY KEY,

                        job_no TEXT UNIQUE NOT NULL,

                        status TEXT DEFAULT 'Proceed',
                        job_type TEXT,

                        booking_no TEXT,
                        customer_name TEXT,

                        shipper TEXT,
                        consignee TEXT,

                        cargo_type TEXT,
                        carrier TEXT,

                        pol TEXT,
                        pod TEXT,

                        etd DATE,
                        eta DATE,

                        bl_no TEXT,
                        invoice_no TEXT,

                        customer_paid BOOLEAN DEFAULT FALSE,

                        remark TEXT,

                        created_by TEXT,
                        updated_by TEXT,

                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_shipments_job_no
                    ON shipments(job_no)
                """)

                # =====================================================
                # BOOKINGS
                # =====================================================
                cur.execute("""
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
                        vessel TEXT,
                        voyage TEXT,
                        cargo_type TEXT,
                        container_summary TEXT,
                        gross_weight NUMERIC(15,2),
                        measurement_cbm NUMERIC(15,2),
                        package_qty INTEGER,
                        package_unit TEXT,
                        commodity TEXT,
                        freight_term TEXT,
                        status TEXT DEFAULT 'Proceed',
                        remark TEXT,
                        created_by TEXT,
                        updated_by TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                # =====================================================
                # BILLS OF LADING
                # =====================================================
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS bills_of_lading (
                        id SERIAL PRIMARY KEY,
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

                # =====================================================
                # CONTAINERS
                # =====================================================
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS containers (
                        id SERIAL PRIMARY KEY,
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
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
                        id SERIAL PRIMARY KEY,
                        shipment_id INTEGER NOT NULL,
                        cost_type TEXT NOT NULL,
                        category TEXT,
                        description TEXT,
                        supplier TEXT,
                        quantity NUMERIC(15,2) DEFAULT 1,
                        unit_price NUMERIC(15,2) DEFAULT 0,
                        amount NUMERIC(15,2) DEFAULT 0,
                        currency TEXT DEFAULT 'THB',
                        amount_thb NUMERIC(15,2) DEFAULT 0,
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
                    )
                """)

                # =====================================================
                # FX RATES
                # =====================================================
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS fx_rates (
                        id SERIAL PRIMARY KEY,
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
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER,
                        tenant_id TEXT,
                        entity TEXT,
                        entity_id TEXT,
                        action TEXT,
                        details TEXT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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