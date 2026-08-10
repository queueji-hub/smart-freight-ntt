# Document Management System Gap Analysis
Based on standard Enterprise Freight Forwarding ERPs (CargoWise, etc.)

## AVAILABLE
- **Central Document Repository:** Implemented via Global Document Center.
- **Job Attachments:** Integrated into Shipment, Booking, and B/L Views.
- **Version Control:** Hashes, original filenames, multiple versions trackable.
- **Document Linking:** Polymorphic `document_links` table supports associating 1 file with N entities.
- **Search:** Global Document search by Type, Uploader, Date and Number.
- **Access Control & Tenant Isolation:** Secure zero-trust model based on `get_current_tenant_id()`.
- **Status Workflows:** Built-in Draft -> Final lifecycle dropdowns.
- **Document Types:** Extensive pre-configured standard Freight Document taxonomy.
- **Localization:** Thai / English placeholders provided in standard components.
- **Physical Safety:** Executables rejected, 50MB size limit.

## PARTIAL
- **Audit Trail:** Basic `created_by` / `updated_at` stored in documents table. Full logging requires extending existing event sourcing architecture.
- **File Preview:** Safe download implemented. In-line image/pdf preview within Streamlit forms requires iframe workarounds, currently deferred to safe downloads.
- **Document Numbers vs File Names:** Supports inputting Doc number separate from filename. Auto-generation fallback logic exists.

## MISSING
- **OCR Integration:** Not implemented. Database schema is OCR-ready (extractable fields provided), but no ML/AI endpoint is connected.
- **Email Attachment Parsing:** No automated incoming SMTP ingestion pipeline is built.
- **Document Checklist Rules Engine:** Hardcoding trade-lane specific mandatory docs (e.g., Export needs HBL, Import needs D/O) is not implemented due to lack of trade-lane master data.
- **Container / Customer / Vendor Document Integration:** Backend supports this, but UI elements are pending insertion into the Customer and Vendor Master screens (if they exist).

## FUTURE ENHANCEMENTS
- Transition `storage_provider=LOCAL` to an S3/Supabase abstracted class.
- Automated email to Document Repository parser (`managers/email_manager.py` hooks).
- LLM-based Invoice data extraction and automated AP/AR entry.
