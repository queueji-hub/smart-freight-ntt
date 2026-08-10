import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from database.connection import get_connection

def patch_bool():
    with get_connection() as conn:
        with conn.cursor() as cur:
            try:
                cur.execute("ALTER TABLE customers ALTER COLUMN is_active TYPE BOOLEAN USING is_active::boolean;")
                conn.commit()
            except Exception as e:
                conn.rollback()
                print(e)
                
            try:
                cur.execute("ALTER TABLE users ALTER COLUMN is_active TYPE BOOLEAN USING is_active::boolean;")
                conn.commit()
            except Exception as e:
                conn.rollback()

if __name__ == "__main__":
    patch_bool()
