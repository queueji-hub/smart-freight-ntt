-- PHASE 30 P0/P1: SSOT, tenant consistency and approval workflow
ALTER TABLE IF EXISTS quotations ADD COLUMN IF NOT EXISTS tenant_id TEXT DEFAULT 'default';
ALTER TABLE IF EXISTS quotations ADD COLUMN IF NOT EXISTS approval_status TEXT DEFAULT 'Draft';
ALTER TABLE IF EXISTS bookings ADD COLUMN IF NOT EXISTS approval_status TEXT DEFAULT 'Draft';
ALTER TABLE IF EXISTS invoices ADD COLUMN IF NOT EXISTS tenant_id TEXT DEFAULT 'default';
ALTER TABLE IF EXISTS invoices ADD COLUMN IF NOT EXISTS approval_status TEXT DEFAULT 'Draft';
ALTER TABLE IF EXISTS bills_of_lading ADD COLUMN IF NOT EXISTS tenant_id TEXT DEFAULT 'default';
ALTER TABLE IF EXISTS bills_of_lading ADD COLUMN IF NOT EXISTS approval_status TEXT DEFAULT 'Draft';
ALTER TABLE IF EXISTS booking_revisions ADD COLUMN IF NOT EXISTS tenant_id TEXT DEFAULT 'default';
ALTER TABLE IF EXISTS shipment_milestones ADD COLUMN IF NOT EXISTS tenant_id TEXT DEFAULT 'default';

UPDATE quotations SET tenant_id=COALESCE(NULLIF(tenant_id,''),'default') WHERE tenant_id IS NULL OR tenant_id='';
UPDATE invoices SET tenant_id=COALESCE(NULLIF(tenant_id,''),'default') WHERE tenant_id IS NULL OR tenant_id='';
UPDATE bills_of_lading SET tenant_id=COALESCE(NULLIF(tenant_id,''),'default') WHERE tenant_id IS NULL OR tenant_id='';
UPDATE quotations SET approval_status=CASE WHEN UPPER(COALESCE(status,''))='APPROVED' THEN 'Approved' ELSE COALESCE(NULLIF(approval_status,''),'Draft') END;
UPDATE bookings SET approval_status=COALESCE(NULLIF(approval_status,''),'Draft') WHERE approval_status IS NULL OR approval_status='';
UPDATE invoices SET approval_status=COALESCE(NULLIF(approval_status,''),'Draft') WHERE approval_status IS NULL OR approval_status='';
UPDATE bills_of_lading SET approval_status=COALESCE(NULLIF(approval_status,''),'Draft') WHERE approval_status IS NULL OR approval_status='';

UPDATE quotations q SET customer_id=c.id FROM customers c WHERE q.customer_id IS NULL AND q.customer_name IS NOT NULL AND lower(trim(q.customer_name))=lower(trim(c.company_name));
UPDATE bookings b SET customer_id=c.id FROM customers c WHERE b.customer_id IS NULL AND b.customer_name IS NOT NULL AND lower(trim(b.customer_name))=lower(trim(c.company_name));
UPDATE shipments s SET customer_id=c.id FROM customers c WHERE s.customer_id IS NULL AND s.customer_name IS NOT NULL AND lower(trim(s.customer_name))=lower(trim(c.company_name));
UPDATE invoices i SET customer_id=c.id FROM customers c WHERE i.customer_id IS NULL AND i.customer_name IS NOT NULL AND lower(trim(i.customer_name))=lower(trim(c.company_name));

CREATE INDEX IF NOT EXISTS idx_quotations_tenant_no ON quotations(tenant_id,quotation_no);
CREATE INDEX IF NOT EXISTS idx_quotations_customer ON quotations(customer_id);
CREATE INDEX IF NOT EXISTS idx_bookings_tenant_customer ON bookings(tenant_id,customer_id);
CREATE INDEX IF NOT EXISTS idx_invoices_tenant_customer ON invoices(tenant_id,customer_id);
CREATE INDEX IF NOT EXISTS idx_bol_tenant_job ON bills_of_lading(tenant_id,job_no);

-- Canonical Booking transport vocabulary: Carrier, Mother Vessel, Voyage, Transshipment Port.
-- Legacy feeder/liner/vessel columns remain only for compatibility.
