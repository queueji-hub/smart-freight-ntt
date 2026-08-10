import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from database.connection import get_connection

with get_connection() as conn:
    with conn.cursor() as cur:
        try:
            cur.execute("ALTER TABLE shipments ADD COLUMN sales_person TEXT")
        except Exception as e:
            print(f"sales_person: {e}")
            conn.rollback()
        
        try:
            cur.execute("ALTER TABLE shipments ADD COLUMN operations_owner TEXT")
        except Exception as e:
            print(f"operations_owner: {e}")
            conn.rollback()

        try:
            cur.execute("ALTER TABLE shipments ADD COLUMN customer_reference TEXT")
        except Exception as e:
            print(f"customer_reference: {e}")
            conn.rollback()

        try:
            cur.execute("ALTER TABLE shipments ADD COLUMN quotation_no TEXT")
        except Exception as e:
            print(f"quotation_no: {e}")
            conn.rollback()

    conn.commit()
