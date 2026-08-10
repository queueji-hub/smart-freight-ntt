# P0-2.2 CANONICAL MANAGER ADAPTER PLAN
## Smart Freight NTT — Adapter Design & Migration Sequence

### 1. Executive Summary
This design document defines a safe transition path to eliminate duplicated Container and Milestone logic from `managers/shipment_manager.py`. Rather than immediately rewriting the UI layer (`views/shipment_view.py`), we will transform the deprecated functions in `shipment_manager.py` into **thin compatibility adapters** that internally delegate to the canonical managers. This approach ensures zero disruption to the UI while unifying the underlying database access layer (DAL). A critical discovery reveals that `milestone_manager.py` currently uses incorrect schema columns, requiring a fix before delegation can occur.

### 2. Current Interface Analysis
**Shipment Manager (Legacy UI Interface):**
- `add_job_container(data: Dict[str, Any]) -> bool`
- `list_job_containers(job_no: str) -> List[Dict]`
- `delete_job_container(container_id: int, job_no: str) -> bool`
- `add_milestone(data: Dict[str, Any]) -> bool`
- `list_milestones(job_no: str) -> List[Dict]`
- `delete_milestone(milestone_id: int, job_no: str) -> bool`

**Canonical Managers:**
- `container_manager.add_container(data: Dict[str, Any]) -> int` (Actually returns `bool` in code)
- `container_manager.list_containers(bl_no: str = None, job_no: str = None) -> List[Dict[str, Any]]`
- `milestone_manager.add_milestone(shipment_id: int, code: str, name: str, occurred_at: Optional[str] = None, note: Optional[str] = None) -> int`

### 3. Container Interface Comparison
The UI sends a dictionary (`data`) to `add_job_container`. Fortunately, `container_manager.add_container` also accepts a dictionary.
However, `add_job_container` checks `_ensure_job_unlocked` and calculates `shipment_id` dynamically if missing.
The canonical `container_manager` enforces VGM/Tare calculations but lacks the `_ensure_job_unlocked` check and lacks a `delete_container` function.

### 4. Milestone Interface Comparison & Schema Mismatch Discovery
**CRITICAL FINDING:** `milestone_manager.py` expects `occurred_at` and `note`. However, the actual database schema in `database/connection.py` uses `event_date`, `location`, and `remark`. The `milestone_manager.py` is disconnected from reality and must be updated to match the database schema before it can act as the canonical manager. The legacy UI sends a dictionary with `milestone_code`, `event_date`, and `location`.

### 5. `job_no` → `shipment_id` Resolution Strategy
The `containers` and `shipment_milestones` tables require both `job_no` and `shipment_id`.
The UI (`views/shipment_view.py`) operates entirely on `job_no`.
**Resolution Strategy:** In the adapter, we will fetch `shipment_id` via a minimal SQL lookup: `SELECT id FROM shipments WHERE job_no = %s`. To prevent N+1 query problems during list operations, the `list_*` functions will join on `job_no` without needing `shipment_id` resolution.

### 6. Adapter Architecture
The deprecated functions in `shipment_manager.py` will be gutted and replaced with delegation logic.

**Example Container Adapter:**
```python
def add_job_container(data: Dict[str, Any]) -> bool:
    _ensure_job_unlocked(data.get("job_no"))
    # shipment_id is already resolved inside container_manager if missing, 
    # but to be safe, we ensure it's in the payload.
    from managers.container_manager import add_container
    return bool(add_container(data))
```

**Example Milestone Adapter:**
```python
def add_milestone(data: Dict[str, Any]) -> bool:
    _ensure_job_unlocked(data.get("job_no"))
    from managers.milestone_manager import add_milestone as canonical_add
    
    # Needs to resolve shipment_id first
    shipment_id = _resolve_shipment_id_from_job(data.get("job_no"))
    
    return bool(canonical_add(
        shipment_id=shipment_id,
        job_no=data.get("job_no"),
        code=data.get("milestone_code"),
        name=data.get("milestone_name", ""),
        event_date=data.get("event_date"),
        location=data.get("location"),
        remark=data.get("remark")
    ))
```

### 7. Before / After Architecture
**BEFORE:**
`views/shipment_view.py` → `shipment_manager.add_job_container` → [RAW SQL INSERT] → Database

**AFTER:**
`views/shipment_view.py` → `shipment_manager.add_job_container` [Adapter] → `container_manager.add_container` → [VGM CALC & RAW SQL INSERT] → Database

### 8. Exact Function Mapping
- `shipment_manager.list_job_containers` → thin wrapper returning `container_manager.list_containers(job_no=job_no)`
- `shipment_manager.delete_job_container` → thin wrapper calling a NEW `container_manager.delete_container(container_id, job_no)`
- `shipment_manager.list_milestones` → thin wrapper returning a NEW `milestone_manager.list_milestones(job_no)`
- `shipment_manager.delete_milestone` → thin wrapper calling a NEW `milestone_manager.delete_milestone(milestone_id, job_no)`

### 9. File-by-File Action Plan
- **`managers/shipment_manager.py`**: **MODIFY**. Strip all raw SQL for containers and milestones. Replace with adapter logic. Keep `_ensure_job_unlocked` as it is a Shipment-level lock.
- **`managers/container_manager.py`**: **MODIFY**. Add `delete_container`.
- **`managers/milestone_manager.py`**: **MODIFY**. Fix DB schema mismatch (`occurred_at` -> `event_date`, `note` -> `remark`, add `location`, `job_no`). Add `list_milestones`, `delete_milestone`.
- **`views/shipment_view.py`**: **KEEP AS-IS**. Do not change.
- **`views/bl_view.py`**: **KEEP AS-IS**. Do not change.
- **`managers/bl_manager.py`**: **DO NOT TOUCH**.
- **`pdf/bl_pdf.py`**: **DO NOT TOUCH**.
- **`database/connection.py`**: **DO NOT TOUCH**.

### 10. Implementation Sequence
- **P0-2.2-A:** Update `milestone_manager.py` to fix schema columns and add missing list/delete functions.
- **P0-2.2-B:** Update `container_manager.py` to add `delete_container`.
- **P0-2.2-C:** Implement adapters in `shipment_manager.py`. Remove duplicated SQL.
- **P0-2.2-D:** Regression testing via UI.
- **P0-2.2-E:** (Future Phase) Modify UI to import directly from canonical managers and drop the adapters.

### 11. Regression Test Plan
- **Container Add:** Validate that adding a container via UI succeeds, and that VGM/Tare are now automatically calculated in the DB.
- **Container Delete:** Validate deletion respects `job_no` scoping and `_ensure_job_unlocked`.
- **Milestone Add/Delete:** Validate milestones appear correctly in the Job UI and save to the DB without crashing due to schema mismatch.
- **B/L Linkage:** Verify the multi-select box in B/L Workspace still successfully pulls `list_job_containers`.
- **Cross-job protection:** Validate it is impossible to delete a container belonging to a different job.

### 12. Rollback Strategy
Git rollback. Since this touches zero database schema (we are conforming Python to the DB, not vice versa), rolling back Python files via `git checkout HEAD` ensures immediate 100% recovery.

### 13. Risks
- VGM/Tare calculation in `container_manager.add_container` might overwrite user-submitted 0.0 values with ISO standard defaults (e.g., Tare = 3900 for 40HC). The UI must handle this seamlessly.

### 14. Final Recommendation
Proceed with the Adapter implementation (Sequence P0-2.2 A→C). The discovery that `milestone_manager.py` was built with incorrect columns proves that the current UI reliance on `shipment_manager.py` was technically a saving grace. Fixing the canonical managers and implementing the adapter is the safest and most robust path.

**P0-2.2 DESIGN COMPLETE — NO PRODUCTION FILES MODIFIED.**
