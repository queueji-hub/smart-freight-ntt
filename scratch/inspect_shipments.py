import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from database.connection import get_connection

def inspect():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, job_no, tenant_id FROM shipments ORDER BY id DESC LIMIT 5;")
            print("Shipments:", cur.fetchall())

if __name__ == "__main__":
    inspect()
