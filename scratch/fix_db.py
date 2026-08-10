import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from database.connection import get_connection

def fix_db():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS document_counters (
                    id SERIAL PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    doc_type TEXT NOT NULL,
                    yymm TEXT NOT NULL,
                    last_running INTEGER DEFAULT 0,
                    UNIQUE (tenant_id, doc_type, yymm)
                );
            """)
            
            try:
                cur.execute("ALTER TABLE audit_logs ADD COLUMN details TEXT;")
            except Exception as e:
                conn.rollback()
                print(e)
            
            # recreate audit_logs if missing
            cur.execute("""
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER,
                    tenant_id TEXT,
                    entity_type TEXT,
                    entity_id TEXT,
                    action TEXT,
                    details TEXT,
                    ip_address TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
        conn.commit()

if __name__ == "__main__":
    fix_db()
