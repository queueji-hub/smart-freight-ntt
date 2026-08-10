# Document Management Audit

## Existing Functionality
- **File Handling**: None for general documents. Only exists as email attachments (`managers/email_manager.py`).
- **Document Tables**: None exist for storing uploaded document metadata.
- **Storage**: No existing object storage configured.
- **PDF Generation**: Exists for Quotation, B/L (HBL/MBL), Profitability, and Invoices. The PDFs are generated on the fly and downloaded directly or sent via email. They are not stored permanently.
- **B/L Handling**: B/L data is stored in DB, PDF is generated on demand.
- **Missing Capabilities**: 
  - File upload UI
  - Document metadata storage
  - Version control for documents
  - Document link mapping to business entities (Jobs, Bookings, etc.)
  - Secure tenant-isolated storage backend.

## Recommended Architecture
1. **Database Schema**:
   - `documents`: Stores document metadata (id, tenant_id, doc_type, status, etc.).
   - `document_versions`: Stores physical file references (version, storage_key, mime_type, size).
   - `document_links`: Polymorphic link table connecting a document to business entities (job_no, booking_no, invoice_id, etc.).
2. **Storage**:
   - Use local filesystem for MVP (e.g., a `storage/` directory in the app folder) structured by `tenant_id/document_id/version_id/filename`.
   - Abstract storage via a `StorageProvider` interface to easily swap to S3/Supabase Storage in the future.
3. **Security**:
   - All DB access filtered by `get_current_tenant_id()`.
   - Storage paths isolated by `tenant_id`.
   - File validation (MIME, extension, size) at upload time.
4. **Integration**:
   - Add a "Documents" tab to Job, Booking, B/L, and Invoice views.
   - Automatically save generated PDFs to the document system.
