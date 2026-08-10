import os
import sys

# Add root directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database.connection import get_connection

if __name__ == "__main__":
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS vendors (
                    id SERIAL PRIMARY KEY,
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

            cur.execute("""
                CREATE TABLE IF NOT EXISTS ap_vouchers (
                    id SERIAL PRIMARY KEY,
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
        conn.commit()
    print("DB init complete.")
