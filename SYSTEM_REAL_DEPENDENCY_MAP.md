# SYSTEM REAL DEPENDENCY MAP
## Smart Freight NTT

### Architecture Flow
1. **Entry Point**: `Dashboard.py`
2. **Session & Auth**: Imports `managers.auth_manager`, `managers.session_manager`
3. **Database Bootstrap**: Imports `database.connection.init_database`
4. **Dynamic Routing**: Uses `PAGE_ROUTES` to dynamically load `views.<module>_view`

### Component Dependencies

#### Booking Module
- **`views/booking_view.py`** 
  - IMPORTS: `managers.booking_manager`, `managers.quotation_manager`, `managers.auth_manager`, `pdf.booking_pdf`
- **`managers/booking_manager.py`** 
  - IMPORTS: `database.connection`, `managers.job_number`, `managers.shipment_manager`, `core.audit`

#### Shipment Module
- **`views/shipment_view.py`** 
  - IMPORTS: `managers.shipment_manager`, `managers.milestone_manager` (Wait: `shipment_manager` has duplicated milestone logic)
- **`managers/shipment_manager.py`** 
  - IMPORTS: `database.connection`, `managers.job_number`

#### Known Circular / Duplicate Risks
- **Duplicate Logic**: `shipment_manager.py` and `container_manager.py` both have direct SQL inserts to the `containers` table.
- **Duplicate Logic**: `shipment_manager.py` handles milestones directly instead of importing `milestone_manager.py` exclusively.

**REALITY AUDIT COMPLETE — NO PRODUCTION FILES MODIFIED.**
