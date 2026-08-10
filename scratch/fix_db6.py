import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from database.connection import get_connection

def fix_audit_logs():
    with get_connection() as conn:
        with conn.cursor() as cur:
            try:
                # Alter audit_logs user_id to string to accept both integer and uuid
                cur.execute("ALTER TABLE audit_logs ALTER COLUMN user_id TYPE VARCHAR(255);")
            except Exception as e:
                print(e)
            conn.commit()

if __name__ == "__main__":
    fix_audit_logs()
