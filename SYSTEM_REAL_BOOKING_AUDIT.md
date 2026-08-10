# SYSTEM REAL BOOKING AUDIT
## Smart Freight NTT

### 1. Booking Table Schema
- Schema successfully holds fields for routing, cargo, dates, and revision tracking.
- Statuses: DRAFT, SUBMITTED, CONFIRMED, CONVERTED TO JOB, CANCELLED.

### 2. Search Capability Reality
**Documentation Claim**: Booking search can filter by Booking No, Customer, Shipper, Consignee, POL, POD, ETD, ETA, Status, Job Type.

**Actual Code Reality (`managers/booking_manager.py`)**:
- Text search (`search_query`) successfully checks `booking_no`, `job_no`, `customer_name`, `pol`, `pod`, `shipper`, `consignee`, `vessel`, `voyage`.
- Date filters (`etd_start`, `etd_end`, `eta_start`, `eta_end`) are implemented in SQL.

**Actual Code Reality (`views/booking_view.py`)**:
- The UI **ONLY** exposes `status_filter`, `job_type_filter`, and `search_query`.
- The UI **DOES NOT EXPOSE** Date Pickers for ETD and ETA filtering.

### 3. Booking Revisions
- Fully implemented. Saves historical snapshots to `booking_revisions`.
- Can download PDF of historical snapshots.

**REALITY AUDIT COMPLETE — NO PRODUCTION FILES MODIFIED.**
