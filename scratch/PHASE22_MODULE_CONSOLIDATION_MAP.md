# PHASE 22 — MODULE CONSOLIDATION MAP

This map outlines the consolidations, deprecations, and target canonical modules for this recovery phase.

| Domain | Canonical Module | Duplicate / Legacy Module | Action | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Shipment / Job** | `managers/shipment_manager.py` | `managers/job_manager.py` | Consolidated and deprecated. Deleted legacy file. | **CONSOLIDATED** |
| **Numbering** | `managers/document_numbering_service.py` | `managers/doc_number.py`<br/>`managers/job_number.py`<br/>`managers/quotation_number.py` | Consolidated to central service. Deleted legacy counters. | **CONSOLIDATED** |
| **UI Views** | Various Active Views | `views/fx_view.py`<br/>`views/finance.py` | Unused exact duplicates / dead code removed. | **CONSOLIDATED** |
| **Templates** | `managers/template_manager.py` | None | Fully implemented core missing functions and seeded defaults. | **STABILIZED** |
