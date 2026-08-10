# PART 18 - UI REALITY AUDIT

## 1. Existing Navigation (`Dashboard.py`)
- Currently uses a flat list of 15 standard modules (Dashboard, CRM, Quotation, Booking, Shipment, BL, Vendor, AP, Document, Tracking, Billing, Profit, Reports, Users, Settings).
- **Gap:** Completely lacks the professional ERP categorization (Executive, Sales, Operations, Documents, Finance, Compliance) demanded by Phase 18.2.

## 2. Existing Managers
- `managers/report_manager.py` (Sales & Company Perf) - **No UI bound.**
- `managers/month_end_manager.py` - **No UI bound.**
- `managers/commission_manager.py` - **No UI bound.**
- `managers/transport_manager.py` - **No UI bound.**
- `managers/physical_document_manager.py` - **No UI bound.**
- `managers/regulatory_manager.py` - **No UI bound.**
- `managers/document_manager.py` - `document_view.py` and `document_ui.py` exist but need significant expansion to handle Job Checklist, Regeneration, PDF Center.

## 3. Existing PDF Engine
- `pdf/report_generator.py` exists and implements Job Sheet and Company Monthly Report.
- **Gap:** There is no UI button to trigger these PDFs.

## 4. Job Control / Job Sheet
- `shipment_view.py` exists but is currently a flat CRUD form.
- **Gap:** Needs to be transformed into the "Job Sheet 360°" multi-tab view (Overview, Shipment Details, Containers, Milestones, Documents, Revenue, Cost, Profit, etc.).

## 5. Security & RBAC
- Role-based Access Control (`managers.auth_manager`) exists and checks read/write against generic module keys (e.g., `can_read(role, 'shipment')`).

## Audit Conclusion
The UI is fundamentally a flat CRUD app. The backend is an ERP. I must bridge this by rewriting `Dashboard.py` to support nested menus, and creating/updating the views to consume the complex D74-D90 backend managers.
