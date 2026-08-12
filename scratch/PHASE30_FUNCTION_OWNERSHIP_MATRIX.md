# PHASE 30 — FUNCTION OWNERSHIP MATRIX

This matrix outlines the single owner module for each core functional area in the Smart Freight NTT platform.

| Function | Owner Module | Other Modules (Read-Only) |
| :--- | :--- | :--- |
| **Job Operations (Status, Routing)** | `managers/shipment_manager.py` | Dashboard, Reports, PDF |
| **Cargo & Container Details** | `managers/container_manager.py` | Shipment Manager, B/L |
| **Milestone Control** | `managers/milestone_manager.py` | Shipment Manager |
| **Bill of Lading Documents** | `managers/bl_manager.py` | Job Details |
| **Billing / Accounts Receivable (AR)** | `managers/invoice_manager.py` | Reports, Dashboard |
| **Accounts Payable (AP)** | `managers/ap_manager.py` | Reports |
| **Financial Summaries (GP & Profit)**| `managers/profit_manager.py` | Reports |
| **KPIs & Performance Aggregations** | `managers/report_manager.py` | Dashboard, Management Reports |
| **Sales Commission Calculations** | `managers/commission_manager.py` | Report Manager |
