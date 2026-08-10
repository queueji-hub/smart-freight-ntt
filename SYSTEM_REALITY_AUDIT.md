# SYSTEM REALITY AUDIT
## Smart Freight NTT - Real Repository Audit

> [!WARNING]
> This is a Reality Audit. It reflects exactly what is in the codebase, not what previous documentation or theoretical architecture claims.

### A. WHAT IS ACTUALLY WORKING
- **PostgreSQL / SQLite Hybrid DB:** The system successfully connects to PostgreSQL or falls back to SQLite via `database/connection.py`.
- **Dynamic Routing:** `Dashboard.py` dynamically routes using `PAGE_ROUTES = {p[0]: (f"views.{p[2]}_view", "render")}`.
- **Booking Management:** The `managers/booking_manager.py` correctly handles CRUD and Revision tracking for bookings, persisting to `bookings` and `booking_revisions` tables.
- **Job Generation:** Conversion from Booking to Job correctly happens through `managers.booking_manager.convert_booking_to_job`, generating a `job_no` and linking it.

### B. WHAT DOCUMENTATION CLAIMS BUT CODE DOES NOT CONFIRM
- **Booking Filtering by ETA/ETD:** The UI (`views/booking_view.py`) does NOT pass the `etd_start`, `etd_end`, `eta_start`, `eta_end` arguments to `list_bookings()`. The manager supports it, but the UI has omitted the inputs entirely.
- **Dashboard ETD/ETA Alerts:** `views/dashboard_view.py` and `managers/dashboard_manager.py` lack true date-control monitoring for Overdue ETA exception workflows as specified in Phase B requirements.
- **B/L Release Logic:** `views/bl_view.py` only tracks simple statuses. There is no hard constraint preventing B/L issuance without container VGM verification.

### C. WHAT IS MISSING
- Full Date Range UI inputs in `booking_view.py` and `shipment_view.py`.
- Automated Invoice locking when containers lack VGM (although `validate_job_readiness_for_billing` exists, it isn't integrated forcefully in the UI flow).
- True RBAC UI visibility (only basic read/write rules exist in `auth_manager.py`).

### D. WHAT IS DUPLICATED
- **Container Management:** `shipment_manager.py` has `add_job_container` and `list_job_containers` while `container_manager.py` has `add_container` and `list_containers`. They perform identical database insertions.
- **Milestone Management:** `shipment_manager.py` manages milestones (`add_milestone`), duplicating responsibility that should reside in a standalone domain logic.

### E. WHAT IS SAFE TO DELETE (RECOMMENDATION ONLY)
- `managers/container_manager.py` OR `shipment_manager.py`'s container functions.
- Redundant logic in `models/` or `services/` (if any old ORM files still exist).

### F. WHAT SHOULD BE REFACTORED
- The duplicated Container and Milestone logic inside `shipment_manager.py` must be stripped out and delegated to `container_manager.py` and `milestone_manager.py`.
- Implement missing UI fields for `etd_start`, `etd_end`, `eta_start`, `eta_end` in `views/booking_view.py` and `views/shipment_view.py`.

### G. WHAT SHOULD NOT BE TOUCHED
- `Dashboard.py` exception handling and dynamic routing.
- `database/connection.py` SQLite fallback (vital for local development).
- The `booking_revisions` table schema.

### H. WHAT SHOULD BE DONE NEXT
1. Consolidate Container logic.
2. Update `booking_view.py` to include ETD/ETA filters.
3. Update `shipment_view.py` to include ETD/ETA filters.

### I. PRIORITY
- **P0:** Resolve duplicate database insertions for Containers (`add_job_container` vs `add_container`).
- **P1:** Implement missing Date Filters in UI.
- **P2:** Integrate `validate_job_readiness_for_billing` into billing workflow.

**REALITY AUDIT COMPLETE — NO PRODUCTION FILES MODIFIED.**
