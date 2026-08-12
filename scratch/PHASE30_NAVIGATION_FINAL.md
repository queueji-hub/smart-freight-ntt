# PHASE 30 — NAVIGATION FINAL SPECIFICATION

The new navigation structure in `Dashboard.py` will consist of the following simplified menu items:

```text
DASHBOARD
  - Dashboard (views/dashboard_view.py)

SALES
  - Customers (views/crm_view.py)
  - Quotations (views/quotation_view.py)
  - Bookings (views/booking_view.py)

OPERATIONS
  - Jobs & Operations (views/shipment_view.py)
  - Bills of Lading (views/bl_view.py)

FINANCE
  - Billing (AR) (views/billing_view.py)
  - Profitability & AP (views/profit_view.py)

REPORTS
  - Management Reports (views/reports_view.py)

DOCUMENTS
  - Document Center (views/document_view.py)

ADMIN
  - Users (views/users_view.py)
  - Settings (views/settings_view.py)
```

By consolidating similar modules:
* Removed redundant standalone pages like "Job Sheet 360", "Transport Orders", "Sales Performance", "Company Monthly Report", "Sales Commission", "AP View", "Physical Documents", "Shipment Tracking".
* Kept operations centralized under "Jobs & Operations" (Job 360).
* Kept reports consolidated under "Management Reports".
