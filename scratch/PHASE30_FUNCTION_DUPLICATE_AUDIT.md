# PHASE 30 — FUNCTION DUPLICATE AUDIT

This audit report identifies redundancies, duplication, and unnecessary complexities across UI views, manager logic, and reporting calculations in the Smart Freight NTT platform.

## 1. UI Screen & Navigation Duplication
* **Job Sheets & Tracking**: 
  * `views/shipment_view.py` acts as a Job Control Center, but there are parallel screens and buttons elsewhere (e.g., `views/tracking_view.py` and `views/ap_view.py`).
  * In `Dashboard.py`, under "OPERATIONS", there are separate menu items for `Job Control Center` (job_control), `Job Sheet 360` (job), `Shipment Tracking` (tracking), `Bill of Lading` (bl), and `Transport Orders` (transport). These separate entries complicate navigation for a small team of 5–10 people.
* **Reports**:
  * `views/reports_view.py` separates "Company Monthly Report" and "Sales Performance" into distinct tabs, implementing separate sub-views and duplicating UI components (date select boxes, generate buttons, etc.).
  * Dashboard has dynamic reporting elements that conflict with main reporting tabs.

## 2. Calculation & Logic Duplication
* **Reporting Month Logic**:
  * Evaluated across `managers/shipment_manager.py` (via `get_reporting_period`) and repeated inside `managers/report_manager.py` and commission calculations. All modules should strictly share `get_reporting_period` from `shipment_manager`.
* **Revenue and GP Calculation**:
  * Repeated queries inside `managers/dashboard_manager.py` and `managers/report_manager.py` compute Company GP and Job Margins from raw tables. This math should be centralized in `managers/report_manager.py`.

## 3. Data Entry Duplication
* **Salesperson Continuity**:
  * Quotations, Bookings, and Jobs each ask for salesperson input at various conversion steps. The salesperson from the Quotation must propagate automatically all the way to the Job without requiring manual input.
