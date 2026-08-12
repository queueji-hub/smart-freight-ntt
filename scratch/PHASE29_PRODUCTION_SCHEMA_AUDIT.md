# PHASE 29 — PRODUCTION SCHEMA AUDIT REPORT

This report inspects the active production database schema on Supabase (PostgreSQL).

## 1. Table Existence & Gaps
* `bookings`: **PRESENT** (Missing `tenant_id` column)
* `quotations`: **PRESENT** (Missing `tenant_id` column)
* `booking_revisions`: **MISSING**
* `bills_of_lading`: **MISSING**
* `bl_containers`: **MISSING**
* `containers`: **PRESENT**
* `shipments`: **PRESENT**
* `customers`: **PRESENT**

## 2. Table Column Audit

### Bookings (bookings)
* **Columns**: `id, booking_no, job_type, customer_id, customer_name, shipper, consignee, notify_party, pol, por, pod, final_destination, transhipment_port, cy_date, cy_place, cfs_date, cfs_place, customer_return_date, return_place, etd, eta, carrier, m_vessel, feeder, liner, closing_time, cargo_type, commodity, quantity, remark, quotation_id, status, created_by, created_at, updated_at`
* **Status**: Missing `tenant_id`.

### Quotations (quotations)
* **Columns**: `id, quotation_no, job_type, customer_id, customer_name, shipper_cnee, carrier, pol, pod, service_type, attention, tel, incoterm, commodity, weight, quantity_desc, payment_term, quotation_date, validity_date, subject, terms_conditions, prepared_by, status, cargo_type, container_size, estimated_cost, selling_price, created_at`
* **Status**: Missing `tenant_id`.

### Booking Revisions (booking_revisions)
* **Status**: Table is completely missing in Supabase.

### Bills of Lading (bills_of_lading)
* **Status**: Table is completely missing in Supabase.

### BL Containers (bl_containers)
* **Status**: Table is completely missing in Supabase.

### Containers (containers)
* **Columns**: `id, bl_no, job_no, container_no, container_size, container_type, seal_no, gross_weight, volume, status, created_at, shipment_id, net_weight, cbm, temperature, ventilation, vgm_kg, vgm_method, tare_weight, max_payload, volume_cbm, soc_coc, remark, temp_setting, temp_unit, vent_setting, genset_no, oog_length_cm, oog_width_cm, oog_height_cm, un_number, imo_class`

### Shipments (shipments)
* **Columns**: `id, job_no, job_type, booking_id, booking_no, customer_id, customer_name, shipper, consignee, notify_party, brand, commodity, combine_commodity, cargo_type, full_or_half, pick_up_date, stuffing_date, return_date, etd, eta, container_no, seal_no, container_size, weight_origin, weight_port, carrier, m_vessel, feeder, pol, por, pod, final_destination, transhipment_port, bl_no, bl_status, closing_time, overnight_trucking, status, invoice_no, customer_paid, dn_type, dn_no, remark, created_by, created_at, updated_at, tenant_id, reporting_date, reporting_month, reporting_year, financial_status, document_status, mode, closed_at, closed_by, sales_person, operations_owner, customer_reference, quotation_no`

### Customers (customers)
* **Columns**: `id, company_name, contact_person, tel, email, address, tax_id, credit_terms_days, notes, is_active, created_at, updated_at, tenant_id`
