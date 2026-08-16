# Smart Freight NTT — Document Form Contract v1

This contract maps database/master data to UI input and PDF output for the supplied NATTAYARAAT references.

## 1. Bill of Lading

### UI input groups
1. Parties
   - Shipper
   - Consignee
   - Notify Party
   - Delivery Agent / Delivery Application
2. Routing & Vessel
   - Pre-Carriage by (optional legacy/operational text)
   - Place of Receipt
   - Vessel
   - Voyage
   - POL
   - POD
   - Place of Delivery
   - Final Destination
3. Cargo
   - Marks & Numbers
   - Container No.
   - Seal No.
   - Container Type
   - Package Qty
   - Description of Goods
   - HS Code
   - Gross Weight KG
   - Measurement CBM
4. Freight & Issuance
   - Freight term: Prepaid / Collect
   - Freight Payable At
   - Place of Issue
   - Issue Date
   - Number of Originals
   - Authorized Signatory

### PDF hierarchy
Company header → BILL OF LADING / B/L No. → Parties → Routing/Vessel → Cargo Grid → Freight/Terms → Legal text → Issuance/Signature.

The normal company-issued B/L workflow does not expose HBL/MBL selectors.

## 2. Billing Note / Receipt-Tax Invoice

### UI input groups
1. Customer
   - Customer Master ID
   - Billing Name
   - Billing Address
   - Tax ID
   - Branch
2. Document
   - Document Type
   - Issue Date
   - Due Date
   - Reference / Job Ref.
   - Currency
3. Charges
   - Charge Code from Charge Master
   - Description from Charge Master
   - Basis / Unit from Charge Master
   - Quantity
   - Unit Rate
   - Tax Type
   - WHT Type
4. Remarks
5. Approval
   - Draft → Pending Approval → Approved

### PDF hierarchy
Company header/logo → Thai/English document title → Customer block + document details → Shipping/Delivery address (when applicable) → Item grid → Amount in words → Totals → Remarks → signatures.

## 3. SSOT rules

- Port selectors store `port_id` and display `CODE — Full Port Name`.
- Customer/party selectors store IDs; display names are resolved from Master Data.
- Invoice customer display snapshot is resolved by `customer_id` at write time.
- Charge lines use `charge_code` / `charge_id`, never free-text charge names for new records.
- PDF renderers consume validated payloads and do not query the database.

## 4. Business presentation rules

- Booking uses Carrier + Vessel + Voyage + Mother Vessel + Transshipment Port.
- Liner and Feeder are not user-facing in the Phase 30 booking workflow or new PDF outputs.
- B/L uses Vessel / Voyage as the printed ocean carriage identity; Mother Vessel remains an operational Booking/Shipment field.
- SEA FCL displays container information.
- SEA LCL displays CBM.
- AIR displays KG / Chargeable KG.
- Truck uses operational trip/package/weight fields.
