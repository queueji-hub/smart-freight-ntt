# SYSTEM REAL RISK REGISTER
## Smart Freight NTT

### 1. Architectural Risks
- **Duplicated Business Logic (HIGH RISK)**: Inserting containers through `shipment_manager.py` bypasses the ISO 6346 validation logic inside `container_manager.py`.
- **UI / Backend Mismatch (MEDIUM RISK)**: The SQL backend supports complex date filtering (`etd_start`, `eta_start`) but the UI fails to provide inputs for them, limiting user capability.
- **Exception Monitoring (MEDIUM RISK)**: The dashboard does not accurately monitor unconverted bookings or overdue ETAs, despite requirements claiming it acts as a "Control Tower".

### 2. Database Risks
- SQLite Fallback allows silent degradation without immediate failure. If a team scales on SQLite inadvertently, they will face locking issues. 

**REALITY AUDIT COMPLETE — NO PRODUCTION FILES MODIFIED.**
