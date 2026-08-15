# SMART FREIGHT NTT — PRODUCTION READY BLUEPRINT

## Mission
Build a lightweight freight-forwarding ERP for a 5–10 person team with one connected flow from quotation to booking, Job/Shipment, documentation and finance.

## Core rule
Enter once, reuse everywhere. Master data is the source of truth. Job/Shipment is the operational spine.

## Canonical workflow

```text
Master Data
  ↓
Quotation
  ↓
Booking
  ↓
Job / Shipment
  ├─ Cargo & Containers
  ├─ Milestones
  ├─ B/L / Documents
  └─ Finance
      ├─ AR / Invoice / Receipt
      ├─ AP / Vendor Cost / Payment
      └─ Profitability
```

This follows the common forwarder pattern of one connected quote-to-invoice/job flow and minimizing re-keying between commercial, operations and finance. citeturn288206search0turn288206search1turn288206search8

## Module responsibilities

### Home / AI
Operational questions, quick KPIs, exceptions and shortcuts. It is not a duplicate data-entry dashboard.

### Customers
Customer master, tax identity, contact, credit terms.

### Quotations
Commercial scope only: customer, sales, route, service, charges and terms.

### Bookings
Carrier booking reference, routing, vessel, cargo/equipment and cut-offs. Keep the form small.

### Jobs
The single operational center. Execution data, cargo, milestones, B/L, revenue and cost all attach to Job.

### Documents
System-generated documents and document status/approval. Do not use it as a binary file warehouse by default.

### Finance
AR, AP, invoice/receipt, billing note, payment and Job profitability.

## Master data SSOT

- Customer
- Sales/User
- Liner
- Ports/Places
- Vendor
- Charge Master
- Equipment/Container Type

Transactions use master IDs as canonical values. Legacy display text is compatibility-only for old records.

## Freight rules

| Transport | Cargo | Primary Unit | Handling | CY | CFS |
|---|---|---|---|---|---|
| Sea | FCL | Container | CY | Yes | No |
| Sea | LCL | CBM | CFS | No | Yes |
| Air | Air | KG / Chargeable KG | CFS | No | Yes |
| Truck | FTL | Truck | CFS | No | Yes |
| Truck | LTL | CBM / KG | CFS | No | Yes |

Mother Vessel display: show Mother Vessel when populated, otherwise fall back to Vessel.

## Document lifecycle

```text
Draft → Pending Approval → Approved → Issued / Official PDF
```

Non-approved PDFs are draft-marked. Approval is tenant-safe and role-controlled.

## PDF set

Quotation, Booking Confirmation, Bill of Lading, Tax Invoice / Receipt, Billing Note, Credit Note, Debit Note, Job Profitability.

All PDFs use one visual language: company identity, document identity, customer/reference, main data, totals, remarks, signature area and page numbering.

## UI system

- One visual system across all pages
- Short logistics terminology
- Flat hierarchy
- Right-aligned document actions
- Responsive 13–15 inch laptop layout
- Minimal borders, subtle shadows, ample whitespace
- No tutorial paragraphs in normal workflows
- No REV / Revised / Revision wording in current UI

## Performance

- Keep data-entry drafts in session state
- Save only on explicit Save / Submit / Proceed
- Lazy-load PDFs
- Lazy-load expensive Job sections when practical
- Cache stable, tenant-scoped master data
- Avoid database reads on every widget change

## Production gates

A module is production-ready only when:

`Source → Schema → Manager → UI → PDF → Tests → CI`

Required verification:
1. Compile
2. Import
3. Unit tests
4. Workflow tests
5. SSOT tests
6. Tenant-isolation tests
7. PDF smoke tests
8. End-to-end quote → booking → job → document → finance test
9. Production PostgreSQL/Supabase migration verification
10. Manual UAT on deployed Streamlit app

## Migration rule

Production DDL changes are additive and belong in `database/migrations/*.sql`. Never replace the canonical schema file with a partial migration fragment.

## Completion test

A 5–10 person team must be able to create a quote, use it for booking, create/convert a Job, manage cargo and milestones, generate B/L and finance PDFs, record AR/AP and payments, review profitability, approve/issue documents, and retrieve all documents from the Job without re-entering core master data.
