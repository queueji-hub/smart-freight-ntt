# D76: JOB PROFITABILITY CENTER COMPLETION

## 1. Summary
The Job Profitability Center has been fundamentally overhauled to meet real-world Freight Forwarding standards. The system now strictly segregates financial figures into the four required operational buckets: ESTIMATED, ACCRUED, ACTUAL, and POSTED, ensuring management always sees a true financial picture.

## 2. Key Enhancements
- **Accrual / Uncosted Control**:
  - `job_costs` table expanded with `cost_status` (`ESTIMATED`, `ACCRUED`, `ACTUAL`, `POSTED`).
  - Users can now explicitly accrue costs for jobs that have arrived/delivered even if the vendor AP invoice is missing, allowing accurate monthly uncosted-job reporting.
- **Profitability Bucketing (get_profit_summary)**:
  - `managers/profit_manager.py` completely rewritten to isolate and aggregate:
    - `ar_estimated` vs `ar_actual`
    - `ap_estimated` vs `ap_accrued` vs `ap_actual` vs `ap_posted`.
  - Calculates `estimated_net_profit` separately from `actual_net_profit`.
- **Tenant Isolation Enforcement**:
  - `tenant_id` is now securely fetched and enforced across all new cost insertion, update, delete, and aggregation methods.

## 3. Implementation Steps Taken
- Applied schema updates via additive ALTER TABLE.
- Replaced `managers/profit_manager.py` with the upgraded `cost_status` logic.
- Validated AP Voucher injection (D63 logic) into the POSTED AP bucket.

**D76 Complete. Proceeding to D77 (Freight Document Template Matrix).**
