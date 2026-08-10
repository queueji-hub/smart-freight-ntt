# 📘 คู่มือการใช้งาน FreightFlow NTT

ระบบบริหารจัดการ Freight Forwarding แบบครบวงจร — เวอร์ชัน 1.0

---

## 📑 สารบัญ

1. [การเริ่มต้นใช้งาน](#1-การเริ่มต้นใช้งาน)
2. [ผู้ใช้และสิทธิ์ (RBAC)](#2-ผู้ใช้และสิทธิ์-rbac)
3. [Dashboard](#3-dashboard)
4. [CRM — จัดการลูกค้า](#4-crm--จัดการลูกค้า)
5. [Quotation — ใบเสนอราคา](#5-quotation--ใบเสนอราคา)
6. [Booking — ใบจองเรือ](#6-booking--ใบจองเรือ)
7. [Shipment — ใบคุมงาน + B/L](#7-shipment--ใบคุมงาน--bl)
8. [Tracking — ติดตามตู้](#8-tracking--ติดตามตู้)
9. [Profit Sheet — สรุปกำไร/ขาดทุน](#9-profit-sheet--สรุปกำไรขาดทุน)
10. [Billing — ออกใบแจ้งหนี้](#10-billing--ออกใบแจ้งหนี้)
11. [FX Rates — อัตราแลกเปลี่ยน](#11-fx-rates--อัตราแลกเปลี่ยน)
12. [Reports — รายงาน](#12-reports--รายงาน)
13. [Users — จัดการผู้ใช้](#13-users--จัดการผู้ใช้)
14. [Settings — ตั้งค่าระบบ](#14-settings--ตั้งค่าระบบ)
15. [Workflow ทำงานจริง End-to-End](#15-workflow-ทำงานจริง-end-to-end)
16. [คำถามที่พบบ่อย (FAQ)](#16-คำถามที่พบบ่อย-faq)

---

## 1. การเริ่มต้นใช้งาน

### 🌐 URL หลัก

```
https://nattayaraat-freight.streamlit.app/
```

### 🔐 Login

เปิดเว็บแล้วจะเจอหน้า Sign In กรอก Username + Password

**บัญชี Demo (เริ่มต้น):**

| Role | Username | Password |
|------|----------|----------|
| 👑 Admin | `admin` | `Admin@2026!` |
| 💼 Sales | `sales` | `Sales@2026!` |
| 📞 Customer Service | `cs` | `Cs@2026!` |
| 🚢 Operation | `operation` | `Ops@2026!` |
| 💰 Accounting | `accounting` | `Acc@2026!` |

> ⚠️ แนะนำให้ Admin สร้างบัญชีจริงและลบ/ปิด demo accounts ก่อนใช้งานจริง

### 📱 อุปกรณ์ที่รองรับ

- 💻 PC / Mac (Chrome, Edge, Safari, Firefox)
- 📱 Mobile (Chrome, Safari) — sidebar จะยุบเป็นไอคอนซ้ายบน
- 📟 Tablet — แสดงผลเต็มรูปแบบ

### 🎯 Sidebar Navigation

หลังจาก Login จะเห็น sidebar ซ้ายมือแสดงเฉพาะเมนูที่บัญชีของคุณมีสิทธิ์เข้าถึง คลิกเมนูเพื่อสลับหน้า

---

## 2. ผู้ใช้และสิทธิ์ (RBAC)

### 👥 4 บทบาทหลัก

#### 💼 Sales (พนักงานขาย)
- ✅ ดู Dashboard
- ✅ จัดการ CRM (สร้าง/แก้ไขลูกค้า)
- ✅ สร้าง/แก้ไข Quotation
- 📖 ดู Booking, Shipment (อ่านอย่างเดียว)
- 👁 Review Profit Sheet (ตรวจสอบ)

#### 📞 CS / Customer Service & 🚢 Operation
> **CS และ Operation มีสิทธิ์เหมือนกันทุกประการ** — ทำงานทดแทนกันได้ใน "Operations Team"

- ✅ จัดการลูกค้า CRM (สร้าง/แก้ไข)
- ✅ สร้าง/แก้ไข Quotation
- ✅ สร้าง/แก้ไข Booking Confirmation
- ✅ จัดการ Shipment (สร้าง/แก้ไข)
- ✅ Container Tracking + Milestones
- ✅ Generate B/L PDF
- ✅ เปลี่ยนสถานะ Proceed → Finished
- ✅ จัดการ FCL/LCL details

#### 💰 Accounting (บัญชี)
- ✅ Profit Sheet (สร้าง + Approve)
- ✅ Billing (Invoice / BN / CN / DN / SOA)
- ✅ Clear Payment
- ✅ เปลี่ยนสถานะเป็น `Closed` (เฉพาะ role นี้)

#### 👑 Admin (ผู้ดูแลระบบ)
- ✅ ทุกสิทธิ์ของทุก role
- ✅ User Management (เพิ่ม/ลบ/Reset password)
- ✅ Settings (Email templates, SMTP, Activity log)

---

## 3. Dashboard

หน้าหลักแสดง KPI แบบ real-time

### 📊 ตัวเลขสำคัญ (KPI Cards)

- **Total Jobs** — จำนวนงานทั้งหมด
- **Proceed** — งานที่กำลังดำเนินการ
- **Finished** — งานที่เสร็จแล้ว (รอเก็บเงิน)
- **Customers** — จำนวนลูกค้าใน CRM
- **Outstanding** — ยอดค้างชำระ (THB)

### 📋 Recent Active Shipments

ตารางแสดงงาน 15 อันล่าสุดที่ยังเป็น `Proceed`

### 📈 Status Breakdown

แสดงจำนวนงานตามสถานะ:
- 🔵 Proceed (สีน้ำเงิน) — กำลังทำงาน
- 🟢 Finished (สีเขียว) — เสร็จแล้ว
- ⚫ Closed (สีเทา) — ปิดงาน
- 🔴 Canceled (สีแดง) — ยกเลิก

### 📅 Monthly Volume Chart

กราฟแท่งจำนวนงานต่อเดือน (อิง ETD)

---

## 4. CRM — จัดการลูกค้า

### 📋 Tab: All Customers

- พิมพ์ชื่อบริษัทเพื่อค้นหา (auto-filter)
- ตารางแสดง: Company, Contact, Tel, Email, Tax ID, Credit Terms, Address

### ➕ Tab: New Customer (Sales/Admin เท่านั้น)

**ฟิลด์ที่ต้องกรอก:**

| ฟิลด์ | จำเป็น | คำอธิบาย |
|-------|--------|----------|
| Company Name | ✅ | ชื่อบริษัทลูกค้า |
| Contact Person | | ชื่อผู้ติดต่อ |
| Phone Number | | เบอร์ติดต่อ |
| | | อีเมล |
| Tax ID | | เลขผู้เสียภาษี 13 หลัก |
| Credit Terms (days) | | จำนวนวันเครดิต (default 30) |
| Address | | ที่อยู่บริษัท |
| Notes | | หมายเหตุภายใน |

### ✏️ การแก้ไข/ปิดลูกค้า

1. เลือกลูกค้าจาก dropdown "Edit / Delete Customer"
2. แก้ไขข้อมูลในฟอร์ม
3. กด **Save Changes** หรือ **Delete (Deactivate)**

> 🔁 **ข้อมูลลูกค้าจะ auto-fill** ในหน้า Quotation, Booking, Shipment, Invoice อัตโนมัติเมื่อพิมพ์ชื่อ

---

## 5. Quotation — ใบเสนอราคา

### ➕ Create New (Tab 1)

**ขั้นตอนสร้าง:**

1. เลือก **Job Type**: SE/SI/AE/AI/TE/TI
2. **Customer** — พิมพ์อย่างน้อย 2 ตัวอักษร ระบบจะแสดง dropdown ลูกค้าจาก CRM
3. กรอกข้อมูล Carrier, POL, POD, Commodity, Weight, Quantity
4. ตั้ง **Quotation Date** + **Validity Date**
5. **Quotation Items** — กรอกรายการค่าใช้จ่าย:
   - ⬆⬇ เลื่อนลำดับ
   - ⤴⤵ แทรกข้างบน/ล่าง
   - 🗑 ลบ
6. แก้ **Terms & Conditions** ตามต้องการ
7. กด **🚀 Generate Quotation**
8. ระบบจะสร้างเลข Quotation No อัตโนมัติ (เช่น `SI26050001`)
9. กด **📥 Download PDF**

### 📋 All Quotations (Tab 2)

ค้นหา → เลือก quotation → กดปุ่ม:

- 📥 **PDF** — ดาวน์โหลดใบเสนอราคา
- ✏️ **Edit** — แก้ไขข้อมูล (รวมถึงเลข Quotation No)
- 📑 **Copy** — สร้างใบใหม่จากใบเก่า (ของลูกค้าเจ้าเดียวกัน)
- ➡️ **→ Booking** — แปลงเป็น Booking Confirmation (data ถูกส่งต่ออัตโนมัติ)

---

## 6. Booking — ใบจองเรือ

### ➕ New Booking (Tab 1, CS/Admin)

**Pull from Quotation:** เลือก Quotation ที่มีอยู่ → ระบบจะ pre-fill ข้อมูลให้

**ฟิลด์สำคัญ:**

#### Routing
- POL (Port of Loading)
- POR (Port of Receipt)
- POD (Port of Discharge)
- Final Destination
- Transhipment Port

#### Vessel & Schedule
- Carrier, M.Vessel, Feeder, Liner
- ETD (Estimated Time of Departure)
- ETA (Estimated Time of Arrival)
- Closing Time

#### Container Yard / CFS
- CY Date + CY Place (Container Yard)
- CFS Date + CFS Place (Container Freight Station)
- Customer Return Date + Return Place

### 📋 All Bookings (Tab 2)

- กรอง Status: All / Proceed / Finished / Closed / Canceled
- เลือก Booking → กด **📥 Generate PDF** → ได้ Booking Confirmation PDF

### ✏️ Edit Booking (Tab 3)

แก้ไข Status, Carrier, ETD, ETA, Remark

---

## 7. Shipment — ใบคุมงาน + B/L

### ➕ New Shipment (Tab 1, Operation/Admin)

**Pull Data feature:**
- 📥 **From Quotation** — ดึงข้อมูลจากใบเสนอราคา
- 📥 **From Booking** — ดึงข้อมูลจาก Booking Confirmation

**ฟิลด์ที่ต้องกรอกเพิ่ม:**

#### Cargo Details
- Cargo Type: FCL / LCL / AIR / TRUCK
- Container Size: 1x20'GP / 1x40'GP / 1x40'HC etc.
- Container No., Seal No.
- Weight Origin, Weight Port

#### Schedule
- Pick Up Date
- Stuffing Date
- Return Date

ระบบจะสร้าง **Job No** อัตโนมัติ เช่น `SE26050001`

### 📋 All Shipments (Tab 2)

- Filter by Job Type / Status / Carrier
- Export CSV
- 📄 **Generate Bill of Lading (B/L)** — สร้าง B/L PDF สำหรับงานนั้น

### ✏️ Edit / Update (Tab 3, Operation)

- เปลี่ยน **Status**: Proceed → Finished → Closed → Canceled
- กรอก B/L No., Container No., Seal No.
- 📑 **Clone this Job** — ทำสำเนางานใหม่
- 🗑️ **Delete** — ลบงาน

> ⚠️ **กฎสำคัญ:**
> - การเปลี่ยนเป็น `Closed` ต้องมี Profit Sheet ก่อน
> - เฉพาะ Accounting / Admin เท่านั้นที่เปลี่ยนเป็น `Closed` ได้

---

## 8. Tracking — ติดตามตู้

ติดตามการเคลื่อนไหวของตู้คอนเทนเนอร์แบบ timeline

### 📍 11 Milestones มาตรฐาน

| Code | Name | Icon |
|------|------|------|
| BKD | Booked | 📋 |
| CY_RCV | Empty Container Received at CY | 📦 |
| STUFF | Stuffing / Loading at Shipper | 🚚 |
| CY_RTN | Loaded Container Returned to CY | 🏭 |
| LOAD | Loaded on Vessel | 🚢 |
| DEP | Vessel Departed POL | ⚓ |
| ARR | Vessel Arrived POD | 🛳️ |
| DISC | Discharged at POD | 📤 |
| CUST | Customs Cleared | ✅ |
| DEL | Delivered to Consignee | 🎯 |
| EMPTY | Empty Returned | ♻️ |

### ➕ เพิ่ม Milestone

1. เลือก Shipment
2. กด **➕ Add Milestone**
3. เลือก Milestone จาก dropdown
4. ตั้ง Date + Time + Location
5. ใส่ Note (optional)
6. กด **✅ Record Milestone**

Timeline จะเรียงตามเวลาที่เกิดเหตุการณ์

---

## 9. Profit Sheet — สรุปกำไร/ขาดทุน

หัวใจของระบบ — ใช้ตรวจสอบกำไรของแต่ละ job ก่อน Closed

### 🎯 ขั้นตอนใช้งาน

#### 1. เลือก Shipment
ระบบจะแสดง Job No, Customer, Status

#### 2. KPI Summary บนสุด

- **Revenue (AR)** — รายรับรวม (THB)
- **Cost (AP)** — ต้นทุนรวม (THB)
- **Net Profit** — กำไรสุทธิ (สีเขียว/แดง)
- **Status** — 🟢 Profit / 🔴 Loss

#### 3. Tab: 💰 Account Receivables (AR)

เพิ่มรายการที่จะเก็บเงินลูกค้า:

**AR Categories:**
- Ocean Freight (Sell)
- Local Charges (Sell)
- Trucking (Sell)
- Customs (Sell)
- DOC Fee
- Handling Fee
- Other Revenue

**ฟิลด์:**
- Category, Description, Customer
- Quantity × Unit Price = Amount
- Currency (รองรับ multi-currency, แปลงเป็น THB อัตโนมัติ)
- Remark

#### 4. Tab: 💸 Account Payables (AP)

เพิ่มต้นทุนที่ต้องจ่ายให้ supplier:

**AP Categories:**
- Ocean Freight (Liner)
- Co-loader Cost
- Overseas Agent
- Trucking Supplier
- Customs Broker
- Warehouse / CFS
- Documentation
- Other Cost

#### 5. Tab: 📋 Profit Sheets

**Generate Profit Sheet PDF:**
1. เพิ่ม AR + AP ให้ครบก่อน
2. กด **🚀 Generate Profit Sheet PDF**
3. ระบบสร้าง Sheet No (เช่น `PS-SE26050001-01`)
4. ดาวน์โหลด PDF ที่มีรายการครบทั้ง AR/AP + Summary + ช่องเซ็นชื่อ 3 จุด:
   - 📝 Prepared By (CS/Operation)
   - 👁 Reviewed By (Sales)
   - ✅ Approved By (Management)

#### 6. Workflow Sign-off

| Action | สิทธิ์ |
|--------|--------|
| Generate Sheet | CS, Operation, Admin |
| 👁 Review | ทุก role ที่มีสิทธิ์ Profit |
| ✅ Approve | Accounting, Admin เท่านั้น |

#### 7. หลัง Approve

กลับไปหน้า **Shipment → Edit** → เปลี่ยนสถานะเป็น `Closed` ได้

> ⚠️ **ถ้าไม่มี Profit Sheet → ระบบจะ block การ Closed**

---

## 10. Billing — ออกใบแจ้งหนี้

### 📊 KPI บนสุด

- Total Billed (รวมยอดออกบิลทั้งหมด)
- Total Paid (รวมยอดที่ได้รับ)
- Outstanding (ค้างชำระ)

### ➕ Create Document (Tab 1, Accounting)

**5 ประเภทเอกสาร:**

| Code | Type | ใช้เมื่อ |
|------|------|---------|
| INV | 📄 Invoice / Tax Invoice | ออกใบกำกับภาษี |
| BN | 📑 Billing Note (ใบวางบิล) | วางบิลลูกค้า |
| CN | 📉 Credit Note | ลดหนี้ลูกค้า |
| DN | 📈 Debit Note | เพิ่มหนี้ลูกค้า |
| SOA | 📊 Statement of Account | สรุปยอดบัญชี |

**ขั้นตอน:**

1. เลือก Document Type
2. เลือก Customer (จาก CRM)
3. Link to Shipment (optional) — เพื่อ trace กลับ
4. ตั้ง Issue Date + Due Date (auto-fill จาก credit terms)
5. เลือก Currency: THB / USD / EUR / CNY
6. เพิ่ม Line Items:
   - Description, Qty, Unit Price → Amount
7. ตั้ง **VAT Rate** (default 7%) + **WHT Rate** (0/1/3/5%)
8. ดู Live Preview:
   ```
   Subtotal:       ฿10,000.00
   VAT (7%):           ฿700.00
   WHT (3%):          -฿300.00
   Net Total:      ฿10,400.00
   ```
9. กด **🚀 Issue Document**

### 📋 All Documents (Tab 2)

- Filter by Type / Status (Unpaid / Partial / Paid / Cancelled)
- 📥 **Generate PDF** — ดาวน์โหลดใบกำกับภาษีในรูปแบบ A4

### 💳 Record Payment (Tab 3)

1. เลือก Invoice ที่ค้างชำระ
2. กรอก Payment Amount + Payment Date
3. กด **💳 Record Payment**

ระบบจะอัปเดต:
- ถ้าจ่ายเต็ม → `Paid`
- ถ้าจ่ายบางส่วน → `Partial`
- คำนวณ Outstanding ใหม่อัตโนมัติ

---

## 11. EX Rates — อัตราแลกเปลี่ยน

### 💱 Currencies ที่รองรับ

THB (base), USD, EUR, CNY, JPY, SGD, HKD

### ➕ Set Exchange Rate (Admin/Accounting)

1. เลือก Currency
2. กรอก Rate (1 หน่วย = X THB)
3. ตั้ง Effective Date
4. กด **💾 Save Rate**

ระบบเก็บ rate ตามวันที่ — การแปลงเงินใน Profit Sheet จะใช้ rate ของวันนั้นๆ

### 🔄 Quick Converter

- กรอก Amount
- เลือก From + To Currency
- ระบบแสดงผลแปลงทันที

### 📜 Rate History

ดูประวัติ rate ทั้งหมดที่เคยตั้ง

---

## 12. Reports — รายงาน

### 📅 Date Range Filter

เลือก From/To เพื่อดูสถิติช่วงเวลานั้น

### 📊 Sections

1. **🚢 Shipment Activity**
   - Total Jobs, Proceed, Finished, Closed
   - Bar chart แยกตาม Job Type

2. **💰 Financial Overview**
   - Total Billed, Total Collected, Outstanding
   - **Top Customers by Revenue** — 10 อันดับ + ยอดบิล + ยอดชำระ + ค้างชำระ

3. **👥 Customer Database**
   - Active Customers count
   - Avg Credit Terms

---

## 13. Users — จัดการผู้ใช้

**Admin only**

### 📋 All Users (Tab 1)

ตารางผู้ใช้ทั้งหมด พร้อม:

#### 🔐 Reset Password
1. เลือก user
2. กรอกรหัสผ่านใหม่
3. กด Reset

#### 🎭 Change Role / Status
1. เลือก user
2. เปลี่ยน Role / ติ๊ก Active
3. กด Update

### ➕ Create User (Tab 2)

กรอก Username, Password, Full Name, Email, Role → กด Create

ระบบจะแสดง permissions ที่ role นั้นมีให้เห็นก่อนสร้าง

---

## 14. Settings — ตั้งค่าระบบ

**Admin only**

### 📝 Tab 1: Email Templates

5 templates default:
- `quotation_send` — ส่งใบเสนอราคา
- `booking_confirmation` — ยืนยัน booking
- `shipment_update` — แจ้งสถานะ shipment
- `invoice_send` — ส่ง Invoice
- `payment_reminder` — ทวงเงิน

**แก้ไข:**
- เลือก template
- แก้ Subject + Body (HTML allowed)
- ใช้ตัวแปร `{{customer_name}}`, `{{job_no}}`, `{{doc_no}}`, `{{total_amount}}` ฯลฯ
- กด Save

### 📨 Tab 2: SMTP & Email Log

ตั้งค่า SMTP ใน Streamlit Cloud Secrets:

```toml
[smtp]
host = "smtp.gmail.com"
port = 587
username = "you@example.com"
password = "your-app-password"
from_email = "you@example.com"
from_name = "FreightFlow NTT"
```

**Gmail:** สร้าง [App Password](https://myaccount.google.com/apppasswords) (ไม่ใช้ password ปกติ)

**Streamlit Cloud:** ไปที่ app settings → Secrets → paste

ดูประวัติ email ที่ส่งทั้งหมด (sent / draft / failed)

### 🔍 Tab 3: Activity Log

ประวัติการกระทำของผู้ใช้ในระบบ (audit trail)

---

## 15. Workflow ทำงานจริง End-to-End

### 🎯 Scenario: ลูกค้าจองเรือ → ส่งของ → เก็บเงิน

#### Day 1 — Sales รับงาน

```
1. CRM → สร้างลูกค้า "ABC Trading Co., Ltd."
2. Quotation → สร้างใบเสนอราคา SI26050001
3. กด "📥 PDF" ส่งให้ลูกค้า
4. ลูกค้าตอบรับ → กด "➡️ → Booking"
```

#### Day 2 — CS ออก Booking

```
5. Booking → ใบ booking ที่แปลงมา → กรอก:
   - CY Date/Place
   - Carrier, M.Vessel, Closing Time
   - ETD, ETA
6. กด "📥 Generate PDF" → ส่งให้ลูกค้า
```

#### Day 3-7 — Operation รับงาน

```
7. Shipment → "📥 Pull from Booking" → สร้าง Job SE26050001
8. กรอก Container No., Seal No., Container Size
9. Tracking → เพิ่ม milestones:
   - BKD (วันจอง)
   - CY_RCV (รับตู้เปล่า)
   - STUFF (โหลดสินค้า)
   - LOAD (โหลดขึ้นเรือ)
   - DEP (เรือออก)
```

#### Day 14 — เรือถึงปลายทาง

```
10. Tracking → เพิ่ม:
    - ARR (เรือถึง)
    - DISC (ขนตู้ลง)
    - CUST (ผ่านศุลกากร)
    - DEL (ส่งลูกค้า)
    - EMPTY (คืนตู้)
11. Operation → Shipment → Edit → เปลี่ยนสถานะเป็น "Finished"
12. Generate B/L PDF
```

#### Day 15 — Accounting

```
13. Profit Sheet → เลือก Job SE26050001
14. AR → เพิ่มทุกค่าใช้จ่ายที่จะเก็บลูกค้า
15. AP → เพิ่มทุกต้นทุน (Liner, Trucking, Broker)
16. กด "🚀 Generate Profit Sheet PDF"
17. กด "✅ Approve"
18. Billing → Create Document (INV) → link to Job SE26050001
19. Generate Invoice PDF → ส่งให้ลูกค้า
```

#### Day 30 — ลูกค้าจ่ายเงิน

```
20. Billing → Record Payment → ใส่ amount + date
21. Status เปลี่ยนเป็น "Paid"
22. Shipment → Edit → เปลี่ยนสถานะเป็น "Closed" ✅
    (ตอนนี้ผ่านได้เพราะมี Profit Sheet แล้ว)
```

---

## 16. คำถามที่พบบ่อย (FAQ)

### Q1: ลืมรหัสผ่าน?
A: ติดต่อ Admin ของบริษัท → ไป Users → Reset Password

### Q2: ทำไมเปลี่ยนสถานะเป็น "Closed" ไม่ได้?
A: ต้องสร้าง **Profit Sheet** ก่อน (ไปที่ 📊 Profit Sheet → Generate)

### Q3: ทำไมเห็นเมนูบางอันไม่ได้?
A: บัญชีของคุณไม่มีสิทธิ์ในเมนูนั้น (เป็นไปตาม role) ติดต่อ Admin หากต้องการสิทธิ์เพิ่ม

### Q4: PDF ไม่มีโลโก้บริษัท?
A: ตรวจสอบไฟล์ `assets/logo.png` ใน repository ต้องมีและขนาดไม่เกิน ~500KB

### Q5: ทำไม email ไม่ส่ง?
A: SMTP ยังไม่ตั้งค่า → ไป Settings → Tab 2 → ดู instruction หรือเช็ค Streamlit Cloud Secrets

### Q6: Login แล้วกลับมาหน้า Login ตลอด?
A: น่าจะเป็น browser block cookies/localStorage → ลอง Incognito Window หรือเช็ค URL ต้องมี `?token=...`

### Q7: ทำไม Shipment list โหลดช้า?
A: ระบบใช้ pagination 100 records/page อยู่แล้ว ถ้ายังช้าให้ใช้ filter (Job Type / Status / Carrier) เพื่อลดข้อมูล

### Q8: เพิ่มลูกค้าใหม่จะปรากฏใน Quotation auto-complete ทันทีไหม?
A: ใช่ — ระบบ refresh ทุกครั้งที่โหลดหน้า

### Q9: เลข Job No ซ้ำได้ไหม?
A: ไม่ได้ — ระบบใช้ counter อะตอมิกใน DB (atomic increment) ทุกเดือนเริ่มที่ 0001 ใหม่

### Q10: Backup database ยังไง?
A: ดาวน์โหลดไฟล์ `data/smart_freight.db` (SQLite) จาก Streamlit Cloud หรือ git repo

---

## 📞 Support

**บริษัท:** NATTAYARAAT CO., LTD.
**Email:** Management@nattayaraat.com
**Tel:** 063-428-9691

---

> 📅 **เวอร์ชัน 1.0** — May 2026
> 💡 คู่มือนี้จะอัปเดตตามฟีเจอร์ใหม่ที่เพิ่มเข้าระบบ
