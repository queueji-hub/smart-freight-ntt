# PHASE 20 SUPABASE REALITY AUDIT

## 1. Database Connectivity Assessment
- **Current Supabase schema:** UNKNOWN (Direct connection intentionally blocked for safety / CLI not installed)
- **Assumption:** Supabase is running the pre-Phase 18 (D1-D73) schema.
- **Goal:** Safely deploy D74-D90 structures using an idempotent script without dropping any existing tables or columns.

## 2. Expected Existing Tables (Pre-D74)
These tables should already exist and contain historical data. They must NOT be dropped or truncated:
- `users`, `sessions`, `audit_logs`
- `customers`, `quotations`, `quotation_items`
- `bookings`, `booking_revisions`
- `shipments`, `shipment_milestones`, `containers`
- `bills_of_lading`, `bl_containers`
- `invoices`, `invoice_items`, `invoice_payments`
- `job_costs`, `profit_sheets`
- `job_counters`, `doc_counters`
- `fx_rates`

## 3. Missing Tables (To Be Added from D74-D90)
These tables were introduced during the operational hardening phases:
- `documents`
- `document_versions`
- `document_links`
- `document_counters`
- `regulatory_submissions`
- `transport_orders`
- `physical_documents`
- `commissions`
- `document_templates`
- `email_log`
- `vendors`
- `ap_vouchers`

## 4. Tenant Isolation Fields
All new tables enforce multi-tenancy via the `tenant_id` field.
The script will ensure `tenant_id` is present on all new operational tables.

## 5. Safety Checks
- **Destructive Commands:** 0 `DROP TABLE` commands will be issued.
- **Historical Data:** No historical records will be mutated.
- **Document Numbers:** Sequence counters (`job_counters`, `doc_counters`, `document_counters`) will not be reset.
- **Indexes:** Safe `CREATE INDEX IF NOT EXISTS` will be utilized.
