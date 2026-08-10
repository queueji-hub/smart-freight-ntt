import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from database.connection import get_connection

def fix_email_log():
    with get_connection() as conn:
        with conn.cursor() as cur:
            try:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS email_log (
                        id SERIAL PRIMARY KEY,
                        tenant_id TEXT NOT NULL,
                        to_email TEXT,
                        cc TEXT,
                        subject TEXT,
                        body TEXT,
                        attachments TEXT,
                        status TEXT,
                        error TEXT,
                        sent_at TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        created_by TEXT
                    )
                """)
            except Exception as e:
                print(e)
            conn.commit()

if __name__ == "__main__":
    fix_email_log()
