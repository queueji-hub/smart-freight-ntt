# AGENT PRODUCTION GAP REPORT

Based on the initial deep READ-ONLY audit, the following critical production gaps have been discovered.

## P0 - PRODUCTION BLOCKERS (Data Loss / Security Leaks)

1. **Tenant Isolation Bypass (Security Leak) - BLOCKED PENDING SCHEMA APPROVAL**
   - **Files:** `customer_manager.py`, `container_manager.py`, `bl_manager.py`, `milestone_manager.py`, `quotation_manager.py`, `invoice_manager.py`, `profit_manager.py`, `schema.sql`
   - **Defect:** Almost all business logic executes `WHERE id = %s` without verifying the `tenant_id`. Furthermore, a schema audit reveals that the `tenant_id` column does **NOT EXIST** on `customers`, `quotations`, `invoices`, `shipments`, `containers`, etc. It only exists on `bookings` and `audit_logs`.
   - **Impact:** Critical Multi-Tenant Security failure.
   - **Remediation Plan (Awaiting Approval):** We must execute an `ALTER TABLE` to append `tenant_id TEXT DEFAULT 'default'` to all primary business tables, and then refactor every `WHERE id = %s` in the Python managers to include `AND tenant_id = %s`. Because altering 15 production tables is a structural migration, **this is BLOCKED pending your explicit confirmation.**

2. **SQLite `AUTOINCREMENT` Hardcoding (Deployment Blocker) - [RESOLVED]**
   - **Defect:** The system relies on Python to initialize tables dynamically using SQLite's `AUTOINCREMENT` syntax, breaking PostgreSQL compatibility.
   - **Status:** I have successfully generated the canonical PostgreSQL `models/schema.sql` artifact using `SERIAL` and standard constraints.

## P1 - HIGH RISK (Financial / State Corruption) - [AUTO-FIX IN PROGRESS]

3. **Financial Precision Loss (Float Conversions)**
   - **Files:** `finance_manager.py`, `invoice_manager.py`, `profit_manager.py`, `quotation_manager.py`
   - **Defect:** Money and currency computations rely on Python's `float()` type. 
   - **Impact:** Rounding errors and binary precision losses in `float` will cause off-by-one-cent accounting errors on large invoices. 
   - **Action:** Migrating all financial mutations to use `decimal.Decimal`.

4. **Transaction Integrity on Multi-Step Workflows**
   - **Files:** `shipment_manager.py`, `booking_manager.py`, `invoice_manager.py`
   - **Defect:** Missing `conn.rollback()` in exception blocks. 
   - **Impact:** Database corruption during partial failures.
   - **Action:** Injecting `conn.rollback()` in all mutation exception handlers.

## P2 - MEDIUM RISK (Configuration / UX)

5. **RBAC UI Hiding without Backend Enforcement**
   - **Files:** `views/*.py`
   - **Defect:** Roles are checked in the UI to hide buttons, but backend managers do not rigorously re-verify the role.
