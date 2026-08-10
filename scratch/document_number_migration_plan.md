# DOCUMENT NUMBER MIGRATION PLAN

## 1. PHASE 1: FOUNDATION (ATOMIC COUNTER SERVICE)
1. Modify `database/connection.py` to create the new canonical `document_counters` table during `init_database()`.
2. Introduce a composite primary key: `PRIMARY KEY (tenant_id, doc_type, yymm)`.
3. Create `managers/document_numbering_service.py` to securely house `generate_document_number(doc_type: str, date_ref: datetime = None)`.
4. Implement strict PostgreSQL transactional generation `ON CONFLICT DO UPDATE ... RETURNING last_running`.

## 2. PHASE 2: QA AND VERIFICATION 
1. Build `scratch/qa_document_numbering.py`.
2. Write extreme concurrency test (100 simultaneous simulated inserts).
3. Prove that `TENANT_A` and `TENANT_B` receive independent sequences (`0001` each).
4. Prove that `generate_document_number` never issues a duplicate.

## 3. PHASE 3: PILOT MIGRATION (QUOTATION)
1. Target `managers/quotation_number.py` and `managers/quotation_manager.py`.
2. Rip out the dangerous `SELECT MAX` logic.
3. Replace with `generate_document_number("QT")`.
4. Ensure historical records (`quotation_no` format) are gracefully retained and unaffected.
5. Update database constraint for `quotations(tenant_id, quotation_no)`.

## 4. PHASE 4: GLOBAL ROLLOUT
Migrate the following using the exact same strategy (One-Manager-At-A-Time):
- `managers/job_number.py` -> Remove.
- `managers/doc_number.py` -> Remove.
- `managers/booking_manager.py` (Migrate to `BK`)
- `managers/shipment_manager.py` (Migrate to `JOB`)
- `managers/invoice_manager.py` (Migrate to `INV`)
- `managers/finance_manager.py` (Migrate to `RCT` / `PAY`)
- `managers/bl_manager.py` (Migrate to `HBL` / `MBL`)

## 5. PHASE 5: REGRESSION & CLEANUP
1. Execute full E2E testing to verify downstream references (e.g., Booking creating Job).
2. Clean up dead modules (`job_number.py`, `doc_number.py`, `quotation_number.py`).
3. Clean up dead tables (`job_counters`, `doc_counters`).
