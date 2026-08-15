# Smart Freight NTT — Master Architecture

## Product intent

Production-oriented freight forwarding ERP for a 5–10 person team. The system favors **Simple > Complex**, one owner per business capability, and **Enter Once → Reuse Everywhere**.

## System spine

```text
Master Data
   ↓
Quotation
   ↓
Booking
   ↓
Job / Shipment  ← operational + financial spine
   ├─ Cargo / Containers
   ├─ Milestones
   ├─ Consolidation / B/Ls
   ├─ Documents
   └─ Finance
       ├─ Revenue / Invoice / Receipt
       ├─ Cost / AP / Payment
       └─ Profitability
```

## Ownership rules

- `customers`, sales/users, carriers, ports/places, vendors, charges and equipment are Master Data.
- Quotation owns commercial intent and pricing context.
- Booking owns carrier booking instructions and schedule context.
- Job/Shipment owns the operational truth.
- Finance owns financial transactions; it references the Job instead of cloning operational data.
- B/L is a child document of a Job/Shipment. One Job can have multiple company-issued B/Ls for consolidation.
- PDF engines only render validated payloads. They must not perform database reads or business calculations.

## Freight profiles

- Sea FCL → container-based, CY workflow, vessel/voyage enabled.
- Sea LCL → CBM-based, CFS workflow, vessel/voyage enabled.
- Air → KG / Chargeable KG, Loose handling.
- Truck → FTL/LTL workflow; no ocean vessel fields.

All profile rules must be enforced in UI, manager/write layer, document payload and report layer.

## Consolidation B/L model

```text
Shipment / Job
   ├─ B/L 001 → Shipper A
   ├─ B/L 002 → Shipper B
   └─ B/L 003 → Shipper C
```

The B/L number is company-issued and centrally sequenced, e.g. `NATTA-LCHNAH2608003`.

## Approval

```text
Draft → Pending Approval → Approved
```

Approval must be tenant-safe and role-controlled. Draft/Pending PDFs must show a visible draft/pending status; only Approved documents are official output.

## Layer rules

### Views / Frontend
- Streamlit only.
- Never write SQL.
- Call managers/services.
- Use session state for UI drafts and transient view state.

### Managers / Backend
- No Streamlit rendering.
- Enforce tenant isolation.
- Validate business rules before writes.
- Return plain Python values.

### PDF
- Accept validated payloads.
- No DB queries.
- No master-data lookups.
- No hidden business rules.
- Return PDF bytes/path.

### QA
- Verify source/schema/manager/UI/PDF contract.
- Test tenant isolation and approval transitions.
- Test end-to-end quote → booking → job → document → finance → profitability.

## Definition of done

A feature is complete only when source, schema, manager, UI, documents, tenant isolation, automated tests, deployment smoke and end-to-end workflow agree.
