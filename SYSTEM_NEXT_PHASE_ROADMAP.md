# SYSTEM NEXT PHASE ROADMAP

> **AUDIT STATUS**: COMPLETED  
> **RULE**: NO CODE IMPLEMENTATIONS OR DATABASE SCHEMAS WERE ALTERED DURING THIS ROADMAP SPECIFICATION AUDIT.

---

## 1. Executive Implementation Priority Matrix (P0 - P4)

| Priority Level | Focus Area | Key Features & Modules | Estimated Target |
| :--- | :--- | :--- | :--- |
| **P0 — Critical / Must Fix** | Search & Ledger Hardening | Multi-column search/filter by `JOB No.`, `Booking No.`, `ETD`, `ETA`, `Customer`, `Vessel` in Booking and Shipment Ledgers | **Phase 1** |
| **P1 — Operationally Important** | Control Tower Exception Monitoring | Dashboard widgets for unconverted bookings, missing containers, missing B/Ls, overdue ETD/ETA alerts | **Phase 2** |
| **P2 — UX Improvement** | Cross-Module Jump Links | Instant navigation links between Quotation $\leftrightarrow$ Booking $\leftrightarrow$ Job $\leftrightarrow$ B/L $\leftrightarrow$ Invoice | **Phase 3** |
| **P3 — Optimization** | Database Indexing & Repository Cleanup | Safe archiving of Group E legacy files, 4-file orphan deletion, composite index creation for `ETD/ETA` | **Phase 4** |
| **P4 — Future Features** | Automated Testing & Financial Enhancements | Automated integration test suite (`scripts/regression_test_suite.py`) and Advanced Accounts Payable (AP) workflows | **Phase 5** |

---

## 2. Phase-by-Phase Technical Specifications

### Phase 1 (P0): Booking & Shipment Ledger Search Hardening
- **Objective**: Implement multi-parameter filtering (`JOB No.`, `Booking No.`, `ETD`, `ETA`, `Customer`, `POL`, `POD`, `Vessel`, `Status`) in Booking and Shipment Ledgers.
- **User Benefit**: Operators and sales reps can locate any booking or active job instantly using key parameters.
- **Files Involved**:
  - [`views/booking_view.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/views/booking_view.py) & [`managers/booking_manager.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/managers/booking_manager.py)
  - [`views/shipment_view.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/views/shipment_view.py) & [`managers/shipment_manager.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/managers/shipment_manager.py)
- **Database Involved**: `bookings`, `shipments`
- **Dependencies**: None
- **Implementation Steps**:
  1. Add `etd_start`, `etd_end`, `eta_start`, `eta_end` date picker controls to `_ledger_view` in `booking_view.py`.
  2. Add text input search bar (`JOB No.`, `Booking No.`, `Container No.`, `HBL/MBL`) to `render()` in `shipment_view.py`.
  3. Update `list_bookings()` and `list_shipments()` query handlers in managers to filter by date ranges and text query strings.
- **QA Steps**: Perform text queries for exact and partial matches; test date range boundary filters.
- **Regression Tests**: Verify existing status filter dropdowns (`Proceed`, `Confirmed`, `In_Transit`) operate correctly.
- **Acceptance Criteria**: All 9 search criteria (`JOB No.`, `Booking No.`, `ETD`, `ETA`, `Customer`, `POL`, `POD`, `Vessel`, `Status`) return filtered dataframes within 300ms.
- **Rollback Plan**: Revert changes in `views/booking_view.py` and `views/shipment_view.py` via `git checkout`.

---

### Phase 2 (P1): Control Tower Exception Monitoring
- **Objective**: Expand [`views/dashboard_view.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/views/dashboard_view.py) to display operational exception alert cards.
- **User Benefit**: Management receives real-time visibility into bottlenecks (unconverted bookings, missing containers, overdue ETD/ETA).
- **Files Involved**:
  - [`views/dashboard_view.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/views/dashboard_view.py)
  - [`managers/dashboard_manager.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/managers/dashboard_manager.py)
- **Database Involved**: `bookings`, `shipments`, `containers`, `bills_of_lading`
- **Dependencies**: Phase 1 search handlers
- **Implementation Steps**:
  1. Add `get_operational_exceptions()` helper in `dashboard_manager.py` querying:
     - Confirmed Bookings not converted to Job.
     - Active Jobs missing assigned Containers.
     - Active Jobs missing an issued B/L.
     - Overdue ETD / ETA shipments.
  2. Render warning card containers in `dashboard_view.py` with direct click-through filters.
- **QA Steps**: Verify exception counts match database state; verify clicking an exception card filters the target ledger.
- **Regression Tests**: Confirm existing KPI cards (Revenue, Active Jobs) remain unchanged.
- **Acceptance Criteria**: Exception metrics calculate accurately with sub-second query performance.
- **Rollback Plan**: Revert `views/dashboard_view.py` and `managers/dashboard_manager.py`.

---

### Phase 3 (P2): `JOB NO.` Standardization & Cross-Module Jump Links
- **Objective**: Establish `JOB NO.` as the primary operational reference across all views and enable jump links between related modules.
- **User Benefit**: Users can click a `JOB NO.` or `Booking No.` anywhere in the app to jump directly to its workspace.
- **Files Involved**:
  - [`views/booking_view.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/views/booking_view.py)
  - [`views/shipment_view.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/views/shipment_view.py)
  - [`views/bl_view.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/views/bl_view.py)
  - [`views/billing_view.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/views/billing_view.py)
- **Database Involved**: `shipments`, `bookings`, `bills_of_lading`, `invoices`
- **Dependencies**: Phase 1 & Phase 2
- **Implementation Steps**:
  1. Add session state navigation keys (`st.session_state["target_job_no"]`).
  2. Render hyperlinked action buttons next to `JOB NO.` and `Booking No.` fields in dataframes.
  3. Ensure jump link sets tab selection and pre-populates target workspace forms.
- **QA Steps**: Click jump links across Quotation $\rightarrow$ Booking $\rightarrow$ Job $\rightarrow$ B/L $\rightarrow$ Invoice.
- **Regression Tests**: Verify manual tab navigation functions normally.
- **Acceptance Criteria**: Clicking any reference link switches tabs and opens the target record workspace within 1 second.
- **Rollback Plan**: Revert navigation button additions in view files.

---

### Phase 4 (P3): Database Indexing & Safe Repository Cleanup
- **Objective**: Create database performance indexes and archive legacy files.
- **User Benefit**: Faster database query response times and a clean codebase without dead code clutter.
- **Files Involved**:
  - [`database/connection.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/database/connection.py)
  - Group E Legacy Files (Archived)
  - Group F Orphan Files (`app.py`, `core/security.py`, `services/booking_service.py`, `services/job_service.py`)
- **Database Involved**: All 12 tables
- **Dependencies**: Phase 1, 2, 3 validation
- **Implementation Steps**:
  1. Add composite indexes in `init_database()`: `idx_shipments_etd_eta`, `idx_shipments_customer`, `idx_bookings_etd_eta`, `idx_bills_of_lading_job_no`.
  2. Move 13 legacy Group E files to `archive/`.
  3. Delete 4 zero-reference orphan Group F files after user confirmation.
- **QA Steps**: Run `python -m py_compile Dashboard.py`; test database connection pool.
- **Regression Tests**: Perform full smoke test across all 15 Streamlit tabs.
- **Acceptance Criteria**: Application compiles cleanly with zero import errors; query execution times decrease.
- **Rollback Plan**: Restore archived files from `archive/` directory; drop created indexes if needed.

---

### Phase 5 (P4): Automated Integration Suite & Financial AP Enhancements
- **Objective**: Build an automated end-to-end integration test suite.
- **User Benefit**: Guarantees zero regression bugs during future feature updates.
- **Files Involved**: [`scripts/seed_shipments.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/scripts/seed_shipments.py), create `scripts/regression_test_suite.py`.
- **Database Involved**: All tables
- **Dependencies**: Phase 1 through 4
- **Implementation Steps**:
  1. Create `scripts/regression_test_suite.py` executing automated CRUD cycles:
     - Customer Creation $\rightarrow$ Quotation $\rightarrow$ Booking $\rightarrow$ Revision $\rightarrow$ Job Conversion $\rightarrow$ Containers $\rightarrow$ B/L $\rightarrow$ Tax Invoice $\rightarrow$ PDF Exporters.
  2. Add automated assertion checks on generated PDF byte stream outputs.
- **QA Steps**: Execute `python scripts/regression_test_suite.py` via CLI.
- **Regression Tests**: 100% test case pass rate.
- **Acceptance Criteria**: All automated lifecycle test cases execute cleanly in under 10 seconds.
- **Rollback Plan**: Delete `scripts/regression_test_suite.py`.
