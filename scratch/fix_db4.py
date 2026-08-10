import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from database.connection import get_connection

def fix_bl():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("ALTER TABLE containers ALTER COLUMN bl_no DROP NOT NULL;")
        conn.commit()

if __name__ == "__main__":
    fix_bl()
