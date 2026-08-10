# SYSTEM REAL DATABASE AUDIT
## Smart Freight NTT

### Database Engine
- Engine: PostgreSQL via `psycopg2.extras.RealDictCursor`
- Fallback: Local SQLite (`smart_freight.db`)

### Schema Discrepancies
- The code dynamically handles schema alterations using a resilient try-except block for `ALTER TABLE` adding columns for V2 structures.

### Key Tables
1. **`users`**
   - PK: `id`
   - UNIQUE: `username`

2. **`bookings`**
   - PK: `id`
   - UNIQUE: `booking_no`
   - Indexes: `idx_bookings_booking_no`, `idx_bookings_etd`, `idx_bookings_eta`

3. **`booking_revisions`**
   - Stores historical JSON snapshots.

4. **`shipments`**
   - PK: `id`
   - UNIQUE: `job_no`
   - Indexes: `idx_shipments_job_no`, `idx_shipments_booking_no`, `idx_shipments_etd`, `idx_shipments_eta`

5. **`containers`**
   - FK: `shipment_id` references `shipments(id) ON DELETE CASCADE`
   - UNIQUE: `(shipment_id, container_no)`

**REALITY AUDIT COMPLETE — NO PRODUCTION FILES MODIFIED.**
