import sys
import os

# Add workspace root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connection import get_connection

TABLES = ['users', 'sessions', 'customers', 'quotations', 'invoices', 'shipments', 'containers', 'shipment_milestones', 'bookings', 'bills_of_lading', 'job_costs']

def audit_tables():
    with get_connection() as conn:
        if conn.__class__.__name__ == "SQLiteConnAdapter":
            print("Operating in SQLite fallback. Cannot query Supabase catalog.")
            return
            
        with conn.cursor() as cur:
            for table in TABLES:
                cur.execute("""
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_name = %s
                """, (table,))
                rows = cur.fetchall()
                cols = [r['column_name'] for r in rows]
                print(f"Table: {table} | Columns: {', '.join(cols)}")

if __name__ == "__main__":
    audit_tables()
