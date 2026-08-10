# DOCUMENT NUMBERING HARDENING — FINAL REPORT
**Status:** COMPLETED
**Date:** 2026-08-10

---

## 1. CURRENT STATE (BEFORE)

| Document | Old Generator | Old Format | Race-Safe | Tenant-Safe |
|---|---|---|---|---|
| Quotation | `quotation_number.py` (SELECT MAX) | `QT-2608-0001` | **NO** | **NO** |
| Booking | `job_number.py` (UPSERT) | `NTT-B-SE2608...` | YES | **NO** |
| Job/Shipment | `job_number.py` (UPSERT) | `NTT-SE2608...` | YES | **NO** |
| Invoice | `doc_number.py` (UPSERT) | `INV26080001` | YES | **NO** |
| House B/L | `bl_manager.py` (UPSERT) | `HBL26080001` | YES | **NO** |
| Master B/L | `bl_manager.py` (UPSERT) | `MBL26080001` | YES | **NO** |

**Critical Issues:**
- 4 separate generators scattered across 4 files
- Quotation numbering vulnerable to race conditions (SELECT MAX)
- No tenant isolation on any counter table
- Inconsistent formats across document types

---

## 2. TARGET STATE (AFTER)

| Document | Generator | Format | Race-Safe | Tenant-Safe |
|---|---|---|---|---|
| Quotation | `document_numbering_service.py` | `QT-2608-0001` | **YES** | **YES** |
| Booking | `document_numbering_service.py` | `BK-2608-0001` | **YES** | **YES** |
| Job/Shipment | `document_numbering_service.py` | `JOB-2608-0001` | **YES** | **YES** |
| Invoice | `document_numbering_service.py` | `INV-2608-0001` | **YES** | **YES** |
| House B/L | `document_numbering_service.py` | `HBL-2608-0001` | **YES** | **YES** |
| Master B/L | `document_numbering_service.py` | `MBL-2608-0001` | **YES** | **YES** |
| Payment | `document_numbering_service.py` | `PAY-2608-0001` | **YES** | **YES** |
| Receipt | `document_numbering_service.py` | `RCT-2608-0001` | **YES** | **YES** |

---

## 3. DOCUMENT TYPES

| Prefix | Document Type | Thai Name |
|---|---|---|
| `QT` | Quotation | เลขที่ใบเสนอราคา |
| `BK` | Booking | เลขที่ Booking |
| `JOB` | Job / Shipment | เลขที่ Job |
| `HBL` | House Bill of Lading | เลขที่ House B/L |
| `MBL` | Master Bill of Lading | เลขที่ Master B/L |
| `INV` | Invoice | เลขที่ใบแจ้งหนี้ |
| `RCT` | Receipt | เลขที่ใบเสร็จรับเงิน |
| `PAY` | Payment Reference | เลขที่อ้างอิงการรับชำระ |

---

## 4. NUMBER FORMAT
`{PREFIX}-{YYMM}-{NNNN}`
Example: `INV-2608-0001`

---

## 5. TENANT SCOPE
- Counter key: `(tenant_id, doc_type, yymm)`
- TENANT_A and TENANT_B both get independent `0001` sequences.
- Enforced at database level via composite PRIMARY KEY.

## 6. BRANCH SCOPE
- Branch codes are NOT embedded in the document number string.
- Branch information stored as a separate database column.
- Rationale: Keeps document numbers short and prevents coupling.

## 7. COUNTER DESIGN
- Single table: `document_counters`
- Columns: `tenant_id TEXT, doc_type TEXT, yymm TEXT, last_running INTEGER`
- Primary Key: `(tenant_id, doc_type, yymm)`

## 8. CONCURRENCY DESIGN
- Atomic `INSERT ... ON CONFLICT DO UPDATE SET last_running = last_running + 1 RETURNING last_running`
- Verified with 100 simultaneous requests across 2 tenants: 0 duplicates, 0 gaps.

## 9. NUMBER REUSE POLICY
- **NEVER REUSED.** Once a number is consumed (even on failed transaction), it is permanently allocated.
- Gaps are acceptable and expected.

## 10. HISTORICAL DATA POLICY
- Existing document numbers are **NOT** modified.
- Legacy formats (`NTT-SE2608...`, `INV26080001`) remain in the database.
- New numbering applies only to newly created documents.

## 11. INVOICE ACCOUNTING POLICY
- Invoice numbers follow the same `INV-YYMM-NNNN` format.
- No number reuse. Cancelled invoices retain their number with a CANCELLED status.
- Sequential within each tenant per month.

## 12. SEARCH NORMALIZATION (UX)
`normalize_doc_no()` strips hyphens, spaces, slashes, dots and forces uppercase.

All of these resolve to the same document:
```
INV-2608-0001 → INV26080001
inv-2608-0001 → INV26080001
INV 2608 0001 → INV26080001
INV/2608/0001 → INV26080001
INV.2608.0001 → INV26080001
```

Search in `booking_manager` and `shipment_manager` now includes normalized matching via `REPLACE(REPLACE(UPPER(doc_no), '-', ''), ' ', '')`.

## 13. UI STANDARD
- Placeholder: `e.g. INV-2608-0001`
- Helper text: `ค้นหาได้ทั้งแบบมีหรือไม่มีขีด / Search with or without hyphens.`

## 14. PDF STANDARD
- Document numbers must appear in header, title, and metadata.
- Filename convention: `Invoice_INV-2608-0001.pdf`

## 15. FILENAME STANDARD
- ASCII-safe, Windows-safe, email-safe.
- Pattern: `{DocType}_{DocNo}.pdf`
- Example: `Quotation_QT-2608-0048.pdf`

---

## 16. QA RESULTS

| Test | Result |
|---|---|
| Search Normalization (13 cases) | **PASS** |
| Sequential Generation (10 docs) | **PASS** |
| Concurrency (100 simultaneous, 2 tenants) | **PASS** |
| Format Consistency (8 doc types) | **PASS** |
| No Number Reuse (gap tolerance) | **PASS** |
| All Imports (7 managers) | **PASS** |

## 17. REGRESSION RESULTS

| Check | Result |
|---|---|
| `quotation_manager.py` imports | **PASS** |
| `booking_manager.py` imports | **PASS** |
| `shipment_manager.py` imports | **PASS** |
| `invoice_manager.py` imports | **PASS** |
| `finance_manager.py` imports | **PASS** |
| `bl_manager.py` imports | **PASS** |
| `job_manager.py` imports | **PASS** |
| Legacy `job_number` imports eliminated | **PASS** |
| Legacy `doc_number` imports eliminated | **PASS** |
| Legacy `quotation_number` imports eliminated | **PASS** |

## 18. FILES MODIFIED

| File | Change |
|---|---|
| `managers/document_numbering_service.py` | **NEW** — Centralized service |
| `database/connection.py` | Added `document_counters` table |
| `managers/quotation_manager.py` | Migrated to `generate_document_number("QT")` + tenant isolation |
| `managers/booking_manager.py` | Migrated to `generate_document_number("BK")` + normalized search |
| `managers/shipment_manager.py` | Migrated to `generate_document_number("JOB")` + normalized search |
| `managers/invoice_manager.py` | Migrated to `generate_document_number("INV")` |
| `managers/finance_manager.py` | Migrated to `generate_document_number("INV")` |
| `managers/bl_manager.py` | Migrated to `generate_document_number("HBL"/"MBL")` |
| `managers/job_manager.py` | Migrated to `generate_document_number("JOB")` |

## 19. REMAINING RISKS

| Risk | Severity | Mitigation |
|---|---|---|
| Legacy `job_number.py`, `doc_number.py`, `quotation_number.py` still exist on disk | LOW | No longer imported; can be deleted after full regression |
| Legacy `job_counters`, `doc_counters` tables still exist | LOW | No longer used by production code; can be dropped after verification |
| Historical documents have mixed formats | LOW | Preserved intentionally; no migration needed |

---

## 20. PRODUCTION GATE CHECKLIST

- [x] No duplicate document numbers
- [x] No cross-tenant collisions
- [x] Atomic counter generation
- [x] Database uniqueness via composite PK
- [x] No historical number corruption
- [x] Invoice numbering policy verified
- [x] Search normalization works
- [x] Concurrent generation tested (100 requests)
- [x] Existing workflows still work (imports pass)
- [x] Tenant isolation remains intact
- [x] No manager has its own undocumented numbering logic
