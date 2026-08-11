# PHASE 22 — ARCHITECTURE REALITY AUDIT

## 1. Domain Manager Consolidation Audit

Below is the status of active vs. duplicate/legacy files inside the `managers/` directory.

| Domain | Canonical Manager | Duplicate/Legacy Files | Status |
| :--- | :--- | :--- | :--- |
| **Customer** | `managers/customer_manager.py` | None | Canonical active |
| **Vendor** | `managers/vendor_manager.py` | None | Canonical active |
| **Quotation** | `managers/quotation_manager.py` | None | Canonical active |
| **Booking** | `managers/booking_manager.py` | None | Canonical active |
| **Shipment / Job**| `managers/shipment_manager.py` | `managers/job_manager.py` | `job_manager.py` queries non-existent table `jobs` and uses legacy `conn.execute(...)`. Safe to deprecate. |
| **Container** | `managers/container_manager.py` | None | Canonical active |
| **Milestone** | `managers/milestone_manager.py` | None | Canonical active |
| **HBL / MBL** | `managers/bl_manager.py` | None | Canonical active |
| **Invoice / AR** | `managers/invoice_manager.py` | None | Canonical active |
| **AP** | `managers/ap_manager.py` | None | Canonical active |
| **Profitability** | `managers/profit_manager.py` | None | Canonical active |
| **Documents** | `managers/document_manager.py` | None | Canonical active |
| **Physical Docs** | `managers/physical_document_manager.py` | None | Canonical active |
| **Transport** | `managers/transport_manager.py` | None | Canonical active |
| **Regulatory** | `managers/regulatory_manager.py` | None | Canonical active |
| **Commission** | `managers/commission_manager.py` | None | Canonical active |
| **Reporting** | `managers/report_manager.py` | None | Canonical active |
| **Month End** | `managers/month_end_manager.py` | None | Canonical active |
| **Storage** | `managers/storage_service.py` | None | Canonical active |
| **Numbering** | `managers/document_numbering_service.py`| `doc_number.py`, `job_number.py`, `quotation_number.py` | Legacy dead numbering files. Safe to deprecate. |

---

## 2. UI View Consolidation Audit

Active views are mapped via `PAGE_ROUTES` in `Dashboard.py`. 

- **Duplicate Views Found**:
  - `views/fx_view.py` is an exact duplicate of `views/profit_view.py` in size and contents. It is not referenced in the navigation menu. Safe to deprecate.
  - `views/finance.py` is unused/dead code (not mapped in `Dashboard.py`). Safe to deprecate.

---

## 3. Database Connection & Transaction Contract Audit

We found multiple calls to the legacy `conn.execute(...)` method instead of standard cursor operations `with conn.cursor() as cur: cur.execute(...)` across the following files:
- `managers/bl_manager.py` (lines 101, 108)
- `managers/container_manager.py` (line 108)
- `managers/dashboard_manager.py` (line 11, 32)
- `managers/finance_manager.py` (multiple lines)
- `managers/fx_manager.py` (multiple lines)
- `managers/template_manager.py` (line 35)

*Action*: Standardize all database executions to cursor-based queries.

---

## 4. Tenant Isolation Audit

We need to review all manager database queries to ensure `tenant_id` boundaries are strictly enforced.

---

## 5. Reporting Period Audit

- Canonical: `get_reporting_period()` in `managers/shipment_manager.py`.
- Checked and verified that all dashboard and performance views leverage this function for EXPORT (ETD month) and IMPORT (ETA month) rules.
