# Reference Document Design - NATTAYARAAT

## Source references reviewed

- Supplied draft Bill of Lading: `NATTA-LCHNAH2608003`.
- Supplied invoice reference: `IV2607-0006_REDLINE.pdf` (the uploaded file is image-only to the text extractor, so visual review is required before copying any exact field wording).
- Supplied receipt/tax-invoice reference: `RC2607-0008. (2).pdf` (image-only to the text extractor; visual review is required before copying any exact field wording).

## Bill of Lading data model requirements

The supplied B/L contains the following business fields and layout concepts: shipper, consignee, notify party, place of receipt, ocean vessel/voyage, port of loading, port of discharge, place of delivery, final destination, marks and numbers, container/seal numbers, description of goods, packages, measurement CBM, gross/net weight, freight prepaid/collect, place/date of issue, original count, HS code and CY-CY statement. These are supported by the parsed reference B/L. fileciteturn132file0L8-L18 fileciteturn132file0L20-L40 fileciteturn132file0L53-L78

## Invoice / financial document requirements

The existing financial engine already supports tax invoice, receipt, billing note, credit note, debit note and SOA document types, with customer details, document number/date, reference/job, currency, line items, VAT/WHT and totals. The new receipt template should complement that engine rather than create a second accounting source of truth. fileciteturn134file0L1-L2

## Receipt / tax invoice visual direction

Use the supplied receipt reference as the visual target for the receipt/tax-invoice family. The implementation uses a restrained green financial-document palette, clear original/copy distinction, compact customer/document information, line-item table, VAT/WHT totals, amount in words, payer/receiver/authorized signature areas, and a clean footer.

## Architectural rule

Documents must remain downstream of Job/Shipment and financial managers. PDF generators consume prepared dictionaries and must not become a second business database. Existing invoice numbering remains centralized through `generate_document_number()`. fileciteturn138file0L2-L2
