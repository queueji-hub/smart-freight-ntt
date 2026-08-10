# SYSTEM REAL FILE INVENTORY
## Smart Freight NTT

### 1. Root Application
- **`Dashboard.py`**: Active Production Runtime. Core Streamlit entry point. Approx 10KB. Imported and executed directly by Streamlit.
- **`config.py`**: Active Production Runtime. Holds `JOB_TYPES` and settings. 5KB. 

### 2. Views (UI Layer)
- **`views/booking_view.py`**: Active Production Runtime (37KB).
- **`views/shipment_view.py`**: Active Production Runtime (33KB).
- **`views/dashboard_view.py`**: Active Production Runtime (15KB).
- **`views/bl_view.py`**: Active Production Runtime (22KB).
- **`views/quotation_view.py`**: Active Production Runtime (29KB).
- **`views/crm_view.py`**, **`views/finance.py`**, **`views/profit_view.py`**: Active Production Runtime.

### 3. Managers (Business Logic)
- **`managers/booking_manager.py`**: Active Production Runtime (22KB). Handles Booking SQL.
- **`managers/shipment_manager.py`**: Active Production Runtime (16KB). Handles Shipment SQL. Contains duplicates of container and milestone logic.
- **`managers/container_manager.py`**: Active Production Runtime (10KB). Handles Container ISO checks and SQL. Duplicates some `shipment_manager.py` logic.
- **`managers/auth_manager.py`**: Active Production Runtime (14KB). Handles RBAC.
- **`managers/job_number.py`**: Active Production Runtime (2KB).

### 4. Database
- **`database/connection.py`**: Active Production Runtime (35KB). PostgreSQL with SQLite fallback. Contains DB schema initializers for all tables.

### 5. Categorized Status
- **A = ACTIVE PRODUCTION**: `Dashboard.py`, `database/connection.py`, `views/booking_view.py`, `managers/booking_manager.py`
- **F = DUPLICATE / LEGACY**: The container functions inside `managers/shipment_manager.py`.

**REALITY AUDIT COMPLETE — NO PRODUCTION FILES MODIFIED.**
