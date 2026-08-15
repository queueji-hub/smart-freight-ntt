# Smart Freight NTT — Production Readiness Runbook

## 1. Code Gate

Required before promotion to `main`:

- Phase 30 Verification workflow is green.
- Streamlit Production Smoke workflow is green.
- No open blocking review comments.

The verification suite currently covers compilation/imports, canonical freight rules, Booking/Quotation SSOT contracts, Charge Master, finance schema, tenant-safe document numbering, profitability, Payables, B/L workspace, Finance workspace, Document Center, PDF smoke, approval workflow and document preflight.

## 2. Production Database Gate

Apply the additive PostgreSQL migrations in this order:

1. `database/migrations/20260815_booking_reference_separation.sql`
2. `database/migrations/20260815_charge_master.sql`
3. `database/migrations/20260815_phase30_ssot_workflow.sql`
4. `database/migrations/20260815_document_numbering_tenant.sql`
5. `database/migrations/20260815_profitability_tenant_contract.sql`
6. `database/migrations/20260815_payables_contract.sql`

After migration, verify the presence of the tenant/approval columns and indexes used by the Phase 30 contracts.

Do not replace the canonical baseline schema destructively. These changes are designed as additive production migrations.

## 3. Secrets / Runtime Gate

The deployment environment must provide the configured PostgreSQL/Supabase connection and any application secrets required by the existing authentication/data layer. Secrets must be stored in the deployment platform secret store, not committed to Git.

## 4. Streamlit UAT Gate

Run the following happy-path sequence in the deployed application:

1. Login as Admin.
2. Open Customers and confirm customer master loads.
3. Create a Quotation and save as Draft.
4. Submit Quotation for Approval.
5. Approve Quotation as an authorized approver.
6. Create a Booking from the commercial data and verify ETD/ETA and freight-type presentation.
7. Submit/Confirm Booking and convert it to a Job.
8. Open the Job and verify customer, route, vessel/voyage, dates and cargo.
9. Create HBL/MBL from the Job and verify container linkage.
10. Generate a B/L PDF and confirm Draft/Approved presentation matches status.
11. Open Finance, create a Draft invoice, edit it, submit/approve it and generate PDF.
12. Register an AP Voucher for a Vendor and verify tenant-safe listing/status transitions.
13. Open Profitability for a Job and verify AR/AP/net profit/margin and PDF output.
14. Open Document Center and verify Job-linked documents are discoverable.

## 5. Security Gate

- Verify a user from another tenant cannot read, update, duplicate or approve documents from the current tenant.
- Verify locked/Issued documents cannot be edited.
- Verify official financial PDFs cannot be issued before the required approval/preflight state.
- Verify duplicate operations always create a new document number and never overwrite the source.

## 6. Promotion Gate

Only after sections 1–5 pass should `feature/phase30-preview` be merged into `main` and the connected Streamlit deployment be promoted to production.

Production Ready means both the automated code gate and the connected deployment/database/UAT gates are green. A green GitHub Actions run alone is not sufficient evidence of Production Ready.