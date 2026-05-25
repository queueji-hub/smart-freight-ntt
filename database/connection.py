import streamlit as st
import psycopg2
import psycopg2.extras
from contextlib import contextmanager


# =========================================================
# DATABASE CONNECTION
# =========================================================
@contextmanager
def get_connection():
    """
    PostgreSQL connection manager for Supabase
    """

    conn = None

    try:
        conn = psycopg2.connect(
            host=st.secrets["DB_HOST"],
            port=st.secrets["DB_PORT"],
            dbname=st.secrets["DB_NAME"],
            user=st.secrets["DB_USER"],
            password=st.secrets["DB_PASSWORD"],
            cursor_factory=psycopg2.extras.RealDictCursor,
            sslmode="require"
        )

        yield conn

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
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

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

                conn.commit()

        except Exception:
            conn.rollback()
            raise