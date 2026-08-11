# PHASE 22 — REPORTING RECONCILIATION FINAL

## 1. Financial Reconciliation Formula
- **Company Revenue** must match the sum of individual Job Revenues.
- **Company Cost** must match the sum of individual Actual Job Costs.
- **Company Gross Profit** = Company Revenue - Company Cost.
- **Salesperson Performance** aggregates total revenue, cost, GP, and eligible commissions correctly.

## 2. Canonical Month Rules
- **EXPORT**: Month of ETD.
- **IMPORT**: Month of ETA.
- Handled uniformly across reports by calling `get_reporting_period()` in `managers/shipment_manager.py`. No manual page-level calculation overrides.
