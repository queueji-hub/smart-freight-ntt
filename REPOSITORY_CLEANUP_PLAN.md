# REPOSITORY CLEANUP PLAN

> **AUDIT STATUS**: COMPLETED  
> **RULE**: NO FILES HAVE BEEN DELETED, RENAMED, MOVED, OR OVERWRITTEN DURING THIS AUDIT.

---

## 1. Executive Strategy & Evidence Governance
The goal of this cleanup plan is to reduce technical debt, eliminate zero-reference duplicate code, and decrease repository weight **WITHOUT** altering production behavior or breaking active dependencies.

Every item proposed for deletion or archiving includes verified empirical evidence.

---

## 2. Comprehensive Cleanup Candidates Table

| Item / Path | Classification | Type of Complexity | Evidence & Verification | Proposed Action | Phase |
| :--- | :--- | :--- | :--- | :--- | :---: |
| [`app.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/app.py) | **SAFE TO DELETE** | Duplicate Entry Alias | Contains 3 lines delegating to `Dashboard.py`. Unimported by any module. | Delete after user confirmation | **Phase 1** |
| [`core/security.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/core/security.py) | **SAFE TO DELETE** | 0-Byte Empty File | File size is 2 bytes (empty). Unimported. Auth lives in `managers/auth_manager.py`. | Delete after user confirmation | **Phase 1** |
| [`services/booking_service.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/services/booking_service.py) | **SAFE TO DELETE** | 0-Byte Empty File | File size is 0 bytes. Unimported. Booking logic lives in `managers/booking_manager.py`. | Delete after user confirmation | **Phase 1** |
| [`services/job_service.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/services/job_service.py) | **SAFE TO DELETE** | 0-Byte Empty File | File size is 0 bytes. Unimported. Job logic lives in `managers/shipment_manager.py`. | Delete after user confirmation | **Phase 1** |
| `temp/*` | **SAFE TO DELETE** | Empty Temporary Directory | Directory is empty. | Remove empty directory | **Phase 1** |
| [`views/finance.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/views/finance.py) | **SAFE TO ARCHIVE** | Legacy View Prototype | Early prototype view superseded by `views/billing_view.py`. Unimported by `Dashboard.py`. | Move to `archive/views/` | **Phase 2** |
| [`contracts/core_contract.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/contracts/core_contract.py) | **SAFE TO ARCHIVE** | Legacy Spec Contract | Unused TypedDict spec. Unimported by active views and managers. | Move to `archive/contracts/` | **Phase 2** |
| [`contracts/crm_contract.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/contracts/crm_contract.py) | **SAFE TO ARCHIVE** | Legacy Spec Contract | Unused CRM TypedDict spec. Unimported. | Move to `archive/contracts/` | **Phase 2** |
| [`contracts/invoice_contract.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/contracts/invoice_contract.py) | **SAFE TO ARCHIVE** | Legacy Spec Contract | Unused Invoice TypedDict spec. Unimported. | Move to `archive/contracts/` | **Phase 2** |
| [`core/audit.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/core/audit.py) | **SAFE TO ARCHIVE** | Standalone Logger Spec | Standalone audit helper. Active audit logging occurs directly in connection/managers. | Move to `archive/core/` | **Phase 2** |
| [`core/state.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/core/state.py) | **SAFE TO ARCHIVE** | Unused Session Spec | Unused state wrapper. Views access `st.session_state` directly. | Move to `archive/core/` | **Phase 2** |
| [`core/workflow_engine.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/core/workflow_engine.py) | **SAFE TO ARCHIVE** | Unused Enum Spec | Early workflow state enum. Unused by active view code. | Move to `archive/core/` | **Phase 2** |
| [`repositories/quotation_repo.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/repositories/quotation_repo.py) | **SAFE TO ARCHIVE** | Abandoned Experiment | Early Repository pattern experiment superseded by `managers/quotation_manager.py`. | Move to `archive/repositories/` | **Phase 2** |
| [`services/quotation_service.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/services/quotation_service.py) | **SAFE TO ARCHIVE** | Abandoned Experiment | Early service layer wrapper. Unimported. | Move to `archive/services/` | **Phase 2** |
| [`ui/quotation_ui.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/ui/quotation_ui.py) | **SAFE TO ARCHIVE** | Legacy UI Prototype | Early prototype UI script superseded by `views/quotation_view.py`. | Move to `archive/ui/` | **Phase 2** |
| [`managers/db_persistence.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/managers/db_persistence.py) | **SAFE TO ARCHIVE** | Legacy Persistence Helper | SQLite persistence helper superseded by `database/connection.py`. | Move to `archive/managers/` | **Phase 2** |
| [`managers/demurrage_manager.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/managers/demurrage_manager.py) | **SAFE TO ARCHIVE** | Legacy Standalone Script | Standalone calculation script unimported by active presentation views. | Move to `archive/managers/` | **Phase 2** |
| [`managers/lcl_manager.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/managers/lcl_manager.py) | **SAFE TO ARCHIVE** | Legacy Standalone Script | Standalone LCL calculation script. Logic embedded in shipment manager. | Move to `archive/managers/` | **Phase 2** |
| [`managers/template_manager.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/managers/template_manager.py) | **SAFE TO ARCHIVE** | Legacy Standalone Script | Standalone document template helper. Unimported. | Move to `archive/managers/` | **Phase 2** |
| [`utils/quotation_number.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/utils/quotation_number.py) & [`managers/quotation_number.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/managers/quotation_number.py) | **REQUIRES REVIEW** | Duplicate Counter Function | Duplicates doc numbering logic. | Consolidation into `managers/doc_number.py` | **Phase 3** |
| `freight-os-compact/*` | **REQUIRES REVIEW** | Parallel Next.js App | Standalone Next.js TypeScript subproject. | Maintain in separate subproject | **Phase 4** |
| `freight-os-mvp/*` | **REQUIRES REVIEW** | Parallel Next.js App | Standalone Next.js Prisma subproject. | Maintain in separate subproject | **Phase 4** |
| Core Files in [`Dashboard.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/Dashboard.py), [`database/connection.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/database/connection.py), Active Views & Managers | **DO NOT TOUCH** | Core Application Code | Active runtime system stack. | Retain in place without modification | **Phase 4** |

---

## 3. Four-Phase Cleanup Execution Roadmap

### Phase 1 — Safe Cleanup (Zero Risk)
- **Target**: Empty and 0-byte orphan placeholder files.
- **Files**: `app.py`, `core/security.py`, `services/booking_service.py`, `services/job_service.py`, `temp/` directory.
- **Action**: Delete after explicit user confirmation.
- **Verification**: Run `python -m py_compile Dashboard.py` to confirm zero compilation or import errors.

### Phase 2 — Low Risk Cleanup (Archiving Only)
- **Target**: Legacy prototype views, unimported contracts, and early specification experiments.
- **Files**: 13 files in Group E (`contracts/*`, `core/audit.py`, `core/state.py`, `core/workflow_engine.py`, `repositories/quotation_repo.py`, `services/quotation_service.py`, `ui/quotation_ui.py`, `managers/db_persistence.py`, `managers/demurrage_manager.py`, `managers/lcl_manager.py`, `managers/template_manager.py`, `views/finance.py`).
- **Action**: Safely move to an `archive/` folder preserving directory structure.
- **Verification**: Execute application regression sanity check.

### Phase 3 — Requires Testing (Duplicate Consolidation)
- **Target**: Duplicate number counter helper modules.
- **Files**: [`utils/quotation_number.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/utils/quotation_number.py) & [`managers/quotation_number.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/managers/quotation_number.py).
- **Action**: Consolidate number generator methods into [`managers/doc_number.py`](file:///c:/Users/User/Desktop/Got/Smart%20Freight%20NTT,/managers/doc_number.py).
- **Verification**: Verify quotation and invoice document sequence generation.

### Phase 4 — Do Not Clean Yet (Maintain & Isolate)
- **Target**: Core production application stack and parallel Next.js subprojects.
- **Files**: `Dashboard.py`, `config.py`, `database/connection.py`, all active views, active managers, PDF exporters, `freight-os-compact/`, `freight-os-mvp/`.
- **Action**: Do NOT clean or touch during current phase.
