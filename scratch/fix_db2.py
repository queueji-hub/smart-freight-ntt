import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from database.connection import get_connection

def fix_containers():
    with get_connection() as conn:
        with conn.cursor() as cur:
            try:
                cur.execute("ALTER TABLE containers ADD COLUMN shipment_id INTEGER;")
            except Exception as e:
                conn.rollback()
                print(e)
            
            try:
                cur.execute("ALTER TABLE audit_logs ADD COLUMN timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP;")
            except Exception as e:
                conn.rollback()
                print(e)
        conn.commit()

if __name__ == "__main__":
    fix_containers()
