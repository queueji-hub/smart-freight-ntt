# SYSTEM REALITY MASTER PLAN
## Smart Freight NTT

> [!WARNING]
> **SOURCE OF TRUTH DISCLAIMER**
> This Master Plan is derived from a physical inspection of the actual Python and SQL code in the Smart Freight NTT repository. Where previous documentation claimed features existed (e.g., ETD/ETA filters in UI, Dashboard Overdue ETA exceptions), this audit overrides those claims based on the explicit lack of implementation in the UI layer.

---

### SECTION 1 — CURRENT SYSTEM REALITY

The system is a Streamlit-based web application backed by a resilient PostgreSQL / SQLite hybrid database.

#### Core Modules
- **Dashboard**
  - **Main UI**: `views/dashboard_view.py`
  - **Manager**: `managers/dashboard_manager.py` (and `managers/shipment_manager.py` stats)
  - **Current Status**: Active / Editable.
  - **Functionality**: Basic metric display (totals, proceed, finished).
  - **Missing**: True Exception Monitoring (e.g., Jobs missing containers, overdue ETAs).

- **Booking**
  - **Main UI**: `views/booking_view.py`
  - **Manager**: `managers/booking_manager.py`
  - **Tables**: `bookings`, `booking_revisions`
  - **PDF**: `pdf/booking_pdf.py`
  - **Current Status**: Active / Frozen core logic.
  - **Functionality**: CRUD operations, Controlled Revisions, PDF generation, Job conversion.
  - **Missing**: ETD / ETA Date Pickers in the UI search filters.

- **Shipment / Job**
  - **Main UI**: `views/shipment_view.py`
  - **Manager**: `managers/shipment_manager.py`
  - **Tables**: `shipments`, `job_counters`
  - **Current Status**: Active / High-Risk (due to duplication).
  - **Functionality**: CRUD operations, generation of `job_no`, container/milestone insertion.
  - **Known Problems**: Container and Milestone DB insertion is duplicated directly within `shipment_manager.py`.

- **Container**
  - **Manager**: `managers/container_manager.py`
  - **Tables**: `containers`
  - **Known Problems**: Duplicated in `shipment_manager.py`.

- **Bill of Lading (B/L)**
  - **Main UI**: `views/bl_view.py`
  - **Manager**: `managers/bl_manager.py`
  - **Tables**: `bills_of_lading`, `bl_containers`
  - **Functionality**: HBL/MBL creation.

- **Database Subsystem**
  - **Manager**: `database/connection.py`
  - **Current Status**: Frozen / High-Reliability. Do not touch the fallback mechanisms.

---

### SECTION 2 — BOOKING REALITY

**Actual Workflow Verified in Code:**
1. **Quotation** (Optional pull from `quotation_manager.py`)
2. **Booking** (DRAFT state created in `bookings` table)
3. **Submit / Confirm** (Status transitions via `can_transition_booking_status`)
4. **Revision** (Pushes JSON snapshot to `booking_revisions` and resets to DRAFT)
5. **Convert to Job** (Generates `job_no` and inserts to `shipments`)

**Actual Tracked Data:**
- Booking No., Customer, ETD, ETA, POL, POD, Vessel, Voyage, Status, Revision No.

**Actual PDF Capabilities:**
- Real-time PDF generation from current record.
- Historical PDF compilation from JSON snapshots in `booking_revisions`.

**Missing / Discrepancies:**
- The database and manager support filtering by ETD/ETA, but the UI (`views/booking_view.py`) **does not have Date Pickers** for filtering.

---

### SECTION 3 — SHIPMENT / JOB REALITY

**Actual Workflow Verified in Code:**
- **JOB No. generation**: Handled by `managers/job_number.py` during `convert_booking_to_job` or manual creation.
- **Data storage**: Stored as `job_no` (UNIQUE) in `shipments`.
- **Relationships**: 
  - Booking is linked via `booking_no` column.
  - Customer is linked via `customer_id` and `customer_name`.
  - Containers are linked via `shipment_id` and `job_no`.
- **Job Status**: Enforced by `_validate_status_transition` (Proceed → In Transit → Arrived → Finished → Closed).

**Search Capabilities (Ledger):**
- **Working**: Search by JOB No., Booking No., Customer, POL, POD, Vessel, Status, Job Type.
- **MISSING — DO NOT IMPLEMENT YET**: ETD Date Range Filter, ETA Date Range Filter.

---

### SECTION 4 — DASHBOARD REALITY

**EXISTING:**
- Basic aggregated counts (Total Shipments, Proceed, Finished, Closed, Canceled).
- Global Navigation / Sidebar Matrix.

**MISSING:**
- Booking conversion metrics (Unconverted Bookings).
- Overdue ETA detection (No active query checking `actual_arrival` vs `eta` against `CURRENT_DATE`).
- Missing Container exception alerts.

**NOT RELIABLE:**
- The Dashboard currently acts as a passive metric viewer, not an active "Operational Control Tower".

---

### SECTION 5 — DATABASE REALITY

| Table | Purpose | Important Relationships | Risk / Note |
|-------|---------|-------------------------|-------------|
| `users` | Auth | FK for audit logs/sessions | Standard |
| `quotations` | Pre-sales | Source for Bookings | Standard |
| `bookings` | Logistics plan | Feeds `shipments` | Solid schema |
| `booking_revisions` | History | FK to `bookings` | JSON snapshots |
| `shipments` | Operational | FK to `customers` | High value |
| `containers` | Cargo specs | FK to `shipments` | **DUPLICATED INSERT LOGIC** |
| `shipment_milestones` | Tracking | FK to `shipments` | **DUPLICATED INSERT LOGIC** |
| `bills_of_lading` | Documentation | FK to `shipments` | Standard |

---

### SECTION 6 — FILE REALITY

- **A. ACTIVE**: `Dashboard.py`, `database/connection.py`, `views/booking_view.py`, `managers/booking_manager.py`, `views/shipment_view.py`, `managers/shipment_manager.py`
- **E. DUPLICATE**: Container insert functions in `managers/shipment_manager.py`. (Why? Duplicate logic causes mismatched data. Risk: High. Replacement: Route all calls to `managers/container_manager.py`). **Safe to delete? NO (Must refactor first)**.
- **F. DO NOT TOUCH**: `database/connection.py` (Resilient connection logic).

---

### SECTION 7 — DEPENDENCY REALITY

**Dependency Flow:**
`Dashboard.py` → `views/*_view.py` → `managers/*_manager.py` → `database/connection.py`

**High Risk Intersections:**
- `managers/booking_manager.py` tightly couples with `managers/shipment_manager.py` during `convert_booking_to_job`. Modifying either requires testing the conversion pipeline.

---

### SECTION 8 — SYSTEM WORKFLOW

Customer Inquiry → Quotation (**EXISTS**)
Quotation → Booking (**EXISTS**)
Booking → Booking Revision (**EXISTS**)
Booking → Confirmation (**EXISTS**)
Confirmation → Convert to JOB (**EXISTS**)
JOB → Container Assignment (**EXISTS BUT DUPLICATED**)
JOB → Milestone Update (**EXISTS BUT DUPLICATED**)
JOB → B/L Issuance (**EXISTS**)
JOB → Job Costs / Profit (**EXISTS**)

---

### SECTION 9 — GAPS

| Priority | Area | Current Reality | Missing | Risk | Recommendation |
|----------|------|-----------------|---------|------|----------------|
| **P0** | Architecture | `shipment_manager` duplicates container SQL | Centralized abstraction | **High** | Refactor to use `container_manager` exclusively |
| **P1** | UI Filters | Managers support Date filters, UI does not | UI Date Pickers | Med | Add ETD/ETA filters to Booking/Job views |
| **P2** | Dashboard | Passive metrics only | Exception Alerts | Low | Implement Overdue ETA & Missing Container lists |

---

### SECTION 10 — WHAT SHOULD NOT BE CHANGED

**Future AI Agents MUST NOT modify:**
1. `database/connection.py` (Do not break SQLite fallback).
2. `Dashboard.py` routing engine (Do not break Streamlit page states).
3. `booking_manager.py` revision logic (`create_booking_revision`). It is perfectly functional.

---

### SECTION 11 — RECOMMENDED NEXT PHASES

**DO NOT IMPLEMENT YET.**

- **Phase P0 — Safety & Cleanup**
  - **Objective**: Remove duplicated SQL logic for Containers and Milestones.
  - **Affected**: `managers/shipment_manager.py`, `views/shipment_view.py`.
  - **Expected Result**: A single source of truth for container validation.

- **Phase P1 — Booking & Job UI Completeness**
  - **Objective**: Expose ETD/ETA search capabilities in the UI.
  - **Affected**: `views/booking_view.py`, `views/shipment_view.py`.

- **Phase P2 — Dashboard Control Tower**
  - **Objective**: Upgrade dashboard to show operational exceptions (Overdue ETA).
  - **Affected**: `managers/dashboard_manager.py`, `views/dashboard_view.py`.

---

### SECTION 12 — NON-PROGRAMMER SUMMARY

**ระบบตอนนี้เป็นอย่างไร (How is the system currently?)**
ระบบ Smart Freight NTT ปัจจุบันสามารถทำงานหลักๆ ได้อย่างดีเยี่ยม ฐานข้อมูลเชื่อมต่อได้เสถียรมาก การออกใบ Booking การแก้ไข (Revision) และการแปลงเป็น Job ทำงานได้จริง

**What works (ส่วนที่ใช้งานได้ดี)**
การสร้าง Booking, การดึงข้อมูลจาก Quotation, การแก้ไข Booking พร้อมเก็บประวัติ (History/PDF), และการเปิด Job ทำงานได้ครบถ้วนสมบูรณ์

**What does not work (ส่วนที่มีปัญหาหรือขาดหายไป)**
- หน้าจอยังไม่สามารถค้นหา Booking หรือ Job แบบ "เลือกช่วงวันที่ (ETD/ETA)" ได้ (โค้ดหลังบ้านทำได้แล้ว แต่หน้าบ้านไม่มีปุ่มให้กด)
- หน้า Dashboard ยังไม่เตือนกรณีที่เรือดีเลย์ (Overdue) หรือ Job ที่ยังไม่ได้ใส่ตู้คอนเทนเนอร์
- มีการเขียนโค้ดบันทึกตู้คอนเทนเนอร์ซ้ำซ้อนกันในระบบหลังบ้าน ซึ่งอาจทำให้ข้อมูลผิดพลาดได้ในอนาคต

**What should we do next (ขั้นตอนต่อไปที่ควรทำ)**
1. แก้ไขโค้ดหลังบ้านที่ซ้ำซ้อนกันให้เป็นระเบียบ (P0)
2. เพิ่มช่องค้นหาด้วยวันที่ (ETD/ETA) ในหน้า Booking และ Job (P1)
3. ปรับปรุง Dashboard ให้แจ้งเตือนงานที่มีปัญหา (P2)

**What should NOT be touched (ส่วนที่ห้ามแตะต้อง)**
ระบบฐานข้อมูลหลัก (`database/connection.py`) และระบบประวัติการแก้ไข Booking ห้ามเข้าไปแก้ไขเพราะตอนนี้ทำงานได้ดีมากแล้ว

---
### FINAL CONFIRMATION
1. **Files Inspected:** `Dashboard.py`, `managers/booking_manager.py`, `views/booking_view.py`, `managers/shipment_manager.py`, `managers/container_manager.py`, `database/connection.py`.
2. **Files Used as Evidence:** The actual Python files listed above.
3. **Conflicts Found:** UI documentation claimed ETD/ETA search existed, but UI files lacked the components. Dashboard documentation claimed exception monitoring existed, but it is passive.
4. **Critical Risks:** Duplicated Container DB insertion logic.
5. **Recommended Next Phase:** P0 Safety & Cleanup (Refactoring `shipment_manager`).
6. **CONFIRMATION:** **REALITY AUDIT COMPLETE — NO PRODUCTION FILES MODIFIED.**
