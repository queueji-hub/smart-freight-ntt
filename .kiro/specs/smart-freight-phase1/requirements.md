# Requirements Document

## Introduction

Smart Freight Phase 1 คือระบบจัดการงาน Freight Forwarder เบื้องต้น ออกแบบมาเพื่อช่วยให้ทีมงานสามารถบันทึก ติดตาม และบริหารจัดการข้อมูล Booking และ Rate Card ของสายการเรือได้อย่างมีประสิทธิภาพ ผ่าน Web Dashboard ที่ใช้งานง่าย โดยใช้ฐานข้อมูลภายใน (SQLite) และ Python Streamlit เป็น Frontend

ระบบนี้ครอบคลุมฟังก์ชันหลัก 2 ส่วน ได้แก่:
1. **Booking Management** — บันทึกและติดตามสถานะการจองตู้สินค้า
2. **Rate Card Management** — บริหารจัดการราคาทุนและราคาขายของแต่ละสายการเรือ แยกตามขนาดตู้และค่า Surcharges

---

## Glossary

- **System**: ระบบ Smart Freight Phase 1 โดยรวม
- **Dashboard**: หน้าเว็บ Streamlit ที่ผู้ใช้งานโต้ตอบกับระบบ
- **Booking**: ข้อมูลการจองตู้สินค้ากับสายการเรือ 1 รายการ
- **Booking_Manager**: โมดูลที่รับผิดชอบการสร้าง อ่าน แก้ไข และลบข้อมูล Booking
- **Rate_Card**: ข้อมูลราคาทุนและราคาขายของสายการเรือ แยกตามขนาดตู้และ Surcharges
- **Rate_Manager**: โมดูลที่รับผิดชอบการสร้าง อ่าน แก้ไข และลบข้อมูล Rate Card
- **Database**: ฐานข้อมูล SQLite ที่เก็บข้อมูลทั้งหมดของระบบ
- **Shipper**: ชื่อลูกค้าผู้ส่งสินค้า
- **Carrier**: สายการเรือ (Shipping Line) เช่น COSCO, MSC, Evergreen
- **POL**: Port of Loading — ท่าเรือต้นทาง
- **POD**: Port of Discharge — ท่าเรือปลายทาง
- **ETD**: Estimated Time of Departure — วันที่เรือออกโดยประมาณ
- **ETA**: Estimated Time of Arrival — วันที่เรือถึงปลายทางโดยประมาณ
- **Booking_Status**: สถานะล่าสุดของ Booking เช่น Pending, Confirmed, Shipped, Arrived, Cancelled
- **Container_Type**: ขนาดและประเภทตู้สินค้า ได้แก่ 20GP, 40GP, 40HC
- **Cost_Rate**: ราคาทุนที่บริษัทจ่ายให้สายการเรือ (ต่อตู้)
- **Sell_Rate**: ราคาขายที่เรียกเก็บจากลูกค้า (ต่อตู้)
- **Surcharge**: ค่าธรรมเนียมเพิ่มเติม เช่น BAF, CAF, PSS, EBS
- **Booking_ID**: รหัสอ้างอิงเฉพาะของ Booking แต่ละรายการ ที่ระบบสร้างขึ้นอัตโนมัติ
- **Effective_Date**: วันที่ Rate Card มีผลบังคับใช้ รูปแบบ YYYY-MM-DD
- **Margin**: กำไรขั้นต้น คำนวณจาก Sell_Rate ลบ Cost_Rate

---

## Requirements

### Requirement 1: Database Initialization

**User Story:** As a system administrator, I want the database to be initialized automatically on first run, so that the system is ready to use without manual setup.

#### Acceptance Criteria

1. WHEN the System starts and no SQLite database file exists at the configured path, THE Database SHALL create a new SQLite file and create all required tables (Bookings, Rate_Cards, Surcharges) automatically.
2. WHEN the System starts and the SQLite database file exists but one or more required tables are absent, THE Database SHALL create only the missing tables without modifying existing tables or data.
3. WHEN the System starts and the Database file and all required tables already exist, THE Database SHALL preserve all existing data without modification.
4. IF the Database file cannot be created due to a file system error, THEN THE System SHALL display an error message that indicates the cause of the failure and the affected file path, and SHALL terminate with a non-zero exit code.

---

### Requirement 2: Booking Creation

**User Story:** As a freight forwarder operator, I want to create a new booking record, so that I can track shipment details from the start.

#### Acceptance Criteria

1. WHEN an operator submits a new Booking form with all required fields, THE Booking_Manager SHALL save the Booking to the Database and assign a unique Booking_ID.
2. THE Booking_Manager SHALL require the following fields for every Booking: Shipper name, Carrier, POL, POD, ETD, ETA, Container_Type, and quantity (a whole number between 1 and 999 inclusive).
3. WHEN a new Booking is saved successfully, THE Booking_Manager SHALL set the initial Booking_Status to "Pending".
4. IF any required field is missing or empty when submitting a Booking, THEN THE Dashboard SHALL display a validation error message identifying the missing field and SHALL NOT save the record.
5. IF ETD is a date that is equal to or later than ETA, THEN THE Dashboard SHALL display a validation error message and SHALL NOT save the record.
6. IF Container_Type does not match one of the predefined values (20GP, 40GP, 40HC), THEN THE Dashboard SHALL display a validation error message and SHALL NOT save the record.

---

### Requirement 3: Booking Retrieval and Display

**User Story:** As a freight forwarder operator, I want to view all bookings in a table, so that I can monitor the status of all shipments at a glance.

#### Acceptance Criteria

1. WHEN an operator opens the Booking page, THE Dashboard SHALL display all Booking records from the Database in a tabular format sorted by ETD ascending by default.
2. THE Dashboard SHALL display the following columns for each Booking: Booking_ID, Shipper, Carrier, POL, POD, ETD, ETA, Container_Type, quantity, and Booking_Status.
3. WHEN the Database contains no Booking records, THE Dashboard SHALL display the message "No bookings found. Create your first booking to get started."
4. WHEN an operator selects a Carrier filter value, THE Dashboard SHALL display only Booking records where the Carrier field matches the selected value exactly.
5. WHEN an operator selects a Booking_Status filter value, THE Dashboard SHALL display only Booking records where the Booking_Status field matches the selected value exactly.
6. WHEN an operator applies both a Carrier filter and a Booking_Status filter simultaneously, THE Dashboard SHALL display only Booking records that satisfy both filter conditions.
7. WHEN active filters return no matching Booking records, THE Dashboard SHALL display the message "No bookings match the selected filters."

---

### Requirement 4: Booking Update

**User Story:** As a freight forwarder operator, I want to update booking details and status, so that I can keep shipment information current.

#### Acceptance Criteria

1. WHEN an operator selects a Booking and submits updated field values, THE Booking_Manager SHALL update the corresponding record in the Database and display a success confirmation to the operator.
2. WHEN an operator updates the Booking_Status of a Booking, THE Booking_Manager SHALL save the new status and record the UTC timestamp of the update.
3. IF an operator attempts to update a Booking with a Booking_ID that does not exist in the Database, THEN THE Booking_Manager SHALL return an error message indicating the record was not found.
4. IF ETD is a date that is equal to or later than ETA during an update, THEN THE Booking_Manager SHALL return a validation error and SHALL NOT save the update.
5. IF any required field is missing or empty during an update, THEN THE Booking_Manager SHALL return a validation error identifying the missing field and SHALL NOT save the update.

---

### Requirement 5: Booking Deletion

**User Story:** As a freight forwarder operator, I want to delete a booking record, so that I can remove incorrect or cancelled entries.

#### Acceptance Criteria

1. WHEN an operator confirms deletion of a Booking, THE Booking_Manager SHALL permanently remove the Booking record from the Database and display a success confirmation to the operator.
2. WHEN an operator initiates deletion of a Booking, THE Dashboard SHALL display a confirmation prompt that includes the Booking_ID before executing the deletion.
3. IF an operator attempts to delete a Booking with a Booking_ID that does not exist, THEN THE Booking_Manager SHALL return an error message indicating the record was not found.
4. IF an operator attempts to delete a Booking whose Booking_Status is "Shipped" or "Arrived", THEN THE Dashboard SHALL display an error message indicating the Booking cannot be deleted in its current status and SHALL NOT execute the deletion.

---

### Requirement 6: Rate Card Creation

**User Story:** As a freight forwarder operator, I want to create a rate card for a carrier and container type, so that I can track cost and sell rates for quotation purposes.

#### Acceptance Criteria

1. WHEN an operator submits a new Rate Card form with all required fields, THE Rate_Manager SHALL save the Rate_Card to the Database and display a success confirmation to the operator.
2. THE Rate_Manager SHALL require the following fields for every Rate_Card: Carrier, POL, POD, Container_Type, Cost_Rate (numeric, 0.01–999,999,999.99), Sell_Rate (numeric, 0.01–999,999,999.99), and Effective_Date (format YYYY-MM-DD).
3. IF any required field is missing or empty when submitting a Rate Card, THEN THE Dashboard SHALL display a validation error message identifying the missing field and SHALL NOT save the record.
4. IF Cost_Rate or Sell_Rate contains a non-numeric value, a zero, or a negative value, THEN THE Dashboard SHALL display a validation error message and SHALL NOT save the record.
5. IF a Rate_Card with the same Carrier, POL, POD, Container_Type, and Effective_Date already exists, THEN THE Rate_Manager SHALL overwrite the existing Cost_Rate and Sell_Rate values and notify the operator that the existing record was updated rather than a new one created.
6. IF Container_Type does not match one of the predefined values (20GP, 40GP, 40HC), THEN THE Dashboard SHALL display a validation error message and SHALL NOT save the record.

---

### Requirement 7: Rate Card Retrieval and Display

**User Story:** As a freight forwarder operator, I want to view all rate cards in a table, so that I can compare rates across carriers and container types.

#### Acceptance Criteria

1. WHEN an operator opens the Rate Card page, THE Dashboard SHALL display all Rate_Card records from the Database in a tabular format sorted by Effective_Date descending by default.
2. THE Dashboard SHALL display the following columns for each Rate_Card: Carrier, POL, POD, Container_Type, Cost_Rate, Sell_Rate, Margin (Sell_Rate minus Cost_Rate, displayed as a signed number), and Effective_Date (formatted as DD-MMM-YYYY).
3. WHEN the Database contains no Rate_Card records, THE Dashboard SHALL display the message "No rate cards found. Add your first rate card to get started."
4. WHEN an operator selects a Carrier filter value, THE Dashboard SHALL display only Rate_Card records where the Carrier field matches the selected value exactly.
5. WHEN an operator selects a Container_Type filter value, THE Dashboard SHALL display only Rate_Card records where the Container_Type field matches the selected value exactly.
6. WHEN an operator applies both a Carrier filter and a Container_Type filter simultaneously, THE Dashboard SHALL display only Rate_Card records that satisfy both filter conditions.
7. WHEN active filters return no matching Rate_Card records, THE Dashboard SHALL display the message "No rate cards match the selected filters."

---

### Requirement 8: Rate Card Update and Deletion

**User Story:** As a freight forwarder operator, I want to update or delete rate card entries, so that I can maintain accurate and current pricing information.

#### Acceptance Criteria

1. WHEN an operator selects a Rate_Card and submits updated field values, THE Rate_Manager SHALL update the corresponding record in the Database and display a success confirmation to the operator.
2. WHEN an operator confirms deletion of a Rate_Card that is not referenced by any existing Booking record, THE Rate_Manager SHALL permanently remove the Rate_Card record from the Database.
3. WHEN an operator initiates deletion of a Rate_Card, THE Dashboard SHALL display a confirmation prompt that includes the Rate_Card identifier (Carrier, POL, POD, Container_Type, Effective_Date) and a warning that the removal is permanent.
4. IF Cost_Rate or Sell_Rate contains a non-numeric value, a zero, or a negative value during an update, THEN THE Dashboard SHALL display a validation error message and SHALL NOT save the update.
5. IF an operator attempts to delete a Rate_Card that is referenced by one or more existing Booking records, THEN THE Rate_Manager SHALL display an error message listing the referencing Booking_IDs and SHALL NOT execute the deletion.
6. IF a Database error occurs during an update or delete operation, THEN THE System SHALL display an error message to the operator and SHALL preserve the existing record without modification.

---

### Requirement 9: Surcharge Management

**User Story:** As a freight forwarder operator, I want to add surcharges to a rate card, so that I can capture all additional fees associated with a shipment route.

#### Acceptance Criteria

1. WHEN an operator adds a Surcharge to a Rate_Card, THE Rate_Manager SHALL save the Surcharge name (non-empty string, maximum 100 characters) and amount (numeric, 0.01–999,999.99, up to 2 decimal places) linked to the corresponding Rate_Card record.
2. THE Rate_Manager SHALL allow multiple Surcharges to be associated with a single Rate_Card.
3. WHEN an operator views a Rate_Card detail, THE Dashboard SHALL display all Surcharges associated with that Rate_Card, showing each Surcharge name and amount.
4. IF a Surcharge amount contains a non-numeric value, THEN THE Dashboard SHALL display a validation error message and SHALL NOT save the Surcharge.
5. WHEN an operator deletes a Rate_Card, THE Rate_Manager SHALL also delete all Surcharges associated with that Rate_Card.
6. IF a Surcharge name is empty or exceeds 100 characters, THEN THE Dashboard SHALL display a validation error message and SHALL NOT save the Surcharge.

---

### Requirement 10: Margin Calculation

**User Story:** As a freight forwarder operator, I want to see the profit margin for each rate card automatically, so that I can quickly assess profitability without manual calculation.

#### Acceptance Criteria

1. WHEN the Dashboard displays a Rate_Card record, THE Dashboard SHALL calculate and display the Margin as Sell_Rate minus Cost_Rate for each Container_Type.
2. WHEN the Dashboard displays a Rate_Card record that includes Surcharges, THE Dashboard SHALL display the total Surcharge amount per Container_Type separately from the base Margin.
3. IF the Margin for a Rate_Card is greater than 0, THEN THE Dashboard SHALL display the Margin value with a green visual indicator.
4. IF the Margin for a Rate_Card is 0 or less, THEN THE Dashboard SHALL display the Margin value with a red visual indicator.
5. IF Sell_Rate or Cost_Rate is unavailable for a Rate_Card record, THEN THE Dashboard SHALL display "N/A" in the Margin column for that record and SHALL NOT display a color indicator.

---

### Requirement 11: Data Persistence

**User Story:** As a freight forwarder operator, I want all data to be saved persistently, so that information is not lost when the application is restarted.

#### Acceptance Criteria

1. THE Database SHALL persist all Booking and Rate_Card data to the SQLite file on disk after every create, update, or delete operation.
2. WHEN the System restarts, THE Database SHALL reload all previously saved Booking and Rate_Card records such that the count and field values of every record are identical to those present before the restart.
3. IF a write operation to the Database fails, THEN THE System SHALL display an error message to the operator, SHALL NOT report the operation as successful, and SHALL leave the existing Database state unchanged.
4. WHEN the System starts for the first time and no SQLite file exists, THE Database SHALL create the SQLite file at the configured path before accepting any read or write operations.
