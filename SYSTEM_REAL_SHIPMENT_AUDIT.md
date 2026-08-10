# SYSTEM REAL SHIPMENT AUDIT
## Smart Freight NTT

### 1. Shipment Table Schema
- Schema holds routing, dates, statuses, and B/L fields.
- Job No. is the UNIQUE identifier and is generated upon Booking Conversion.

### 2. Search Capability Reality
**Documentation Claim**: Job Search supports Job No, Booking No, ETD, ETA.

**Actual Code Reality (`managers/shipment_manager.py`)**:
- Text search checks `job_no`, `booking_no`, `customer_name`, `pol`, `pod`, `vessel`, `voyage`, `hbl_no`, `mbl_no`.
- ETD/ETA filters are implemented in SQL.

**Actual Code Reality (`views/shipment_view.py`)**:
- Similar to Booking, the UI does NOT expose Date Pickers for ETD and ETA filtering. It only provides basic text and status dropdown searches.

### 3. Container & Milestone Relationships
- The code handles Containers and Milestones.
- **Architectural Discrepancy**: Container insert and milestone insert logic is duplicated directly inside `shipment_manager.py` (`add_job_container`, `add_milestone`). It ignores the standalone `managers/container_manager.py` and `managers/milestone_manager.py` files.

**REALITY AUDIT COMPLETE — NO PRODUCTION FILES MODIFIED.**
