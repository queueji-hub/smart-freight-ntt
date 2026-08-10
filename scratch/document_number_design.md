# DOCUMENT NUMBER ARCHITECTURE DESIGN

## 1. STRATEGY & GOALS
- Consolidate legacy generation (`managers/job_number.py`, `managers/quotation_number.py`, `managers/doc_number.py`) into a single, unified generation module: `managers/document_numbering_service.py`.
- Resolve quotation race conditions by utilizing a strict transactional database counter strategy, similar to the one used for invoices.
- Implement strict tenant isolation (`tenant_id` scopes) for all business sequences.
- Adopt standard canonical prefixes (`QT`, `BK`, `JOB`, `INV`, `HBL`, `MBL`, `RCT`, `PAY`).

## 2. FORMAT ARCHITECTURE
**Format:** `{PREFIX}-{YYMM}-{SEQ}`
**Examples:** `QT-2608-0001`, `JOB-2608-0001`
**Why YYMM?** It is standard in freight forwarding, keeping the sequence number short while segregating records by month, simplifying monthly accounting cycles and reporting. 
**Why not YYYY?** `202608` makes the document number unnecessarily long, increasing reading and dictation errors.

## 3. MULTI-TENANT ISOLATION (SEQUENCE SCOPE)
All counters will be generated with **Unique per Tenant** isolation.
The SaaS platform requires that `TENANT_A` and `TENANT_B` both maintain their own continuous sequences starting from `0001` every month without interacting with or perceiving each other's activity.

## 4. BRANCH SUPPORT
Branch codes will NOT be appended to the document string directly (e.g., *no* `QT-BKK-2608-0001`).
**Why?** Injecting branches into sequences creates bloated strings, makes searching more complex, and tightly couples the document to a branch when shipments frequently transfer between branches.
**Recommendation:** Maintain the physical string as `QT-2608-0001` but store the `branch_code` as an explicit relational column in the database (e.g., `quotations.branch_code = 'BKK'`).

## 5. COUNTER STORAGE DESIGN
A new universal tracking table will supersede `job_counters` and `doc_counters`.

```sql
CREATE TABLE document_counters (
    tenant_id TEXT NOT NULL,
    doc_type TEXT NOT NULL,
    yymm TEXT NOT NULL,
    last_running INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (tenant_id, doc_type, yymm)
);
```

**Concurrency Protection:** Generation will use `INSERT ... ON CONFLICT DO UPDATE SET last_running = last_running + 1 RETURNING last_running`, guaranteeing absolute atomic operations with zero race conditions during parallel execution.

## 6. NUMBER REUSE & GAPS
**Policy:** Strict NO-REUSE. 
If an invoice `INV-2608-0001` is cancelled or a transaction rollback occurs *after* the sequence is retrieved, `0001` remains consumed. The next document is `0002`. This is universally accepted and often required by auditors to track exactly where a number went (preventing deletion fraud).

## 7. HISTORICAL DATA MIGRATION
Historical data (pre-existing Quotations, Invoices, Jobs) will **NOT** be rewritten to match the new format. Modifying historical data risks breaking external API dependencies, PDF footprints, and customer interactions.
**Migration Approach:** 
1. New schema applied.
2. New documents use `document_counters` and the new format.
3. Existing references continue resolving their old strings.

## 8. UNIQUE CONSTRAINTS
All unique constraints across documents must be upgraded to composite constraints: `UNIQUE(tenant_id, quotation_no)`, `UNIQUE(tenant_id, booking_no)`, etc.
