import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from database.connection import get_connection

def apply_templates_schema():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS document_templates (
                    id SERIAL PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    template_code TEXT NOT NULL,
                    template_name TEXT NOT NULL,
                    document_type TEXT,
                    version INTEGER DEFAULT 1,
                    status TEXT DEFAULT 'DRAFT',
                    effective_date DATE,
                    language TEXT DEFAULT 'EN',
                    paper_size TEXT DEFAULT 'A4',
                    is_official_form BOOLEAN DEFAULT FALSE,
                    external_submission_required BOOLEAN DEFAULT FALSE,
                    created_by TEXT,
                    approved_by TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE (tenant_id, template_code, version)
                )
            """)
        conn.commit()

if __name__ == '__main__':
    apply_templates_schema()
