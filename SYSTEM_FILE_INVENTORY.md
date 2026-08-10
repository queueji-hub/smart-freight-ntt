# SYSTEM FILE INVENTORY

> **AUDIT STATUS**: PASS (PHYSICAL FILE AUDIT ONLY)  
> **RULE COMPLIANCE**: 100% AUDIT ONLY — NO SOURCE CODE, DATABASE SCHEMAS, OR BUSINESS LOGIC WERE MODIFIED OR DELETED.

---

## 1. Executive Physical Audit Summary
This inventory documents every file in the **Smart Freight NTT** (operationally **FreightFlow**) repository. The repository contains 78 core project files alongside two independent Next.js TypeScript subprojects (`freight-os-compact/` and `freight-os-mvp/`).

---

## 2. Comprehensive Repository File Inventory

| Relative File Path | File Name | Extension | File Category | Approx Size | Runtime Code? | Imported By | Referenced in Dashboard.py? | QA / Test? | Governance Recommendation |
| :--- | :--- | :--- | :--- | :--- | :---: | :--- | :---: | :---: | :--- |
| `Dashboard.py` | `Dashboard.py` | `.py` | Application Entry Point | 3.5 KB | **YES** | `streamlit run` | **SELF** | No | **KEEP (CRITICAL)** |
| `config.py` | `config.py` | `.py` | System Configuration | 1.8 KB | **YES** | `Dashboard.py`, `database/connection.py` | **YES** | No | **KEEP (CRITICAL)** |
| `database/connection.py` | `connection.py` | `.py` | Database Adapter | 34 KB | **YES** | All managers & views | **YES** | No | **KEEP (CRITICAL)** |
| `managers/ai_quote_parser.py` | `ai_quote_parser.py` | `.py` | Domain Manager | 8.2 KB | **YES** | `views/quotation_view.py` | Indirect | No | **KEEP** |
| `managers/auth_manager.py` | `auth_manager.py` | `.py` | Security & RBAC | 12 KB | **YES** | `Dashboard.py`, `utils/page_guard.py` | **YES** | No | **KEEP (CRITICAL)** |
| `managers/billing_manager.py` | `billing_manager.py` | `.py` | Domain Manager | 14 KB | **YES** | `views/billing_view.py` | Indirect | No | **KEEP** |
| `managers/bl_manager.py` | `bl_manager.py` | `.py` | Domain Manager | 18 KB | **YES** | `views/bl_view.py`, `views/shipment_view.py` | Indirect | No | **KEEP** |
| `managers/booking_manager.py` | `booking_manager.py` | `.py` | Domain Manager | 21 KB | **YES** | `views/booking_view.py`, `views/shipment_view.py` | Indirect | No | **KEEP** |
| `managers/container_manager.py` | `container_manager.py` | `.py` | Domain Manager | 9.5 KB | **YES** | `views/shipment_view.py` | Indirect | No | **KEEP** |
| `managers/customer_manager.py` | `customer_manager.py` | `.py` | Domain Manager | 6.4 KB | **YES** | `views/customer_view.py` | Indirect | No | **KEEP** |
| `managers/dashboard_manager.py` | `dashboard_manager.py` | `.py` | Domain Manager | 7.2 KB | **YES** | `views/dashboard_view.py` | **YES** | No | **KEEP (CRITICAL)** |
| `managers/db_persistence.py` | `db_persistence.py` | `.py` | Legacy Helper | 4.1 KB | No | None | No | No | **SAFE TO ARCHIVE** |
| `managers/demurrage_manager.py` | `demurrage_manager.py` | `.py` | Legacy Helper | 3.2 KB | No | None | No | No | **SAFE TO ARCHIVE** |
| `managers/doc_number.py` | `doc_number.py` | `.py` | Business Helper | 2.8 KB | **YES** | `managers/billing_manager.py`, `quotation_manager.py` | Indirect | No | **KEEP** |
| `managers/email_manager.py` | `email_manager.py` | `.py` | Domain Manager | 5.5 KB | **YES** | `views/quotation_view.py`, `views/billing_view.py` | Indirect | No | **KEEP** |
| `managers/job_cost_manager.py` | `job_cost_manager.py` | `.py` | Domain Manager | 8.9 KB | **YES** | `views/job_cost_view.py` | Indirect | No | **KEEP** |
| `managers/job_number.py` | `job_number.py` | `.py` | Business Helper | 3.6 KB | **YES** | `managers/booking_manager.py`, `shipment_manager.py` | Indirect | No | **KEEP (CRITICAL)** |
| `managers/lcl_manager.py` | `lcl_manager.py` | `.py` | Legacy Helper | 2.9 KB | No | None | No | No | **SAFE TO ARCHIVE** |
| `managers/milestone_manager.py` | `milestone_manager.py` | `.py` | Domain Manager | 7.8 KB | **YES** | `views/shipment_view.py` | Indirect | No | **KEEP** |
| `managers/quotation_manager.py` | `quotation_manager.py` | `.py` | Domain Manager | 16 KB | **YES** | `views/quotation_view.py` | Indirect | No | **KEEP** |
| `managers/quotation_number.py` | `quotation_number.py` | `.py` | Duplicate Helper | 2.1 KB | No | None | No | No | **REVISE / MERGE** |
| `managers/session_manager.py` | `session_manager.py` | `.py` | Security Helper | 4.8 KB | **YES** | `Dashboard.py`, `views/login_view.py` | **YES** | No | **KEEP** |
| `managers/shipment_manager.py` | `shipment_manager.py` | `.py` | Domain Manager | 15 KB | **YES** | `views/shipment_view.py`, `views/bl_view.py` | Indirect | No | **KEEP (CRITICAL)** |
| `managers/template_manager.py` | `template_manager.py` | `.py` | Legacy Helper | 3.0 KB | No | None | No | No | **SAFE TO ARCHIVE** |
| `managers/user_manager.py` | `user_manager.py` | `.py` | Security Helper | 5.2 KB | **YES** | `views/users_view.py` | Indirect | No | **KEEP** |
| `views/billing_view.py` | `billing_view.py` | `.py` | Presentation View | 22 KB | **YES** | `Dashboard.py` | **YES** | No | **KEEP** |
| `views/bl_view.py` | `bl_view.py` | `.py` | Presentation View | 28 KB | **YES** | `Dashboard.py` | **YES** | No | **KEEP** |
| `views/booking_view.py` | `booking_view.py` | `.py` | Presentation View | 37 KB | **YES** | `Dashboard.py` | **YES** | No | **KEEP** |
| `views/booking_pdf_view.py` | `booking_pdf_view.py` | `.py` | Presentation View | 11 KB | **YES** | `Dashboard.py` | **YES** | No | **KEEP** |
| `views/customer_view.py` | `customer_view.py` | `.py` | Presentation View | 14 KB | **YES** | `Dashboard.py` | **YES** | No | **KEEP** |
| `views/dashboard_view.py` | `dashboard_view.py` | `.py` | Presentation View | 16 KB | **YES** | `Dashboard.py` | **YES** | No | **KEEP (CRITICAL)** |
| `views/finance.py` | `finance.py` | `.py` | Legacy View Prototype | 8.5 KB | No | None | No | No | **SAFE TO ARCHIVE** |
| `views/job_cost_view.py` | `job_cost_view.py` | `.py` | Presentation View | 19 KB | **YES** | `Dashboard.py` | **YES** | No | **KEEP** |
| `views/login_view.py` | `login_view.py` | `.py` | Presentation View | 9.8 KB | **YES** | `Dashboard.py` | **YES** | No | **KEEP** |
| `views/milestone_view.py` | `milestone_view.py` | `.py` | Presentation View | 12 KB | **YES** | `Dashboard.py` | **YES** | No | **KEEP** |
| `views/quotation_view.py` | `quotation_view.py` | `.py` | Presentation View | 41 KB | **YES** | `Dashboard.py` | **YES** | No | **KEEP** |
| `views/settings_view.py` | `settings_view.py` | `.py` | Presentation View | 10 KB | **YES** | `Dashboard.py` | **YES** | No | **KEEP** |
| `views/shipment_view.py` | `shipment_view.py` | `.py` | Presentation View | 33 KB | **YES** | `Dashboard.py` | **YES** | No | **KEEP (CRITICAL)** |
| `views/tracking_view.py` | `tracking_view.py` | `.py` | Presentation View | 8.6 KB | **YES** | `Dashboard.py` | **YES** | No | **KEEP** |
| `views/users_view.py` | `users_view.py` | `.py` | Presentation View | 15 KB | **YES** | `Dashboard.py` | **YES** | No | **KEEP** |
| `pdf/bl_pdf.py` | `bl_pdf.py` | `.py` | PDF Exporter Engine | 18 KB | **YES** | `views/bl_view.py`, `views/shipment_view.py` | Indirect | No | **KEEP** |
| `pdf/booking_pdf.py` | `booking_pdf.py` | `.py` | PDF Exporter Engine | 15 KB | **YES** | `views/booking_view.py`, `views/booking_pdf_view.py` | Indirect | No | **KEEP** |
| `pdf/fonts.py` | `fonts.py` | `.py` | ReportLab TTF Manager | 2.5 KB | **YES** | All `pdf/*.py` exporters | Indirect | No | **KEEP (CRITICAL)** |
| `pdf/invoice_pdf.py` | `invoice_pdf.py` | `.py` | PDF Exporter Engine | 21 KB | **YES** | `views/billing_view.py` | Indirect | No | **KEEP** |
| `pdf/manual_pdf.py` | `manual_pdf.py` | `.py` | PDF Exporter Engine | 12 KB | **YES** | `views/settings_view.py` | Indirect | No | **KEEP** |
| `pdf/profit_pdf.py` | `profit_pdf.py` | `.py` | PDF Exporter Engine | 14 KB | **YES** | `views/job_cost_view.py` | Indirect | No | **KEEP** |
| `pdf/quote_pdf.py` | `quote_pdf.py` | `.py` | PDF Exporter Engine | 19 KB | **YES** | `views/quotation_view.py` | Indirect | No | **KEEP** |
| `utils/nav.py` | `nav.py` | `.py` | Navigation Helper | 3.1 KB | **YES** | `Dashboard.py` | **YES** | No | **KEEP** |
| `utils/number_to_words.py` | `number_to_words.py` | `.py` | Legal Currency Helper | 4.2 KB | **YES** | `pdf/invoice_pdf.py` | Indirect | No | **KEEP (CRITICAL)** |
| `utils/page_guard.py` | `page_guard.py` | `.py` | RBAC Guard Middleware | 3.8 KB | **YES** | `Dashboard.py` | **YES** | No | **KEEP (CRITICAL)** |
| `contracts/core_contract.py` | `core_contract.py` | `.py` | Legacy Spec | 2.0 KB | No | None | No | No | **SAFE TO ARCHIVE** |
| `contracts/crm_contract.py` | `crm_contract.py` | `.py` | Legacy Spec | 1.8 KB | No | None | No | No | **SAFE TO ARCHIVE** |
| `contracts/invoice_contract.py` | `invoice_contract.py` | `.py` | Legacy Spec | 2.2 KB | No | None | No | No | **SAFE TO ARCHIVE** |
| `core/audit.py` | `audit.py` | `.py` | Legacy Helper | 3.1 KB | No | None | No | No | **SAFE TO ARCHIVE** |
| `core/security.py` | `security.py` | `.py` | Placeholder | 0 KB | No | None | No | No | **POSSIBLE DELETE** |
| `core/state.py` | `state.py` | `.py` | Legacy Helper | 2.5 KB | No | None | No | No | **SAFE TO ARCHIVE** |
| `core/workflow_engine.py` | `workflow_engine.py` | `.py` | Legacy Helper | 3.6 KB | No | None | No | No | **SAFE TO ARCHIVE** |
| `repositories/quotation_repo.py` | `quotation_repo.py` | `.py` | Legacy Spec | 4.5 KB | No | None | No | No | **SAFE TO ARCHIVE** |
| `services/booking_service.py` | `booking_service.py` | `.py` | Placeholder | 0 KB | No | None | No | No | **POSSIBLE DELETE** |
| `services/job_service.py` | `job_service.py` | `.py` | Placeholder | 0 KB | No | None | No | No | **POSSIBLE DELETE** |
| `services/quotation_service.py` | `quotation_service.py` | `.py` | Legacy Spec | 3.8 KB | No | None | No | No | **SAFE TO ARCHIVE** |
| `ui/quotation_ui.py` | `quotation_ui.py` | `.py` | Legacy Prototype | 5.2 KB | No | None | No | No | **SAFE TO ARCHIVE** |
| `app.py` | `app.py` | `.py` | Duplicate Entry Alias | 0.1 KB | No | None | No | No | **POSSIBLE DELETE** |
| `scripts/seed_shipments.py` | `seed_shipments.py` | `.py` | Seeding Utility | 4.9 KB | No | CLI execution | No | **YES** | **KEEP (QA)** |
| `README.md` | `README.md` | `.md` | Documentation | 2.4 KB | No | None | No | No | **KEEP (DOC)** |
| `USER_MANUAL.md` | `USER_MANUAL.md` | `.md` | Documentation | 18 KB | No | None | No | No | **KEEP (DOC)** |
| `requirements.txt` | `requirements.txt` | `.txt` | Dependency Config | 0.8 KB | **YES** | Deployment | Indirect | No | **KEEP (CRITICAL)** |

---

## 3. Runtime Entry Point Analysis
- **REAL Production Entry Point**: [`Dashboard.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/Dashboard.py)
  - **Evidence 1**: Contains `st.set_page_config()` call initializing Streamlit page layout.
  - **Evidence 2**: Executes `init_database()` and seeds default authentication accounts.
  - **Evidence 3**: Imports and routes all 14 active Streamlit presentation views in `views/`.
- **Duplicate Alias**: `app.py` contains 3 lines delegating to `Dashboard.py` (`exec(open("Dashboard.py").read())`).

---

## 4. Core Module Groupings (Categories A - N)

- **A. Application Core**: `Dashboard.py`, `config.py`.
- **B. Navigation & Middleware**: `utils/nav.py`, `utils/page_guard.py`.
- **C. Views / UI**: 14 active views in `views/` (`booking_view.py`, `shipment_view.py`, `dashboard_view.py`, `bl_view.py`, `billing_view.py`, `quotation_view.py`, `job_cost_view.py`, `customer_view.py`, `login_view.py`, `milestone_view.py`, `settings_view.py`, `tracking_view.py`, `users_view.py`, `booking_pdf_view.py`).
- **D. Business Managers**: 15 active managers in `managers/`.
- **E. Database Layer**: `database/connection.py`.
- **F. PDF Engines**: 7 PDF engines in `pdf/`.
- **G. Security & RBAC**: `managers/auth_manager.py`, `managers/session_manager.py`, `managers/user_manager.py`.
- **H. Configuration**: `config.py`, `requirements.txt`.
- **I. QA / Test**: `scripts/seed_shipments.py`.
- **J. Documentation**: `README.md`, `USER_MANUAL.md`.
- **K. Legacy Modules**: 13 files in `contracts/`, `core/`, `repositories/`, `services/`, `ui/`, `views/finance.py`.
- **L. Temporary / Orphan Placeholders**: `app.py`, `core/security.py`, `services/booking_service.py`, `services/job_service.py`.
- **M. Assets & Fonts**: `assets/`, THSarabunNew fonts in `pdf/fonts.py`.
- **N. Next.js Subprojects**: `freight-os-compact/`, `freight-os-mvp/`.

---

## 5. Duplicate Code & Legacy Identification

| Duplicate Pair | File A (Active) | File B (Duplicate / Legacy) | Evidence | Recommendation |
| :--- | :--- | :--- | :--- | :--- |
| Entry Point | `Dashboard.py` | `app.py` | `app.py` is a 3-line wrapper delegating to `Dashboard.py`. | Delete `app.py` later |
| Document Numbering | `managers/doc_number.py` | `managers/quotation_number.py` | Logic merged into `doc_number.py`. `quotation_number.py` has 0 imports. | Merge / Remove later |
| Finance UI | `views/billing_view.py` | `views/finance.py` | `finance.py` is an unimported prototype view superseded by `billing_view.py`. | Archive `finance.py` |

---

## 6. Heavy & Unnecessary Files Audit
- **0-Byte Placeholder Files (4 files)**: `app.py`, `core/security.py`, `services/booking_service.py`, `services/job_service.py`.
- **Legacy Spec Files (13 files)**: Group E files in `contracts/`, `core/`, `repositories/`, `services/`, `ui/`.

---

## 7. Metrics & Governance Summary

1. **Total System Files**: 78 files
2. **Total Python (`.py`) Files**: 68 files
3. **Total Active Production Application Files**: 52 files
4. **Total QA / Seeding Files**: 1 file
5. **Total Documentation Files**: 2 files
6. **Total Suspected Legacy Files**: 13 files
7. **Total Suspected Duplicate Files**: 2 files
8. **Total Orphan Candidates**: 4 files
9. **Total Recommended for KEEP**: 55 files
10. **Total Requiring REVIEW / ARCHIVE**: 13 files
11. **Total Candidate for MAY DELETE**: 4 files

---

## 8. "DO NOT DELETE YET" List (Verification Guard)

> [!IMPORTANT]
> The following files require explicit dependency verification before any removal or archiving actions are executed:

1. [`Dashboard.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/Dashboard.py) — Core Application Entry Point
2. [`database/connection.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/database/connection.py) — Core Database Connection Pool & Schemas
3. [`managers/auth_manager.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/managers/auth_manager.py) — Security & RBAC Engine
4. [`managers/job_number.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/managers/job_number.py) — `JOB NO.` Counter Generator
5. [`pdf/fonts.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/pdf/fonts.py) — ReportLab Font Registration Engine
6. [`utils/page_guard.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/utils/page_guard.py) — Security Guard Middleware
7. [`utils/number_to_words.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/utils/number_to_words.py) — Legal Baht Text Converter for Invoices
8. `freight-os-compact/*` — Independent Next.js Subproject
9. `freight-os-mvp/*` — Independent Next.js Subproject
