import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from database.connection import get_connection

def add_tenant_id(table_name):
    with get_connection() as conn:
        with conn.cursor() as cur:
            try:
                cur.execute(f"ALTER TABLE {table_name} ADD COLUMN tenant_id TEXT DEFAULT 'default';")
                conn.commit()
                print(f"Added tenant_id to {table_name}")
            except Exception as e:
                conn.rollback()
                print(f"Skipped {table_name}: {e}")

if __name__ == "__main__":
    for t in ["customers", "shipments", "invoices", "invoice_items", "invoice_payments", "job_costs"]:
        add_tenant_id(t)
