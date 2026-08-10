# SYSTEM REAL UNUSED FILE AUDIT
## Smart Freight NTT

### Duplicated / Legacy Files
1. **Container Management**:
   - `managers/container_manager.py` handles container additions and SOLAS VGM checks.
   - However, `managers/shipment_manager.py` contains identical SQL inserts (`add_job_container`). This renders one of these implementations redundant and highly risky.

2. **Milestone Management**:
   - `managers/shipment_manager.py` also contains `add_milestone` and `list_milestones` which duplicates responsibility.

### Dead Imports
- The system heavily relies on `managers.shipment_manager.add_job_container` while `managers.container_manager.add_container` is possibly completely disconnected from the active UI pipeline.

**REALITY AUDIT COMPLETE — NO PRODUCTION FILES MODIFIED.**
