# SYSTEM DATABASE ARCHITECTURE

> **AUDIT STATUS**: COMPLETED  
> **RULE**: NO DATABASE SCHEMAS, TABLES, INDEXES, OR SQL CODE WERE MODIFIED DURING THIS AUDIT.

---

## 1. Relational Database Overview
The **Smart Freight NTT** database architecture operates primarily on **PostgreSQL (Supabase)** with an automated local **SQLite fallback adapter** implemented in [`database/connection.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/database/connection.py).

All DDL statements, table initialization, index definitions, and default user seedings are defined centrally in `init_database()` and `ensure_default_users()`.

---

## 2. Table-by-Table Schema Specifications

### Table 1: `users`
- **Purpose**: System actor credentials, security role clearance (RBAC), and user profile status.
- **Primary Key**: `id` (INTEGER PK AUTOINCREMENT / SERIAL)
- **Foreign Keys**: None
- **Unique Constraints**: `username` (TEXT UNIQUE)
- **Indexes**: `idx_users_username` on `username`
- **Important Columns**: `username`, `password_hash` (`bcrypt`), `role` (`admin`, `sales`, `operation`, `accounting`), `full_name`, `email`
- **Status Fields**: `is_active` (BOOLEAN DEFAULT TRUE)
- **Date Fields**: `created_at` (TIMESTAMP DEFAULT CURRENT_TIMESTAMP)
- **Relationships**: Parent to `sessions`
- **Runtime Manager**: [`managers/auth_manager.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/managers/auth_manager.py)
- **UI Views**: [`views/login_view.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/views/login_view.py), [`views/users_view.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/views/users_view.py)

---

### Table 2: `sessions`
- **Purpose**: Active user login session tokens for browser refresh persistence.
- **Primary Key**: `id` (INTEGER PK)
- **Foreign Keys**: `user_id` $\rightarrow$ `users(id)` (ON DELETE CASCADE)
- **Unique Constraints**: `token` (TEXT UNIQUE)
- **Indexes**: `idx_sessions_token` on `token`
- **Important Columns**: `token`, `expires_at`
- **Status Fields**: None
- **Date Fields**: `expires_at`, `created_at`
- **Relationships**: Child of `users`
- **Runtime Manager**: [`managers/session_manager.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/managers/session_manager.py)
- **UI Views**: [`Dashboard.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/Dashboard.py)

---

### Table 3: `customers`
- **Purpose**: Customer directory, contact details, tax IDs, and credit terms.
- **Primary Key**: `id` (INTEGER PK)
- **Foreign Keys**: None
- **Unique Constraints**: None
- **Indexes**: `idx_customers_company_name` on `company_name`
- **Important Columns**: `company_name`, `contact_person`, `tel`, `email`, `address`, `tax_id`, `credit_terms_days` (DEFAULT 30)
- **Status Fields**: `is_active` (BOOLEAN DEFAULT TRUE)
- **Date Fields**: `created_at`, `updated_at`
- **Relationships**: Parent to `quotations`, `bookings`, `shipments`, `invoices`
- **Runtime Manager**: [`managers/customer_manager.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/managers/customer_manager.py)
- **UI Views**: [`views/crm_view.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/views/crm_view.py), [`views/quotation_view.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/views/quotation_view.py)

---

### Table 4: `quotations` & `quotation_items`
- **Purpose**: Commercial pre-sales rate quotes and line item pricing breakdown.
- **Primary Key**: `id` (INTEGER PK)
- **Foreign Keys**: `customer_id` $\rightarrow$ `customers(id)`
- **Unique Constraints**: `quotation_no` (TEXT UNIQUE)
- **Indexes**: `idx_quotations_no` on `quotation_no`
- **Important Columns**: `quotation_no`, `job_type`, `customer_name`, `pol`, `pod`, `carrier`, `validity_date`, `subject`, `terms_conditions`
- **Line Items FK**: `quotation_items.quotation_id` $\rightarrow$ `quotations(id)` (ON DELETE CASCADE)
- **Status Fields**: `status` ('ACTIVE', 'EXPIRED', 'CONVERTED')
- **Date Fields**: `quotation_date`, `validity_date`, `created_at`
- **Relationships**: Parent to `bookings` (`quotation_id`)
- **Runtime Manager**: [`managers/quotation_manager.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/managers/quotation_manager.py)
- **UI Views**: [`views/quotation_view.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/views/quotation_view.py)

---

### Table 5: `bookings` & `booking_revisions`
- **Purpose**: Operational booking manifests and immutable revision history snapshots.
- **Primary Key**: `id` (INTEGER PK)
- **Foreign Keys**: `customer_id` $\rightarrow$ `customers(id)`
- **Unique Constraints**: `booking_no` (TEXT UNIQUE)
- **Indexes**: `idx_bookings_booking_no` on `booking_no`
- **Link to Job**: `job_no` (TEXT) $\rightarrow$ `shipments(job_no)`
- **Revision Control Table**: `booking_revisions` (`id`, `booking_no`, `revision_no`, `revised_by`, `revised_at`, `revision_reason`, `snapshot` [JSON TEXT])
- **Status Fields**: `status` ('Proceed', 'Confirmed', 'Converted_to_Job', 'Cancelled')
- **Date Fields**: `cy_date`, `cfs_date`, `customer_return_date`, `etd`, `eta`, `closing_time`, `created_at`, `updated_at`
- **Relationships**: Child of `quotations`; Parent to `shipments` (`job_no`)
- **Runtime Manager**: [`managers/booking_manager.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/managers/booking_manager.py)
- **UI Views**: [`views/booking_view.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/views/booking_view.py)

---

### Table 6: `shipments` (Master Operational Job Table)
- **Purpose**: **MASTER OPERATIONAL JOB LEDGER** storing all shipment execution parameters.
- **Primary Key**: `id` (INTEGER PK)
- **Unique Constraints**: `job_no` (TEXT UNIQUE NOT NULL — Master Operational ID)
- **Indexes**: `idx_shipments_job_no` on `job_no`
- **Foreign Keys**: `customer_id` $\rightarrow$ `customers(id)`
- **Important Columns**: `job_no` (**MASTER OPERATIONAL ID**), `booking_no`, `quotation_no`, `customer_name`, `shipper`, `consignee`, `pol`, `pod`, `vessel`, `voyage`, `mbl_no`, `hbl_no`
- **Status Fields**: `status` ('Proceed', 'In_Transit', 'Arrived', 'Completed', 'Cancelled'), `customs_status`
- **Date Fields**: `etd`, `eta`, `actual_departure` (ATD), `actual_arrival` (ATA), `customs_clearance_date`, `created_at`, `updated_at`
- **Relationships**: Parent to `containers`, `shipment_milestones`, `bills_of_lading`, `job_costs`, `profit_sheets`, `invoices`
- **Runtime Manager**: [`managers/shipment_manager.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/managers/shipment_manager.py)
- **UI Views**: [`views/shipment_view.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/views/shipment_view.py), [`views/tracking_view.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/views/tracking_view.py)

---

### Table 7: `containers` & `shipment_milestones` (J3 Subsystems)
- **`containers`**:
  - Primary Key: `id` (INTEGER PK)
  - Foreign Keys: `shipment_id` $\rightarrow$ `shipments(id)` (ON DELETE CASCADE)
  - Unique Constraint: `(shipment_id, container_no)`
  - Indexes: `idx_containers_job_no` on `job_no`
  - Important Columns: `container_no`, `container_size`, `container_type`, `seal_no`, `vgm_kg`, `gross_weight`, `tare_weight`, `soc_coc`, `temp_setting`, `vent_setting`
  - Status Fields: `status` ('Loaded', 'Gated-In', 'Discharged', 'Delivered')
- **`shipment_milestones`**:
  - Primary Key: `id` (INTEGER PK)
  - Foreign Keys: `shipment_id` $\rightarrow$ `shipments(id)` (ON DELETE CASCADE)
  - Indexes: `idx_shipment_milestones_job_no` on `job_no`
  - Important Columns: `job_no`, `milestone_code`, `milestone_name`, `event_date`, `location`, `remark`

---

### Table 8: `bills_of_lading` & `bl_containers` (J4 / J5 Subsystems)
- **`bills_of_lading`**:
  - Primary Key: `id` (INTEGER PK)
  - Unique Constraints: `bl_no` (TEXT UNIQUE)
  - Foreign Keys: `shipment_id` $\rightarrow$ `shipments(id)`
  - Important Columns: `bl_no`, `job_no`, `booking_no`, `shipper`, `consignee`, `notify_party`, `pol`, `pod`, `vessel`, `voyage`, `bl_type` ('Original', 'Express_Release', 'Seaway_Bill')
  - Status Fields: `status` ('Draft', 'Issued', 'Cancelled')
  - Date Fields: `bl_date`, `etd`, `eta`
- **`bl_containers` (Junction Table)**:
  - Foreign Keys: `bl_id` $\rightarrow$ `bills_of_lading(id)` (ON DELETE CASCADE), `container_id` $\rightarrow$ `containers(id)` (ON DELETE CASCADE)
  - Unique Constraint: `(bl_id, container_id)`

---

### Table 9: Financial Ledger Tables (`job_costs`, `profit_sheets`, `invoices`, `invoice_items`, `fx_rates`)
- `job_costs`: P&L expenses linked to `shipments(id)` (ON DELETE CASCADE).
- `profit_sheets`: Job Profit Summary sheets linked to `shipment_id` (`sheet_no` UNIQUE).
- `invoices` & `invoice_items`: AR Billing Invoices linked to `shipment_id` (`doc_no` UNIQUE).
- `fx_rates`: Currency exchange rates (`currency`, `rate_to_thb`, `effective_date` UNIQUE).
- `job_counters`: Running counter sequence table (`job_type`, `yymm` PK).
- `audit_logs`: Operational security audit log entries.

---

## 3. Audit of JOB NO. Operational Master Control

| Criteria | Status | Evidence & Audit Findings |
| :--- | :---: | :--- |
| **Unique Constraint** | **PASS** | `job_no TEXT UNIQUE NOT NULL` defined in `shipments` table schema in [`database/connection.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/database/connection.py#L421). |
| **Primary Operational Reference** | **PASS** | `job_no` is automatically generated upon Job conversion and serves as the master key across `containers`, `shipment_milestones`, `bills_of_lading`, and `profit_sheets`. |
| **Searchable in Ledger** | **PARTIAL** | Searchable by text in Shipment Ledger, but missing explicit multi-column filters (`Container No.`, `HBL`, `MBL`). |
| **Linked to Booking** | **PASS** | `bookings.job_no` connects back to `shipments.job_no` upon conversion. |
| **Linked to Containers** | **PASS** | `containers.job_no` and `containers.shipment_id` form an indexed foreign key. |
| **Linked to Milestones** | **PASS** | `shipment_milestones.job_no` forms an indexed foreign key. |
| **Linked to B/L** | **PASS** | `bills_of_lading.job_no` connects to `shipments.job_no`. |
| **Linked to Finance** | **PASS** | `job_costs`, `profit_sheets`, and `invoices` link via `shipment_id`. |
| **Protected Against Duplication** | **PASS** | Sequence generator in [`managers/job_number.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/managers/job_number.py) uses atomic `job_counters` locks to prevent duplicate allocation. |

---

## 4. Ledger Search & Index Audit

### Booking Ledger Search Support:
- **`Booking No`**: Supported (Text Search)
- **`Customer`**: Supported (Text Search)
- **`POL / POD`**: Supported (Text Search)
- **`Status`**: Supported (Dropdown Filter)
- **`ETD / ETA`**: **MISSING** (Date Range Picker Required)
- **`Vessel / Voyage`**: **MISSING** (Filter Dropdown Required)
- **`Job No`**: **MISSING** (Reverse Link Filter Required)

### Shipment Ledger Search Support:
- **`JOB No`**: Supported (Selected Dropdown)
- **`Status`**: Supported (Dropdown Filter)
- **`Booking No`**: **MISSING** (Filter Parameter Required)
- **`Customer`**: **MISSING** (Text Filter Required)
- **`ETD / ETA`**: **MISSING** (Date Range Picker Required)
- **`Container No`**: **MISSING** (Junction Filter Required)
- **`HBL / MBL No`**: **MISSING** (Filter Parameter Required)

### Missing Indexes Recommended for Future Addition:
1. `CREATE INDEX IF NOT EXISTS idx_shipments_etd_eta ON shipments(etd, eta);`
2. `CREATE INDEX IF NOT EXISTS idx_shipments_customer ON shipments(customer_name);`
3. `CREATE INDEX IF NOT EXISTS idx_bookings_etd_eta ON bookings(etd, eta);`
4. `CREATE INDEX IF NOT EXISTS idx_bills_of_lading_job_no ON bills_of_lading(job_no);`

---

## 5. Schema Inconsistencies Audit
- **Zero Schema Breaking Inconsistencies Found**: All columns used by business managers in [`managers/`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/managers) match the DDL definitions in [`database/connection.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/database/connection.py).
- **SQLite Fallback Compatibility**: SQLite fallback handles `%s` to `?` placeholder adaptation seamlessly via `SQLiteConnAdapter` in [`database/connection.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/database/connection.py#L56-L77).
