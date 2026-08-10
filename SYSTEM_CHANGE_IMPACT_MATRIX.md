# SYSTEM CHANGE IMPACT MATRIX

> **AUDIT STATUS**: COMPLETED  
> **RULE**: NO SOURCE CODE WAS MODIFIED DURING THIS IMPACT ANALYSIS.

---

## 1. Module-by-Module Technical Impact Matrix

| Module | Files Involved | DB Tables Involved | Upstream Dependencies | Downstream Dependencies | APIs / Functions Used | PDF Dependencies | UI Dependencies | Risk Level | Regression Tests Required |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Quotation** | `views/quotation_view.py`, `managers/quotation_manager.py` | `quotations`, `quotation_items` | Customer CRM | Booking | `list_quotations()`, `create_quotation()` | `pdf/quotation_pdf.py` | Quotation Tab | **LOW** | Test quote creation, rate calculation, PDF export |
| **Booking** | `views/booking_view.py`, `managers/booking_manager.py` | `bookings` | Quotation | Job / Shipment | `list_bookings()`, `create_booking()`, `convert_booking_to_job()` | `pdf/booking_pdf.py` | Booking Ledger & Workspace | **MEDIUM** | Test booking creation, status lock, Job conversion |
| **Booking Revision** | `views/booking_view.py`, `managers/booking_manager.py` | `booking_revisions` | Booking Confirmation | Booking PDF | `create_booking_revision()`, `get_revision_history()` | `pdf/booking_pdf.py` (Historical) | Revision Snapshot Tab | **MEDIUM** | Test revision snapshot creation, reason logging, PDF revision view |
| **Booking PDF** | `pdf/booking_pdf.py`, `pdf/fonts.py` | None | Booking, Revision | Customer Email | `generate_booking_pdf()` | `reportlab` | Download PDF Button | **LOW** | Test PDF font registration, layout rendering, byte stream output |
| **Job / Shipment** | `views/shipment_view.py`, `managers/shipment_manager.py` | `shipments` | Booking Conversion | Containers, Milestones, B/L, Billing | `list_shipments()`, `update_shipment()`, `get_shipment()` | None | Job Control Center UI | **HIGH** | Test `JOB NO.` generation, status workflow, routing updates |
| **Container (J3)** | `views/shipment_view.py`, `managers/container_manager.py` | `containers` | Job / Shipment | B/L Container Mapping | `list_job_containers()`, `add_job_container()` | Feeds `pdf/bl_pdf.py` | Containers Tab | **MEDIUM** | Test container add/delete, VGM weight calculation, B/L linking |
| **Milestone (J3)** | `views/shipment_view.py`, `managers/milestone_manager.py` | `shipment_milestones` | Job / Shipment | Tracking View | `list_milestones()`, `add_milestone()` | None | Milestones Tab, Tracking Portal | **LOW** | Test milestone timestamp logging, location updates |
| **B/L (J4)** | `views/bl_view.py`, `managers/bl_manager.py` | `bills_of_lading`, `bl_containers` | Job, Container | B/L PDF | `create_bl()`, `add_bl_container()`, `update_bl_status()` | `pdf/bl_pdf.py` | B/L Workspace UI | **HIGH** | Test MBL/HBL creation, container mapping, status lock |
| **B/L PDF (J5)** | `pdf/bl_pdf.py`, `pdf/fonts.py` | None | B/L, Container | Customer Export | `generate_bl_pdf()` | `reportlab` | Download B/L Button | **LOW** | Test maritime B/L PDF layout, font rendering, container table output |
| **Dashboard** | `views/dashboard_view.py`, `managers/dashboard_manager.py` | All tables | All Modules | Executive Reporting | `get_dashboard_stats()`, `get_kpi_summary()` | None | Control Tower Screen | **LOW** | Test KPI card aggregation, Plotly chart rendering |
| **Billing / Invoice** | `views/billing_view.py`, `managers/invoice_manager.py` | `invoices`, `invoice_items` | Job / Shipment | Profit Sheet | `create_invoice()`, `list_invoices()` | `pdf/invoice_pdf.py` | Billing Workspace UI | **HIGH** | Test subtotal, VAT 7%, WHT 1%/3%, outstanding calculation |
| **Profit (P&L)** | `views/profit_view.py`, `managers/profit_manager.py` | `profit_sheets`, `job_costs` | Job, Invoice | Executive Reports | `get_profit_sheet()`, `add_job_cost()` | `pdf/profit_pdf.py` | Profit Workspace UI | **MEDIUM** | Test AR/AP summation, net margin %, profit sheet PDF export |
| **Customer CRM** | `views/crm_view.py`, `managers/customer_manager.py` | `customers` | None | Quotation, Booking, Shipment, Invoice | `list_customers()`, `create_customer()` | None | CRM Directory UI | **LOW** | Test customer creation, credit terms updates |
| **Authentication** | `views/login_view.py`, `managers/auth_manager.py` | `users`, `sessions` | None | Entire Platform | `authenticate()`, `verify_password()` | None | Login Screen | **CRITICAL** | Test bcrypt password validation, active status check |
| **RBAC** | `utils/page_guard.py`, `managers/auth_manager.py` | `users` | Auth | All Views | `can()`, `can_read()`, `can_write()` | None | Security Refusal Banners | **CRITICAL** | Test role clearance (`admin`, `sales`, `operation`, `accounting`) |
| **Database** | `database/connection.py` | All 12 tables | Environment Config | All Managers | `get_connection()`, `execute_query()` | None | App Infrastructure | **CRITICAL** | Test Postgres connection, SQLite fallback, seed function |
| **Navigation** | `utils/nav.py` | None | Session State | Dashboard Entry | `render_navigation_bar()` | None | Top Navigation Bar | **MEDIUM** | Test menu tab switching, active role badge rendering |

---

## 2. Requirement-by-Requirement Impact & Modification Scope

### Requirement 1: `JOB NO.` Becomes Primary Job Control Reference
- **Files That MAY Need Modification**: [`views/shipment_view.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/views/shipment_view.py), [`views/bl_view.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/views/bl_view.py), [`views/profit_view.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/views/profit_view.py) (Update label prompts to emphasize `JOB NO.`).
- **Files That MUST NOT Be Touched**: [`managers/job_number.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/managers/job_number.py), [`database/connection.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/database/connection.py) (DB constraint `job_no UNIQUE` is already correctly implemented).
- **Risk Level**: **LOW**.

### Requirement 2: Shipment Search by Job No.
- **Files That MAY Need Modification**: [`views/shipment_view.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/views/shipment_view.py) (Add text search input bar in `render()`).
- **Files That MUST NOT Be Touched**: [`managers/shipment_manager.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/managers/shipment_manager.py) (Existing `get_shipment(job_no)` already supports exact lookup).
- **Risk Level**: **LOW**.

### Requirement 3: Shipment Search by Booking No.
- **Files That MAY Need Modification**: [`views/shipment_view.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/views/shipment_view.py), [`managers/shipment_manager.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/managers/shipment_manager.py) (Add `booking_no` filter parameter to `list_shipments()`).
- **Files That MUST NOT Be Touched**: [`pdf/bl_pdf.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/pdf/bl_pdf.py), [`pdf/invoice_pdf.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/pdf/invoice_pdf.py).
- **Risk Level**: **LOW**.

### Requirement 4: Shipment Search by ETD
- **Files That MAY Need Modification**: [`views/shipment_view.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/views/shipment_view.py), [`managers/shipment_manager.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/managers/shipment_manager.py) (Add `etd_start` / `etd_end` date filter).
- **Files That MUST NOT Be Touched**: [`database/connection.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/database/connection.py) (Column `etd DATE` already exists).
- **Risk Level**: **LOW**.

### Requirement 5: Shipment Search by ETA
- **Files That MAY Need Modification**: [`views/shipment_view.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/views/shipment_view.py), [`managers/shipment_manager.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/managers/shipment_manager.py) (Add `eta_start` / `eta_end` date filter).
- **Files That MUST NOT Be Touched**: [`database/connection.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/database/connection.py) (Column `eta DATE` already exists).
- **Risk Level**: **LOW**.

### Requirement 6: Booking Search by Booking No.
- **Files That MAY Need Modification**: None required in backend. UI in [`views/booking_view.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/views/booking_view.py) already supports text search for `booking_no`.
- **Files That MUST NOT Be Touched**: [`managers/booking_manager.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/managers/booking_manager.py).
- **Risk Level**: **NONE**.

### Requirement 7 & 8: Booking Search by ETD / ETA
- **Files That MAY Need Modification**: [`views/booking_view.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/views/booking_view.py), [`managers/booking_manager.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/managers/booking_manager.py) (Add date range picker controls to `_ledger_view`).
- **Files That MUST NOT Be Touched**: [`pdf/booking_pdf.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/pdf/booking_pdf.py).
- **Risk Level**: **LOW**.

### Requirement 9: Consistent Booking and Shipment Filtering Component
- **Files That MAY Need Modification**: Create a new reusable UI helper `views/components/filter_bar.py` (optional refactor in Phase 2).
- **Files That MUST NOT Be Touched**: [`Dashboard.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/Dashboard.py), [`utils/nav.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/utils/nav.py).
- **Risk Level**: **LOW**.

### Requirement 10: Control Tower Dashboard Enhancements
- **Files That MAY Need Modification**: [`views/dashboard_view.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/views/dashboard_view.py), [`managers/dashboard_manager.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/managers/dashboard_manager.py) (Add exception queries for unconverted bookings and overdue ETD/ETA).
- **Files That MUST NOT Be Touched**: [`managers/auth_manager.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/managers/auth_manager.py), [`database/connection.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/database/connection.py).
- **Risk Level**: **LOW**.
