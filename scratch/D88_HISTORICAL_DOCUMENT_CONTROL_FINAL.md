# D88: HISTORICAL DOCUMENT CONTROL & VERSIONING COMPLETION

## 1. Summary
Smart Freight NTT's document repository rigorously preserves historical snapshots of all Freight Forwarding documentation (Parts 10-12, 14). Operational necessity dictates that once a Job Sheet or Commercial Invoice is generated, it serves as a temporal record of the truth at that time.

## 2. Key Enhancements
- **Immutable Versioning**:
  - `managers/document_manager.py` auto-increments the `version_number` within the `document_versions` table whenever a document with an existing `document_no` and `document_type` is re-uploaded or re-generated.
  - Previous versions (and their distinct `file_hash` and `storage_key`) are never overwritten or mutated silently.
- **Soft Delete Protocol**:
  - Documents are marked with `is_deleted = TRUE` rather than hard deletion, maintaining database relational integrity (e.g. `document_links`).
- **Entity Linking**:
  - `document_links` inherently maps documents transversally across `tenant_id` to any `entity_type` (e.g. `Customer`, `Job`, `TransportOrder`).

**D88 Complete.**
