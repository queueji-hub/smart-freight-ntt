# D86: JOB SHEET & FINANCIAL CONTROL COMPLETION

## 1. Summary
The Job Sheet has been rigorously verified against the D86 specifications to act as the single operational and financial control page for Freight Forwarding.

## 2. Operational Timeline
- The system captures all crucial routing and customs fields (`pol`, `pod`, `vessel`, `voyage`, `etd`, `eta`, `hbl_no`, `mbl_no`).
- `shipment_milestones` correctly supports the temporal progression of a job (Quotation -> Booking Confirmed -> Cargo Ready -> ETD -> ETA -> Delivery) capturing Planned vs Actual.

## 3. Financial Segregation (Part 5)
- The strict prohibition of mixing bucket logic is inherently enforced by `managers/profit_manager.py` and subsequently `managers/report_manager.py`.
- No `ACTUAL` profit is ever contaminated by `ESTIMATED` invoices. Accruals (`ACCRUED`) are fully supported for vendor cost missing scenarios without faking AP vouchers.
- **Formula explicitly auditable:** Gross Margin = Actual Net / Actual AR.

**D86 Complete.**
