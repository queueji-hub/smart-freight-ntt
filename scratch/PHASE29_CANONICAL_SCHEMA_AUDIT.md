# PHASE 29 — CANONICAL SCHEMA AUDIT REPORT

This report audits the canonical database schema definitions from the application source code (`database/connection.py` and `models/schema.sql`).

## 1. Bookings Table Schema
* **Columns**:
  * `id`: SERIAL (Primary Key)
  * `tenant_id`: TEXT (Default: `'default'`, Nullable: YES/NO depending on PostgreSQL behavior, expected not null/nullable)
  * `booking_no`: TEXT (Unique, Not Null)
  * `job_type`: TEXT
  * `customer_id`: INTEGER
  * `customer_name`: TEXT
  * `shipper`: TEXT
  * `consignee`: TEXT
  * `notify_party`: TEXT
  * `pol`: TEXT
  * `por`: TEXT
  * `pod`: TEXT
  * `final_destination`: TEXT
  * `transhipment_port`: TEXT
  * `cy_date`: DATE
  * `cy_place`: TEXT
  * `cfs_date`: DATE
  * `cfs_place`: TEXT
  * `customer_return_date`: DATE
  * `return_place`: TEXT
  * `etd`: DATE
  * `eta`: DATE
  * `carrier`: TEXT
  * `m_vessel`: TEXT
  * `feeder`: TEXT
  * `liner`: TEXT
  * `vessel`: TEXT
  * `voyage`: TEXT
  * `closing_time`: TIMESTAMP
  * `cargo_type`: TEXT
  * `container_summary`: TEXT
  * `gross_weight`: NUMERIC(15,2)
  * `measurement_cbm`: NUMERIC(15,2)
  * `package_qty`: INTEGER
  * `quantity`: INTEGER
  * `package_unit`: TEXT
  * `commodity`: TEXT
  * `freight_term`: TEXT
  * `status`: TEXT (Default: `'Proceed'`)
  * `remark`: TEXT
  * `quotation_id`: INTEGER
  * `quotation_no`: TEXT
  * `job_no`: TEXT
  * `revision_no`: INTEGER (Default: `0`)
  * `is_current`: INTEGER (Default: `1`)
  * `previous_booking_id`: INTEGER
  * `revision_reason`: TEXT
  * `revised_by`: TEXT
  * `revised_at`: TIMESTAMP
  * `created_by`: TEXT
  * `updated_by`: TEXT
  * `created_at`: TIMESTAMP (Default: `CURRENT_TIMESTAMP`)
  * `updated_at`: TIMESTAMP (Default: `CURRENT_TIMESTAMP`)
* **Primary Key**: `id`
* **Foreign Keys**: None
* **Unique Constraints**: `booking_no`
* **Indexes**: `idx_bookings_booking_no` (on `booking_no`), `idx_bookings_etd` (on `etd`), `idx_bookings_eta` (on `eta`)
* **Tenant Isolation**: Mandatory `tenant_id` filtering in `views/booking_view.py`.
* **Application Callers**: `views/booking_view.py`, `managers/booking_manager.py`

## 2. Quotations Table Schema
* **Columns**:
  * `id`: SERIAL (Primary Key)
  * `quotation_no`: TEXT (Unique, Not Null)
  * `job_type`: TEXT
  * `customer_id`: INTEGER
  * `customer_name`: TEXT
  * `customer_address`: TEXT
  * `customer_email`: TEXT
  * `attention`: TEXT
  * `tel`: TEXT
  * `salesperson`: TEXT
  * `shipper`: TEXT
  * `consignee`: TEXT
  * `service_type`: TEXT
  * `origin`: TEXT
  * `pol`: TEXT
  * `transshipment_port`: TEXT
  * `pod`: TEXT
  * `destination`: TEXT
  * `carrier`: TEXT
  * `quotation_date`: DATE
  * `validity_date`: DATE
  * `payment_term`: TEXT
  * `incoterm`: TEXT
  * `freight_term`: TEXT
  * `commodity`: TEXT
  * `hs_code`: TEXT
  * `quantity`: NUMERIC(15,2) (Default: `0`)
  * `package_type`: TEXT
  * `weight_kg`: NUMERIC(15,2) (Default: `0`)
  * `volume_cbm`: NUMERIC(15,2) (Default: `0`)
  * `container_type`: TEXT
  * `container_quantity`: INTEGER (Default: `0`)
  * `is_dg`: BOOLEAN (Default: `FALSE`)
  * `subject`: TEXT
  * `terms_conditions`: TEXT
  * `status`: TEXT (Default: `'ACTIVE'`)
  * `tenant_id`: TEXT (Default: `'default'`)
  * `created_by`: TEXT
  * `updated_by`: TEXT
  * `created_at`: TIMESTAMP (Default: `CURRENT_TIMESTAMP`)
* **Primary Key**: `id`
* **Foreign Keys**: `customer_id` REFERENCES `customers(id)`
* **Unique Constraints**: `quotation_no`
* **Indexes**: `idx_quotations_no` (on `quotation_no`)
* **Tenant Isolation**: Mandatory `tenant_id` filtering.
* **Application Callers**: `views/quotation_view.py`, `managers/quotation_manager.py`

## 3. Booking Revisions Table Schema
* **Columns**:
  * `id`: SERIAL (Primary Key)
  * `booking_no`: TEXT (Not Null)
  * `revision_no`: INTEGER (Not Null)
  * `revised_by`: TEXT
  * `revised_at`: TIMESTAMP (Default: `CURRENT_TIMESTAMP`)
  * `revision_reason`: TEXT
  * `snapshot`: TEXT (Not Null, stores JSON string representing booking state snapshot)
  * `created_at`: TIMESTAMP (Default: `CURRENT_TIMESTAMP`)
* **Primary Key**: `id`
* **Foreign Keys**: None
* **Unique Constraints**: None (Multiple revisions can exist for a `booking_no`)
* **Indexes**: None
* **Tenant Isolation**: Handled via matching booking number checks.
* **Application Callers**: `managers/booking_manager.py`, `views/booking_view.py`

## 4. Bills of Lading Table Schema
* **Columns**:
  * `id`: SERIAL (Primary Key)
  * `bl_no`: TEXT (Unique, Not Null)
  * `job_no`: TEXT (Not Null)
  * `shipment_id`: INTEGER
  * `booking_no`: TEXT
  * `shipper`: TEXT
  * `consignee`: TEXT
  * `notify_party`: TEXT
  * `place_of_receipt`: TEXT
  * `port_of_loading`: TEXT
  * `port_of_discharge`: TEXT
  * `place_of_delivery`: TEXT
  * `final_destination`: TEXT
  * `vessel`: TEXT
  * `voyage`: TEXT
  * `etd`: DATE
  * `eta`: DATE
  * `bl_date`: DATE
  * `place_of_issue`: TEXT
  * `number_of_originals`: TEXT
  * `freight_term`: TEXT
  * `freight_payable_at`: TEXT
  * `marks_numbers`: TEXT
  * `package_qty`: INTEGER (Default: `0`)
  * `package_type`: TEXT
  * `description_of_goods`: TEXT
  * `gross_weight`: NUMERIC(15,2) (Default: `0`)
  * `measurement_cbm`: NUMERIC(15,2) (Default: `0`)
  * `hs_code`: TEXT
  * `remarks`: TEXT
  * `special_instructions`: TEXT
  * `bl_type`: TEXT (Default: `'Original'`)
  * `status`: TEXT (Default: `'Draft'`)
  * `created_by`: TEXT
  * `created_at`: TIMESTAMP (Default: `CURRENT_TIMESTAMP`)
  * `updated_at`: TIMESTAMP (Default: `CURRENT_TIMESTAMP`)
* **Primary Key**: `id`
* **Foreign Keys**: None
* **Unique Constraints**: `bl_no`
* **Indexes**: None
* **Tenant Isolation**: Inherited from linked shipment records.
* **Application Callers**: `views/bl_view.py`, `managers/bl_manager.py`

## 5. BL Containers Table Schema
* **Columns**:
  * `id`: SERIAL (Primary Key)
  * `bl_id`: INTEGER (Not Null)
  * `container_id`: INTEGER (Not Null)
  * `created_at`: TIMESTAMP (Default: `CURRENT_TIMESTAMP`)
* **Primary Key**: `id`
* **Foreign Keys**:
  * `bl_id` REFERENCES `bills_of_lading(id)` ON DELETE CASCADE
  * `container_id` REFERENCES `containers(id)` ON DELETE CASCADE
* **Unique Constraints**: `bl_id`, `container_id`
* **Indexes**: None
* **Tenant Isolation**: Inherited.
* **Application Callers**: `managers/bl_manager.py`
