import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from database.connection import get_connection

def create_doc_tables():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id SERIAL PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    document_no TEXT NOT NULL,
                    document_type TEXT NOT NULL,
                    document_category TEXT NOT NULL,
                    document_date TEXT,
                    description TEXT,
                    status TEXT DEFAULT 'Draft',
                    is_deleted BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_by TEXT
                )
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_documents_tenant ON documents(tenant_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_documents_no ON documents(document_no)")

            cur.execute("""
                CREATE TABLE IF NOT EXISTS document_versions (
                    id SERIAL PRIMARY KEY,
                    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
                    version_number INTEGER NOT NULL,
                    original_file_name TEXT NOT NULL,
                    mime_type TEXT,
                    file_size INTEGER,
                    storage_key TEXT NOT NULL,
                    storage_provider TEXT DEFAULT 'LOCAL',
                    file_hash TEXT,
                    uploaded_by TEXT,
                    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_doc_versions_doc_id ON document_versions(document_id)")

            cur.execute("""
                CREATE TABLE IF NOT EXISTS document_links (
                    id SERIAL PRIMARY KEY,
                    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
                    entity_type TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_by TEXT
                )
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_doc_links_doc_id ON document_links(document_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_doc_links_entity ON document_links(entity_type, entity_id)")
            
        conn.commit()
    print("Document tables created successfully")

if __name__ == "__main__":
    create_doc_tables()
