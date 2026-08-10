import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from database.connection import get_connection

def fix_job_costs():
    with get_connection() as conn:
        with conn.cursor() as cur:
            try:
                cur.execute("ALTER TABLE job_costs ADD COLUMN exchange_rate NUMERIC DEFAULT 1.0;")
            except Exception as e:
                print(e)
            conn.commit()

if __name__ == "__main__":
    fix_job_costs()
