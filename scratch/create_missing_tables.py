import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from database.connection import get_connection

def create_missing():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS job_costs (
                    id SERIAL PRIMARY KEY,
                    tenant_id TEXT NOT NULL DEFAULT 'default',
                    shipment_id INTEGER,
                    cost_type TEXT,
                    category TEXT,
                    description TEXT,
                    supplier TEXT,
                    quantity NUMERIC,
                    unit_price NUMERIC,
                    amount NUMERIC,
                    currency TEXT,
                    amount_thb NUMERIC,
                    remark TEXT,
                    created_by TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            cur.execute("""
                CREATE TABLE IF NOT EXISTS invoice_payments (
                    id SERIAL PRIMARY KEY,
                    tenant_id TEXT NOT NULL DEFAULT 'default',
                    invoice_id INTEGER,
                    doc_no TEXT,
                    payment_amount NUMERIC,
                    payment_method TEXT,
                    payment_reference TEXT,
                    payment_date DATE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
        conn.commit()
    print("Created missing tables.")

if __name__ == "__main__":
    create_missing()
