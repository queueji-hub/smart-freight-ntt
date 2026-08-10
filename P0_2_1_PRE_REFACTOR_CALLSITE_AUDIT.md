# P0-2.1 PRE-REFACTOR CALL-SITE AUDIT
## Smart Freight NTT

### 1. Executive Summary
A comprehensive call-site and dependency audit was performed on the entire repository to identify all imports and execution paths for the duplicated Container and Milestone logic. The audit confirms that the UI layer relies entirely on the deprecated functions within `managers/shipment_manager.py`. Refactoring this will require careful adaptation, as the canonical managers (`container_manager.py` and `milestone_manager.py`) have different function signatures and behavioral traits (e.g., ISO validations, VGM calculations).

### 2. Complete Deprecated Function Call Map
**Container Functions (`managers/shipment_manager.py`)**
- `add_job_container(data)`
  - Called by: `views/shipment_view.py` (line 149, 538)
  - Passes: `Dict` from UI form.
  - Expects: Boolean/Success state.
- `list_job_containers(job_no)`
  - Called by: `views/shipment_view.py` (line 113, 452, 502) and `views/bl_view.py` (line 405)
  - Passes: `job_no` string.
  - Expects: `List[Dict]` of container records.
- `delete_job_container(container_id, job_no)`
  - Called by: `views/shipment_view.py` (line 123, 512)
  - Passes: `del_id` integer and `job_no`.
  - Expects: Boolean/Success state.

**Milestone Functions (`managers/shipment_manager.py`)**
- `add_milestone(data)`
  - Called by: `views/shipment_view.py` (line 207)
  - Passes: `Dict` from UI form.
  - Expects: Boolean/Success state.
- `list_milestones(job_no)`
  - Called by: `views/shipment_view.py` (line 169)
  - Passes: `job_no`.
  - Expects: `List[Dict]` of milestone records.
- `delete_milestone(milestone_id, job_no)`
  - Called by: `views/shipment_view.py` (line 181)
  - Passes: `del_id` integer and `job_no`.
  - Expects: Boolean/Success state.

### 3. Complete Canonical Function Call Map
**Container Functions (`managers/container_manager.py`)**
- `add_container(data)`
  - Called by: Internally by `parse_and_add_containers_batch` (line 206).
  - Not called by any UI component.
- `list_containers(bl_no, job_no)`
  - Called by: Internally by `validate_job_readiness_for_billing` (line 245).
  - Not called by any UI component.

**Milestone Functions (`managers/milestone_manager.py`)**
- `add_milestone(shipment_id, code, name, occurred_at, note)`
  - Called by: No UI components. Completely disconnected.
- `update_milestone(...)`
  - Called by: No UI components.

### 4. Container Behavioral Comparison
| Feature | Deprecated (`shipment_manager`) | Canonical (`container_manager`) |
|---------|--------------------------------|----------------------------------|
| Signature | `add_job_container(data: Dict)` | `add_container(data: Dict)` |
| ISO 6346 Validation | None (Allows blind entry) | Yes (Calculates Checksum) |
| VGM & Tare Logic | None (Blind insert) | Yes (`calculate_container_metrics`) |
| Lock Validation | Yes (`_ensure_job_unlocked`) | None currently |
| Duplicate Check | Yes (Checks unique constraint catch) | Yes (via SQL INSERT payload) |
| Return Value | `bool` | `int` (Returns True actually in code) |

### 5. Milestone Behavioral Comparison
| Feature | Deprecated (`shipment_manager`) | Canonical (`milestone_manager`) |
|---------|--------------------------------|----------------------------------|
| Signature | `add_milestone(data: Dict)` | `add_milestone(shipment_id, code, ...)` |
| Linkage | Links via `job_no` | Links via `shipment_id` (Integer FK) |
| Lock Validation | Yes (`_ensure_job_unlocked`) | None currently |
| Duplicate Check | Yes (Checks exact time/location) | None |

### 6. UI Dependency Analysis
`views/shipment_view.py` is entirely dependent on `managers.shipment_manager` for both Containers and Milestones. The UI forms construct a dictionary mapping directly to the DB column schemas expected by the deprecated functions. To safely swap this, the new Canonical managers must accept these exact dictionary payloads or the UI must be rewritten to match positional arguments.

### 7. B/L Dependency Analysis
- `views/bl_view.py` imports `list_job_containers` from `managers.shipment_manager`. It uses this to populate the multi-select box for linking containers to B/Ls.
- `managers/bl_manager.py` interacts heavily with the `bl_containers` junction table but does NOT import `shipment_manager`.
- `pdf/bl_pdf.py` relies solely on `managers.bl_manager.list_bl_containers` to pull data for rendering. It does not call any deprecated container functions.

### 8. Hidden / Indirect Dependencies
- **Status Locking:** The deprecated `add_job_container` checks `_ensure_job_unlocked`. If we move to `container_manager`, we MUST migrate the `_ensure_job_unlocked` validation or the UI will allow users to add containers to "Closed" jobs.
- **Job_no vs Shipment_id:** The canonical milestone manager expects a `shipment_id` (integer) while the UI passes `job_no` (string). This is a critical mismatch that requires a database lookup adapter.

### 9. Risk Assessment
- **HIGH RISK:** Changing the import in `views/shipment_view.py` from `add_job_container` to `add_container` will break if `add_container` throws validation errors (e.g., ISO checksum fails) that the UI isn't prepared to display nicely, or if the UI passes `job_no` and the new function expects `shipment_id`.
- **MEDIUM RISK:** Moving the `delete_container` and `delete_milestone` functions. They don't exist in the canonical managers yet, so they must be copy-pasted and adapted securely.
- **LOW RISK:** `views/bl_view.py` importing `list_containers` instead of `list_job_containers`.

### 10. Exact Files That Must Be Modified
1. `managers/shipment_manager.py` (Delete deprecated functions)
2. `managers/container_manager.py` (Adapt `add_container`, add `delete_container`, adapt `list_containers`)
3. `managers/milestone_manager.py` (Rewrite to accept `data: Dict`, add `list_milestones`, add `delete_milestone`)
4. `views/shipment_view.py` (Update imports and function calls)
5. `views/bl_view.py` (Update imports for `list_containers`)

### 11. Exact Functions That Must Be Replaced
- `shipment_manager.add_job_container` → `container_manager.add_container`
- `shipment_manager.list_job_containers` → `container_manager.list_containers`
- `shipment_manager.delete_job_container` → `container_manager.delete_container`
- `shipment_manager.add_milestone` → `milestone_manager.add_milestone`
- `shipment_manager.list_milestones` → `milestone_manager.list_milestones`
- `shipment_manager.delete_milestone` → `milestone_manager.delete_milestone`

### 12. Functions That MUST NOT Be Deleted Yet
- The `_ensure_job_unlocked(job_no)` function in `shipment_manager.py` MUST be kept, or imported by the new managers to ensure status locking is preserved.
- `container_manager.calculate_container_metrics`
- `container_manager.validate_container_number`

### 13. Recommended Refactor Sequence
1. **Phase 1 (Manager Expansion):** Add `delete_container`, `list_containers`, and `delete_milestone`, `list_milestones` to the canonical managers. Adapt their `add_*` functions to accept the exact dictionaries the UI sends. Integrate `_ensure_job_unlocked`.
2. **Phase 2 (UI Cutover):** Modify `views/shipment_view.py` and `views/bl_view.py` to import and call the canonical managers.
3. **Phase 3 (Cleanup):** Delete the deprecated functions from `shipment_manager.py`.

### 14. QA Test Plan Before Refactor
- Create a Job.
- Add a Container in the UI (observe it saves successfully without VGM validation).
- Add a Milestone in the UI.
- Verify B/L container selection UI works.

### 15. QA Test Plan After Refactor
- Attempt to add a Container. It should now enforce ISO 6346 validation (if the UI handles the exception) and auto-calculate VGM.
- Attempt to add a Milestone. It should save accurately.
- Verify `views/bl_view.py` can still list containers for a job.
- Verify we cannot add a container to a "Closed" job (status lock check intact).

### 16. Final Recommendation
Proceed with the refactor. The architectural mismatch is severe, and the UI is currently bypassing critical CargoWise standard compliance checks (VGM/ISO) because it uses the deprecated functions. Adapting the canonical managers to accept the UI's dictionary payload is the safest path forward.

**PRE-REFACTOR AUDIT COMPLETE — NO PRODUCTION FILES MODIFIED.**
