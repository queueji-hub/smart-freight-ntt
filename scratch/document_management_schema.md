# Document Management Design & Schema

## Database Schema (PostgreSQL/SQLite compatible)

```sql
CREATE TABLE IF NOT EXISTS documents (
    id SERIAL PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    document_no TEXT NOT NULL, -- e.g. INV-2608-0001
    document_type TEXT NOT NULL, -- e.g. Commercial Invoice
    document_category TEXT NOT NULL, -- e.g. COMMERCIAL
    document_date TEXT,
    description TEXT,
    status TEXT DEFAULT 'Draft',
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by TEXT
);
CREATE INDEX IF NOT EXISTS idx_documents_tenant ON documents(tenant_id);
CREATE INDEX IF NOT EXISTS idx_documents_no ON documents(document_no);

CREATE TABLE IF NOT EXISTS document_versions (
    id SERIAL PRIMARY KEY,
    document_id INTEGER NOT NULL,
    version_number INTEGER NOT NULL,
    original_file_name TEXT NOT NULL,
    mime_type TEXT,
    file_size INTEGER,
    storage_key TEXT NOT NULL,
    storage_provider TEXT DEFAULT 'LOCAL',
    file_hash TEXT,
    uploaded_by TEXT,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_doc_versions_doc_id ON document_versions(document_id);

CREATE TABLE IF NOT EXISTS document_links (
    id SERIAL PRIMARY KEY,
    document_id INTEGER NOT NULL,
    entity_type TEXT NOT NULL, -- e.g., JOB, BOOKING, INVOICE, HBL, MBL
    entity_id TEXT NOT NULL, -- The ID or No of the entity
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by TEXT
);
CREATE INDEX IF NOT EXISTS idx_doc_links_doc_id ON document_links(document_id);
CREATE INDEX IF NOT EXISTS idx_doc_links_entity ON document_links(entity_type, entity_id);
```

## Storage Architecture
For the MVP, we will use local storage in `storage/{tenant_id}/{document_id}/{version_number}_{filename}`.
This can easily be swapped for S3 or Supabase by changing the `storage_provider` logic in the manager.

## Security
- `get_current_tenant_id()` is strictly enforced on all `documents` queries.
- Directory traversal checks are enforced on file read/write.
- File extensions and MIME types are validated against an allowed list. Exe, bat, script files are blocked.
