# Smart Freight NTT

Freight forwarding operating system for NATTAYARAAT CO., LTD.

Target deployment: a lightweight, professional ERP for a 5–10 person forwarding team.

## Operating principle

**Enter once. Reuse everywhere.**

Master Data is the source of truth. Quotation and Booking are lightweight handoff modules. Job / Shipment is the operational center. Documents and Finance consume the Job record instead of creating disconnected copies.

```text
Master Data
    ↓
Quotation
    ↓
Booking
    ↓
Job / Shipment
    ├── Cargo & Containers
    ├── Milestones
    ├── Documents / B/L
    └── Finance
          ├── AR / Invoice / Receipt
          ├── AP / Vendor Cost / Payment
          └── Profitability
```

## Core modules

- **Home / AI** — operational and financial questions plus quick KPIs.
- **Customers** — customer master data, contacts, tax information and commercial terms.
- **Quotations** — customer, sales, route, service, charges, validity and terms.
- **Bookings** — carrier booking reference, routing, vessel, cargo and receiving instructions.
- **Jobs** — operational execution, milestones, cargo, documents, revenue, cost and financial context.
- **Documents** — Booking Confirmation, B/L and controlled financial documents.
- **Finance** — receivables, payables, payments, billing notes, tax invoices/receipts and profitability.
- **Reports** — management and operational reporting.
- **Master Data** — customers, sales, liners, ports/places, vendors, charges and equipment.
- **Settings** — access, tenant and application configuration.

## Freight handling rules

| Transport | Cargo | Primary Unit | Receiving |
|---|---|---|---|
| Sea | FCL | Container / Qty | CY |
| Sea | LCL | CBM / KG / Packages | CFS |
| Air | Air | KG / Chargeable KG | CFS |
| Truck | FTL | Truck / Qty | CFS |
| Truck | LTL | CBM / KG / Packages | CFS |

For vessel display, **Mother Vessel** is shown when available; otherwise **Vessel** is used.

Booking input uses the streamlined concepts:

`Transport → Liner → Vessel → Mother Vessel → Voyage → Transshipment Port`

Legacy Carrier / Feeder fields remain readable for historical records but are not part of the preferred new-entry workflow.

## Document control

Documents use a common approval state machine:

```text
Draft
  ↓
Pending Approval
  ↓
Approved
  ↓
Issued / Official PDF
```

Draft and Pending Approval documents are marked as draft output. Official clean PDFs require Approved status.

## PDF families

- Quotation
- Booking Confirmation
- Bill of Lading
- Tax Invoice / Receipt
- Billing Note
- Credit Note
- Debit Note
- Job Profitability

PDF generation is lazy-loaded and should occur only after an explicit user action.

## Master Data / SSOT

New records should use IDs for reusable master entities whenever the schema supports them:

- `customer_id`
- `sales_id`
- liner / carrier master reference
- port / place master reference
- charge master reference
- equipment / container type master reference

Legacy display text may remain for historical compatibility, but new workflows should not require free-text re-entry of master values.

## Performance rules

- Keep draft data in session state while users are editing.
- Commit on Save / Submit / Proceed rather than every widget change.
- Lazy-load PDF generation.
- Avoid loading heavy Job tabs unless selected.
- Cache stable master-data reads with tenant-aware keys when appropriate.
- Keep business managers independent from Streamlit UI code.

## Production gates

A module is considered production-ready only when all layers agree:

`Source → Schema → Manager → UI → PDF → Tests → CI → Migration Verification → UAT`

Current CI validates Python compilation, imports, freight rules, Booking/Quotation workspaces, SSOT write contracts, Charge Master, finance schema, tenant-safe document numbering, profitability tenant contracts, Payables schema, B/L workspace, Finance workspace, Document Center, PDF smoke output, Approval Workflow and Document Preflight.

## Database

Production PostgreSQL/Supabase DDL changes belong in `database/migrations/*.sql`.

The repository intentionally keeps incremental migrations separate from the canonical schema baseline so existing deployments are not overwritten by partial schema files.

Required Phase 30 migrations include:

- `20260815_booking_reference_separation.sql`
- `20260815_charge_master.sql`
- `20260815_phase30_ssot_workflow.sql`
- `20260815_document_numbering_tenant.sql`
- `20260815_profitability_tenant_contract.sql`
- `20260815_payables_contract.sql`

## Development

```bash
git clone https://github.com/queueji-hub/smart-freight-ntt.git
cd smart-freight-ntt
pip install -r requirements.txt
streamlit run Dashboard.py
```

## Branch policy for Phase 30

Development target:

`feature/phase30-preview`

Do not push these development changes directly to `main`.

## Deployment note

Streamlit Cloud should use PostgreSQL/Supabase for persistent production data. SQLite is retained as a development fallback only; production mode raises when PostgreSQL configuration is unavailable.
