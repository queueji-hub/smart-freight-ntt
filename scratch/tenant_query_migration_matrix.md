# TENANT QUERY MIGRATION MATRIX

| File | Function | SQL Operation | Table | Current WHERE | Tenant Requirement | Current Params | Required Params | Migration Status |
|---|---|---|---|---|---|---|---|---|
| `managers/booking_manager.py` | `get_booking_by_id` | SELECT | `bookings` | `WHERE id = %s` | YES | `(id,)` | `(id, tenant_id)` | COMPLETED |
| `managers/booking_manager.py` | `list_bookings` | SELECT | `bookings` | None | YES | `()` | `(tenant_id,)` | COMPLETED |
| `managers/booking_manager.py` | `add_booking` | INSERT | `bookings` | N/A | YES | `(..., )` | `(..., tenant_id)` | COMPLETED |
| `managers/shipment_manager.py` | `get_shipment` | SELECT | `shipments` | `WHERE id = %s` | YES | `(id,)` | `(id, tenant_id)` | COMPLETED |
| `managers/shipment_manager.py` | `delete_shipment` | DELETE | `shipments` | `WHERE id = %s` | YES | `(id,)` | `(id, tenant_id)` | COMPLETED |
| `managers/invoice_manager.py` | `get_invoice` | SELECT | `invoices` | `WHERE id = %s` | YES | `(id,)` | `(id, tenant_id)` | COMPLETED |
| `managers/invoice_manager.py` | `list_invoices` | SELECT | `invoices` | None | YES | `()` | `(tenant_id,)` | COMPLETED |
| `managers/invoice_manager.py` | `create_invoice` | INSERT | `invoices` | N/A | YES | `(..., )` | `(..., tenant_id)` | COMPLETED |
| `managers/invoice_manager.py` | `record_payment` | SELECT FOR UPDATE | `invoices` | `WHERE doc_no = %s` | YES | `(doc_no,)` | `(doc_no, tenant_id)` | COMPLETED |
| `managers/invoice_manager.py` | `record_payment` | UPDATE | `invoices` | `WHERE id = %s` | YES | `(..., inv_id)` | `(..., inv_id, tenant_id)` | COMPLETED |
| `managers/invoice_manager.py` | `record_payment` | INSERT | `invoice_payments` | N/A | YES | `(..., )` | `(..., tenant_id)` | COMPLETED |
| `managers/invoice_manager.py` | `get_outstanding_summary` | SELECT | `invoices` | `WHERE payment_status != 'CANCELLED'` | YES | `()` | `(tenant_id,)` | COMPLETED |

*Note: This is a representative sample of the 50+ queries across the platform that must be manually verified and migrated according to the One-Manager-At-A-Time protocol.*
