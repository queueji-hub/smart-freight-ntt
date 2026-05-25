import streamlit as st
import psycopg2
import psycopg2.extras

try:
    bootstrap()
except Exception as e:
    st.error("System bootstrap failed")
    st.exception(e)
    st.stop()
    
# =========================================================
# DATABASE CONNECTION
# =========================================================
def get_connection():
    """
    PostgreSQL connection for Supabase
    """

    return psycopg2.connect(
        host=st.secrets["DB_HOST"],
        port=st.secrets["DB_PORT"],
        dbname=st.secrets["DB_NAME"],
        user=st.secrets["DB_USER"],
        password=st.secrets["DB_PASSWORD"],
        cursor_factory=psycopg2.extras.RealDictCursor,
        sslmode="require"
    )


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
    Universal DB executor
    """

    conn = get_connection()

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

    except Exception as e:
        conn.rollback()
        raise e

    finally:
        conn.close()


# =========================================================
# INIT DATABASE
# =========================================================
def init_database():
    """
    Initialize required tables
    """

    conn = get_connection()

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
                    is_active INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # =====================================================
            # SESSIONS
            # =====================================================
            cur.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id),
                    token TEXT UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
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
                    is_active INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
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
                    subtotal NUMERIC DEFAULT 0,
                    vat_amount NUMERIC DEFAULT 0,
                    total_amount NUMERIC DEFAULT 0,
                    remark TEXT,
                    status TEXT DEFAULT 'Draft',
                    created_by TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
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

                    subtotal NUMERIC DEFAULT 0,
                    vat_rate NUMERIC DEFAULT 0,
                    vat_amount NUMERIC DEFAULT 0,

                    wht_amount NUMERIC DEFAULT 0,

                    total_amount NUMERIC DEFAULT 0,
                    outstanding NUMERIC DEFAULT 0,

                    payment_status TEXT DEFAULT 'Unpaid',

                    ref_doc_no TEXT,
                    remark TEXT,
                    created_by TEXT,

                    advance_amount NUMERIC DEFAULT 0,
                    wht_1_amount NUMERIC DEFAULT 0,
                    wht_3_amount NUMERIC DEFAULT 0,

                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # =====================================================
            # INVOICE ITEMS
            # =====================================================
            cur.execute("""
                CREATE TABLE IF NOT EXISTS invoice_items (
                    id SERIAL PRIMARY KEY,
                    invoice_id INTEGER REFERENCES invoices(id),

                    description TEXT,
                    quantity NUMERIC DEFAULT 1,
                    unit_price NUMERIC DEFAULT 0,
                    amount NUMERIC DEFAULT 0,

                    tax_type TEXT,
                    wht_type TEXT,

                    sort_order INTEGER DEFAULT 0
                )
            """)

            conn.commit()

    except Exception as e:
        conn.rollback()
        raise e

    finally:
        conn.close()