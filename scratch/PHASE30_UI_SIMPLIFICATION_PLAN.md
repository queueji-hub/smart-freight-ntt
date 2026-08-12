# PHASE 30 — UI SIMPLIFICATION PLAN

This document outlines the consolidation plan for UI screens to match the operational needs of a 5–10 person freight forwarder.

## 1. Job Control Center & Job 360 Consolidation
* **Current State**: Separate `Job Control Center` lists jobs, and `Job Sheet 360` views details, with 10 tabs.
* **Proposed State**:
  * Consolidate into a single module `📦 Jobs & Operations` (`views/shipment_view.py`).
  * Display a simplified Job List showing columns: `JOB NO`, `CUSTOMER`, `MODE`, `POL`, `POD`, `ETD`, `ETA`, `STATUS`, `SALES`.
  * Select a Job to open the **Job 360 View**, which will be simplified into exactly **7 tabs**:
    1. **Overview**: Job No, Customer, Salesperson, Mode, POL, POD, ETD, ETA, Vessel / Flight, Status, Job Profit summary.
    2. **Operations**: Routing details, Vessel/Voyage, ATD, ATA, Customs details, and operational remarks.
    3. **Cargo & Containers**: Commodity description, container details (container number, size, seal, VGM, weight).
    4. **Milestones**: Timestamps and status of standard lifecycle events.
    5. **Documents**: Link to B/L details, transport orders, physical documents, and PDF generation.
    6. **Financial**: Displays detailed GP summary (Revenue, Est Cost, Actual Cost, Accrued Cost, Margin) and links to finance modules.
    7. **History**: Controlled revision history snapshots, audit logs, and version control.

## 2. Management Reports Consolidation
* **Current State**: Separate "Company Monthly Report" and "Sales Performance" tabs.
* **Proposed State**:
  * Consolidate reports into a single `Management Reports` view (`views/reports_view.py`).
  * Use a selector to switch between:
    * `Company Report` (displays month, revenue, cost, GP, margin, job counts, export/import jobs).
    * `Salesperson Report` (displays selector for salesperson, monthly summary of revenue, cost, GP, margin, commission, and a button to drill down to specific jobs).
