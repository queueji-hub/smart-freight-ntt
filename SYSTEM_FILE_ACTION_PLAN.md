# SYSTEM FILE ACTION PLAN

> **AUDIT STATUS**: COMPLETED  
> **RULE**: NO SOURCE CODE HAS BEEN MODIFIED, DELETED, OR REFECTORED DURING THIS AUDIT.

---

## 1. File Classification & Action Plan Matrix

### A. Core Architecture & Navigation (`DO NOT TOUCH` / `KEEP`)

| File Path | Action | Why | Functionality Involved | Depends On / Depended By | Risk | Required QA | Replacement File |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| [`Dashboard.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/Dashboard.py) | **DO NOT TOUCH** | Main application entry point & Streamlit page router. | Routing, CSS injection, Session init | Depended on by CLI `streamlit run Dashboard.py`. Imports all views. | **CRITICAL** | Test app launch, menu navigation, session persistence | None |
| [`config.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/config.py) | **DO NOT TOUCH** | Central system configuration and global constants. | Config, Job Types, VAT/WHT rates | Depended on by `Dashboard.py` and all view modules. | **HIGH** | Test global config loading and dropdown options | None |
| [`requirements.txt`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/requirements.txt) | **DO NOT TOUCH** | Package dependency list. | Deployment packaging | Depended on by `pip` installer. | **HIGH** | Test clean virtualenv `pip install -r requirements.txt` | None |
| [`database/connection.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/database/connection.py) | **DO NOT TOUCH** | PostgreSQL connector with automated SQLite fallback & table initialization. | DB access pool & DDL initialization | Depended on by all managers in `managers/`. | **CRITICAL** | Test Postgres connection, SQLite fallback, seed function | None |
| [`utils/nav.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/utils/nav.py) | **DO NOT TOUCH** | Navigation bar rendering helper. | Top navigation UI | Depended on by `Dashboard.py`. | **CRITICAL** | Test navigation bar rendering and active tab highlights | None |
| [`utils/page_guard.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/utils/page_guard.py) | **DO NOT TOUCH** | RBAC clearance middleware. | Role access security | Depended on by `Dashboard.py` and views. | **CRITICAL** | Test security refusal banners for unauthorized roles | None |
| [`utils/number_to_words.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/utils/number_to_words.py) | **DO NOT TOUCH** | Legal Thai Baht text converter (บาทถ้วน). | Tax Invoice legal wording | Depended on by `pdf/invoice_pdf.py`. | **HIGH** | Test Baht text generation for invoice PDF exports | None |

---

### B. Presentation Layer & View Modules

| File Path | Action | Why | Functionality Involved | Depends On / Depended By | Risk | Required QA | Replacement File |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| [`views/dashboard_view.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/views/dashboard_view.py) | **MODIFY** | Needs operational exception monitoring widgets. | Control Tower Analytics | Depended on by `Dashboard.py`. | **LOW** | Test KPI card rendering and exception alert displays | None |
| [`views/booking_view.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/views/booking_view.py) | **MODIFY** | Needs multi-parameter search/filter controls (`ETD`, `ETA`, `Vessel`). | Booking Ledger & Workspace | Depended on by `Dashboard.py`. | **LOW** | Test booking ledger search, status filters, revision snapshots | None |
| [`views/shipment_view.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/views/shipment_view.py) | **MODIFY** | Needs text search input (`JOB No.`, `Booking No.`, `Container No.`, `HBL/MBL`). | Job Control Center UI | Depended on by `Dashboard.py`. | **LOW** | Test Job search, container tab, milestone tab | None |
| [`views/crm_view.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/views/crm_view.py) | **KEEP** | Customer CRM UI is fully operational. | CRM Directory | Depended on by `Dashboard.py`. | **LOW** | Test customer creation and edit forms | None |
| [`views/quotation_view.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/views/quotation_view.py) | **KEEP** | Quotation workspace & AI PDF parser fully operational. | Commercial Quotations | Depended on by `Dashboard.py`. | **LOW** | Test quotation creation, AI PDF parsing, PDF download | None |
| [`views/bl_view.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/views/bl_view.py) | **KEEP** | B/L Management UI (J4/J5) fully operational. | Maritime B/L Issuance | Depended on by `Dashboard.py`. | **LOW** | Test B/L creation, container attachment, B/L PDF export | None |
| [`views/profit_view.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/views/profit_view.py) | **KEEP** | Job Profitability UI fully operational. | P&L Ledger & Margin Calc | Depended on by `Dashboard.py`. | **LOW** | Test cost line entry, margin %, Profit Sheet PDF export | None |
| [`views/billing_view.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/views/billing_view.py) | **KEEP** | Invoicing UI fully operational. | AR Billing & Tax Invoices | Depended on by `Dashboard.py`. | **LOW** | Test invoice creation, VAT/WHT calculation, Tax Invoice PDF | None |
| [`views/fx_view.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/views/fx_view.py) | **KEEP** | FX Rates Management UI operational. | Currency Exchange Rates | Depended on by `Dashboard.py`. | **LOW** | Test exchange rate input and rate history view | None |
| [`views/users_view.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/views/users_view.py) | **KEEP** | IAM & Access Management UI operational. | Security & Password Reset | Depended on by `Dashboard.py`. | **LOW** | Test user creation, password reset, role update | None |
| [`views/email_helper.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/views/email_helper.py) | **KEEP** | Email dialog modal operational. | Outgoing Document Emails | Depended on by Quotation & Billing views. | **LOW** | Test email dialog modal rendering and attachment sending | None |
| [`views/help_view.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/views/help_view.py) | **KEEP** | User Manual tab operational. | In-App System Help | Depended on by `Dashboard.py`. | **LOW** | Test User Manual markdown rendering | None |
| [`views/login_view.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/views/login_view.py) | **KEEP** | Login Form UI operational. | Authentication Screen | Depended on by `Dashboard.py`. | **LOW** | Test user login authentication flow | None |
| [`views/tracking_view.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/views/tracking_view.py) | **KEEP** | Public Tracking Portal operational. | Shipment Tracking UI | Depended on by `Dashboard.py`. | **LOW** | Test shipment milestone tracking lookup | None |
| [`views/reports_view.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/views/reports_view.py) | **KEEP** | Reports Export UI operational. | Executive Analytics | Depended on by `Dashboard.py`. | **LOW** | Test CSV report generation | None |
| [`views/settings_view.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/views/settings_view.py) | **KEEP** | System Settings UI operational. | Corporate Preferences | Depended on by `Dashboard.py`. | **LOW** | Test branding & setting configuration | None |
| [`views/finance.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/views/finance.py) | **ARCHIVE** | Superseded by `billing_view.py`. | Early Finance Prototype | Unimported. | **LOW** | Verify zero imports in codebase | Archive to `archive/views/` |

---

### C. Business Managers & PDF Engines

| File Path | Action | Why | Functionality Involved | Depends On / Depended By | Risk | Required QA | Replacement File |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| All Core Managers in [`managers/`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/managers) | **KEEP** | Active business logic handlers. | CRUD, RBAC, Calculations | Depended on by View modules & DB connection. | **HIGH** | Test individual manager functions | None |
| [`managers/quotation_number.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/managers/quotation_number.py) | **MERGE** | Duplicates doc numbering logic. | Quotation Counter | Depended on by `utils/quotation_number.py`. | **LOW** | Test document counter generation | Merge into `managers/doc_number.py` |
| [`utils/quotation_number.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/utils/quotation_number.py) | **MERGE** | 3-line import wrapper alias. | Quotation Counter Alias | Depended on by legacy references. | **LOW** | Test document counter generation | Merge into `managers/doc_number.py` |
| All PDF Exporters in [`pdf/`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/pdf) | **KEEP** | Active ReportLab PDF exporter engines. | Document PDF Generation | Depended on by Views & Help tab. | **HIGH** | Test PDF export for Quotation, Booking, B/L, Invoice, Profit | None |

---

## 2. FILES THAT MUST NEVER BE TOUCHED DURING THIS PHASE

> [!CAUTION]
> Modifying any of these core files during feature additions risks causing global application failures, security vulnerabilities, or database corruption.

1. **[`Dashboard.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/Dashboard.py)** — Main routing entry point.
2. **[`database/connection.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/database/connection.py)** — Master PostgreSQL / SQLite fallback connection pool and schema definitions.
3. **[`managers/auth_manager.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/managers/auth_manager.py)** — Core security, bcrypt hashing, and RBAC clearance engine.
4. **[`managers/job_number.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/managers/job_number.py)** — Atomic `JOB NO.` sequence generator.
5. **[`pdf/fonts.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/pdf/fonts.py)** — TrueType font registration engine for ReportLab PDFs.
6. **[`utils/page_guard.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/utils/page_guard.py)** — RBAC middleware security guard.
7. **[`utils/number_to_words.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/utils/number_to_words.py)** — Legal Thai Baht text generator for Tax Invoices.

---

## 3. FILES THAT SHOULD BE MODIFIED FOR JOB / BOOKING SEARCH

To fulfill upcoming search and filter requirements, only the following UI and manager files should be modified:

1. **[`views/booking_view.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/views/booking_view.py)**: Add date range pickers (`ETD`, `ETA`), `Vessel`, and reverse lookup by `Job No.` to `_ledger_view`.
2. **[`managers/booking_manager.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/managers/booking_manager.py)**: Add `etd_start`, `etd_end`, `eta_start`, `eta_end` filter parameters to `list_bookings()`.
3. **[`views/shipment_view.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/views/shipment_view.py)**: Add multi-column search input bar (`JOB No.`, `Booking No.`, `Container No.`, `HBL/MBL`) to `render()`.
4. **[`managers/shipment_manager.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/managers/shipment_manager.py)**: Add `search_query` string parameter and date filters to `list_shipments()`.
5. **[`views/dashboard_view.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/views/dashboard_view.py)**: Add exception monitoring cards (Unconverted Bookings, Missing Containers, Overdue ETD/ETA).

---

## 4. Evidence for Candidates Marked DELETE or ARCHIVE

### Evidence for Candidate Deletions:
- **[`app.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/app.py)**: Contains 3 lines delegating to `Dashboard.py`. Proven unimported across the entire Python codebase.
- **[`core/security.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/core/security.py)**: Exact file size is 2 bytes (empty file). Proven unused; authentication engine lives in `managers/auth_manager.py`.
- **[`services/booking_service.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/services/booking_service.py)**: Exact file size is 0 bytes. Proven unused; booking logic lives in `managers/booking_manager.py`.
- **[`services/job_service.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/services/job_service.py)**: Exact file size is 0 bytes. Proven unused; shipment logic lives in `managers/shipment_manager.py`.

### Evidence for Archiving:
- **`contracts/core_contract.py`**, **`contracts/crm_contract.py`**, **`contracts/invoice_contract.py`**: Unused TypedDict contracts superseded by runtime python dictionary mappings in business managers.
- **`core/audit.py`**, **`core/state.py`**, **`core/workflow_engine.py`**: Early framework helpers superseded by Streamlit session state and inline audit logging in `database/connection.py`.
- **`repositories/quotation_repo.py`**, **`services/quotation_service.py`**, **`ui/quotation_ui.py`**: Early experimental prototype files superseded by `views/quotation_view.py` and `managers/quotation_manager.py`.
- **`managers/db_persistence.py`**, **`managers/demurrage_manager.py`**, **`managers/lcl_manager.py`**, **`managers/template_manager.py`**: Legacy standalone scripts unimported by active presentation views.
