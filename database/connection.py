import psycopg2
from psycopg2.extras import RealDictCursor

DB_CONFIG = {
    "host": "localhost",
    "database": "smart_freight",
    "user": "postgres",
    "password": "postgres",
    "port": 5432,
}

# =========================================================
# CORE CONNECTION
# =========================================================
def get_connection():
    return psycopg2.connect(**DB_CONFIG)


# =========================================================
# SAFE EXECUTOR (ใช้ทั้งระบบ)
# =========================================================
def execute(query, params=None, fetch=False):
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params or ())

            if fetch:
                return cur.fetchall()

            conn.commit()
            return None

    finally:
        conn.close()


# =========================================================
# INIT DATABASE (ใช้ bootstrap)
# =========================================================
def init_database():
    conn = get_connection()
    try:
        with conn.cursor() as cur:

            cur.execute("""
                CREATE TABLE IF NOT EXISTS shipments (
                    id SERIAL PRIMARY KEY,
                    job_no TEXT UNIQUE,
                    status TEXT DEFAULT 'Proceed',
                    job_type TEXT,
                    customer_name TEXT,
                    shipper TEXT,
                    consignee TEXT,
                    pol TEXT,
                    pod TEXT,
                    etd DATE,
                    eta DATE,
                    bl_no TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS bookings (
                    id SERIAL PRIMARY KEY,
                    booking_no TEXT UNIQUE,
                    job_type TEXT,
                    customer_name TEXT,
                    pol TEXT,
                    pod TEXT,
                    etd DATE,
                    eta DATE,
                    status TEXT DEFAULT 'Draft',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS invoices (
                    id SERIAL PRIMARY KEY,
                    doc_no TEXT UNIQUE,
                    customer_name TEXT,
                    total_amount NUMERIC DEFAULT 0,
                    outstanding NUMERIC DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

        conn.commit()

    finally:
        conn.close()