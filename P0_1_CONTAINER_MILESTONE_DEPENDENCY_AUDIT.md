# P0-1 CONTAINER & MILESTONE DEPENDENCY AUDIT
## Smart Freight NTT — Pre-Refactor Inspection

### 1. Executive Summary
This audit inspects the current repository code to identify the exact locations and dependencies of Container and Milestone operations. The investigation confirms significant duplication where `managers/shipment_manager.py` handles database insertions directly, bypassing the dedicated logic in `managers/container_manager.py` and `managers/milestone_manager.py`. The source of truth for UI operations currently points to the duplicated functions in `shipment_manager.py`.

### 2. Actual Files Inspected
- `views/shipment_view.py`
- `views/bl_view.py`
- `managers/shipment_manager.py`
- `managers/container_manager.py`
- `managers/milestone_manager.py`
- `database/connection.py`

### 3. Container Function Inventory
- **Container INSERT:**
  - `managers/shipment_manager.py` (`add_job_container`) -> **USED BY UI**
  - `managers/container_manager.py` (`add_container`) -> NOT used by UI.
- **Container UPDATE:** None found.
- **Container DELETE:**
  - `managers/shipment_manager.py` (`delete_job_container`) -> **USED BY UI**
- **Container LIST/SELECT:**
  - `managers/shipment_manager.py` (`list_job_containers`) -> **USED BY UI**
  - `managers/container_manager.py` (`list_containers`) -> Used by internal validator.
- **Container Validation:**
  - `managers/container_manager.py` (`validate_container_number`, `calculate_container_metrics`).

### 4. Milestone Function Inventory
- **Milestone INSERT:**
  - `managers/shipment_manager.py` (`add_milestone`) -> **USED BY UI** (accepts `data: Dict`)
  - `managers/milestone_manager.py` (`add_milestone`) -> NOT used by UI (accepts positional args).
- **Milestone UPDATE:**
  - `managers/milestone_manager.py` (`update_milestone`) -> NOT used by UI.
- **Milestone DELETE:**
  - `managers/shipment_manager.py` (`delete_milestone`) -> **USED BY UI**
- **Milestone LIST/SELECT:**
  - `managers/shipment_manager.py` (`list_milestones`) -> **USED BY UI**
- **Milestone Validation:** None explicit.

### 5. Real Call Graph
**For Container:**
`views/shipment_view.py`
→ `shipment_manager.add_job_container()`
→ SQL INSERT
→ `containers` table

`views/bl_view.py`
→ `shipment_manager.list_job_containers()`
→ SQL SELECT
→ `containers` table

**For Milestone:**
`views/shipment_view.py`
→ `shipment_manager.add_milestone()`
→ SQL INSERT
→ `shipment_milestones` table

### 6. Duplicate Logic Found
- **Container:** Both `shipment_manager.py` and `container_manager.py` have raw SQL `INSERT` statements to the `containers` table. The one in `container_manager.py` intelligently calculates VGM, Tare, and Payload metrics. The one in `shipment_manager.py` relies solely on user input and skips validation.
- **Milestone:** Both `shipment_manager.py` and `milestone_manager.py` define `add_milestone` with different signatures.

### 7. Current Source of Truth
Despite `container_manager.py` and `milestone_manager.py` being the theoretical managers, the **actual operational Source of Truth** for the UI is currently `managers/shipment_manager.py`. All views import from `shipment_manager.py`.

### 8. Recommended Source of Truth
- **Container Canonical Manager:** `managers/container_manager.py`
- **Milestone Canonical Manager:** `managers/milestone_manager.py`

### 9. Functions Safe to Deprecate
- `managers/shipment_manager.py -> list_job_containers()` (Replace with `container_manager.list_containers()`)
- `managers/shipment_manager.py -> add_job_container()` (Replace with `container_manager.add_container()`)
- `managers/shipment_manager.py -> delete_job_container()` (Move logic to `container_manager.py`)
- `managers/shipment_manager.py -> list_milestones()` (Move logic to `milestone_manager.py`)
- `managers/shipment_manager.py -> add_milestone()` (Refactor to use `milestone_manager.add_milestone()`)
- `managers/shipment_manager.py -> delete_milestone()` (Move logic to `milestone_manager.py`)

### 10. Functions That Must NOT Be Deleted
- `container_manager.calculate_container_metrics()`
- `container_manager.validate_container_number()`
- `shipment_manager.create_shipment()`
- `shipment_manager.get_shipment()`

### 11. Compatibility Requirements
When migrating `add_job_container` to `add_container`, the data payload signature (`Dict[str, Any]`) must be preserved or mapped so that `views/shipment_view.py` does not break.
Similarly, `delete_job_container(container_id, job_no)` must be implemented as `delete_container(container_id, job_no)` in `container_manager.py`.

### 12. Regression Risk Matrix
| Module | Risk Level | Details |
|--------|------------|---------|
| Quotation | None | Not linked to Containers/Milestones. |
| Booking | None | Not linked to Containers/Milestones. |
| Job Conversion | None | Job generation does not trigger container insertion. |
| Shipment | **MEDIUM** | `views/shipment_view.py` must have imports updated successfully. |
| Container | **HIGH** | The core payload to `containers` table will change slightly because `container_manager` forces VGM calculation. |
| Milestone | **MEDIUM** | `shipment_milestones` schema is simple, low risk on migration. |
| B/L | **MEDIUM** | `views/bl_view.py` calls `list_job_containers`. Import must be updated. |
| B/L PDF | **MEDIUM** | PDFs render container data. Ensuring `list_containers` returns identical key formats is crucial. |
| Billing | Low | Billing requires VGM. Switching to `container_manager` will IMPROVE billing integrity. |

### 13. P0 Refactor Plan
- **Step 1:** Extract `delete_job_container` and `list_job_containers` from `shipment_manager.py` and merge them into `container_manager.py` as `delete_container` and `list_containers`.
- **Step 2:** Ensure `container_manager.add_container` supports all fields currently passed by `views/shipment_view.py`.
- **Step 3:** Extract `list_milestones`, `add_milestone`, `delete_milestone` from `shipment_manager.py` and merge them into `milestone_manager.py`. Ensure dictionary compatibility.
- **Step 4:** Update `views/shipment_view.py` and `views/bl_view.py` to import directly from `managers.container_manager` and `managers.milestone_manager`.
- **Step 5:** Remove the dead functions from `shipment_manager.py`.

### 14. Exact Files That Will Be Modified
- `managers/shipment_manager.py`
- `managers/container_manager.py`
- `managers/milestone_manager.py`
- `views/shipment_view.py`
- `views/bl_view.py`

### 15. Exact Files That Must NOT Be Modified
- `database/connection.py`
- `managers/booking_manager.py`
- `Dashboard.py`
- `views/booking_view.py`
- Any PDF generators (`pdf/bl_pdf.py`).

### 16. Pre-Refactor Backup/Recovery Recommendation
Ensure the repository is fully committed to `git` on the `main` branch (which was done recently) before making any code modifications. If tests fail, `git reset --hard HEAD` is sufficient.

### 17. QA Tests Required After Refactor
1. **Container Test**: Add a new container in `views/shipment_view.py`, verify it calculates VGM, and displays correctly. Delete it.
2. **Milestone Test**: Add a new milestone in `views/shipment_view.py`, verify it displays correctly. Delete it.
3. **B/L Link Test**: Open `views/bl_view.py` and confirm the container list renders correctly without throwing import errors.

### 18. Final Recommendation
The Refactor is highly recommended and low risk. Moving the functions will resolve the duplicate validation bypass and consolidate the Data Access Layer (DAL) cleanly.

**AUDIT COMPLETE — NO PRODUCTION FILES MODIFIED.**
