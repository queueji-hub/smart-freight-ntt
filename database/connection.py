import streamlit as st
import psycopg2
import psycopg2.extras


# =========================================================
# DATABASE CONNECTION
# =========================================================
def get_connection():
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

        return conn

    except Exception as e:
        raise Exception(f"""
DB CONNECTION FAILED ❌

Reason:
{str(e)}

Please check Streamlit Secrets.
""")


# =========================================================
# INIT DATABASE
# =========================================================
def init_database():
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
                user_id INTEGER,
                token TEXT UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)

            # =====================================================
            # CUSTOMERS
            # =====================================================
            cur.execute("""
            CREATE TABLE IF NOT EXISTS customers (
                id SERIAL PRIMARY KEY,
                name TEXT UNIQUE,
                company_name TEXT,
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
                quotation_no TEXT UNIQUE,
                customer_name TEXT,
                issue_date DATE,
                validity_date DATE,
                subtotal NUMERIC DEFAULT 0,
                vat NUMERIC DEFAULT 0,
                grand_total NUMERIC DEFAULT 0,
                status TEXT DEFAULT 'Draft',
                remark TEXT,
                created_by TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
                customer_paid INTEGER DEFAULT 0,
                remark TEXT,
                created_by TEXT,
                updated_by TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)

            # =====================================================
            # INVOICES
            # =====================================================
            cur.execute("""
            CREATE TABLE IF NOT EXISTS invoices (
                id SERIAL PRIMARY KEY,
                doc_no TEXT UNIQUE,
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
                invoice_id INTEGER,
                description TEXT,
                quantity NUMERIC DEFAULT 1,
                unit_price NUMERIC DEFAULT 0,
                amount NUMERIC DEFAULT 0,
                tax_type TEXT,
                wht_type TEXT,
                sort_order INTEGER DEFAULT 0
            )
            """)

            # =====================================================
            # INDEXES
            # =====================================================
            cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_users_username
            ON users(username)
            """)

            cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_shipments_job_no
            ON shipments(job_no)
            """)

            cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_invoice_doc_no
            ON invoices(doc_no)
            """)

            conn.commit()

    except Exception as e:
        conn.rollback()
        raise e

    finally:
        conn.close()