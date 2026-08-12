# PHASE 29 — SCHEMA DIFFERENCE MATRIX

This matrix identifies the schema differences between the Canonical Application Schema and the Production Supabase database, and defines the action executed for each object.

| Object | Canonical | Production | Action | Status |
| :--- | :--- | :--- | :--- | :--- |
| `bookings.tenant_id` | `TEXT` default `'default'` | Missing | Added column | **RECONCILED** |
| `quotations.tenant_id` | `TEXT` default `'default'` | Missing | Added column | **RECONCILED** |
| `booking_revisions` | Table required | Missing | Created table (with `tenant_id`) | **RECONCILED** |
| `bills_of_lading` | Table required | Missing | Created table | **RECONCILED** |
| `bl_containers` | Table required (junction) | Missing | Created table | **RECONCILED** |
| `bookings.vessel` | `TEXT` | Missing | Added column | **RECONCILED** |
| `bookings.voyage` | `TEXT` | Missing | Added column | **RECONCILED** |
| `bookings.package_qty` | `INTEGER` | Missing | Added column | **RECONCILED** |
| `bookings.package_unit` | `TEXT` | Missing | Added column | **RECONCILED** |
| `bookings.measurement_cbm` | `NUMERIC(15,2)` | Missing | Added column | **RECONCILED** |
| `bookings.gross_weight` | `NUMERIC(15,2)` | Missing | Added column | **RECONCILED** |
| `bookings.container_summary` | `TEXT` | Missing | Added column | **RECONCILED** |
| `bookings.freight_term` | `TEXT` | Missing | Added column | **RECONCILED** |
| `bookings.quotation_no` | `TEXT` | Missing | Added column | **RECONCILED** |
| `bookings.job_no` | `TEXT` | Missing | Added column | **RECONCILED** |
| `bookings.revision_no` | `INTEGER` default `0` | Missing | Added column | **RECONCILED** |
| `bookings.is_current` | `INTEGER` default `1` | Missing | Added column | **RECONCILED** |
| `bookings.previous_booking_id` | `INTEGER` | Missing | Added column | **RECONCILED** |
| `bookings.revision_reason` | `TEXT` | Missing | Added column | **RECONCILED** |
| `bookings.revised_by` | `TEXT` | Missing | Added column | **RECONCILED** |
| `bookings.revised_at` | `TIMESTAMP` | Missing | Added column | **RECONCILED** |
| `quotations` (17 columns) | Missing (address, email, salesperson, shipper, consignee, etc.) | Missing | Added columns | **RECONCILED** |
| `quotation_items` (4 columns) | Missing (`basis`, `quantity`, `unit_rate`, `amount`) | Missing | Added columns | **RECONCILED** |
| `shipments.place_of_receipt` | `TEXT` | Missing | Added column | **RECONCILED** |
| `shipments.transshipment_port` | `TEXT` | Missing | Added column | **RECONCILED** |
| `shipments.place_of_delivery` | `TEXT` | Missing | Added column | **RECONCILED** |
| `shipments.vessel` | `TEXT` | Missing | Added column | **RECONCILED** |
| `shipments.voyage` | `TEXT` | Missing | Added column | **RECONCILED** |
