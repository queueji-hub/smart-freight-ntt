# DOCUMENT NUMBER AUDIT

## 1. INVENTORY SUMMARY

| Document | Prefix | Current Generator | Table / Logic | Tenant-Safe | Concurrency-Safe | Human-Readable |
|---|---|---|---|---|---|---|
| Quotation | `QT-YYMM-0000` | `managers/quotation_number.py` | `quotations` (SELECT MAX) | NO | NO (Race Condition) | Yes |
| Booking | `NTT-B-SE2608...` | `managers/job_number.py` | `job_counters` (UPDATE) | NO | YES | Marginal (Long) |
| Job / Shipment | `NTT-SE2608...` | `managers/job_number.py` | `job_counters` (UPDATE) | NO | YES | Marginal (Long) |
| Invoice / AR | `INV26080000` | `managers/doc_number.py` | `doc_counters` (RETURNING) | NO | YES | Yes |
| House B/L | `HBL26080000` | `managers/bl_manager.py` | `job_counters` (UPDATE) | NO | YES | Yes |
| Master B/L | `MBL26080000` | `managers/bl_manager.py` | `job_counters` (UPDATE) | NO | YES | Yes |

## 2. KEY ISSUES DISCOVERED
1. **Decentralized Generators:** Document generation logic is scattered across four different managers (`quotation_number.py`, `job_number.py`, `doc_number.py`, `bl_manager.py`). 
2. **Quotation Concurrency Risk:** `generate_quotation_number` performs a `SELECT quotation_no FROM quotations ... ORDER BY DESC LIMIT 1` followed by string splitting in Python. This is highly vulnerable to race conditions when multiple users create quotations simultaneously.
3. **No Tenant Isolation in Counters:** The `doc_counters` and `job_counters` tables do not have a `tenant_id` column. The entire platform currently shares sequence numbers across all tenants. 
4. **Counter Table Duplication:** There are two counter tables doing the same thing: `job_counters` and `doc_counters`.
5. **Atypical Formatting:** Booking numbers derive directly from Job sequence generators (e.g., `NTT-B-SE2608...`). A separate sequence for Booking (`BK-2608-0001`) is generally preferred for independent lifecycle management.
6. **No Uniqueness Constraints (Tenant Context):** The `UNIQUE` database constraints currently apply globally (e.g. `quotation_no TEXT UNIQUE NOT NULL`). With multi-tenancy, it usually requires a composite `UNIQUE(tenant_id, document_no)`.

## 3. LIFECYCLE BEHAVIOR
- **Reuse:** None of the generators reuse deleted numbers.
- **Rollback handling:** If a transaction fails after calling the counter (e.g. `generate_doc_number`), the counter is already incremented/committed. The number is consumed (leaving a gap). This is standard for performance but may require explanation for accountants looking at Invoice sequences.

## 4. BRANCH SUPPORT
- No current branch code support is implemented. (e.g. `BKK` or `CNX`).

## 5. RECOMMENDATION
- Consolidate all document generation into a single service.
- Add `tenant_id` to the counter table schema.
- Define a canonical `generate_document_number` method.
- Update `UNIQUE` database constraints to be `(tenant_id, document_no)`.
