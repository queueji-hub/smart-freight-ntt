# PHASE 21 — MODULE DUPLICATION AUDIT

This audit identifies duplicates, legacy patterns, and mixed database access patterns in the Smart Freight NTT codebase.

## A. Duplicate Managers & Core Functions

1. **Milestone Management**
   - **Canonical**: [milestone_manager.py](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/managers/milestone_manager.py)
   - **Wrapper**: `list_milestones`, `add_milestone`, `delete_milestone` in [shipment_manager.py](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/managers/shipment_manager.py)
   - **Classification**: COMPATIBILITY WRAPPERS (shipment_manager), CANONICAL (milestone_manager).

2. **Container Management**
   - **Canonical**: [container_manager.py](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/managers/container_manager.py)
   - **Wrapper**: `list_job_containers`, `add_job_container`, `delete_job_container` in [shipment_manager.py](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/managers/shipment_manager.py)
   - **Classification**: COMPATIBILITY WRAPPERS (shipment_manager), CANONICAL (container_manager).

3. **Document Numbering**
   - **Canonical**: [document_numbering_service.py](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/managers/document_numbering_service.py)
   - **Legacy/Duplicate**: [doc_number.py](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/managers/doc_number.py), `quotation_number.py`, `job_number.py`
   - **Classification**: CANONICAL (document_numbering_service), LEGACY/DEAD (doc_number, quotation_number, job_number).

## B. Database Access Helpers & Inconsistent patterns
- `database/connection.py` defines `get_connection()` context manager and `execute_query()`.
- Some files (e.g. `managers/milestone_manager.py`) call `conn.execute(...)` directly, which is incompatible with psycopg2.
- Classification: CANONICAL (psycopg2 cursor pattern), INCOMPATIBLE (direct conn.execute on psycopg2).

## C. Month-End Reporting Mismatch
- `managers/month_end_manager.py` defines `get_month_end_summary(reporting_month)`.
- UI passes `r_month, r_year` which raises argument count mismatch errors.
- Classification: NEEDS MERGE / REFACTOR.
